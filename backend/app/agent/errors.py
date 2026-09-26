"""Agent error types — now aliased to the backend's canonical ``app.errors``.

This module originally defined its own provisional error classes. Per its own note
("keep identity so ``isinstance`` checks survive the eventual move"), the backend
canonical module has landed, so these names now *are* the backend classes. That makes
error handling work across the boundary in both directions:

- Backend tools raise ``app.errors.AuthExpiredError`` / ``GmailRateLimited`` — the
  agent's ``isinstance`` checks in ``wrappers``/``graph`` now match them, so a real
  401/429 is handled instead of being swallowed as a 502.
- Errors escaping ``start_run``/``resume_run`` are ``DraftAgentError`` subclasses, so
  the backend's existing exception handler maps them to Contract A codes with no extra
  wiring.

Backend HTTP mapping:

===========================  ==========================================
Agent error                  Backend HTTP mapping
===========================  ==========================================
AuthExpiredError             401 AUTH_EXPIRED
RunNotFoundError             404 NOT_FOUND   (non-disclosing message)
RunStateConflictError        409 RUN_STATE_CONFLICT
GmailRateLimitedError        429 GMAIL_RATE_LIMITED (fatal at save only)
SaveDraftError               502 UPSTREAM_ERROR
DraftGenerationError         502 UPSTREAM_ERROR
===========================  ==========================================
"""

from __future__ import annotations

# Re-exported backend classes (aliased to agent-facing names). Listed in __all__ so the
# renamed aliases are recognised as intentional re-exports, not dead imports.
from ..errors import (
    AuthExpiredError,
    UpstreamError,
)
from ..errors import (
    GmailRateLimited as GmailRateLimitedError,
)
from ..errors import (
    NotFound as RunNotFoundError,
)
from ..errors import (
    RunStateConflict as RunStateConflictError,
)

# Identical for unknown, malformed and wrong-owner run ids — callers cannot probe
# which check failed.
NOT_FOUND_MESSAGE = "Run not found."


class DraftGenerationError(UpstreamError):
    """Draft model output was empty/whitespace or contained tool_calls. -> 502."""


class SaveDraftError(UpstreamError):
    """create_draft returned no gmail_draft_id, or a non-quota save failed. -> 502."""


class AgentToolError(Exception):
    """Recoverable read-tool failure whose message is already sanitized.

    Never escapes to HTTP — the ToolNode error callback returns ``str(e)`` as
    ToolMessage content. Stays a plain Exception on purpose.
    """


__all__ = [
    "AuthExpiredError",
    "GmailRateLimitedError",
    "RunNotFoundError",
    "RunStateConflictError",
    "DraftGenerationError",
    "SaveDraftError",
    "AgentToolError",
    "NOT_FOUND_MESSAGE",
]
