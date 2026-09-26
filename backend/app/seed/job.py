"""Background seed job + in-memory per-user status feeding GET /style/status."""

from __future__ import annotations

import threading
from datetime import UTC, datetime

from ..config import get_settings
from ..errors import DraftAgentError
from ..style_store import StyleStore
from ..tools import gmail_tools

# States: not_started, running, ready, failed
_status: dict[str, dict] = {}
_lock = threading.Lock()


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def get_status(user_id: str) -> dict:
    settings = get_settings()
    with _lock:
        st = _status.get(user_id)
    if st is None:
        store = StyleStore(user_id, settings.style_store_dir)
        if store.is_ready():
            return {
                "state": "ready",
                "pairs_count": store.pair_count(),
                "window_days": settings.seed_days,
                "updated_at": None,
                "error": None,
            }
        return {
            "state": "not_started",
            "pairs_count": 0,
            "window_days": settings.seed_days,
            "updated_at": None,
            "error": None,
        }
    return st


def _set(user_id: str, **fields) -> None:
    with _lock:
        cur = _status.get(user_id, {})
        cur.update(fields)
        cur["updated_at"] = _now()
        _status[user_id] = cur


async def run_seed(user_id: str) -> None:
    """Fetch recent reply pairs and seed the style store. Idempotent per folder."""
    settings = get_settings()
    store = StyleStore(user_id, settings.style_store_dir)

    # If the folder already exists for the user, skip seeding and mark ready.
    if store.is_ready():
        _set(
            user_id,
            state="ready",
            pairs_count=store.pair_count(),
            window_days=settings.seed_days,
            error=None,
        )
        return

    _set(user_id, state="running", pairs_count=0, window_days=settings.seed_days, error=None)
    try:
        pairs = await gmail_tools.fetch_recent_reply_pairs(
            user_id, days=settings.seed_days, max_pairs=settings.seed_max_pairs
        )
        store.seed(pairs)
        _set(user_id, state="ready", pairs_count=len(pairs), error=None)
    except DraftAgentError as exc:
        _set(user_id, state="failed", error=exc.message)
    except Exception as exc:  # noqa: BLE001 - surface any seed failure as status
        _set(user_id, state="failed", error=str(exc))
