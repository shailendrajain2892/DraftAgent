from __future__ import annotations

import asyncio
import os
import re
from contextlib import asynccontextmanager
from uuid import uuid4

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import ToolNode
from langgraph.types import Command, interrupt

from .errors import (
    NOT_FOUND_MESSAGE,
    AuthExpiredError,
    DraftGenerationError,
    GmailRateLimitedError,
    RunNotFoundError,
    RunStateConflictError,
    SaveDraftError,
)
from .prompts import DRAFT_SYSTEM, FALLBACK_QUESTION, GATHER_SYSTEM
from .state import DraftState
from .tool_client import ToolClient
from .wrappers import handle_tool_errors, make_wrapped_tools

# run_id = "user_id:gmail_thread_id:nonce"; parsed with rsplit so a user_id
# containing ":" can never shift the other parts.
_THREAD_ID_RE = re.compile(r"[A-Za-z0-9._-]{4,128}")
_NONCE_RE = re.compile(r"[0-9a-f]{8}")

# Attributes attached to the compiled graph in build_graph.
_RECURSION_LIMIT = "_draftagent_recursion_limit"
_LOCKS = "_draftagent_locks"


def validated_env_int(name: str, default: int) -> int:
    """Positive int from the environment, or *default* when unset/blank."""
    raw = os.environ.get(name)
    if raw is None or not raw.strip():
        return default
    try:
        value = int(raw.strip())
    except ValueError:
        raise ValueError(f"{name} must be an integer, got {raw!r}") from None
    if value < 1:
        raise ValueError(f"{name} must be >= 1, got {value}")
    return value


# ---------------------------------------------------------------------------
# Message helpers
# ---------------------------------------------------------------------------

def _content_text(message) -> str:
    """Plain text of a message — string content or content blocks."""
    content = getattr(message, "content", "")
    if isinstance(content, str):
        return content
    parts = []
    for block in content if isinstance(content, list) else []:
        if isinstance(block, str):
            parts.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            parts.append(str(block.get("text", "")))
        elif hasattr(block, "text"):
            parts.append(str(block.text))
    return "".join(parts)


def _single_question(text: str) -> str:
    """Enforce exactly one question: keep everything up to and including the first '?'.

    The gather prompt asks for one question but a small model sometimes appends a second;
    this guarantees the interrupt shows a single question.
    """
    text = (text or "").strip()
    if text.count("?") <= 1:
        return text
    return text[: text.index("?") + 1].strip()


def with_single_system(messages, system_text: str):
    """Prepend *system_text* exactly once — never duplicated in a loop."""
    return [SystemMessage(content=system_text)] + [
        m for m in messages
        if not (isinstance(m, SystemMessage) and m.content == system_text)
    ]


# ---------------------------------------------------------------------------
# run_id
# ---------------------------------------------------------------------------

def make_run_id(user_id: str, gmail_thread_id: str) -> str:
    return f"{user_id}:{gmail_thread_id}:{uuid4().hex[:8]}"


def parse_run_id(run_id: str):
    """-> (user_id, gmail_thread_id, nonce) or None if malformed."""
    if not isinstance(run_id, str):
        return None
    parts = run_id.rsplit(":", 2)
    if len(parts) != 3 or not parts[0]:
        return None
    user_id, thread_id, nonce = parts
    if not _THREAD_ID_RE.fullmatch(thread_id) or not _NONCE_RE.fullmatch(nonce):
        return None
    return user_id, thread_id, nonce


# ---------------------------------------------------------------------------
# Interrupt inspection (snapshot state — not ``.next`` alone)
# ---------------------------------------------------------------------------

def _snapshot_question(snapshot) -> str | None:
    """Question of the pending interrupt, if the run is paused on one."""
    sources = [getattr(task, "interrupts", None) or ()
               for task in (getattr(snapshot, "tasks", None) or ())]
    values = getattr(snapshot, "values", None)
    if isinstance(values, dict):
        sources.append(values.get("__interrupt__") or ())
    for items in sources:
        for item in items:
            value = item.value if hasattr(item, "value") else item
            if isinstance(value, dict):
                question = value.get("question")
                if isinstance(question, str) and question.strip():
                    return question.strip()
    return None


@asynccontextmanager
async def _run_lock(graph, run_id: str):
    """One asyncio lock per run, registry attached to the graph itself.

    Entries are never evicted — same lifetime as the checkpointer's own
    per-run state, so the registry cannot outgrow it.
    """
    locks = getattr(graph, _LOCKS, None)
    if locks is None:
        locks = {}
        setattr(graph, _LOCKS, locks)
    async with locks.setdefault(run_id, asyncio.Lock()):
        yield


def _run_config(graph, user_id: str, run_id: str) -> dict:
    # user_id travels in EVERY ainvoke/aget_state config — trusted identity.
    return {
        "configurable": {"thread_id": run_id, "user_id": user_id},
        "recursion_limit": getattr(graph, _RECURSION_LIMIT, 22),
    }


# ---------------------------------------------------------------------------
# build_graph
# ---------------------------------------------------------------------------

