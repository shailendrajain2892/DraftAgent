# DraftAgent: shared overview and contracts

Everyone reads this file first. The four component specs (`01` to `04`) build on it.
If a contract here needs to change, edit this file in a PR and post in the WhatsApp channel.

## Owners

| Component | Spec | Owner |
| --- | --- | --- |
| Repo scaffold and web UI | `01_web_ui_spec.md` | Antim Jain |
| FastAPI, Gmail MCP tools, CI/CD, API contracts | `02_backend_tools_cicd_spec.md` | Shailendra Jain |
| LangGraph agent | `03_langgraph_agent_spec.md` | Yashshree Nigudkar |
| Style store (RAG) | `04_style_store_rag_spec.md` | TBD (fourth team member) |

Diagrams (Lucid):
- Architecture v3: https://lucid.app/lucidchart/0756efa9-e9d5-43f8-9be0-d14c3a8b0400/edit
- Sequence v3.1: https://lucid.app/lucidchart/a7abd963-d0dc-4fe2-83ce-92c59f611931/edit

## What we are building

A standalone web app. The user connects Gmail with Google OAuth and sees a list of recent threads.
They pick one and click **Draft reply**. A LangGraph agent reads the thread and related threads,
looks up how the user usually writes (style store), asks the user for optional extra context,
then an OpenAI LLM writes the reply. The reply is saved to Gmail as a draft and shown in the UI.
It is never sent automatically.

## Decisions (from the meeting, plus follow-ups)

1. Standalone web UI for the MVP. The Gmail Chrome extension is dropped (10-day window).
2. All Gmail access goes through the Gmail MCP tools layer only. No direct Gmail calls from the graph.
3. Tools gather data. The OpenAI LLM composes the reply text. The `create_draft` tool only saves
   that text to Gmail as a draft.
4. The agent pauses with `interrupt()` to ask the user for extra context. State is kept in the
   LangGraph checkpointer (in-memory).
5. On first connect the backend seeds the style store from the last **30 days** of email
   (changed from the 7 to 14 days written in the MOM).
6. The style store is saved to files on disk so it survives restarts. No database.
7. Deploy to AWS free tier via CI/CD. The repo must be cloneable so each member can deploy to
   their own AWS account.
8. Shared GitHub repo. Feature branches and PRs into `main`.
9. The eval framework waits until the end-to-end flow works.

## Repo layout (Antim scaffolds this)

```text
draftagent/
  backend/
    app/main.py            # FastAPI app, routers, CORS, session middleware
    app/api/               # auth.py, threads.py, style.py, runs.py   (Shailendra)
    app/inbox/service.py   # list and preview for the picker           (Shailendra)
    app/tools/             # gmail_tools.py, mcp_server.py             (Shailendra)
    app/agent/             # state.py, nodes.py, graph.py, prompts.py  (Yashshree)
    app/style_store/       # store.py, seed.py, clean.py, summary.py   (style store owner)
    tests/
  web/                     # web UI                                    (Antim)
  infra/                   # AWS infrastructure as code               (Shailendra)
  .github/workflows/       # ci.yml, deploy.yml                        (Shailendra)
  docs/specs/              # these files
  .env.example
```

Branches: `feat/web-ui`, `feat/backend-api`, `feat/tools`, `feat/agent`, `feat/style-store`,
`feat/cicd`. Open small PRs into `main`. At least one other member reviews each PR.

## Shared types

```python
# ReplyPair: one earlier email the user answered, plus the reply they sent
class ReplyPair(TypedDict):
    id: str                 # "<thread_id>:<reply_message_id>"
    inbound: str            # cleaned text of the message being answered
    reply: str              # cleaned text of the user's reply
    recipient_email: str    # who the user replied to
    recipient_domain: str
    subject: str
    date: str               # ISO 8601
    reply_words: int

# Message and Thread: cleaned text only, no HTML
class Message(TypedDict):
    id: str
    from_: str              # "Name <email>"; the JSON key is "from"
    to: list[str]
    date: str               # ISO 8601
    body_text: str          # quoted history and signatures removed

class Thread(TypedDict):
    id: str
    subject: str
    messages: list[Message] # oldest first
```

## Contract A: Web UI to FastAPI (REST, JSON)

Auth is a session cookie named `draftagent_session` (HttpOnly, SameSite=Lax).
The UI never sees Google tokens. If the UI is served from a different origin in dev,
send `credentials: "include"` and set `FRONTEND_ORIGIN` on the backend for CORS.
Preferred: FastAPI serves the built UI as static files, so there is no CORS at all.

