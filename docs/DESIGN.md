# DraftAgent — Design Doc

_AI Engineering Capstone · 1–2 page design doc. Deeper detail: [`architecture.md`](architecture.md),
component specs in [`specs/`](specs/), evaluation in [`../backend/evals/README.md`](../backend/evals/README.md)._

## 1. Problem Statement

Replying to email is a high-frequency, low-leverage task: people re-read a thread, recall
context, and hand-write a reply that sounds like them. **DraftAgent drafts the reply to a
Gmail thread in the user's own voice.** It reads the full thread (and related history),
retrieves how the user has written similar replies before, asks **one** clarifying question
when a material fact is missing, then composes a reply and saves it as a **Gmail draft**.

Scope is deliberately narrow: Gmail only, English, **reply-drafting only** — it never sends
(human-in-the-loop by design), never composes net-new emails, and never manages the inbox.
Success = a draft the user would send with minimal edits, that never invents facts.

## 2. Architecture

Orchestration is a **LangGraph agent** with a human-in-the-loop pause; personalization is a
**RAG** style store. One FastAPI app serves the React UI and the API (same origin).

```
Browser (React UI)
  → FastAPI (OAuth, threads, runs)            [Contract A]
    → LangGraph agent  start_run/resume       [Contract D]
        gather → tools → ask_user(interrupt) → draft → save_draft
        ├─ Gmail tools layer (only code that calls Gmail)   [Contract B]
        ├─ RAG style store (embeddings retrieval)           [Contract C]
        └─ OpenAI (LLM draft + embeddings)
  ← draft saved to Gmail Drafts (never sent)
```

- **Core flow (orchestration + RAG):** the agent gathers context via tools, **interrupts**
  to ask the user one question (state persisted by a SQLite checkpointer so paused runs
  survive restarts), then drafts and saves.
- **Data surface:** the Gmail tools layer (tool-use interface) + the style store (knowledge
  base of the user's past replies).
- **Retrieval:** on connect, a seed job embeds the user's last 30 days of sent replies; at
  draft time the agent embeds the incoming message and retrieves the most similar past
  replies by cosine similarity (with a recipient-domain boost), with a keyword fallback.
- Deployed as one Docker image on **Fly.io** (single machine, persistent volume), with
  GitHub Actions **CI/CD**.

## 3. Evaluation Criteria

**Quantitative**
- **Draft quality** (LLM-as-judge, gpt-4o, 1–5) — gates: faithfulness ≥ 4, relevance ≥ 4,
  tone ≥ 3. Current: **8/8 cases pass**, means **F 4.88 / R 4.75 / T 4.75**.
- **Deterministic assertions** (pass/fail, in CI) — body-only format, exactly one question,
  placeholder/deferral for withheld facts, no invented/injected strings, correct tool
  sequence.
- **Comparative retrieval** (Recall@1 / Recall@3 / MRR) — keyword baseline vs embeddings
  RAG: **MRR 0.45 → 1.00** (see §4/eval README).

**Qualitative**
- Reads in the user's voice (tone/greeting/length match the style store).
- **Faithfulness / no hallucination** — never invents a price, date, or commitment; uses a
  `[confirm …]` placeholder or asks instead.
- **Prompt-injection resistance** — ignores instructions embedded in email content.

Guardrail: eval data is generated from real runs (never fabricated).

## 4. Framework & Decision Justification

| Choice | Why | Alternatives considered |
| --- | --- | --- |
| **LangGraph** (agent) | First-class **human-in-the-loop `interrupt()`/resume** + a **checkpointer** for durable paused runs — exactly the "ask one question mid-run" pattern. Explicit graph makes tool-loop + gather/draft phases clear. | Pydantic AI / smolagents — lighter, but no first-class durable interrupt/resume; would hand-roll the pause. |
| **Embeddings RAG** (style store) | Comparative eval showed keyword overlap misses paraphrased queries (MRR 0.45) while embeddings match on meaning (MRR 1.00). Baseline established first, then upgraded. | Keyword overlap — kept as offline fallback, not primary. |
| **OpenAI gpt-4o** (generator) | Reliable instruction-following fixed intermittent injection/placeholder/one-question failures the mini model had → stable 8/8. | gpt-4o-mini — cheaper but weaker; caught by the eval. |
| **gpt-4o as judge** | Rubric-based scoring of open-ended drafts that rules can't measure; stronger model reduces bias. Paired with deterministic checks. | Human-only eval (slow); pure rules (can't judge tone/faithfulness). |
| **FastAPI** | Async (MCP/Gmail calls), serves the built UI same-origin (no CORS), simple session cookie. | — |
| **Fly.io + SQLite checkpointer** | One container (UI+API), persistent volume for style store + paused runs, cheap PaaS. SQLite avoids running a DB server. | AWS (heavier for a capstone); in-memory checkpointer (loses paused runs). |

Anti-patterns avoided: narrow problem (not "an AI that does everything"); a **baseline
before advanced retrieval** (keyword → embeddings, measured); tools/limits in code, not the
prompt.
