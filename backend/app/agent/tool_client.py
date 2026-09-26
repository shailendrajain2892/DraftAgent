"""Contract B: ToolClient protocol + deterministic offline FakeToolClient.

The fake never touches the network; fixtures are keyed by
``(user_id, gmail_thread_id)`` and returns are deep-copied so graph
mutations cannot leak between runs. Caps mirror the real tools layer:
get_thread <= 10 messages / body_text <= 2000 chars, search_related
<= 5 results / snippet <= 150 chars and never the excluded (current)
thread, get_style_examples k respected. Every call is recorded.
"""

from __future__ import annotations

import copy
from typing import Any, Protocol, runtime_checkable

from .errors import AgentToolError, SaveDraftError  # noqa: F401  (SaveDraftError re-export for convenience)

USER_ID = "me@example.com"

QUOTE_THREAD_ID = "18c2f0a1b2c3d4e5"
SCHEDULING_THREAD_ID = "9f8e7d6c5b4a3921"
ACKNOWLEDGEMENT_THREAD_ID = "5566778899aabbcc"


@runtime_checkable
class ToolClient(Protocol):
    """The four async, agent-facing tools (Contract B)."""

    async def get_thread(self, user_id: str, thread_id: str,
                         max_messages: int = 10) -> dict: ...

    async def search_related(self, user_id: str, query: str,
                             exclude_thread_id: str,
                             max_results: int = 5) -> list[dict]: ...

    async def get_style_examples(self, user_id: str, thread_id: str,
                                 k: int = 4) -> dict: ...

    async def create_draft(self, user_id: str, thread_id: str,
                           body_text: str) -> dict: ...


# ---------------------------------------------------------------------------
# Scenario fixtures (Contract 3.1 shapes)
# ---------------------------------------------------------------------------

QUOTE_FIXTURE = {
    "thread": {
        "id": QUOTE_THREAD_ID,
        "subject": "Q3 vendor quote",
        "messages": [
            {
                "id": "m1",
                "from": "Priya Nair <priya@acme.com>",
                "to": [USER_ID],
                "date": "2026-09-18T10:42:00Z",
                "body_text": (
                    "Can you confirm the revised numbers by Friday? What price "
                    "and delivery date should I put in the PO?"
                ),
            }
        ],
    },
    "related": [],
    "style": {
        "mode": "retrieval",
        "summary": (
            "Short polite replies; opens with \"Hi <first name>\"; gets to the "
            "point quickly; signs off simply."
        ),
        "examples": [
            {
                "inbound": "Are the specs final for the pilot?",
                "reply": "Hi Tom, yes, the specs are final. I've attached the "
                         "PDF. Shout if anything looks off.",
            },
            {
                "inbound": "Can you send the invoice for August?",
                "reply": "Hi Lena, invoice attached. Let me know if you need "
                         "anything else.",
            },
        ],
    },
}

SCHEDULING_FIXTURE = {
    "thread": {
        "id": SCHEDULING_THREAD_ID,
        "subject": "Re: kickoff meeting",
        "messages": [
            {
                "id": "m1",
                "from": "Arjun Rao <arjun@corp.example>",
                "to": [USER_ID],
                "date": "2026-09-21T09:15:00Z",
                "body_text": (
                    "As discussed last week about the kickoff meeting — which "
                    "day and time work for you?"
                ),
            }
        ],
    },
    "related": [
        {
            "thread_id": "aabbccdd11223344",
            "subject": "Kickoff planning",
            "date": "2026-09-14T14:05:00Z",
            "participants": ["arjun@corp.example", USER_ID],
            "snippet": "Can we push the kickoff to next week? I'll send a "
                       "few slots once I hear back from design.",
        },
        {
            # current thread also appears in search results — must be excluded
            "thread_id": SCHEDULING_THREAD_ID,
            "subject": "Re: kickoff meeting",
            "date": "2026-09-21T09:15:00Z",
            "participants": ["arjun@corp.example", USER_ID],
            "snippet": "As discussed last week about the kickoff meeting — "
                       "which day and time work for you?",
        },
    ],
    "style": {
        "mode": "summary_only",
        "summary": "Replies are brief and direct; proposes concrete times.",
        "examples": [],
    },
}

ACKNOWLEDGEMENT_FIXTURE = {
    "thread": {
        "id": ACKNOWLEDGEMENT_THREAD_ID,
        "subject": "Notes shared",
        "messages": [
            {
                "id": "m1",
                "from": "Sam Ortiz <sam@x.io>",
                "to": [USER_ID],
                "date": "2026-09-22T08:30:00Z",
                "body_text": "Noted, thanks!",
            }
        ],
    },
    "related": [],
    "style": {
        "mode": "default",
        "summary": "Neutral default style while the personal style store is "
                   "still seeding.",
        "examples": [],
    },
}

