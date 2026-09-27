"""Unit tests for the agent's pure helpers, FakeToolClient caps, and error handling.

All offline and deterministic — no LLM, no network.
"""

from __future__ import annotations

import pytest

from app import errors as backend_errors
from app.agent import errors as agent_errors
from app.agent.graph import _single_question, make_run_id, parse_run_id, validated_env_int
from app.agent.tool_client import (
    QUOTE_THREAD_ID,
    SCHEDULING_THREAD_ID,
    USER_ID,
    FakeToolClient,
)
from app.agent.wrappers import handle_tool_errors, sanitize_error


# --------------------------------------------------------------------------- run_id
def test_run_id_round_trip():
    rid = make_run_id("me@example.com", "thread123")
    user_id, thread_id, nonce = parse_run_id(rid)
    assert user_id == "me@example.com"
    assert thread_id == "thread123"
    assert len(nonce) == 8


def test_run_id_user_with_colon_is_preserved():
    # rsplit(":", 2) means a user_id containing ':' can't shift the other parts.
    rid = make_run_id("weird:user", "thread123")
    assert parse_run_id(rid)[0] == "weird:user"


@pytest.mark.parametrize("bad", ["", "nocolons", "a:b", "u:t:NOTHEX", "u:!!:abcd1234", 123, None])
def test_parse_run_id_rejects_malformed(bad):
    assert parse_run_id(bad) is None


def test_single_question_keeps_one():
    assert _single_question("Anything to add?") == "Anything to add?"
    assert _single_question("Context here. Want A? Or B?") == "Context here. Want A?"
    assert _single_question("No question here").count("?") == 0


# --------------------------------------------------------------------------- env int
def test_validated_env_int_default_and_parse(monkeypatch):
    monkeypatch.delenv("X_STEPS", raising=False)
    assert validated_env_int("X_STEPS", 6) == 6
    monkeypatch.setenv("X_STEPS", "9")
    assert validated_env_int("X_STEPS", 6) == 9


@pytest.mark.parametrize("bad", ["abc", "0", "-3"])
def test_validated_env_int_rejects_bad(monkeypatch, bad):
    monkeypatch.setenv("X_STEPS", bad)
    with pytest.raises(ValueError):
        validated_env_int("X_STEPS", 6)


# --------------------------------------------------------------------------- error aliasing
def test_agent_errors_are_backend_errors():
    # The whole point of the integration: identity, so isinstance works across the boundary.
    assert agent_errors.AuthExpiredError is backend_errors.AuthExpiredError
    assert agent_errors.GmailRateLimitedError is backend_errors.GmailRateLimited
    assert agent_errors.RunNotFoundError is backend_errors.NotFound
    assert agent_errors.RunStateConflictError is backend_errors.RunStateConflict
    assert issubclass(agent_errors.SaveDraftError, backend_errors.UpstreamError)
    assert issubclass(agent_errors.DraftGenerationError, backend_errors.UpstreamError)


# --------------------------------------------------------------------------- wrappers
def test_sanitize_error_strips_paths_and_truncates():
    msg = sanitize_error(RuntimeError("boom at /Users/x/secret/file.py line 3"))
    assert "/Users/x/secret" not in msg
    assert "[path]" in msg
    assert len(msg) <= 300


def test_handle_tool_errors_auth_escapes():
    with pytest.raises(agent_errors.AuthExpiredError):
        handle_tool_errors(agent_errors.AuthExpiredError("expired"))


def test_handle_tool_errors_agent_tool_error_passthrough():
    out = handle_tool_errors(agent_errors.AgentToolError("already sanitized"))
    assert out == "already sanitized"


def test_handle_tool_errors_generic_sanitized():
    out = handle_tool_errors(ValueError("weird /a/b/c thing"))
    assert out.startswith("ValueError:")
    assert "[path]" in out


# --------------------------------------------------------------------------- FakeToolClient
async def test_get_thread_caps_messages_and_body():
    fake = FakeToolClient()
    thread = await fake.get_thread(USER_ID, QUOTE_THREAD_ID, max_messages=99)
    assert len(thread["messages"]) <= 10
    for m in thread["messages"]:
        assert len(m["body_text"]) <= 2000


async def test_search_related_caps_and_excludes_current():
    fake = FakeToolClient()
    results = await fake.search_related(USER_ID, "kickoff", SCHEDULING_THREAD_ID, max_results=99)
    assert len(results) <= 5
    # the current thread appears in the fixture's related list but must be excluded
    assert all(r["thread_id"] != SCHEDULING_THREAD_ID for r in results)
    for r in results:
        assert len(r["snippet"]) <= 150


async def test_unknown_thread_raises_recoverable_tool_error():
    fake = FakeToolClient()
    with pytest.raises(agent_errors.AgentToolError):
        await fake.get_thread(USER_ID, "does-not-exist")


async def test_deepcopy_isolation():
    fake = FakeToolClient()
    t1 = await fake.get_thread(USER_ID, QUOTE_THREAD_ID)
    t1["messages"][0]["body_text"] = "MUTATED"
    t2 = await fake.get_thread(USER_ID, QUOTE_THREAD_ID)
    assert t2["messages"][0]["body_text"] != "MUTATED"


async def test_create_draft_returns_id_and_records_body():
    fake = FakeToolClient()
    out = await fake.create_draft(USER_ID, QUOTE_THREAD_ID, "Hello there")
    assert out["gmail_draft_id"]
    assert fake.calls[-1]["body_text"] == "Hello there"


async def test_create_draft_missing_id_fault():
    fake = FakeToolClient(faults={"create_draft": "missing_id"})
    assert await fake.create_draft(USER_ID, QUOTE_THREAD_ID, "body") == {}


async def test_fault_list_raises_once_then_succeeds():
    fake = FakeToolClient(faults={"get_thread": [agent_errors.AgentToolError("boom")]})
    with pytest.raises(agent_errors.AgentToolError):
        await fake.get_thread(USER_ID, QUOTE_THREAD_ID)
    # second call succeeds (list exhausted)
    thread = await fake.get_thread(USER_ID, QUOTE_THREAD_ID)
    assert thread["id"] == QUOTE_THREAD_ID
