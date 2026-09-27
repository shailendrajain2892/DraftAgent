"""Tests for the RAG StyleStore (Contract C) — embeddings path (monkeypatched, offline)
and the keyword-overlap fallback. No network.
"""

from __future__ import annotations

import os

from app.style_store import StyleStore

USER = "me@example.com"

# Deterministic fake embedder over a tiny vocab so cosine ranking is testable offline.
_VOCAB = ["invoice", "meeting", "price"]


def _fake_embed(_self, texts):
    return [[float(t.lower().count(w)) for w in _VOCAB] for t in texts]


def _pair(pid, inbound, reply, domain):
    return {
        "id": pid, "inbound": inbound, "reply": reply,
        "recipient_email": f"x@{domain}", "recipient_domain": domain,
        "subject": "s", "date": "2026-09-20T10:00:00Z", "reply_words": len(reply.split()),
    }


PAIRS = [
    _pair("p1", "please send the invoice", "Invoice attached.", "acme.com"),
    _pair("p2", "can we schedule a meeting", "How about Tuesday?", "corp.com"),
    _pair("p3", "confirm the price please", "Confirmed, looks good.", "acme.com"),
]


def _store(tmp_path):
    return StyleStore(USER, str(tmp_path))


def test_not_ready_then_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(StyleStore, "_embed", _fake_embed)
    s = _store(tmp_path)
    assert not s.is_ready()
    s.seed(PAIRS)
    assert s.is_ready()
    assert s.pair_count() == 3
    assert "recent replies" in s.summary()


def test_embedding_retrieval_ranks_by_topic(tmp_path, monkeypatch):
    monkeypatch.setattr(StyleStore, "_embed", _fake_embed)
    s = _store(tmp_path)
    s.seed(PAIRS)
    assert os.path.exists(s._emb_path)  # embeddings persisted
    top = s.retrieve("can you resend the invoice?", "someone@other.com", k=1)
    assert top[0]["id"] == "p1"  # invoice topic wins on cosine


def test_domain_boost_breaks_ties(tmp_path, monkeypatch):
    monkeypatch.setattr(StyleStore, "_embed", _fake_embed)
    s = _store(tmp_path)
    s.seed(PAIRS)
    # price topic + acme domain -> p3 (price, acme) should rank first
    top = s.retrieve("what is the price?", "buyer@acme.com", k=1)
    assert top[0]["id"] == "p3"


def test_keyword_fallback_when_no_embeddings(tmp_path, monkeypatch):
    # _embed returns [] -> no embeddings file, retrieve uses keyword overlap
    monkeypatch.setattr(StyleStore, "_embed", lambda _self, texts: [])
    s = _store(tmp_path)
    s.seed(PAIRS)
    assert not os.path.exists(s._emb_path)
    top = s.retrieve("please send me the invoice", "someone@other.com", k=1)
    assert top[0]["id"] == "p1"


def test_retrieve_empty_when_unseeded(tmp_path):
    assert _store(tmp_path).retrieve("anything", "a@b.com") == []
