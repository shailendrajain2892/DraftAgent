# web

DraftAgent web UI. Owner: Antim Jain (`docs/specs/01_web_ui_spec.md`).
React + Vite, plain JSX, no UI framework. Talks to Contract A in
`docs/specs/00_shared_overview_and_contracts.md`.

## Run with mocks (no backend needed)

```bash
cd web
npm install
npm run dev
```

Open http://localhost:5173. `.env.development` ships with `VITE_USE_MOCKS=true`, so every call is
served from the fixture JSON in `web/mocks/`.

A **mocks** pill in the bottom-right corner switches scenario, or add `?mock=<name>` to the URL:

| Scenario | What it exercises |
| --- | --- |
| `default` | Happy path: 25 threads, Load more, question, draft |
| `empty` | "No threads in the last 30 days." |
| `unauthenticated` | Connect screen, then the style-seeding banner after connecting |
| `auth-expired` | `GET /threads` returns 401 -> back to Connect with a "session expired" note |
| `upstream-error` | `POST /runs` returns 502 -> error with Retry |
| `slow-run` | `POST /runs` takes 5 seconds -> spinner state |
| `style-failed` | Seed failed -> warning banner, drafting still allowed |

## Run against the real backend

```bash
# terminal 1
cd backend && uvicorn app.main:app --reload --port 8000

# terminal 2
cd web
echo VITE_USE_MOCKS=false > .env.local
npm run dev
```

`vite.config.js` proxies `/auth`, `/threads`, `/style`, `/runs` and `/health` to
`http://localhost:8000`, so the UI and API share an origin and the `draftagent_session`
cookie works with no manual steps.

## Build for the demo

```bash
cd web && npm run build
```

Output lands in `web/dist`. FastAPI mounts that folder at `/` (see `backend/app/main.py`,
override the path with `WEB_DIST_DIR`), so in the deployed demo there is no CORS at all.
Production builds default to `VITE_USE_MOCKS` unset, which means the real API.

## How it is put together

```text
src/
  api/            Contract A client
    httpClient.js   real fetch client, credentials: "include"
    mockClient.js   fixture-backed client + scenarios
    errors.js       ApiError, error-code -> UI copy, retry rules
    index.js        picks one via VITE_USE_MOCKS
  hooks/          useAuth, useThreads, useThread, useStyleStatus, useDraftRun
  components/     one file per screen or piece of a screen
  utils/format.js date and sender helpers
mocks/            fixture JSON, see mocks/README.md
```

Notes worth knowing:

- **`run_id` lives only in component state** (`useDraftRun`). Reloading mid-run loses the run,
  which the spec allows for the MVP.
- **Any 401 anywhere** calls `onAuthError` and drops back to the Connect screen.
- **Nothing sensitive reaches the browser.** No Google token and no OpenAI key: the session is an
  HttpOnly cookie the backend sets, and the UI only ever reads Contract A JSON.
- **Style seeding does not block drafting.** The banner polls `GET /style/status` every 3s while
  the state is `running`, and hides itself when it turns `ready`.

## Not in scope (spec 01)

Editing the draft in the UI, streaming, multiple accounts, mobile layout polish. An edit box is
the first stretch item if there is time.
