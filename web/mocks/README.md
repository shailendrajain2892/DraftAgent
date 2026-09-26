# mocks

Fixture JSON that matches Contract A in `docs/specs/00_shared_overview_and_contracts.md`.
Used when `VITE_USE_MOCKS=true`; `src/api/mockClient.js` serves these files.

| File | What it covers |
| --- | --- |
| `auth_me.json`, `auth_me_unauthenticated.json` | `GET /auth/me`, both states |
| `threads_page1.json` | 25 threads, `next_page_token` set |
| `threads_page2.json` | 11 threads, `next_page_token: null` (Load more path) |
| `threads_empty.json` | Empty inbox state |
| `thread_details.json` | `GET /threads/{id}` for two hand-written threads; other ids are synthesised from the list row |
| `style_status.json` | All four `GET /style/status` states |
| `runs.json` | Questions and draft bodies for `POST /runs` and `/resume` |
| `errors.json` | One example per error code in Contract A |

## Scenarios

Pick one with `VITE_MOCK_SCENARIO`, or at runtime with `?mock=<name>` (a scenario bar shows in
the corner while mocks are on).

| Scenario | Behaviour |
| --- | --- |
| `default` | Happy path. Two pages, style seed goes `running` -> `ready` after ~9s |
| `empty` | Empty inbox |
| `unauthenticated` | `GET /auth/me` says not signed in |
| `auth-expired` | `GET /threads` returns 401 `AUTH_EXPIRED` |
| `upstream-error` | `POST /runs` returns 502 `UPSTREAM_ERROR` |
| `slow-run` | `POST /runs` takes 5 seconds |
| `style-failed` | Style seed ends in `failed` |