FIXTURES: dict[tuple[str, str], dict[str, Any]] = {
    (USER_ID, QUOTE_THREAD_ID): QUOTE_FIXTURE,
    (USER_ID, SCHEDULING_THREAD_ID): SCHEDULING_FIXTURE,
    (USER_ID, ACKNOWLEDGEMENT_THREAD_ID): ACKNOWLEDGEMENT_FIXTURE,
}


# ---------------------------------------------------------------------------
# FakeToolClient
# ---------------------------------------------------------------------------

class FakeToolClient:
    """Deterministic, recording, fault-injectable stand-in for the backend tools.

    ``faults`` maps a method name to one of:
    - an ``Exception`` instance  -> raised on every call of that method;
    - a list of ``Exception``    -> raised one per call, then calls succeed;
    - the string ``"missing_id"`` -> (create_draft only) returns ``{}``.
    """

    def __init__(self, fixtures: dict | None = None,
                 faults: dict | None = None) -> None:
        self.fixtures = FIXTURES if fixtures is None else fixtures
        self.faults: dict = dict(faults or {})
        self.calls: list[dict] = []
        self._draft_counter = 0

    # -- internals ----------------------------------------------------------

    def _check_fault(self, method: str):
        """Raise this method's scripted fault, if any.

        Returns the string sentinel ``"missing_id"`` (create_draft only),
        or None when there is no string fault.
        """
        fault = self.faults.get(method)
        if fault is None:
            return None
        if isinstance(fault, str):
            return fault
        if isinstance(fault, list):
            if fault:
                raise fault.pop(0)
            return None
        raise fault

    def _entry(self, user_id: str, thread_id: str) -> dict:
        entry = self.fixtures.get((user_id, thread_id))
        if entry is None:
            # Recoverable typed tool error (model sees readable text).
            raise AgentToolError(f"unknown thread {thread_id}")
        return entry

    # -- Contract B ---------------------------------------------------------

    async def get_thread(self, user_id: str, thread_id: str,
                         max_messages: int = 10) -> dict:
        self.calls.append({
            "method": "get_thread",
            "user_id": user_id,
            "thread_id": thread_id,
            "max_messages": max_messages,
        })
        self._check_fault("get_thread")
        thread = copy.deepcopy(self._entry(user_id, thread_id)["thread"])
        limit = min(int(max_messages), 10)  # hard cap: newest 10, oldest first
        if limit <= 0:
            thread["messages"] = []
        else:
            thread["messages"] = thread["messages"][-limit:]
        for message in thread["messages"]:
            message["body_text"] = message["body_text"][:2000]
        return thread

    async def search_related(self, user_id: str, query: str,
                             exclude_thread_id: str,
                             max_results: int = 5) -> list[dict]:
        self.calls.append({
            "method": "search_related",
            "user_id": user_id,
            "query": query,
            "exclude_thread_id": exclude_thread_id,
            "max_results": max_results,
        })
        self._check_fault("search_related")
        entry = self.fixtures.get((user_id, exclude_thread_id))
        related = copy.deepcopy(entry["related"]) if entry else []
        cap = min(int(max_results), 5)  # hard cap: <= 5 results
        results: list[dict] = []
        if cap <= 0:
            return results
        for item in related:
            if item["thread_id"] == exclude_thread_id:
                continue  # never return the excluded (current) thread
            item["snippet"] = item["snippet"][:150]
            results.append(item)
            if len(results) >= cap:
                break
        return results

    async def get_style_examples(self, user_id: str, thread_id: str,
                                 k: int = 4) -> dict:
        self.calls.append({
            "method": "get_style_examples",
            "user_id": user_id,
            "thread_id": thread_id,
            "k": k,
        })
        self._check_fault("get_style_examples")
        style = copy.deepcopy(self._entry(user_id, thread_id)["style"])
        # k is respected but is not a frozen hard cap (Contract B).
        limit = int(k)
        style["examples"] = style["examples"][:max(limit, 0)]
        return style

    async def create_draft(self, user_id: str, thread_id: str,
                           body_text: str) -> dict:
        self.calls.append({
            "method": "create_draft",
            "user_id": user_id,
            "thread_id": thread_id,
            "body_text": body_text,  # record the BODY actually passed
        })
        sentinel = self._check_fault("create_draft")
        if sentinel == "missing_id":
            return {}
        if not body_text or not str(body_text).strip():
            raise SaveDraftError("create_draft received an empty body")
        self._draft_counter += 1
        return {"gmail_draft_id": f"draft-{thread_id}-{self._draft_counter}"}
