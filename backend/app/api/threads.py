"""Inbox list and thread preview. See Contract A."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from ..deps import current_user_id
from ..inbox import service
from ..types import Message, Thread

router = APIRouter(tags=["threads"])


def _serialize_message(m: Message) -> dict:
    # JSON key is `from`, not `from_` (Contract 00).
    return {
        "id": m["id"],
        "from": m["from_"],
        "to": m["to"],
        "date": m["date"],
        "body_text": m["body_text"],
    }


def _serialize_thread(t: Thread) -> dict:
    return {
        "id": t["id"],
        "subject": t["subject"],
        "messages": [_serialize_message(m) for m in t["messages"]],
    }


@router.get("/threads")
async def list_threads(
    request: Request,
    page_token: str | None = None,
    q: str | None = None,
    user_id: str = Depends(current_user_id),
):
    return await service.list_page(user_id, page_token=page_token, query=q)


@router.get("/threads/{thread_id}")
async def get_thread(
    thread_id: str,
    user_id: str = Depends(current_user_id),
):
    thread = await service.preview(user_id, thread_id)
    return _serialize_thread(thread)
