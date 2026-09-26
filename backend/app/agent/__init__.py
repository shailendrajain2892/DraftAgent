"""DraftAgent agent component (Spec 03) — real LangGraph, mocked externals.

Importing this package pulls in ``langgraph`` through ``.graph``/``.state``:
if a pinned dependency is missing, the import fails loudly with a clear
ImportError naming the package. There is no silent fallback anywhere.
"""

from .errors import (
    NOT_FOUND_MESSAGE,
    AgentToolError,
    AuthExpiredError,
    DraftGenerationError,
    GmailRateLimitedError,
    RunNotFoundError,
    RunStateConflictError,
    SaveDraftError,
)
from .graph import build_graph, parse_run_id, resume_run, start_run
from .state import DraftState, Message, Thread

__all__ = [
    "build_graph",
    "start_run",
    "resume_run",
    "parse_run_id",
    "DraftState",
    "Message",
    "Thread",
    "NOT_FOUND_MESSAGE",
    "AgentToolError",
    "AuthExpiredError",
    "DraftGenerationError",
    "GmailRateLimitedError",
    "RunNotFoundError",
    "RunStateConflictError",
    "SaveDraftError",
]
