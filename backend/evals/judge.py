"""LLM-as-judge (default gpt-4o) scoring faithfulness, relevance, and tone 1-5.

Judged with a stronger model than the generator to reduce self-preference bias. Returns a
dict per dimension plus a short rationale. Requires OPENAI_API_KEY; the model is set by
EVAL_JUDGE_MODEL (default gpt-4o).
"""

from __future__ import annotations

import asyncio
import json
import os

from app.config import get_settings

JUDGE_MODEL = os.environ.get("EVAL_JUDGE_MODEL", "gpt-4o")

_RUBRIC = """You are a strict evaluator of an email reply DRAFT written on the user's behalf.
Score each dimension from 1 (bad) to 5 (excellent). Be conservative.

- faithfulness: Does the draft avoid inventing facts (prices, dates, amounts, commitments,
  policies) that are NOT present in the thread or the user's answer? Correct use of a
  placeholder like [confirm price] for a genuinely missing fact is GOOD (high score).
  Inventing a specific value that was not provided is a serious failure (score 1-2).
- relevance: Does the draft address what the thread actually asks, per the stated goal?
- tone: Does the draft match the described writing style?

Return ONLY compact JSON:
{"faithfulness": n, "relevance": n, "tone": n, "rationale": "one sentence"}"""


def _thread_text(case) -> str:
    return "\n".join(f"{m['from']}: {m['body_text']}" for m in case.messages)


def _judge_sync(case, draft: str) -> dict:
    from openai import OpenAI

    settings = get_settings()
    client = OpenAI(api_key=settings.openai_api_key)
    user = (
        f"THREAD:\n{_thread_text(case)}\n\n"
        f"USER'S ANSWER: {case.answer if case.answer is not None else '(skipped / none)'}\n\n"
        f"STYLE: {case.style.get('summary', '')} — target: {case.style_desc}\n\n"
        f"WHAT A GOOD REPLY MUST ADDRESS: {case.relevance_goal}\n\n"
        f"DRAFT TO SCORE:\n{draft}"
    )
    resp = client.chat.completions.create(
        model=JUDGE_MODEL,
        response_format={"type": "json_object"},
        messages=[{"role": "system", "content": _RUBRIC}, {"role": "user", "content": user}],
    )
    data = json.loads(resp.choices[0].message.content)
    return {
        "faithfulness": int(data.get("faithfulness", 0)),
        "relevance": int(data.get("relevance", 0)),
        "tone": int(data.get("tone", 0)),
        "rationale": str(data.get("rationale", ""))[:300],
    }


async def judge(case, draft: str) -> dict:
    return await asyncio.to_thread(_judge_sync, case, draft)
