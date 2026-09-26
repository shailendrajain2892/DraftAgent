"""Draft run endpoints. See Contract A and Contract D.

`user_id` always comes from the session. A run_id that does not start with the caller's
user_id is rejected (NOT_FOUND).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from ..deps import current_user_id
from ..errors import NotFound

router = APIRouter(prefix="/runs", tags=["runs"])


class StartRunBody(BaseModel):
    gmail_thread_id: str


class ResumeBody(BaseModel):
    answer: str | None = None


def _agent(request: Request):
    """The Contract D module and compiled graph, wired at app startup."""
    return request.app.state.agent, request.app.state.graph


@router.post("")
async def start_run(
    body: StartRunBody,
    request: Request,
    user_id: str = Depends(current_user_id),
):
    agent, graph = _agent(request)
    result = await agent.start_run(graph, user_id, body.gmail_thread_id)
    return {
        "run_id": result["run_id"],
        "status": "awaiting_input",
        "question": result["question"],
    }


@router.post("/{run_id}/resume")
async def resume_run(
    run_id: str,
    body: ResumeBody,
    request: Request,
    user_id: str = Depends(current_user_id),
):
    if not run_id.startswith(f"{user_id}:"):
        raise NotFound("Run not found.")
    agent, graph = _agent(request)
    result = await agent.resume_run(graph, run_id, user_id, body.answer)
    return {
        "run_id": run_id,
        "status": "completed",
        "draft": {"text": result["text"], "gmail_draft_id": result["gmail_draft_id"]},
    }
