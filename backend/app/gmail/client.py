"""Gmail service builder plus a retrying/refreshing execute wrapper.

All Gmail traffic goes through here. The googleapiclient calls are synchronous and are
run in a thread pool from the async tools layer. Per-user concurrency is bounded so we
never fan out more than ~5 requests to Gmail for one user.
"""

from __future__ import annotations

import asyncio
import random
import threading
import time
from collections.abc import Callable
from typing import Any, TypeVar

import google_auth_httplib2
import httplib2
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request as GoogleAuthRequest
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .. import session_store
from ..config import get_settings
from ..errors import AuthExpiredError, GmailRateLimited, UpstreamError

T = TypeVar("T")

# One asyncio.Semaphore per user_id, created lazily.
_semaphores: dict[str, asyncio.Semaphore] = {}
_sem_lock = threading.Lock()


def _semaphore_for(user_id: str) -> asyncio.Semaphore:
    with _sem_lock:
        sem = _semaphores.get(user_id)
        if sem is None:
            sem = asyncio.Semaphore(get_settings().gmail_max_concurrency)
            _semaphores[user_id] = sem
        return sem


def _ensure_fresh(user_id: str, creds: Credentials) -> Credentials:
    """Refresh the access token if needed. Raise AuthExpiredError on invalid_grant."""
    if creds.valid:
        return creds
    if creds.expired and creds.refresh_token:
        try:
            creds.refresh(GoogleAuthRequest())
        except RefreshError as exc:  # invalid_grant etc.
            raise AuthExpiredError() from exc
        session_store.update_credentials(user_id, creds)
        return creds
    raise AuthExpiredError()


def build_service(user_id: str):
    """Build a Gmail API service for the user from stored credentials.

    The returned service is used only to *construct* requests. Each request is executed
    with its own HTTP connection (see `_execute_with_retry`) because httplib2.Http is not
    thread-safe and we fan out requests concurrently.
    """
    creds = session_store.credentials_for_user(user_id)
    if creds is None:
        raise AuthExpiredError()
    creds = _ensure_fresh(user_id, creds)
    # cache_discovery=False avoids a noisy warning and file cache in server contexts.
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _fresh_http(user_id: str):
    """A brand-new authorized httplib2.Http for one request (thread-safe isolation)."""
    creds = session_store.credentials_for_user(user_id)
    if creds is None:
        raise AuthExpiredError()
    creds = _ensure_fresh(user_id, creds)
    return google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http())


def _http_reason(exc: HttpError) -> str:
    """Best-effort human-readable reason from a Gmail HttpError (no bodies/tokens)."""
    try:
        for err in exc.error_details or []:  # type: ignore[attr-defined]
            if isinstance(err, dict) and err.get("reason"):
                return str(err["reason"])
    except Exception:  # noqa: BLE001
        pass
    reason = getattr(exc, "reason", None)
    return str(reason) if reason else "unknown"


def _execute_with_retry(user_id: str, request_factory: Callable[[], Any]) -> Any:
    """Execute a googleapiclient request with retry on 429/5xx.

    `request_factory` returns a fresh request object each call so retries are clean.
    Each execute uses its own authorized Http so concurrent calls never share a
    non-thread-safe connection.
    """
    settings = get_settings()
    last_exc: Exception | None = None
    for attempt in range(settings.gmail_max_retries):
        try:
            return request_factory().execute(http=_fresh_http(user_id))
        except HttpError as exc:
            status = getattr(exc.resp, "status", None)
            status = int(status) if status is not None else None
            if status == 401:
                raise AuthExpiredError() from exc
            if status == 429 or (status is not None and 500 <= status < 600):
                last_exc = exc
                sleep = (2**attempt) + random.uniform(0, 0.5)
                time.sleep(sleep)
                continue
            reason = _http_reason(exc)
            raise UpstreamError(f"Gmail error {status}: {reason}") from exc
    # Retries exhausted.
    status = getattr(getattr(last_exc, "resp", None), "status", None)
    if status is not None and int(status) == 429:
        raise GmailRateLimited() from last_exc
    raise UpstreamError("Gmail failed after retries.") from last_exc


async def run_gmail(user_id: str, request_factory: Callable[[], Any]) -> Any:
    """Async entry point: bound concurrency + run the blocking call in a thread."""
    sem = _semaphore_for(user_id)
    async with sem:
        return await asyncio.to_thread(_execute_with_retry, user_id, request_factory)