| Method and path | Purpose | Success response |
| --- | --- | --- |
| `GET /auth/google/login` | Start OAuth | 302 to Google consent |
| `GET /auth/google/callback?code&state` | Finish OAuth, set cookie, start seed job | 302 to `/` |
| `GET /auth/me` | Who is logged in | `{"authenticated": true, "email": "a@b.com"}` |
| `POST /auth/logout` | Clear session | `{"ok": true}` |
| `GET /threads?page_token=&q=` | Inbox list, one page | see below |
| `GET /threads/{id}` | Preview one thread | see below |
| `GET /style/status` | Seed progress | see below |
| `POST /runs` | Start a draft run, runs until the question | see below |
| `POST /runs/{run_id}/resume` | Send the answer, finish the draft | see below |

`GET /threads` returns 25 threads per page. Default query is `in:inbox newer_than:30d`.
`q` is optional and uses Gmail search syntax.

```json
{
  "threads": [
    {
      "id": "18c2f0a1b2c3d4e5",
      "subject": "Q3 vendor quote",
      "from_name": "Priya Nair",
      "from_email": "priya@acme.com",
      "snippet": "Can you confirm the revised numbers by Friday?",
      "message_count": 3,
      "last_message_at": "2026-09-18T10:42:00Z"
    }
  ],
  "next_page_token": null
}
```

`GET /threads/{id}` returns a `Thread` (see shared types). The sender key is `from` in JSON:

```json
{
  "id": "18c2f0a1b2c3d4e5",
  "subject": "Q3 vendor quote",
  "messages": [
    {
      "id": "18c2f0a1b2c3d4e6",
      "from": "Priya Nair <priya@acme.com>",
      "to": ["me@example.com"],
      "date": "2026-09-18T10:42:00Z",
      "body_text": "Thanks for the call earlier. Can you confirm the revised numbers by Friday?"
    }
  ]
}
```

`GET /style/status`:

```json
{ "state": "ready", "pairs_count": 142, "window_days": 30, "updated_at": "2026-09-20T09:00:00Z", "error": null }
```

`state` is one of `not_started`, `running`, `ready`, `failed`. The UI polls every 3 seconds while `running`.
The UI can still start a draft while `running`. The agent falls back to a default style.

`POST /runs` with body `{ "gmail_thread_id": "18c2f0a1b2c3d4e5" }`. This call can take 10 to 30 seconds.
There is no streaming in the MVP, so the UI shows a spinner.

```json
{ "run_id": "me@example.com:18c2f0a1b2c3d4e5:a1b2c3d4", "status": "awaiting_input",
  "question": "This asks for revised numbers. Do you want to include a price or a date?" }
```

The agent always asks. If it has nothing specific, the question is a generic
"Anything to add before I draft this?". The user can skip.

`POST /runs/{run_id}/resume` with body `{ "answer": "Offer 10% off, deliver by 30 Sep" }`.
`answer` is `null` when the user skips.

```json
{ "run_id": "me@example.com:18c2f0a1b2c3d4e5:a1b2c3d4", "status": "completed",
  "draft": { "text": "Hi Priya, ...", "gmail_draft_id": "r-8812345" } }
```

Errors always use this shape, with the matching HTTP status:

```json
{ "error": { "code": "AUTH_EXPIRED", "message": "Please sign in with Google again." } }
```

| Code | HTTP | UI behaviour |
| --- | --- | --- |
| `UNAUTHENTICATED` | 401 | Show the Connect Gmail screen |
| `AUTH_EXPIRED` | 401 | Same, with a "session expired" note |
| `NOT_FOUND` | 404 | Thread or run missing, go back to the list |
| `RUN_STATE_CONFLICT` | 409 | Run is not waiting for an answer, restart it |
| `GMAIL_RATE_LIMITED` | 429 | Show "try again in a moment" |
| `UPSTREAM_ERROR` | 502 | Gmail or OpenAI failed, offer Retry |
| `RUN_TIMEOUT` | 504 | Offer Retry |

## Contract B: LangGraph agent to Gmail MCP tools

Tool functions live in `backend/app/tools/gmail_tools.py` and are exposed through an MCP server.
Every tool takes `user_id`. The agent's tool wrapper injects `user_id` and hides it from the
LLM's tool schema. The LLM never chooses a user.

| Tool | Arguments | Returns | Visible to LLM |
| --- | --- | --- | --- |
| `get_thread` | `user_id, thread_id, max_messages=10` | `Thread` | yes |
| `search_related` | `user_id, query, exclude_thread_id, max_results=5` | list of `{thread_id, subject, date, participants, snippet}` (snippet at most 150 chars) | yes |
| `get_style_examples` | `user_id, thread_id, k=4` | `{summary, examples: [{inbound, reply}], mode}` where `mode` is `retrieval`, `summary_only` or `default` | yes |
| `create_draft` | `user_id, thread_id, body_text` | `{gmail_draft_id}` | no, called by the `save_draft` node |
| `list_threads` | `user_id, page_token, max_results, query` | same as `GET /threads` | no, Inbox service only |
| `fetch_recent_reply_pairs` | `user_id, days=30, max_pairs=300` | list of `ReplyPair` | no, seed job only |

