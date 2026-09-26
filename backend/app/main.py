"""FastAPI app factory: session middleware, CORS, routers, error handlers, static UI.

Contract D wiring: the agent module and compiled graph are built once at startup and
stored on `app.state` for the runs router. When an OpenAI key is configured we use the
real LangGraph agent (`app.agent.graph`) driven by the Gmail tools; otherwise we fall
back to `app.agent.stub` (used by contract tests / keyless environments).
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from .api import auth, runs, style, threads
from .config import get_settings
from .errors import DraftAgentError, draftagent_exception_handler, error_body


def _select_agent(settings):
    """Return (agent_module, compiled_graph) for Contract D.

    Real agent when OPENAI_API_KEY is set: the Gmail tools module IS the Contract B
    ToolClient (matching call signatures), and the LLM is a ChatOpenAI. Otherwise the
    stub, which needs no LLM.
    """
    if settings.openai_api_key:
        from langchain_openai import ChatOpenAI

        from .agent import graph as agent_module
        from .tools import gmail_tools

        llm = ChatOpenAI(model=settings.openai_chat_model, api_key=settings.openai_api_key)
        # checkpointer=None -> the graph uses an in-memory saver (paused runs are lost on
        # restart, acceptable for the MVP). Swap in an async SQLite saver via lifespan later.
        compiled = agent_module.build_graph(tools=gmail_tools, llm=llm, checkpointer=None)
        return agent_module, compiled

    from .agent import stub as agent_module

    return agent_module, agent_module.build_graph(tools=None, llm=None, checkpointer=None)


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
