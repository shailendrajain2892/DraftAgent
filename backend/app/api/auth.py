"""Google OAuth: login, callback, /me, logout. See Contract A."""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Request
from fastapi.responses import JSONResponse, RedirectResponse
from google_auth_oauthlib.flow import Flow

from .. import session_store
from ..config import get_settings
from ..deps import current_user_id
from ..seed.job import run_seed

router = APIRouter(prefix="/auth", tags=["auth"])

# Local-dev OAuth allowances. When the cookie is not Secure we are on http://localhost:
# oauthlib refuses non-HTTPS token exchange, and Google often returns a slightly
# different scope set (adds openid, reorders) which oauthlib treats as an error.
if not get_settings().cookie_secure:
    os.environ.setdefault("OAUTHLIB_INSECURE_TRANSPORT", "1")
    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")


def _build_flow(settings, state: str | None = None) -> Flow:
    client_config = {
        "web": {
            "client_id": settings.google_client_id,
            "client_secret": settings.google_client_secret,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.oauth_redirect_uri],
        }
    }
    # PKCE off: this is a confidential web client (has client_secret), so PKCE is
    # optional. Disabling it avoids threading the code_verifier through the session.
    return Flow.from_client_config(
        client_config,
        scopes=settings.gmail_scopes,
        state=state,
        redirect_uri=settings.oauth_redirect_uri,
        autogenerate_code_verifier=False,
    )


@router.get("/google/login")
def login(request: Request):
    settings = get_settings()
    flow = _build_flow(settings)
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
    )
    request.session["oauth_state"] = state
    return RedirectResponse(auth_url, status_code=302)


@router.get("/google/callback")
def callback(request: Request, background: BackgroundTasks, code: str = "", state: str = ""):
    # A bare visit to the callback (no code) isn't part of the flow — send them to login.
    if not code:
        return RedirectResponse("/auth/google/login", status_code=302)
    settings = get_settings()
    saved_state = request.session.get("oauth_state")
    flow = _build_flow(settings, state=saved_state)
    flow.fetch_token(code=code)
    creds = flow.credentials

    # Identify the user (email) via the userinfo endpoint.
    from googleapiclient.discovery import build

    oauth2 = build("oauth2", "v2", credentials=creds, cache_discovery=False)
    info = oauth2.userinfo().get().execute()
    user_id = info["email"]

    session_id = uuid.uuid4().hex
    session_store.bind_session(session_id, user_id, creds)
    request.session["sid"] = session_id
    request.session.pop("oauth_state", None)

    # Kick off the style-store seed in the background, then redirect home.
    background.add_task(run_seed, user_id)
    return RedirectResponse("/", status_code=302)


@router.get("/me")
def me(request: Request):
    try:
        user_id = current_user_id(request)
    except Exception:
        return JSONResponse({"authenticated": False, "email": None})
    return {"authenticated": True, "email": user_id}


@router.post("/logout")
def logout(request: Request):
    session_store.drop_session(request.session.get("sid"))
    request.session.clear()
    return {"ok": True}
