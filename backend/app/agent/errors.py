"""Shared error types for the agent (Spec 03), re-exported from ``app.agent``.

Provisional until the backend lands its canonical module; keep identity
(no re-subclasses) so ``isinstance`` checks survive the eventual move.

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

# Identical for unknown, malformed and wrong-owner run ids — callers cannot
# probe which check failed.
NOT_FOUND_MESSAGE = "Run not found."


class AuthExpiredError(Exception):
    """Gmail credentials expired/revoked. Escapes the graph unchanged."""


class GmailRateLimitedError(Exception):
    """Gmail quota exceeded.

    Fatal when raised by ``create_draft`` at save time (backend -> 429).
    Recoverable on the read path: sanitized into tool text for the model;
    if the model recovers, the run completes and no 429 is produced.
    """


class AgentToolError(Exception):
    """Recoverable read-tool failure whose message is already sanitized.

    The ToolNode error callback returns ``str(e)`` as ToolMessage content —
    the wrapper raises it with a message only, no tool_call_id scope.
    """


class DraftGenerationError(Exception):
    """Draft model output was empty/whitespace or contained tool_calls."""


class SaveDraftError(Exception):
    """create_draft returned no gmail_draft_id, or a non-quota save failed."""


class RunNotFoundError(Exception):
    """Unknown, malformed or wrong-owner run id. Message is non-disclosing."""


class RunStateConflictError(Exception):
    """Resume attempted on a run that is not waiting for an answer."""
