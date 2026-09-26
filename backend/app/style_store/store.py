"""Disk-backed stub StyleStore implementing Contract C.

Retrieval is a naive keyword-overlap ranker, not embeddings — good enough to exercise
the seed job, tools and API. The spec-04 owner replaces this file with the real RAG.
Files land under {base_dir}/{safe_user_id}/ so it survives restarts (no DB).
"""

from __future__ import annotations

import json
import os
import re
from collections import Counter

from ..types import ReplyPair

_WORD = re.compile(r"[a-z0-9']+")


def _tokens(text: str) -> Counter:
    return Counter(_WORD.findall(text.lower()))


def _safe(user_id: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]", "_", user_id)


class StyleStore:
    def __init__(self, user_id: str, base_dir: str):
        self.user_id = user_id
        self.base_dir = base_dir
        self.dir = os.path.join(base_dir, _safe(user_id))
        self._pairs_path = os.path.join(self.dir, "pairs.json")
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

    def retrieve(
        self, inbound_text: str, recipient_email: str, k: int = 4
    ) -> list[ReplyPair]:
        pairs = self._load_pairs()
        if not pairs:
            return []
        query = _tokens(inbound_text)
        domain = recipient_email.split("@")[-1].lower() if "@" in recipient_email else ""

        def score(p: ReplyPair) -> float:
            overlap = sum((query & _tokens(p["inbound"])).values())
            same_domain = 1.0 if domain and p.get("recipient_domain", "") == domain else 0.0
            return overlap + 2.0 * same_domain

        ranked = sorted(pairs, key=score, reverse=True)
        return ranked[:k]

    def summary(self) -> str:
        if os.path.exists(self._summary_path):
            with open(self._summary_path, encoding="utf-8") as f:
                return f.read()
        return self._default_summary()

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
