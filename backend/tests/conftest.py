"""Test fixtures: a TestClient with auth overridden and Gmail/agent calls stubbed.

These are contract tests — they assert the API JSON matches Contract A exactly, without
touching real Gmail. Real-Gmail wiring is exercised manually (see backend/README.md).
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.deps import current_user_id
from app.main import create_app

USER = "me@example.com"


@pytest.fixture
def client(monkeypatch):
    app = create_app()
    app.dependency_overrides[current_user_id] = lambda: USER

    # ---- stub the inbox service (no real Gmail) ----
    async def fake_list_page(user_id, page_token=None, query=None):
        return {
            "threads": [
                {
                    "id": "18c2f0a1b2c3d4e5",
                    "subject": "Q3 vendor quote",
                    "from_name": "Priya Nair",
                    "from_email": "priya@acme.com",
                    "snippet": "Can you confirm the revised numbers by Friday?",
                    "message_count": 3,
                    "last_message_at": "2026-09-18T10:42:00Z",
                }
            ],
            "next_page_token": None,
        }

    async def fake_preview(user_id, thread_id):
        return {
            "id": thread_id,
            "subject": "Q3 vendor quote",
            "messages": [
                {
                    "id": "18c2f0a1b2c3d4e6",
                    "from_": "Priya Nair <priya@acme.com>",
                    "to": ["me@example.com"],
                    "date": "2026-09-18T10:42:00Z",
                    "body_text": "Can you confirm the revised numbers by Friday?",
                }
            ],
        }

    monkeypatch.setattr("app.inbox.service.list_page", fake_list_page)
    monkeypatch.setattr("app.inbox.service.preview", fake_preview)

    # ---- stub style status ----
    monkeypatch.setattr(
        "app.api.style.get_status",
        lambda user_id: {
            "state": "ready",
            "pairs_count": 142,
            "window_days": 30,
            "updated_at": "2026-09-20T09:00:00Z",
            "error": None,
        },
    )

    # ---- stub the agent (Contract D) ----
    async def fake_start_run(graph, user_id, gmail_thread_id):
        return {
            "run_id": f"{user_id}:{gmail_thread_id}:a1b2c3d4",
            "question": "Anything to add before I draft this?",
        }

    async def fake_resume_run(graph, run_id, user_id, answer):
        return {"text": "Hi Priya, ...", "gmail_draft_id": "r-8812345"}

    monkeypatch.setattr(app.state.agent, "start_run", fake_start_run)
    monkeypatch.setattr(app.state.agent, "resume_run", fake_resume_run)

    return TestClient(app)
