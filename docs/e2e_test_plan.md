# End-to-end test plan

Run the whole thing against a real Gmail account and a real OpenAI key. Everything below was
checked against `main` at commit `48741fc`, except the steps marked **needs credentials**,
which cannot be verified without your Google and OpenAI keys.

Budget about 20 minutes the first time, 5 minutes on repeat runs.

---

## 0. One-time setup

### 0.1 Google Cloud (about 5 minutes)

1. https://console.cloud.google.com -> create a project -> **APIs & Services -> Library -> Gmail API -> Enable.**
2. **OAuth consent screen:** External. Add **your own Gmail address as a Test user**, plus every
   teammate who will demo. Sign-in is blocked for anyone not on that list.
3. **Credentials -> Create credentials -> OAuth client ID -> Web application.** Authorised
   redirect URI, exactly, no trailing slash:
   ```
   http://localhost:8000/auth/google/callback
   ```
4. Copy the Client ID and Client secret.

### 0.2 `backend/.env`

The settings loader reads `.env` **relative to the working directory**, and you start uvicorn
from `backend/`. So the file goes at `backend/.env`, not the repo root:

```text
GOOGLE_CLIENT_ID=<from step 0.1>
GOOGLE_CLIENT_SECRET=<from step 0.1>
OAUTH_REDIRECT_URI=http://localhost:8000/auth/google/callback
SESSION_SECRET=<any long random string>
OPENAI_API_KEY=<your key>
```

`OPENAI_API_KEY` is not optional. Without it the app starts and the inbox works, but
`POST /runs` has no compiled graph and fails with a 502 at the **Draft reply** step.

### 0.3 Install

The backend README uses `uv`. If you do not have it, plain venv + pip works:

```bash
cd backend
python -m venv .venv
.venv\Scripts\activate
pip install -e ".[dev]"
```

---

## 1. Build and start

Run the UI **from FastAPI on port 8000**, not from the Vite dev server. The OAuth callback
redirects to `/`, so after Google consent you land on port 8000 regardless of where you started.
Single origin is also exactly how the Fly deployment serves it.

```bash
cd web && npm run build
```

```bash
cd backend && .venv\Scripts\activate && uvicorn app.main:app --port 8000
```

Open **http://localhost:8000**.

> Use `npm run dev` on port 5173 only for UI work against mocks. The dev proxy forwards API calls
> to 8000, but the post-login redirect still lands you on 8000.

---

## 2. Smoke checks before touching the UI

```bash
curl -s http://localhost:8000/healthz
curl -s http://localhost:8000/auth/me
curl -s http://localhost:8000/threads
```

| Check | Expected | Verified |
| --- | --- | --- |
| `/healthz` | `{"ok":true}` | yes |
| `/auth/me` with no session | `{"authenticated":false,"email":null}` | yes |
| `/threads` with no session | 401 and `{"error":{"code":"UNAUTHENTICATED","message":"Please sign in with Google."}}` | yes |
| `GET /` | 200 `text/html`, the built UI | yes |
| `/auth/google/login` | 302 to `accounts.google.com` with `access_type=offline`, `prompt=consent`, the four scopes | yes |

If `/threads` returns anything other than that error envelope, stop: the UI's error handling keys
off `error.code`, and everything downstream will misbehave.

---

## 3. Happy path (needs credentials)

| # | Do this | Expect |
| --- | --- | --- |
| 3.1 | Open http://localhost:8000 | Connect screen, one **Connect Gmail** button, no thread list |
| 3.2 | Click **Connect Gmail** | Google consent. An "unverified app" warning is normal in Testing mode: **Advanced -> Go to DraftAgent** |
| 3.3 | Approve both Gmail permissions | Back on the app, your email in the top right, your **real** threads in the left pane |
| 3.4 | Look at the banner | "Building your style profile..." appears while the seed job runs, then disappears on its own. It should never block you |
| 3.5 | Scroll to the bottom of the list, click **Load more** | A second page appends. The button disappears when `next_page_token` is null |
| 3.6 | Click a thread | Right pane shows subject, message count, and every message oldest first, with quoted history and signatures stripped |
| 3.7 | Click **Draft reply** | Button disables, spinner, "This usually takes 10 to 30 seconds." Nothing else in the UI locks up |
| 3.8 | Wait for the question | One question, relevant to that thread, with a text box, **Continue** and **Skip** |
| 3.9 | Type an instruction the draft could not invent, e.g. "offer 10% off, deliver by 30 Sep", click **Continue** | Spinner, then the draft |
| 3.10 | Read the draft | Your instruction is reflected, the tone resembles how you write, "Saved to your Gmail drafts" is shown |
| 3.11 | **Open Gmail drafts** | A real draft exists on that thread with the same text |
| 3.12 | Check your Sent folder | **Nothing sent.** This is the one non-negotiable check |
| 3.13 | Click **Draft another** | Back to the inbox, selection cleared |

