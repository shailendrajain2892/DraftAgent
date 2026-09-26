# DraftAgent backend

FastAPI backend: Google OAuth, Gmail MCP tools, style-store seed job, and draft-run
endpoints. Implements Contracts A, B and D from `../docs/specs/00_shared_overview_and_contracts.md`.

## Layout

```text
app/
  main.py              # app factory: session, CORS, routers, error handlers, static UI
  config.py            # settings from env (.env)
  types.py             # shared TypedDicts (Message, Thread, ReplyPair)
  errors.py            # domain errors -> Contract A codes/HTTP
  deps.py              # current_user_id from session
  session_store.py     # in-memory session id -> user, user -> Google credentials
  api/                 # auth.py, threads.py, style.py, runs.py
  inbox/service.py     # list + preview for the picker
  gmail/client.py      # service builder, token refresh, retry/backoff, concurrency limit
  tools/gmail_tools.py # the 6 Contract B tools (plain async Python)
  tools/mcp_server.py  # thin MCP wrapper (optional `agent` extra)
  style_store/         # STUB (spec 04 owns the real RAG): clean_body + disk StyleStore
  seed/job.py          # background seed job + in-memory status
  agent/stub.py        # STUB for Contract D (spec 03 owns the real LangGraph agent)
tests/                 # contract tests (FastAPI TestClient, no real Gmail)
```

`agent/stub.py` and `style_store/` are placeholders so the backend runs end-to-end today.
Replace them with Yashshree's graph and the style-store owner's RAG when they land — the
import sites are noted in `main.py` and `style_store/__init__.py`.

## Run locally

```bash
cd backend
uv venv --python 3.11
uv pip install -e ".[dev]"          # add ",agent" for LangGraph/MCP/OpenAI extras
cp .env.example .env                # then fill in Google + OpenAI creds
uv run uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000/auth/google/login to sign in.

### Google Cloud setup (one-time)

1. Create an OAuth client (type **Web application**) in Google Cloud Console.
2. Add `http://localhost:8000/auth/google/callback` as an authorized redirect URI.
3. OAuth consent screen: keep it in **Testing** mode; add every teammate/demo account as a
   test user. (Testing mode expires refresh tokens after ~7 days and shows an unverified
   warning — both fine for the capstone.)
4. Scopes: `gmail.readonly`, `gmail.compose`, plus `openid`/`userinfo.email` for identity.

## Test & lint

```bash
uv run pytest -q
uv run ruff check .
```

## Manual end-to-end (real Gmail)

1. Sign in via `/auth/google/login`. The callback starts the seed job in the background.
2. `GET /style/status` — watch it go `running` -> `ready`.
3. `GET /threads` — list your inbox; pick an `id`.
4. `POST /runs` with `{"gmail_thread_id": "<id>"}` — returns a `run_id` + question.
5. `POST /runs/{run_id}/resume` with `{"answer": "..."}` (or `null`) — composes the reply
   (OpenAI if `OPENAI_API_KEY` is set, else a stub body) and **saves it as a Gmail draft**.
   Nothing is ever sent.

## Notes

- `user_id` (your email) always comes from the session cookie, never the request body.
- Tokens live server-side in memory only; a restart means signing in again (MVP-acceptable).
- Limits (10 msgs/thread, 2000 chars/body, 5 related, per-user concurrency 5, 3 retries)
  live in the tools/client, not the prompt.
