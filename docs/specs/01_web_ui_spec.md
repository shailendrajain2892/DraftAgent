# Spec 01: Repo scaffold and web UI

Owner: Antim Jain. Read `00_shared_overview_and_contracts.md` first (Contract A is your API).

## Your scope

1. Create the shared GitHub repo and push the scaffold (layout in the overview file).
2. Build the web UI: connect Gmail, email list, thread preview, Draft reply button,
   the question step, and the draft review step.

Stack is your choice (React with Vite is a good default). The build output must be plain static
files that FastAPI can serve, so we avoid CORS problems in the demo.

## Scaffold checklist (do this first, by Tue 22 Sep)

- [ ] Repo created, team added, `main` protected (PRs only).
- [ ] Folders from the overview layout, each with a short README or `.gitkeep`.
- [ ] `backend/`: minimal FastAPI app with `GET /health`, `requirements.txt` (or `pyproject.toml`), `pytest` set up.
- [ ] `.env.example` with the variables listed in the overview file.
- [ ] `.gitignore` covers `.env`, `node_modules`, `__pycache__`, and the style store folder.
- [ ] Copy the spec files into `docs/specs/`.
- [ ] PR template with a "which contract does this touch?" line.

## Screens and states

| Screen | What the user sees | Data |
| --- | --- | --- |
| Connect | App name, one **Connect Gmail** button | `GET /auth/me` says not authenticated |
| Inbox | Left: thread list. Right: preview of the selected thread | `GET /threads`, `GET /threads/{id}` |
| Style banner | "Building your style profile..." while seeding, hidden when ready | `GET /style/status` |
| Question | Modal or panel with the agent's question, a text box, **Continue** and **Skip** | `POST /runs` response |
| Draft review | The draft text, a note that it was saved to Gmail drafts, a link to Gmail drafts | `POST /runs/{id}/resume` response |

### Inbox list

- Each row: sender name, subject, snippet, message count, time.
- **Load more** button at the bottom uses `next_page_token`. Do not load everything up front.
- Empty state: "No threads in the last 30 days."
- Clicking a row selects it (highlight) and loads the preview. Nothing is sent to the agent yet.

### Draft flow

1. **Draft reply** is enabled only when a thread is selected.
2. Click: call `POST /runs` with the thread id. Show a spinner and disable the button. This can take 10 to 30 seconds.
3. Show the question. **Continue** sends the text, **Skip** sends `null`. Both call `POST /runs/{run_id}/resume`.
4. Show the draft. The draft is already saved in Gmail. Link to `https://mail.google.com/mail/u/0/#drafts`.
5. **Draft another** returns to the inbox.

Keep `run_id` in component state. If the page reloads mid-run, the run is lost, which is fine for the MVP.

### Errors

Use the table in Contract A. Every failed call shows a short message and a **Retry** button.
On `401`, go back to the Connect screen.

## Working before the backend exists

Build against fixture JSON that copies the examples in Contract A. Put fixtures in
`web/mocks/` and switch between mock and real API with one env flag (for example `VITE_USE_MOCKS=true`).
A tiny mock server such as MSW or json-server works well. Include at least: an empty inbox, a
two-page inbox, a `401`, a `502`, and a slow `POST /runs` (5 second delay).

## Definition of done

- [ ] Repo, scaffold and PR template merged by Tue 22 Sep.
- [ ] All five screens work against the mocks, including the error cases above.
- [ ] `npm run build` output is served by FastAPI at `/` (agree the folder with Shailendra).
- [ ] Works against the real backend for the happy path: connect, list, preview, draft, question, review.
- [ ] Session cookie works with no manual steps in the browser.
- [ ] No Google token or OpenAI key is ever visible in the browser.
- [ ] Short README section: how to run the UI locally with mocks and with the real backend.

## Not in scope

Editing the draft in the UI, streaming, multiple accounts, mobile layout polish.
(If time allows, an edit box is the first stretch item, because it supports the "user edits feed
back as signal" idea.)
