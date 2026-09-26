"""FastAPI dependencies: resolve the current user from the session cookie."""

from __future__ import annotations

from fastapi import Request

from . import session_store
from .errors import Unauthenticated


def current_user_id(request: Request) -> str:
    """Return the caller's user_id (email) or raise Unauthenticated.

    The session id lives in Starlette's signed session under the key `sid`.
    """
    session_id = request.session.get("sid")
    user_id = session_store.user_for_session(session_id)
    if not user_id:
        raise Unauthenticated()
    return user_id
