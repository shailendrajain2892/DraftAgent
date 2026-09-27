"""Run the eval suite: drive the real agent over the dataset, apply deterministic
assertions + the gpt-4o judge, print a report, and exit nonzero if a gate fails.

    uv run python -m evals.run_eval                 # assertions + judge
    uv run python -m evals.run_eval --no-judge      # assertions only (still generates drafts)
    uv run python -m evals.run_eval --json out.json # also write a JSON report

Needs OPENAI_API_KEY (generation, and the judge unless --no-judge).
"""

from __future__ import annotations

import argparse
import asyncio
import json

from langchain_openai import ChatOpenAI

from app.agent.graph import build_graph, resume_run, start_run
from app.agent.tool_client import USER_ID
from app.config import get_settings

from .assertions import run_assertions, summarize
from .dataset import CASES
from .judge import JUDGE_MODEL, judge

# Gate thresholds (1-5). Tone is softer while the style store is a stub.
GATES = {"faithfulness": 4.0, "relevance": 4.0, "tone": 3.0}


async def _run_case(case, llm, use_judge: bool) -> dict:
    client = case.client()
    graph = build_graph(tools=client, llm=llm, checkpointer=None)
    started = await start_run(graph, USER_ID, case.thread_id)
    result = await resume_run(graph, started["run_id"], USER_ID, case.answer)
    draft = result["text"]

    findings = run_assertions(case, draft, started["question"], client.calls)
    scores = await judge(case, draft) if use_judge else None
    passed, total = summarize(findings)
    gate_ok = all((scores or {}).get(k, 5) >= v for k, v in GATES.items()) if scores else True
    return {
        "id": case.id, "category": case.category, "draft": draft,
        "question": started["question"], "findings": findings, "scores": scores,
        "assertions_ok": passed == total, "gate_ok": gate_ok,
        "assertions": f"{passed}/{total}",
    }


async def main_async(limit: int | None, use_judge: bool, json_path: str | None) -> int:
    settings = get_settings()
    if not settings.openai_api_key:
        print("OPENAI_API_KEY not set — cannot generate drafts.")
        return 2
    llm = ChatOpenAI(model=settings.openai_chat_model, api_key=settings.openai_api_key)
    cases = CASES[:limit] if limit else CASES

    print(f"Running {len(cases)} case(s) | gen={settings.openai_chat_model} | "
          f"judge={JUDGE_MODEL if use_judge else 'off'}\n")
    results = []
    for case in cases:  # sequential — kinder to rate limits
        try:
            results.append(await _run_case(case, llm, use_judge))
        except Exception as exc:  # noqa: BLE001
            results.append({"id": case.id, "category": case.category, "error": str(exc),
                            "assertions_ok": False, "gate_ok": False, "assertions": "-",
                            "findings": [], "scores": None})

    # ---- report ----
    print(f"{'case':<34}{'assert':<9}{'F':>3}{'R':>3}{'T':>3}  result")
    print("-" * 70)
    ok = 0
    for r in results:
        s = r.get("scores") or {}
        f, rel, t = (s.get("faithfulness", "-"), s.get("relevance", "-"), s.get("tone", "-"))
        overall = "PASS" if r["assertions_ok"] and r["gate_ok"] and "error" not in r else "FAIL"
        ok += overall == "PASS"
        print(f"{r['id']:<34}{r['assertions']:<9}{str(f):>3}{str(rel):>3}{str(t):>3}  {overall}")
        if "error" in r:
            print(f"    error: {r['error']}")
        for fd in r["findings"]:
            if not fd.passed:
                print(f"    ✗ {fd.name} {fd.detail}")
        if s.get("rationale"):
            print(f"    judge: {s['rationale']}")

    # aggregate judge means
    scored = [r["scores"] for r in results if r.get("scores")]
    if scored:
        for dim in ("faithfulness", "relevance", "tone"):
            avg = sum(x[dim] for x in scored) / len(scored)
            print(f"  mean {dim}: {avg:.2f}  (gate {GATES[dim]})")
    print(f"\n{ok}/{len(results)} cases passed")

    if json_path:
        serializable = [{**r, "findings": [vars(f) for f in r["findings"]]} for r in results]
        with open(json_path, "w") as fh:
            json.dump(serializable, fh, indent=2)
        print(f"wrote {json_path}")

    return 0 if ok == len(results) else 1


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None)
    ap.add_argument("--no-judge", action="store_true")
    ap.add_argument("--json", dest="json_path", default=None)
    args = ap.parse_args()
    return asyncio.run(main_async(args.limit, not args.no_judge, args.json_path))


if __name__ == "__main__":
    raise SystemExit(main())
