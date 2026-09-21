# Spec 04: Style store (RAG)

Owner: TBD (fourth team member). Read `00_shared_overview_and_contracts.md` first.
Contract C is your interface. `get_style_examples` (Shailendra) calls it, and the seed job
(Shailendra) feeds it.

## Why this exists

The thread alone does not show how this user writes to this person. Looking up earlier replies
at request time is slow and repetitive, so we process the user's past replies once into a style
store. At draft time the agent gets a few similar past replies plus a short style summary.

## Your scope

1. `clean_body`: strip quoted history, signatures and forwards from email text.
2. `StyleStore`: build, save, load and search the store.
3. Style summary generation (one LLM call).
4. Tiered retrieval and the cold-start rules.

## Data model and files

One folder per user under `STYLE_STORE_DIR` (use a hash of the user id as the folder name):

```text
{STYLE_STORE_DIR}/{user_hash}/
  pairs.jsonl     # one ReplyPair per line
  index.faiss     # vectors of the inbound messages
  summary.json    # style summary text and structured fields
  meta.json       # seeded_at, window_days, pair_count
```

`ReplyPair` is defined in the overview file. Save files by writing a temp file and renaming it,
so a crash never leaves a half-written index. Load from disk if the folder exists. Seeding should
be skipped when files are already there.

## clean_body

Remove: quoted lines starting with `>`, "On ... wrote:" blocks, "From: ... Sent: ..." forwarded
headers, signatures (common sign-offs followed by a short block, "Sent from my iPhone"),
disclaimers and auto-replies. Handle plain text and HTML (`is_html=True`).
Shailendra's tools use this function, so deliver a first working version by **Wed 23 Sep**.
Until then he uses a stub.

## seed(pairs)

1. Drop pairs whose reply is under about 10 words or very long.
2. Drop near-duplicate replies (same reply text) and cap how many pairs come from one recipient
   (for example 15) so one contact does not dominate.
3. Optional holdout: mark about 20% of pairs `holdout=true` (deterministic from the pair id),
   keep them in `pairs.jsonl` but leave them out of the index. This keeps a test set for the
   evaluation later. Confirm the fraction on Wednesday (open question 6 in the overview).
4. Embed the `inbound` text of the remaining pairs with `OPENAI_EMBED_MODEL` in batches.
5. Build a flat FAISS index (a few hundred vectors need no fancy index). Normalise vectors and use
   inner product for cosine similarity.
6. Generate the style summary (below). Write all files.

## Style summary

One LLM call over a sample of up to 40 replies. Return JSON, and also store a plain-text version:

```json
{
  "greeting": "Hi <first name>,",
  "signoff": "Thanks,\n<first name>",
  "formality": "friendly but professional",
  "avg_length_words": 55,
  "typical_phrases": ["Happy to help", "Let me know"],
  "avoid": ["exclamation marks", "emoji"]
}
```

## retrieve(inbound_text, recipient_email, k=4)

Tiered filter, then vector search:
1. Candidate pairs where `recipient_email` matches.
2. If fewer than `k`, add pairs with the same `recipient_domain`.
3. If still fewer than `k`, use all non-holdout pairs.
4. Embed `inbound_text`, search the candidates, return the top `k`. Cap the pairs per recipient
   in the result so near-identical recurring emails do not fill it.
5. Truncate long `inbound` and `reply` text (about 500 characters each) in what you return.

## Cold start and modes

| Condition | Result |
| --- | --- |
| `pair_count() >= COLD_START_MIN_PAIRS` and `STYLE_MODE=retrieval` | Examples from `retrieve` plus the summary |
| `pair_count() < COLD_START_MIN_PAIRS`, or `STYLE_MODE=summary_only` | Summary only |
| No store at all | A neutral default summary ("clear, polite, concise") |

`STYLE_MODE` is the switch for the later A vs B comparison, so make it easy to flip.

## Working before other parts exist

- Create a synthetic `pairs` fixture file (30 to 60 `ReplyPair` records with 3 or 4 different recipients).
- Test `seed`, `retrieve` and reload-from-disk with it. You need only an OpenAI key, not Gmail.
- Test `clean_body` on a folder of sample emails (plain, HTML, replies with long quoted history, forwards).

## Definition of done

- [ ] `clean_body` handles the sample set: no quoted history or signatures left in the output.
- [ ] `seed` builds the four files from a fixture. A second run with files present is skipped.
- [ ] `retrieve` returns the same-recipient pairs first, then domain, then all.
- [ ] Reload after a process restart works without re-embedding.
- [ ] Cold-start and `STYLE_MODE` rules behave as in the table.
- [ ] Summary generation returns valid JSON. Bad JSON falls back to the default summary.
- [ ] Unit tests for cleaning, dedupe, tiered retrieval and atomic writes.

## Stretch (only after end to end works)

- `record_feedback(user_id, thread_id, draft_text, sent_text)`: keep the user's edited version as a
  future signal, as the meeting suggested. This needs the final sent text, so it depends on either
  an edit box in the UI or reading the sent message later.
- Refresh: add new replies incrementally instead of only seeding once.
