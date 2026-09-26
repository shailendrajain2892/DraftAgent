"""Contract D flow test for the real graph, driven by a fake LLM (no network).

The fake LLM returns a plain question in the gather step (no tool calls) so the run
pauses on the interrupt, then returns the draft body in the draft step. This exercises
start_run -> interrupt -> resume_run -> draft -> save_draft end to end, deterministically.
"""

from __future__ import annotations

import pytest
from langchain_core.messages import AIMessage

from app.agent import errors as agent_errors
from app.agent.graph import build_graph, resume_run, start_run
from app.agent.tool_client import QUOTE_THREAD_ID, USER_ID, FakeToolClient

QUESTION = "What price and delivery date should I put in the PO?"
DRAFT_BODY = "Hi Priya,\n\nThe price is $12,000, delivery by 30 Sep.\n\nBest,"


class FakeLLM:
    """Minimal ChatOpenAI stand-in: distinguishes gather vs draft by the system prompt."""

    def bind_tools(self, tools):
        return self  # gather uses the bound llm; same object is fine for the fake

    async def ainvoke(self, messages, config=None):
        system = getattr(messages[0], "content", "") if messages else ""
        if "final reply email" in system:  # DRAFT_SYSTEM
            return AIMessage(content=DRAFT_BODY)
        return AIMessage(content=QUESTION)  # gather: a question, no tool_calls -> ask_user


def _graph():
    return build_graph(tools=FakeToolClient(), llm=FakeLLM(), checkpointer=None)


async def test_full_flow_with_answer():
    g = _graph()
    started = await start_run(g, USER_ID, QUOTE_THREAD_ID)
    assert started["run_id"].startswith(f"{USER_ID}:")
    assert started["question"] == QUESTION

    result = await resume_run(g, started["run_id"], USER_ID, "Offer $12,000, deliver 30 Sep.")
    assert result["text"] == DRAFT_BODY
    assert result["gmail_draft_id"]


async def test_full_flow_skip_answer():
    g = _graph()
    started = await start_run(g, USER_ID, QUOTE_THREAD_ID)
    result = await resume_run(g, started["run_id"], USER_ID, None)  # user skipped
    assert result["text"] == DRAFT_BODY
    assert result["gmail_draft_id"]


async def test_resume_rejects_foreign_user():
    g = _graph()
    started = await start_run(g, USER_ID, QUOTE_THREAD_ID)
    with pytest.raises(agent_errors.RunNotFoundError):
        await resume_run(g, started["run_id"], "someone-else@example.com", "hi")


async def test_resume_unknown_run_id():
    g = _graph()
    with pytest.raises(agent_errors.RunNotFoundError):
        await resume_run(g, f"{USER_ID}:thread:deadbeef", USER_ID, "hi")
