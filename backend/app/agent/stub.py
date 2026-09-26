"""Stub implementation of Contract D (build_graph / start_run / resume_run).

Yashshree's LangGraph agent (spec 03) replaces this. Until then this stub follows the
same contract and produces a REAL Gmail draft so the end-to-end flow is demoable:

  gather thread + style  ->  interrupt() to ask the user  ->  compose reply  ->  save_draft

Design notes for the real graph:
- `run_id` == LangGraph `thread_id`, format `{user_id}:{gmail_thread_id}:{uuid8}`.
- The real graph keeps paused state in a SQLite checkpointer (decision: SqliteSaver);
  this stub keeps an in-memory registry with the same lifecycle.
"""

from __future__ import annotations

import threading
import uuid

from ..config import get_settings
from ..errors import NotFound, RunStateConflict, UpstreamError
from ..tools import gmail_tools

# run_id -> {"user_id", "gmail_thread_id", "status", "question"}
_runs: dict[str, dict] = {}
_lock = threading.Lock()


class StubGraph:
    """Placeholder for the CompiledGraph handed around by Contract D."""

    def __init__(self, checkpointer=None):
        self.checkpointer = checkpointer


def build_graph(tools=None, llm=None, checkpointer=None) -> StubGraph:  # Contract D
    return StubGraph(checkpointer=checkpointer)


async def start_run(graph, user_id: str, gmail_thread_id: str) -> dict:
    """Run gather, stop at the interrupt, return the question."""
    thread = await gmail_tools.get_thread(user_id, gmail_thread_id)
    if not thread["messages"]:
        raise NotFound("Thread not found or empty.")

    run_id = f"{user_id}:{gmail_thread_id}:{uuid.uuid4().hex[:8]}"
    question = _draft_question(thread)
    with _lock:
        _runs[run_id] = {
            "user_id": user_id,
            "gmail_thread_id": gmail_thread_id,
            "status": "awaiting_input",
            "question": question,
        }
    return {"run_id": run_id, "question": question}


async def resume_run(graph, run_id: str, user_id: str, answer: str | None) -> dict:
    """Continue: compose the reply and save it to Gmail as a draft."""
    with _lock:
        run = _runs.get(run_id)
    if run is None:
        raise NotFound("Run not found.")
    if run["user_id"] != user_id:
        raise NotFound("Run not found.")
    if run["status"] != "awaiting_input":
        raise RunStateConflict()

    gmail_thread_id = run["gmail_thread_id"]
    thread = await gmail_tools.get_thread(user_id, gmail_thread_id)
    style = await gmail_tools.get_style_examples(user_id, gmail_thread_id)
    text = await _compose(thread, style, answer)

    result = await gmail_tools.create_draft(user_id, gmail_thread_id, text)
    with _lock:
        run["status"] = "completed"
    return {"text": text, "gmail_draft_id": result["gmail_draft_id"]}


# ---------------------------------------------------------------------------
def _draft_question(thread: dict) -> str:
    subject = thread.get("subject") or "this email"
    return f'Anything to add before I draft a reply to "{subject}"?'


async def _compose(thread: dict, style: dict, answer: str | None) -> str:
    """Compose reply text. Uses OpenAI if configured, else a deterministic fallback."""
    settings = get_settings()
    latest = thread["messages"][-1]
    from email.utils import parseaddr

    name = parseaddr(latest["from_"])[0] or "there"
    first_name = name.split()[0] if name else "there"

    if settings.openai_api_key:
        try:
            return await _compose_openai(thread, style, answer, settings)
        except Exception as exc:  # noqa: BLE001
            raise UpstreamError(f"OpenAI failed: {exc}") from exc

    # Deterministic fallback (no LLM configured): honest placeholder draft.
    extra = f"\n\nContext you gave me: {answer}" if answer else ""
    return (
        f"Hi {first_name},\n\n"
        "Thanks for your message. [DraftAgent stub reply — replace with the LangGraph "
        f"agent's OpenAI output.]{extra}\n\n"
        "Best,\n"
    )


async def _compose_openai(thread: dict, style: dict, answer: str | None, settings) -> str:
    import asyncio

    from openai import OpenAI

    client = OpenAI(api_key=settings.openai_api_key)
    convo = "\n\n".join(
        f"{m['from_']} ({m['date']}):\n{m['body_text']}" for m in thread["messages"]
    )
    examples = "\n".join(
        f"- They wrote: {e['inbound'][:200]}\n  You replied: {e['reply'][:200]}"
        for e in style.get("examples", [])
    )
    system = (
        "You draft an email reply in the user's voice. Style summary: "
        f"{style.get('summary', '')}\n"
        f"Examples of how the user replies:\n{examples or '(none)'}"
    )
    user = (
        f"Thread:\n{convo}\n\n"
        f"Extra context from the user: {answer or '(none)'}\n\n"
        "Write only the reply body, no subject line."
    )

    def _call():
        resp = client.chat.completions.create(
            model=settings.openai_chat_model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return resp.choices[0].message.content.strip()

    return await asyncio.to_thread(_call)