### 3.14 Skip path

Repeat 3.6 to 3.9 on a different thread but click **Skip**. The draft must still be produced and
saved. Skip sends `answer: null`, which is a different code path from an empty string.

---

## 4. Error and edge cases

| # | How to trigger | Expect |
| --- | --- | --- |
| 4.1 | Click **Sign out** | Back to Connect. Reload: still signed out |
| 4.2 | Sign out, then reload a page that fetches threads | Connect screen, no crash, no blank pane |
| 4.3 | Stop the backend mid-session, click a thread | Short message plus a **Retry** button, not a stuck spinner |
| 4.4 | Restart the backend, click **Retry** | Recovers without a reload |
| 4.5 | Start a draft, then reload the page while the question modal is open | Back to the inbox. The run is lost by design in the MVP; it must not wedge the UI |
| 4.6 | Revoke access at https://myaccount.google.com/permissions, then click a thread | 401 handling: back to Connect with "session expired" |
| 4.7 | A thread with a single message, and one with 5+ messages | Both render; message count is right |
| 4.8 | An HTML-heavy newsletter thread | Readable text, no raw tags |

The UI shows a Retry button for every code except `NOT_FOUND` and `RUN_STATE_CONFLICT`, which are
not retryable as-is.

---

## 5. Security checks

Worth doing once before submitting, since two of these are definition-of-done items.

| # | Check | How |
| --- | --- | --- |
| 5.1 | No Google token in the browser | DevTools -> Application -> Cookies. Only `draftagent_session`, marked HttpOnly. Nothing that looks like `ya29.` or a refresh token |
| 5.2 | No OpenAI key in the bundle | `grep -r "sk-" web/dist/` returns nothing |
| 5.3 | No fixtures in the production build | `grep -r "mock-page-2" web/dist/` returns nothing. Verified: the mock client is tree-shaken out when `VITE_USE_MOCKS` is unset |
| 5.4 | `.env` is not committed | `git status` shows no `.env`; `git log --all -- backend/.env` is empty |
| 5.5 | No send scope | The consent screen asks to *read* mail and *create drafts*, never to send |

---

## 6. Regression suites

```bash
cd backend && .venv\Scripts\activate && pytest -q     # 47 passed
cd web && npm run build                                # builds clean
```

The mock scenarios still exercise UI states that are awkward to reproduce against a real inbox
(empty inbox, 502, slow run). `cd web && npm run dev`, then use the **mocks** pill:

```
http://localhost:5173/?mock=empty
http://localhost:5173/?mock=upstream-error
http://localhost:5173/?mock=slow-run
```

---

## Known gotchas

- **`redirect_uri_mismatch`** — the Google Cloud URI must match `OAUTH_REDIRECT_URI` character for
  character, including port and no trailing slash.
- **"Access blocked ... verification process"** — the address signing in is not on the Test users list.
- **Refresh tokens expire after about 7 days in Testing mode.** Just sign in again.
- **A blank page on port 8000** means `web/dist` does not exist. Run `npm run build`.
- **`POST /runs` 502s** — usually a missing or out-of-quota `OPENAI_API_KEY`. The uvicorn console
  logs the real traceback; the browser only ever sees the Contract A error envelope.
- **First inbox load is slower than the mocks** — it is a real Gmail listing call plus batched
  metadata for 25 threads.
