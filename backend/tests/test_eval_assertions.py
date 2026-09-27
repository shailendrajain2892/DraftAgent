"""Offline unit tests for the eval assertions + dataset (no LLM, no network).

These validate the eval harness logic itself so it can be trusted; the judge-scored suite
(evals/run_eval.py) runs separately against the real generator.
"""

from __future__ import annotations

from evals.assertions import Finding, run_assertions, summarize
from evals.dataset import CASES, STYLE_CASUAL, EvalCase


def _find(findings, name):
    return next(f for f in findings if f.name == name)


TOOL_CALLS_OK = [
    {"method": "get_thread", "body_text": None},
    {"method": "get_style_examples"},
    {"method": "create_draft", "body_text": "Hi Priya, the price is $12,000.\n\nBest,"},
]


def _case(**kw):
    base = dict(
        id="c", category="x", thread_id="t", subject="s",
        messages=[{"id": "m1", "from": "A <a@x.com>", "to": ["me@example.com"],
                   "date": "2026-09-20T10:00:00Z", "body_text": "hi"}],
        style=STYLE_CASUAL, answer=None, relevance_goal="g", style_desc="d",
    )
    base.update(kw)
    return EvalCase(**base)


def test_good_draft_passes_core_checks():
    case = _case(require_substrings=["12,000"])
    draft = "Hi Priya, the price is $12,000.\n\nBest,"
    findings = run_assertions(case, draft, "Anything to add?", TOOL_CALLS_OK)
    assert _find(findings, "no_subject_line").passed
    assert _find(findings, "present:12,000").passed
    assert _find(findings, "saved_body_matches").passed
    assert _find(findings, "consulted_style").passed


def test_forbidden_invented_fact_fails():
    case = _case(forbidden=["$12,000"])
    findings = run_assertions(case, "The price is $12,000.", "Q?", TOOL_CALLS_OK)
    assert not _find(findings, "absent:$12,000").passed


def test_missing_required_substring_fails():
    case = _case(require_substrings=["MacBook"])
    findings = run_assertions(case, "Sure, will send it.", "Q?", TOOL_CALLS_OK)
    assert not _find(findings, "present:MacBook").passed


def test_placeholder_required():
    case = _case(require_placeholder=True)
    no_ph = run_assertions(case, "The price is fine.", "Q?", TOOL_CALLS_OK)
    assert not _find(no_ph, "uses_placeholder").passed
    with_ph = run_assertions(case, "The price is [confirm price].", "Q?", TOOL_CALLS_OK)
    assert _find(with_ph, "uses_placeholder").passed


def test_subject_line_and_meta_detected():
    case = _case()
    f = run_assertions(case, "Subject: Re: hi\n\nHello", "Q?", TOOL_CALLS_OK)
    assert not _find(f, "no_subject_line").passed
    f2 = run_assertions(case, "Here is a draft reply for you: Hello", "Q?", TOOL_CALLS_OK)
    assert not _find(f2, "no_meta_commentary").passed


def test_single_question_check():
    case = _case()
    f = run_assertions(case, "Hello", "Do you want A? Or B?", TOOL_CALLS_OK)
    assert not _find(f, "single_question").passed


def test_missing_tool_calls_fail():
    case = _case()
    f = run_assertions(case, "Hello", "Q?", [{"method": "create_draft", "body_text": "Hello"}])
    assert not _find(f, "called_get_thread").passed
    assert not _find(f, "consulted_style").passed
    assert _find(f, "saved_draft").passed


def test_summarize_counts():
    findings = [Finding("a", True), Finding("b", False), Finding("c", True)]
    assert summarize(findings) == (2, 3)


def test_dataset_clients_build_and_key_correctly():
    assert len(CASES) >= 6
    for case in CASES:
        client = case.client()
        assert (client.fixtures.get(("me@example.com", case.thread_id))) is not None
