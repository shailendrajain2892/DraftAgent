"""Disk-backed style store implementing Contract C, with embeddings-based RAG.

On seed we embed each reply pair's *inbound* text (what the user was replying to) with the
OpenAI embeddings model and persist the vectors. On retrieve we embed the current inbound
message and rank past pairs by cosine similarity, with a small boost for the same
recipient domain — so the agent gets the user's most relevant past replies to imitate.

If embeddings are unavailable (no API key, offline CI, or an embedding error), it falls
back to keyword-overlap retrieval so the store still works. Files land under
{base_dir}/{safe_user_id}/ and survive restarts (no DB).
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter
from math import sqrt

from ..config import get_settings
from ..types import ReplyPair

_WORD = re.compile(r"[a-z0-9']+")
_DOMAIN_BOOST = 0.1  # added to a same-recipient-domain pair's similarity score


def _tokens(text: str) -> Counter:
    return Counter(_WORD.findall(text.lower()))


def _safe(user_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", user_id)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = sqrt(sum(x * x for x in a))
    nb = sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


class StyleStore:
    def __init__(self, user_id: str, base_dir: str):
        self.user_id = user_id
        self.base_dir = base_dir
        self.dir = os.path.join(base_dir, _safe(user_id))
        self._pairs_path = os.path.join(self.dir, "pairs.json")
        self._emb_path = os.path.join(self.dir, "embeddings.json")
        self._summary_path = os.path.join(self.dir, "summary.txt")

    # ---- Contract C ----
    def is_ready(self) -> bool:
        return os.path.exists(self._pairs_path)

    def pair_count(self) -> int:
        return len(self._load_pairs())

    def seed(self, pairs: list[ReplyPair]) -> None:
        os.makedirs(self.dir, exist_ok=True)
        with open(self._pairs_path, "w", encoding="utf-8") as f:
            json.dump(pairs, f)
        with open(self._summary_path, "w", encoding="utf-8") as f:
            f.write(self._build_summary(pairs))
        # Best-effort embeddings; keyword fallback covers failure.
        vectors = self._embed([p["inbound"] for p in pairs]) if pairs else []
        if vectors:
            with open(self._emb_path, "w", encoding="utf-8") as f:
                json.dump(vectors, f)
        elif os.path.exists(self._emb_path):
            os.remove(self._emb_path)  # stale vectors from a prior seed

    def retrieve(
        self, inbound_text: str, recipient_email: str, k: int = 4
    ) -> list[ReplyPair]:
        pairs = self._load_pairs()
        if not pairs:
            return []
        domain = recipient_email.split("@")[-1].lower() if "@" in recipient_email else ""
        vectors = self._load_embeddings()
        query_vec = self._embed([inbound_text])[0] if vectors else None

        if query_vec is not None and len(vectors) == len(pairs):
            scored = [
                (_cosine(query_vec, vec)
                 + (_DOMAIN_BOOST if domain and p.get("recipient_domain", "") == domain else 0),
                 p)
                for p, vec in zip(pairs, vectors, strict=False)
            ]
        else:
            # keyword-overlap fallback
            query = _tokens(inbound_text)
            scored = [
                (sum((query & _tokens(p["inbound"])).values())
                 + (2.0 if domain and p.get("recipient_domain", "") == domain else 0),
                 p)
                for p in pairs
            ]
        scored.sort(key=lambda s: s[0], reverse=True)
        return [p for _, p in scored[:k]]

    def summary(self) -> str:
        if os.path.exists(self._summary_path):
            with open(self._summary_path, encoding="utf-8") as f:
                return f.read()
        return self._default_summary()

    # ---- embeddings ----
    def _embed(self, texts: list[str]) -> list[list[float]]:
        """Embed texts with the OpenAI model. Returns [] on any failure (-> fallback)."""
        settings = get_settings()
        if not settings.openai_api_key or not texts:
            return []
        try:
            from openai import OpenAI

            client = OpenAI(api_key=settings.openai_api_key)
            resp = client.embeddings.create(model=settings.openai_embed_model, input=texts)
            return [d.embedding for d in resp.data]
        except Exception:  # noqa: BLE001 - retrieval degrades to keyword mode
            return []

    def _load_embeddings(self) -> list[list[float]]:
        if not os.path.exists(self._emb_path):
            return []
        with open(self._emb_path, encoding="utf-8") as f:
            return json.load(f)

    # ---- helpers ----
    def _load_pairs(self) -> list[ReplyPair]:
        if not os.path.exists(self._pairs_path):
            return []
        with open(self._pairs_path, encoding="utf-8") as f:
            return json.load(f)

    @staticmethod
    def _default_summary() -> str:
        return (
            "Write a clear, friendly, concise reply. Match a professional but warm tone. "
            "Keep it short and get to the point."
        )

    def _build_summary(self, pairs: list[ReplyPair]) -> str:
        if not pairs:
            return self._default_summary()
        avg_words = round(sum(p.get("reply_words", 0) for p in pairs) / max(len(pairs), 1))
        return (
            f"Based on {len(pairs)} of your recent replies. Your replies average about "
            f"{avg_words} words. Tone: professional and friendly. Prefer concise, direct "
            "answers and a brief sign-off."
        )
