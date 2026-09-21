# Spec 02: FastAPI backend, Gmail MCP tools, CI/CD

Owner: Shailendra Jain. Contracts A, B and D in `00_shared_overview_and_contracts.md` are yours to keep accurate.

## Your scope

1. FastAPI app: Google OAuth, session cookie, inbox endpoints, style status, run endpoints.
2. Inbox service for the picker (list and preview).
3. Gmail MCP tools layer (the only code that talks to Gmail).
4. Seed job that fills the style store after first connect.
5. CI/CD to the AWS free tier, cloneable to other AWS accounts.
6. Keep the API contract and the specs current.

## Modules

```text
backend/app/
  main.py                 # app factory, session middleware, static UI mount, routers
  api/auth.py             # /auth/google/login, /callback, /me, /logout
  api/threads.py          # GET /threads, GET /threads/{id}
  api/style.py            # GET /style/status
  api/runs.py             # POST /runs, POST /runs/{run_id}/resume
  inbox/service.py        # list and preview using the tools layer
  gmail/client.py         # builds a Gmail service from stored credentials, retry and refresh
  tools/gmail_tools.py    # the tool functions from Contract B
  tools/mcp_server.py     # exposes the tools over MCP
  seed/job.py             # background seed job and in-memory status per user
```

## OAuth and sessions

- Library: `google-auth-oauthlib` for the flow, Starlette `SessionMiddleware` (or signed cookie) for the session.
- Scopes: `gmail.readonly` and `gmail.compose`. Nothing wider.
- Store tokens server-side in memory, keyed by `user_id` (the user's email). The cookie holds only a session id.
- Cookie: `draftagent_session`, HttpOnly, SameSite=Lax, `Secure` in AWS.
- Google Cloud setup: keep the OAuth consent screen in **Testing** mode and add every team member and
  demo user as a test user. Note that in Testing mode Google expires refresh tokens after about
  7 days, and unverified apps show a warning screen. Both are fine for a capstone.
- Tokens are lost when the process restarts, so users sign in again. That is acceptable for the MVP.
- After the callback succeeds, start the seed job in a FastAPI background task, then redirect to `/`.

## Gmail client rules

- Refresh access tokens automatically. If refresh fails (`invalid_grant`), raise `AuthExpiredError`,
  which becomes `AUTH_EXPIRED` (401).
- Retry `429` and `5xx` up to 3 times with exponential backoff. If it still fails, raise
  `GmailRateLimited` (429) or `UpstreamError` (502).
- Limit concurrent Gmail calls to about 5 per user.
- Never log email bodies or tokens.

## Tools layer (Contract B)

- **list_threads:** `threads.list` with the query, then `threads.get` with `format=metadata`
  (headers `From`, `Subject`, `Date`) for each ID on the page. Fetch metadata concurrently.
- **get_thread:** `threads.get` with `format=full`. Parse MIME: prefer `text/plain`, else convert HTML
  to text. Run `clean_body` from the style store package (use a simple stub until it lands).
  Return the newest 10 messages, oldest first, 2,000 characters each.
- **search_related:** `threads.list` with the LLM's query, drop `exclude_thread_id`, then metadata
  and snippet only. Hard cap 5 results.
- **get_style_examples:** get the latest inbound message from the thread (cache the fetch with
  `get_thread`), call `StyleStore.retrieve` and `summary`, apply the cold-start rules in Contract C.
- **fetch_recent_reply_pairs:** search `newer_than:{days}d`, find messages the user sent that reply
  to someone else's message, and return up to `max_pairs`, newest first, as `ReplyPair` records.
- **create_draft:** build a MIME reply: `To` is the sender of the latest inbound message, subject
  `Re: ...`, `In-Reply-To` and `References` from that message, `threadId` set. Call `drafts.create`.
  Return the draft id.

Expose the tools over MCP with the Python MCP SDK. The agent connects through
`langchain-mcp-adapters`. Bind the MCP server to localhost only. Open question 1 in the overview
decides the transport, so keep the tool functions plain Python and make the MCP layer a thin wrapper.

## API layer rules

- `user_id` always comes from the session, never from the request body.
- `POST /runs` and `/resume` call `start_run` and `resume_run` from Contract D.
- Reject a `run_id` that does not start with the caller's `user_id`.
- Map exceptions to the error codes in Contract A. Every error uses the same JSON shape.
- `/style/status` reads the in-memory seed status. Seed job states: `not_started`, `running`, `ready`, `failed`.

## Seed job

Runs once after first connect, in the background:
1. `fetch_recent_reply_pairs(days=SEED_DAYS, max_pairs=SEED_MAX_PAIRS)`.
2. `StyleStore.seed(pairs)`.
3. Set status to `ready` (or `failed` with the error message).

If the style store folder already exists for the user, skip seeding and set `ready`.

## CI/CD

- `ci.yml` on every PR: lint (ruff), tests (pytest), UI build.
- `deploy.yml` on merge to `main`: build a Docker image, deploy to AWS free tier.
- Proposed target (confirm on Wednesday): one small EC2 instance running Docker, with a mounted
  volume for `STYLE_STORE_DIR` so redeploys do not wipe the style store. Check current AWS
  free-tier terms before choosing sizes.
- Secrets in GitHub Actions secrets or AWS Parameter Store: never in the repo.
- Cloneable: everything account-specific (region, account, instance, domain) lives in repo
  variables and infrastructure code under `infra/`, and the README has "Deploy to your own AWS
  account" steps.

## Working before other parts exist

- Mock the Gmail client with fixtures. Use a stub `StyleStore` that returns canned examples.
- Contract tests: use FastAPI `TestClient` and assert the response JSON matches Contract A exactly.
- For the agent endpoints, stub `start_run` and `resume_run` until Yashshree's graph is ready.

## Definition of done

- [ ] Login, callback, `/auth/me` and logout work with a real Google account.
- [ ] `GET /threads`, `GET /threads/{id}`, `GET /style/status` match Contract A.
- [ ] All six tools in Contract B work against a real mailbox, with the limits enforced.
- [ ] Seed job runs after connect and reports status.
- [ ] `POST /runs` and `/resume` work end to end with the real agent.
- [ ] CI runs on PRs. Merge to `main` deploys to AWS.
- [ ] Another team member can deploy to their own account using only the README.
- [ ] Unit and contract tests pass. No secrets or email bodies in logs.
