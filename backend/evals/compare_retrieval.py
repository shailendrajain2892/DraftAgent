"""Comparative evaluation: keyword-overlap baseline vs. embeddings RAG for the style store.

The style store retrieves the user's most relevant past replies for the LLM to imitate.
This benchmarks the two retrieval approaches on a labeled set and picks a winner, per the
capstone's "compare at least two approaches, justify the final choice" requirement (and
"establish a simple baseline before advanced retrieval").

Metrics (higher is better):
  Recall@1  — top result is the right topic
  Recall@3  — a right-topic result appears in the top 3
  MRR       — mean reciprocal rank of the first right-topic result

Both retrievers are the SAME StyleStore code path: the baseline runs with embeddings
removed (keyword-overlap fallback), RAG runs with OpenAI embeddings. Needs OPENAI_API_KEY.

    uv run python -m evals.compare_retrieval
"""

from __future__ import annotations

import os
import tempfile

from app.config import get_settings
from app.style_store import StyleStore

USER = "me@example.com"


def _pair(pid, inbound, reply, topic, domain="ext.example"):
    return {
        "id": pid, "inbound": inbound, "reply": reply,
        "recipient_email": f"x@{domain}", "recipient_domain": domain,
        "subject": topic, "date": "2026-09-20T10:00:00Z",
        "reply_words": len(reply.split()), "_topic": topic,
    }


# Labeled corpus: the user's past reply pairs across distinct topics.
CORPUS = [
    _pair("b1", "please send the August invoice", "Invoice attached — let me know.", "billing"),
    _pair("b2", "can you resend invoice #123?", "Resent it just now.", "billing"),
    _pair("s1", "can we schedule the kickoff call", "Tuesday 3pm works for me.", "scheduling"),
    _pair("s2", "what time works for the weekly sync?", "How about Thursday at 10?", "scheduling"),
    _pair("p1", "what is the price for the enterprise plan?", "It's $2,000/mo.", "pricing"),
    _pair("p2", "can you quote 100 units?", "Quote for 100 units is attached.", "pricing"),
    _pair("t1", "the app crashes on login", "Fixed — please try again now.", "support"),
    _pair("t2", "getting a 500 error on upload", "Patched the upload bug — retry.", "support"),
    _pair("i1", "loved your talk, can we connect?", "Absolutely — great to connect!", "intro"),
    _pair("i2", "intro from a mutual friend", "Thanks for the intro — happy to chat.", "intro"),
]

# Queries paraphrase the topics (little literal word overlap) — where semantics beats keywords.
QUERIES = [
    ("resend me the latest bill please", "billing"),
    ("let's find a slot for the meeting", "scheduling"),
    ("how much would 50 licenses cost?", "pricing"),
    ("the sign-in page throws an error", "support"),
    ("the file keeps failing to upload", "support"),
    ("great meeting you — let's stay in touch", "intro"),
]

TOPIC = {p["id"]: p["_topic"] for p in CORPUS}


def _rank_topics(store: StyleStore, inbound: str) -> list[str]:
    # neutral recipient domain so the domain boost doesn't skew the semantic comparison
    results = store.retrieve(inbound, "someone@neutral.example", k=len(CORPUS))
    return [TOPIC[p["id"]] for p in results]


def _metrics(rankings: list[tuple[list[str], str]]) -> dict:
    r1 = r3 = mrr = 0.0
    for ranked, gold in rankings:
        if ranked[:1] == [gold]:
            r1 += 1
        if gold in ranked[:3]:
            r3 += 1
        for i, t in enumerate(ranked, 1):
            if t == gold:
                mrr += 1 / i
                break
    n = len(rankings)
    return {"recall@1": r1 / n, "recall@3": r3 / n, "mrr": mrr / n}


def _build_store(base: str, name: str, keyword_only: bool) -> StyleStore:
    store = StyleStore(f"{name}@x.com", base)
    store.seed(CORPUS)
    if keyword_only and os.path.exists(store._emb_path):
        os.remove(store._emb_path)  # force the keyword-overlap fallback path
    return store


def main() -> int:
    if not get_settings().openai_api_key:
        print("OPENAI_API_KEY not set — needed for the embeddings arm.")
        return 2
    base = tempfile.mkdtemp()
    baseline = _build_store(base, "keyword", keyword_only=True)
    rag = _build_store(base, "rag", keyword_only=False)
    if not os.path.exists(rag._emb_path):
        print("Embeddings did not persist — cannot run the RAG arm.")
        return 2

    arms = {"Keyword (baseline)": baseline, "Embeddings RAG": rag}
    results = {}
    for label, store in arms.items():
        rankings = [(_rank_topics(store, q), gold) for q, gold in QUERIES]
        results[label] = _metrics(rankings)

    print(f"Comparative retrieval eval — {len(QUERIES)} queries, {len(CORPUS)} corpus pairs\n")
    print(f"{'approach':<22}{'Recall@1':>10}{'Recall@3':>10}{'MRR':>8}")
    print("-" * 50)
    for label, m in results.items():
        print(f"{label:<22}{m['recall@1']:>10.2f}{m['recall@3']:>10.2f}{m['mrr']:>8.2f}")

    kw, rg = results["Keyword (baseline)"], results["Embeddings RAG"]
    print("\nJustified choice:")
    if rg["mrr"] >= kw["mrr"]:
        print(f"  → Embeddings RAG wins (MRR {rg['mrr']:.2f} vs {kw['mrr']:.2f}). Keyword overlap "
              "misses paraphrased queries with no shared words; embeddings match on meaning. "
              "We ship RAG, keeping keyword overlap as an offline fallback.")
    else:
        print(f"  → Keyword baseline held up (MRR {kw['mrr']:.2f} vs {rg['mrr']:.2f}) on this set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
