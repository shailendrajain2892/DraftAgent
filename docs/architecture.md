# DraftAgent — architecture

This document describes the system as built. The authoritative contracts live in
[`specs/00_shared_overview_and_contracts.md`](specs/00_shared_overview_and_contracts.md);
per-component detail is in `specs/01`–`04`.

Interactive architecture diagram (Lucid, icon-based):
https://lucid.app/lucidchart/eab9c7be-5262-4fb7-87fb-cd6c1b5a605b/view

## Components

| Component | Where | Responsibility |
| --- | --- | --- |
| Web UI | `web/` | React + Vite client of Contract A. Served by FastAPI in prod (same origin). |
| FastAPI backend | `backend/app/api`, `main.py` | OAuth + session, inbox, style status, run endpoints, error mapping. |
| Gmail tools | `backend/app/tools`, `backend/app/gmail` | The only code that calls Gmail. Enforces limits, retries, token refresh, per-user concurrency. |
| LangGraph agent | `backend/app/agent` | Reads context, asks one question, drafts with OpenAI, saves the draft. |
| Style store | `backend/app/style_store` | Disk-backed RAG of the user's past replies (Contract C). |
| Seed job | `backend/app/seed` | On first connect, indexes the last 30 days of sent replies. |

## Agent graph (LangGraph)

```mermaid
stateDiagram-v2
    [*] --> gather_agent
    gather_agent --> tools: model requested a tool
    tools --> gather_agent
    gather_agent --> ask_user: no tool call (has a question)
    ask_user --> ask_user: interrupt() — wait for the user's answer
    ask_user --> draft: answer (or skip) received
    draft --> save_draft
    save_draft --> [*]
```

- **gather_agent** — bound to the read tools; loops with **tools** until it has enough
  context, capped by `MAX_AGENT_STEPS`.
- **ask_user** — always asks exactly one question via `interrupt()`; the run pauses here
  and the checkpointer persists state.
- **draft** — the unbound LLM composes the reply (never calls tools).
- **save_draft** — calls `create_draft`; auth/quota errors escape as 401/429, others → 502.

`run_id = "{user_id}:{gmail_thread_id}:{nonce}"` and is also LangGraph's `thread_id`.

### Graph detail — nodes, tools, LLM, checkpointer

```mermaid
flowchart TD
    STARTN(["START"]) --> GA

    subgraph compiled["Compiled graph (DraftState + SQLite checkpointer)"]
        GA["gather_agent<br/>LLM bound to read tools"]
        TN["tools (ToolNode)<br/>get_thread / search_related / get_style_examples"]
        AU["ask_user<br/>interrupt(question)"]
        DR["draft<br/>unbound LLM composes the reply"]
        SD["save_draft<br/>create_draft"]

        GA -->|"tool_calls present"| TN
        TN -->|"ToolMessages"| GA
        GA -->|"no tool_calls / cap hit"| AU
        AU --> DR
        DR --> SD
    end

    AU -. "interrupt: pause + persist" .-> PAUSE{{"paused — awaiting answer"}}
    PAUSE -. "resume(answer)" .-> DR
    SD --> FIN(["END: text + gmail_draft_id"])

    GA -. "ainvoke" .-> OAI[["OpenAI"]]
    DR -. "ainvoke" .-> OAI
    TN -. "Gmail tools layer" .-> GM[["Gmail API"]]
    SD -. "Gmail tools layer" .-> GM
    CP[("SQLite checkpointer<br/>state saved each step")] -. "persists" .- compiled

    classDef ext fill:#eee,stroke:#999,color:#333;
    class OAI,GM ext;
```

State (`DraftState`): `messages`, `gmail_thread_id`, `user_context` (the answer; `None` =
skipped), `draft`, `gmail_draft_id`, `gather_steps`. Tool wrappers inject the trusted
`user_id`/`thread_id` from run config + state, so the model never supplies identity.
`start_run` drives the graph to the `interrupt`; `resume_run` supplies the answer and runs
to `END`.

## Request flow (Contract D)

`POST /runs` → `start_run` runs the graph to the interrupt and returns the question.
`POST /runs/{run_id}/resume` → `resume_run` supplies the answer, runs to completion, and
returns `{text, gmail_draft_id}`. A `run_id` that does not start with the caller's
`user_id` is rejected as `NOT_FOUND`.

## Error mapping (Contract A)

Domain errors in `backend/app/errors.py` carry a Contract A code + HTTP status. The agent
error names alias these same classes, so a real Gmail failure maps consistently:

| Error | HTTP | Code |
| --- | --- | --- |
| `AuthExpiredError` | 401 | `AUTH_EXPIRED` |
| `NotFound` | 404 | `NOT_FOUND` |
| `RunStateConflict` | 409 | `RUN_STATE_CONFLICT` |
| `GmailRateLimited` | 429 | `GMAIL_RATE_LIMITED` |
| `UpstreamError` (+ `SaveDraftError`, `DraftGenerationError`) | 502 | `UPSTREAM_ERROR` |

## Deployment topology

```mermaid
flowchart LR
    DEV["push to main"] --> CI

    subgraph GH["GitHub Actions"]
        CI["ci.yml<br/>ruff · pytest · web build"]
        CD["deploy.yml<br/>flyctl deploy (remote build)"]
    end

    CI --> CD
    CD --> IMG["Docker image<br/>UI build → FastAPI serves web/dist"]
    IMG --> FLY

    subgraph FLY["Fly.io — app: draftagent (sin)"]
        M["1 machine · 1 worker"]
        V[("/data volume<br/>style store + checkpoints.sqlite")]
        M --- V
    end
```

- Single machine / single worker on purpose — sessions and Google tokens live in process
  memory (lost on restart; users re-auth). No database.
- The `/data` volume persists the style store and the SQLite checkpointer across restarts
  and redeploys, so paused runs survive.
- Secrets (Google, OpenAI, `SESSION_SECRET`, `OAUTH_REDIRECT_URI`) are set via
  `fly secrets`, never committed. `FLY_API_TOKEN` (a Fly deploy token) is a GitHub secret.

## Notable design decisions

- **Gmail only through the tools layer** — the agent/LLM never call Gmail directly; limits
  (10 messages/thread, 2000 chars/body, 5 related) live in code, not the prompt.
- **Prompt-injection aware** — thread and related-thread content are treated as untrusted
  data; the model is told to ignore instructions inside them.
- **Same-origin UI** — FastAPI serves the built UI, so the `draftagent_session` cookie
  needs no CORS and Google tokens never reach the browser.
