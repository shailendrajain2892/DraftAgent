"""FastAPI app factory: session middleware, CORS, routers, error handlers, static UI.

Contract D wiring: the agent module and compiled graph are built once at startup and
stored on `app.state` for the runs router. When an OpenAI key is configured we use the
real LangGraph agent (`app.agent.graph`) driven by the Gmail tools; otherwise we fall
back to `app.agent.stub` (used by contract tests / keyless environments).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .api import auth, runs, style, threads
from .config import get_settings
from .errors import DraftAgentError, draftagent_exception_handler, error_body

_log = logging.getLogger("draftagent")


def _build_real_graph(settings, checkpointer):
    """Compile the real agent graph: Gmail tools as the Contract B ToolClient + ChatOpenAI.

    `checkpointer=None` lets the graph use an in-memory saver.
    """
    from langchain_openai import ChatOpenAI

    from .agent import graph as agent_module
    from .tools import gmail_tools

    llm = ChatOpenAI(model=settings.openai_chat_model, api_key=settings.openai_api_key)
    compiled = agent_module.build_graph(tools=gmail_tools, llm=llm, checkpointer=checkpointer)
    return agent_module, compiled


def _select_agent(settings):
    """Baseline (synchronous) Contract D wiring, always set so tests never hit an unset
    app.state. Real agent (in-memory saver) when OPENAI_API_KEY is set; else the stub.

    In production the lifespan upgrades the real graph to a durable SQLite checkpointer.
    """
    if settings.openai_api_key:
        return _build_real_graph(settings, checkpointer=None)

    from .agent import stub as agent_module

    return agent_module, agent_module.build_graph(tools=None, llm=None, checkpointer=None)


@asynccontextmanager
async def _lifespan(app: FastAPI):
    """On startup, upgrade the real agent to a durable async SQLite checkpointer so
    paused runs survive restarts; close it cleanly on shutdown. No-op for the stub.
    """
    settings = get_settings()
    saver_cm = None
    if settings.openai_api_key:
        try:
            from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver

            os.makedirs(os.path.dirname(settings.checkpointer_db) or ".", exist_ok=True)
            saver_cm = AsyncSqliteSaver.from_conn_string(settings.checkpointer_db)
            saver = await saver_cm.__aenter__()
            app.state.agent, app.state.graph = _build_real_graph(settings, checkpointer=saver)
            _log.info("agent: real graph with SQLite checkpointer at %s", settings.checkpointer_db)
        except Exception:  # noqa: BLE001 - fall back to the in-memory graph from create_app
            _log.exception("SQLite checkpointer init failed; keeping in-memory checkpointer")
            saver_cm = None
    try:
        yield
    finally:
        if saver_cm is not None:
            await saver_cm.__aexit__(None, None, None)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="DraftAgent backend", version="0.1.0", lifespan=_lifespan)

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
    app.state.agent, app.state.graph = _select_agent(settings)

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
