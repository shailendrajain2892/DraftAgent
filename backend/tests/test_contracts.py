"""Contract A conformance tests for the API surface."""

from __future__ import annotations

USER = "me@example.com"


def test_healthz(client):
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"ok": True}


def test_list_threads_shape(client):
    r = client.get("/threads")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"threads", "next_page_token"}
    t = body["threads"][0]
    assert set(t) == {
        "id",
        "subject",
        "from_name",
        "from_email",
        "snippet",
        "message_count",
        "last_message_at",
    }


def test_get_thread_uses_from_json_key(client):
    r = client.get("/threads/18c2f0a1b2c3d4e5")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"id", "subject", "messages"}
    msg = body["messages"][0]
    # JSON key is `from`, not `from_`.
    assert "from" in msg and "from_" not in msg
    assert set(msg) == {"id", "from", "to", "date", "body_text"}


def test_style_status_shape(client):
    r = client.get("/style/status")
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"state", "pairs_count", "window_days", "updated_at", "error"}
    assert body["state"] in {"not_started", "running", "ready", "failed"}


def test_start_run(client):
    r = client.post("/runs", json={"gmail_thread_id": "18c2f0a1b2c3d4e5"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "awaiting_input"
    assert body["run_id"].startswith(f"{USER}:")
    assert "question" in body


def test_resume_run(client):
    run_id = f"{USER}:18c2f0a1b2c3d4e5:a1b2c3d4"
    r = client.post(f"/runs/{run_id}/resume", json={"answer": "Offer 10% off"})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "completed"
    assert set(body["draft"]) == {"text", "gmail_draft_id"}


def test_resume_rejects_foreign_run_id(client):
    r = client.post("/runs/someoneelse@x.com:tid:abcd1234/resume", json={"answer": None})
    assert r.status_code == 404
    assert r.json()["error"]["code"] == "NOT_FOUND"


def test_unauthenticated_returns_contract_error():
    # No dependency override here: hit auth directly.
    from fastapi.testclient import TestClient

    from app.main import create_app

    c = TestClient(create_app())
    r = c.get("/threads")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "UNAUTHENTICATED"
