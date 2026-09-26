"""State schema and shared data shapes for the agent (Spec 03).

Top-level langgraph import: if langgraph is missing this fails loudly with a
clear ImportError naming the package — there is no silent fallback anywhere.
"""

from typing import TypedDict

from langgraph.graph import MessagesState


class DraftState(MessagesState):
    """Graph state: message history plus per-run draft bookkeeping.

    All keys are initialised explicitly by ``start_run``; TypedDicts are
    dicts — nodes read ``state["key"]`` and return partial update dicts,
    never attribute assignments.
    """

    gmail_thread_id: str        # the Gmail thread we reply to (not LangGraph's thread_id)
    user_context: str | None    # the human's answer; None = skipped
    draft: str | None           # final generated reply text
    gmail_draft_id: str | None  # id returned by create_draft
    gather_steps: int           # gather-model invocations so far (cap counter)


# Message wire shape uses the functional TypedDict form because `from` is a
# Python keyword; the JSON/wire key is always "from".
Message = TypedDict("Message", {
    "id": str,
    "from": str,          # "Name <email>"
    "to": list[str],
    "date": str,          # ISO 8601
    "body_text": str,     # cleaned plain text
})

Thread = TypedDict("Thread", {  # noqa: UP013  (functional form kept to match Message)
    "id": str,
    "subject": str,
    "messages": list[Message],  # oldest first
})