Limits that live inside the tools (not the prompt): 10 messages per thread, 2,000 characters per
message body, 5 related threads, a hard cap on whatever `max_results` the LLM asks for.
Tool errors come back as readable text for the LLM, except `AuthExpiredError`, which fails the run.

## Contract C: tools and seed job to style store

```python
class StyleStore:
    def __init__(self, user_id: str, base_dir: str): ...
    def is_ready(self) -> bool: ...
    def pair_count(self) -> int: ...
    def seed(self, pairs: list[ReplyPair]) -> None: ...   # build index and summary, save to disk
    def retrieve(self, inbound_text: str, recipient_email: str, k: int = 4) -> list[ReplyPair]: ...
    def summary(self) -> str: ...                          # global style summary text

def clean_body(raw: str, is_html: bool = False) -> str: ...  # strip quoted history, signatures, forwards
```

`get_style_examples` calls `retrieve` and `summary`. If `pair_count() < COLD_START_MIN_PAIRS` it
returns the summary only (`mode = "summary_only"`). If there is nothing at all it returns a neutral
default summary (`mode = "default"`).

## Contract D: FastAPI to LangGraph agent (Python)

Everything is async because MCP client tools are async.

```python
# Build once at app startup
def build_graph(tools: "ToolClient", llm, checkpointer) -> "CompiledGraph": ...

# POST /runs calls this: runs gather, stops at interrupt, returns the question
async def start_run(graph, user_id: str, gmail_thread_id: str) -> dict:
    ...  # {"run_id": str, "question": str}

# POST /runs/{id}/resume calls this: continues to draft and save
async def resume_run(graph, run_id: str, user_id: str, answer: str | None) -> dict:
    ...  # {"text": str, "gmail_draft_id": str}
```

`run_id` format: `{user_id}:{gmail_thread_id}:{uuid8}`. It is also LangGraph's `thread_id`.
The backend must reject a `run_id` that does not start with the caller's `user_id`.

## Environment variables

```text
GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, OAUTH_REDIRECT_URI
SESSION_SECRET             # signs the session cookie
FRONTEND_ORIGIN            # only needed if the UI is served separately
OPENAI_API_KEY, OPENAI_CHAT_MODEL, OPENAI_EMBED_MODEL
STYLE_STORE_DIR            # folder for style store files, must be on a persistent volume in AWS
SEED_DAYS=30, SEED_MAX_PAIRS=300
COLD_START_MIN_PAIRS=30
STYLE_MODE=retrieval       # or summary_only, used later for the A vs B comparison
MAX_AGENT_STEPS=6
```

## Working without each other (mocks)

Nobody should wait for someone else's code. Each spec says what to mock:
- UI works against fixture JSON that matches Contract A.
- Agent works against a fake `ToolClient` that returns fixture threads and style examples.
- Tools and API work against a mocked Gmail client and a stub `StyleStore`.
- Style store works with a synthetic `ReplyPair` file.

## Milestones (proposed, adjust at Wednesday's sync)

Project submission is due Sun 27 Sep 2026, so end-to-end has to work before the last weekend.

| When | Goal |
| --- | --- |
| Mon 21 to Tue 22 Sep | Scaffold pushed. Contracts agreed. Each owner builds against mocks. |
| Wed 23 Sep (sync) | Each component runs on its own with mocks. Review progress. |
| Thu 24 Sep | Swap mocks for real pieces: UI to API, API to tools, agent to tools, tools to style store. |
| Fri 25 Sep (sync) | First full end-to-end run locally. |
| Sat 26 Sep | Deploy to AWS, evals, demo video, README failure analysis. |
| Sun 27 Sep | Submit. |

## Open questions for Wednesday

1. **MCP transport.** In-process, stdio subprocess, or localhost HTTP? Does the Inbox service call
   the MCP client or the same Python functions directly?
2. **Checkpointer.** In-memory (as in the MOM) loses paused runs on restart. SQLite would keep them.
3. **Style store volume on AWS.** Which persistent volume holds `STYLE_STORE_DIR` so redeploys do not wipe it?
4. **Style store owner.** Who is the fourth member?
5. **Deploy target.** Single EC2 instance with Docker, or something else?
6. **Holdout for evals.** Keep 20% of pairs out of the index now, or decide later?

## Change process

Contracts change only by PR to this file. Announce in WhatsApp. The owner of the affected
component confirms before merge.