def build_graph(tools: ToolClient, llm, checkpointer):
    """Compile the graph: *tools* = Contract B client, *llm* = ChatOpenAI-like."""
    max_steps = validated_env_int("MAX_AGENT_STEPS", default=6)

    wrapped = make_wrapped_tools(tools)      # 3 read tools, model-safe schemas
    bound_llm = llm.bind_tools(wrapped)      # gather only — draft stays unbound
    tool_node = ToolNode(wrapped, handle_tool_errors=handle_tool_errors)

    async def gather(state: DraftState, config):
        steps = state.get("gather_steps") or 0
        if steps >= max_steps:
            # Cap hit: stop without another model call or tool loop.
            return {"messages": [AIMessage(content=FALLBACK_QUESTION)]}
        response = await bound_llm.ainvoke(
            with_single_system(state.get("messages") or [], GATHER_SYSTEM),
            config)
        if not getattr(response, "tool_calls", None) \
                and not _content_text(response).strip():
            response = AIMessage(content=FALLBACK_QUESTION)
        return {"messages": [response], "gather_steps": steps + 1}

    def route(state: DraftState) -> str:
        last = (state.get("messages") or [None])[-1]
        return "tools" if getattr(last, "tool_calls", None) else "ask_user"

    async def ask_user(state: DraftState):
        question = FALLBACK_QUESTION
        for message in reversed(state.get("messages") or []):
            if isinstance(message, AIMessage) and not message.tool_calls:
                if text := _content_text(message).strip():
                    question = text
                    break
        question = _single_question(question)  # enforce exactly one question
        # resume=None is ambiguous in LangGraph — always the answer envelope.
        payload = interrupt({"question": question})
        if isinstance(payload, dict) and "answer" in payload:
            return {"user_context": payload["answer"]}
        return {"user_context": payload}

    async def draft(state: DraftState, config):
        answer = state.get("user_context")
        label = "none" if answer is None else answer   # "" passes through as ""
        history = list(state.get("messages") or []) + [
            HumanMessage(content=f"USER_ANSWER: {label}")]
        # Original unbound llm — never tool-bound in the draft step.
        response = await llm.ainvoke(
            [SystemMessage(content=DRAFT_SYSTEM)] + history, config)
        if getattr(response, "tool_calls", None):
            raise DraftGenerationError("draft model output contained tool_calls")
        text = _content_text(response)
        if not text.strip():
            raise DraftGenerationError("draft model output was empty")
        return {"draft": text.strip()}

    async def save_draft(state: DraftState, config):
        user_id = (config.get("configurable") or {}).get("user_id")
        try:
            result = await tools.create_draft(
                user_id, state.get("gmail_thread_id"), state.get("draft") or "")
        except (AuthExpiredError, GmailRateLimitedError, SaveDraftError):
            raise                       # fatal, identity preserved (401 / 429)
        except Exception as exc:
            raise SaveDraftError(
                f"create_draft failed ({type(exc).__name__})") from exc
        gmail_draft_id = (result.get("gmail_draft_id")
                          if isinstance(result, dict) else None)
        if not gmail_draft_id or not str(gmail_draft_id).strip():
            raise SaveDraftError("create_draft returned no gmail_draft_id")
        return {"gmail_draft_id": str(gmail_draft_id)}

    graph = StateGraph(DraftState)
    graph.add_node("gather_agent", gather)
    graph.add_node("tools", tool_node)
    graph.add_node("ask_user", ask_user)
    graph.add_node("draft", draft)
    graph.add_node("save_draft", save_draft)
    graph.add_edge(START, "gather_agent")
    graph.add_conditional_edges(
        "gather_agent", route, {"tools": "tools", "ask_user": "ask_user"})
    graph.add_edge("tools", "gather_agent")
    graph.add_edge("ask_user", "draft")
    graph.add_edge("draft", "save_draft")
    graph.add_edge("save_draft", END)

    if checkpointer is None:
        checkpointer = InMemorySaver()     # convenience default, still real
    compiled = graph.compile(checkpointer=checkpointer)
    setattr(compiled, _RECURSION_LIMIT, 2 * max_steps + 10)
    setattr(compiled, _LOCKS, {})
    return compiled


# ---------------------------------------------------------------------------
# Contract D entry points
# ---------------------------------------------------------------------------

async def start_run(graph, user_id: str, gmail_thread_id: str) -> dict:
    """Start a run up to the mandatory question interrupt."""
    run_id = make_run_id(user_id, gmail_thread_id)
    config = _run_config(graph, user_id, run_id)
    initial_state = {
        "messages": [],
        "gmail_thread_id": gmail_thread_id,
        "gather_steps": 0,
        "user_context": None,
        "draft": None,
        "gmail_draft_id": None,
    }
    await graph.ainvoke(initial_state, config)

    question = _snapshot_question(await graph.aget_state(config))
    if not question:
        raise RunStateConflictError(
            "run did not pause for the question (internal error)")
    return {"run_id": run_id, "question": question}   # exactly these two keys


async def resume_run(graph, run_id: str, user_id: str,
                     answer: str | None) -> dict:
    """Answer the pending question; run to completion and return the draft."""
    async with _run_lock(graph, run_id):
        parsed = parse_run_id(run_id)
        if parsed is None or parsed[0] != user_id:
            raise RunNotFoundError(NOT_FOUND_MESSAGE)   # malformed / foreign

        config = _run_config(graph, user_id, run_id)
        snapshot = await graph.aget_state(config)
        if not getattr(snapshot, "values", None):
            raise RunNotFoundError(NOT_FOUND_MESSAGE)   # unknown run
        if _snapshot_question(snapshot) is None:
            raise RunStateConflictError(
                "Run is not waiting for an answer, restart it.")

        # Always the answer envelope — even when answer is None.
        await graph.ainvoke(Command(resume={"answer": answer}), config)

        final_values = getattr(await graph.aget_state(config), "values", None) or {}
        text = final_values.get("draft")
        gmail_draft_id = final_values.get("gmail_draft_id")
        if not text or not gmail_draft_id:
            raise RunStateConflictError(
                "run finished without a draft (internal error)")
        return {"text": text, "gmail_draft_id": gmail_draft_id}  # exactly two
