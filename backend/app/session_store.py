"""In-memory server-side store for OAuth credentials, keyed by user_id (email).

The browser cookie holds only a session id -> user_id mapping. Google tokens never
leave the server and are lost on process restart (acceptable for the MVP, per spec 02).
"""

from __future__ import annotations

import threading

from google.oauth2.credentials import Credentials

# session_id -> user_id (email)
_sessions: dict[str, str] = {}
# user_id (email) -> Google Credentials
_credentials: dict[str, Credentials] = {}
_lock = threading.Lock()


def bind_session(session_id: str, user_id: str, creds: Credentials) -> None:
    with _lock:
        _sessions[session_id] = user_id
        _credentials[user_id] = creds


def user_for_session(session_id: str | None) -> str | None:
    if not session_id:
        return None
    with _lock:
        return _sessions.get(session_id)


def credentials_for_user(user_id: str) -> Credentials | None:
    with _lock:
        return _credentials.get(user_id)


def update_credentials(user_id: str, creds: Credentials) -> None:
    with _lock:
        _credentials[user_id] = creds


def drop_session(session_id: str | None) -> None:
    if not session_id:
        return
    with _lock:
        _sessions.pop(session_id, None)
