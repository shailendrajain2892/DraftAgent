"""FastAPI app factory: session middleware, CORS, routers, error handlers, static UI.

Contract D wiring: the agent module and compiled graph are built once at startup and
stored on `app.state` for the runs router. Swap `agent.stub` for Yashshree's real module
(`app.agent.graph`) when it lands — the import is the only line that changes.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .agent import stub as agent_module
from .api import auth, runs, style, threads
from .config import get_settings
from .errors import DraftAgentError, draftagent_exception_handler, error_body


def _build_graph(settings):
    """Build the compiled graph with a SQLite checkpointer if the agent extra is present."""
    checkpointer = None
    try:
        from langgraph.checkpoint.sqlite import SqliteSaver

        os.makedirs(os.path.dirname(settings.checkpointer_db) or ".", exist_ok=True)
        checkpointer = SqliteSaver.from_conn_string(settings.checkpointer_db)
    except Exception:  # noqa: BLE001 - stub graph works without a checkpointer
        checkpointer = None
    return agent_module.build_graph(tools=None, llm=None, checkpointer=checkpointer)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="DraftAgent backend", version="0.1.0")

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.session_secret,
        session_cookie=settings.session_cookie_name,
        https_only=settings.cookie_secure,
        same_site="lax",
    )

    if settings.frontend_origin:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=[settings.frontend_origin],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    # Contract D wiring.
    app.state.agent = agent_module
    app.state.graph = _build_graph(settings)

    # Error handlers (Contract A shape).
    app.add_exception_handler(DraftAgentError, draftagent_exception_handler)

    @app.exception_handler(Exception)
    async def _unhandled(request: Request, exc: Exception) -> JSONResponse:  # noqa: ANN202
        # Log the full traceback server-side; return the Contract A error shape to clients.
        logging.getLogger("draftagent").exception(
            "Unhandled error on %s %s", request.method, request.url.path
        )
        return JSONResponse(
            status_code=502,
            content=error_body("UPSTREAM_ERROR", "Unexpected server error."),
        )

    @app.get("/healthz")
    def healthz():  # noqa: ANN202
        return {"ok": True}

    app.include_router(auth.router)
    app.include_router(threads.router)
    app.include_router(style.router)
    app.include_router(runs.router)

    # Serve the built web UI as static files if present (no CORS in that case).
    default_dist = os.path.join(os.path.dirname(__file__), "..", "..", "web", "dist")
    web_dist = os.getenv("WEB_DIST", default_dist)
    if os.path.isdir(web_dist):
        app.mount("/", StaticFiles(directory=web_dist, html=True), name="web")

    return app


app = create_app()
