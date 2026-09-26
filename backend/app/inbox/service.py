"""Inbox service for the picker: list and preview, via the tools layer.

The Inbox service calls the plain-Python tools directly (not through the LLM). It never
exposes `create_draft`/seed tools.
"""

from __future__ import annotations

from ..tools import gmail_tools
from ..types import Thread


async def list_page(
    user_id: str, page_token: str | None = None, query: str | None = None
) -> dict:
    q = query or "in:inbox newer_than:30d"
    return await gmail_tools.list_threads(
        user_id, page_token=page_token, max_results=25, query=q
    )


async def preview(user_id: str, thread_id: str) -> Thread:
    return await gmail_tools.get_thread(user_id, thread_id)
