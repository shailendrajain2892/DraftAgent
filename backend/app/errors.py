"""Domain exceptions and their mapping to Contract A error codes / HTTP statuses."""

from __future__ import annotations

from fastapi import Request
from fastapi.responses import JSONResponse


class DraftAgentError(Exception):
    """Base error carrying a Contract A code, HTTP status and a user-facing message."""

    code: str = "UPSTREAM_ERROR"
    http_status: int = 502
    default_message: str = "Something went wrong."

    def __init__(self, message: str | None = None):
        self.message = message or self.default_message
        super().__init__(self.message)


class Unauthenticated(DraftAgentError):
    code = "UNAUTHENTICATED"
    http_status = 401
    default_message = "Please sign in with Google."


class AuthExpiredError(DraftAgentError):
    code = "AUTH_EXPIRED"
    http_status = 401
    default_message = "Please sign in with Google again."


class NotFound(DraftAgentError):
    code = "NOT_FOUND"
    http_status = 404
    default_message = "Not found."


class RunStateConflict(DraftAgentError):
    code = "RUN_STATE_CONFLICT"
    http_status = 409
    default_message = "This run is not waiting for an answer."


class GmailRateLimited(DraftAgentError):
    code = "GMAIL_RATE_LIMITED"
    http_status = 429
    default_message = "Gmail is rate limiting us. Try again in a moment."


class UpstreamError(DraftAgentError):
    code = "UPSTREAM_ERROR"
    http_status = 502
    default_message = "Gmail or OpenAI failed."


class RunTimeout(DraftAgentError):
    code = "RUN_TIMEOUT"
    http_status = 504
    default_message = "The draft run timed out."


def error_body(code: str, message: str) -> dict:
    return {"error": {"code": code, "message": message}}


async def draftagent_exception_handler(_: Request, exc: DraftAgentError) -> JSONResponse:
    return JSONResponse(
        status_code=exc.http_status,
        content=error_body(exc.code, exc.message),
    )
