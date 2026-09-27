# DraftAgent — demo video guide

A repeatable script for recording the ~3-minute demo. Anyone on the team can follow this
and get a consistent result. Live app: **https://draftagent.fly.dev**

## Recording tool (macOS)

- **Built-in:** press `⌘⇧5` → "Record Entire Screen" (or a selected portion) → Record; stop
  from the menu bar. Turn on the **microphone** in the `⌘⇧5` **Options** menu for narration.
- **Loom** (recommended): screen + webcam bubble + instant shareable link, easy trimming.
- **OBS** for more control/overlays.

Zoom the browser to ~125–150% (`⌘+`) so text is readable in the recording.

## Prep (do this before recording)

- [ ] Use a **dedicated demo Gmail account** that is added as a test user
      (Google Cloud → Google Auth Platform → Audience → Test users).
- [ ] Seed a few realistic threads in that inbox, including one that **needs a fact**
      (e.g. a vendor asking "what price and delivery date should I put in the PO?").
- [ ] **Pre-seed the style store:** sign in once beforehand and wait for
      `/style/status` → `ready`, so you don't film the seed wait.
- [ ] Close noisy tabs, silence notifications (Do Not Disturb).
- [ ] **Never show** `.env`, tokens, API keys, or private email.
- [ ] Do one full dry run — OAuth consent and the first draft take ~10–30s.

## Script (~3 minutes)

| Time | On screen | Narration |
|---|---|---|
| 0:00 | README architecture diagram (or a title slide) | "DraftAgent reads a full Gmail thread and drafts a reply in your voice — and it never sends, only saves a draft." |
| 0:20 | `https://draftagent.fly.dev` → **Connect Gmail** → Google consent | "You connect Gmail with Google OAuth. Tokens stay server-side; the browser never sees them." |
| 0:40 | Inbox list loads | "It shows your recent threads." |
| 0:55 | Pick a thread → **Draft reply** | "Pick one and hit Draft reply." |
| 1:05 | The **clarifying question** appears | "The agent has already read the thread — and related threads — and asks one targeted question before drafting." |
| 1:20 | Type an answer (or click skip) → Submit | "I give it the price and delivery date…" |
| 1:35 | Draft shown → switch to **Gmail → Drafts** to show it saved | "…and it writes the reply in my style and saves it straight to Gmail Drafts. Nothing is sent." |
| 2:00 | *(bonus)* `backend/evals/README.md` — 8/8 + the injection case | "We evaluate every draft for faithfulness, relevance, and tone with an LLM judge — currently 8/8 — and it resists prompt-injection attempts hidden in emails." |
| 2:30 | *(bonus)* GitHub Actions (CI green) + architecture diagram | "CI runs tests and eval assertions on every PR, and every merge auto-deploys to Fly.io." |
| 2:50 | Close | "Built on FastAPI, LangGraph, and OpenAI." |

Keep the happy path (0:00–2:00) tight. The bonus technical bits (2:00–2:50) add depth for
graders but can be cut if you want a 2-minute cut.

## Shot list (the must-haves)

1. Connect Gmail → consent screen (proves real OAuth).
2. Inbox list of real threads.
3. The clarifying **question** (the agent's interrupt — the differentiator).
4. Draft text rendered in the UI.
5. **The saved draft open in Gmail Drafts** — the money shot that proves it works.

## Tips

- If a draft run is slow on camera, say: "this takes ~15 seconds — it's reading the thread,
  checking my writing style, and composing." Then trim dead time in post.
- End on the saved Gmail draft; that's the strongest proof.
- Add captions/timestamps in Loom or iMovie if you want.

## After recording

- Trim, export at 1080p.
- Add the link here and in the root README (a short "Demo" section).
