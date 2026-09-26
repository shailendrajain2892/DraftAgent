"""Style seed status. See Contract A."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from ..deps import current_user_id
from ..seed.job import get_status

router = APIRouter(tags=["style"])


@router.get("/style/status")
def style_status(user_id: str = Depends(current_user_id)):
    return get_status(user_id)
