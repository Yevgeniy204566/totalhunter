"""
vault.py — Long-polling balance sync.

GET /vault/sync/{hwid} — бот подключается и ждёт изменения баланса.
notify_balance_changed(hwid) вызывается после начисления → мгновенно будит бота.
"""

import asyncio
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User

router = APIRouter(prefix="/vault", tags=["vault"])

_notifiers: Dict[str, asyncio.Event] = {}


def notify_balance_changed(hwid: str | None) -> None:
    """Вызывать после любого изменения кредитов. Будит ожидающий long-poll бота."""
    if hwid and hwid in _notifiers:
        _notifiers[hwid].set()


@router.get("/sync/{hwid}")
async def balance_sync(hwid: str, db: AsyncSession = Depends(get_db)):
    """
    Long-poll: держит соединение до изменения баланса или 50-секундного timeout.
    Бот переподключается сразу после каждого ответа.
    """
    event = asyncio.Event()
    _notifiers[hwid] = event

    try:
        await asyncio.wait_for(event.wait(), timeout=50.0)
    except asyncio.TimeoutError:
        pass  # Нормальный heartbeat — всё равно вернуть баланс
    finally:
        _notifiers.pop(hwid, None)

    result = await db.execute(select(User).where(User.hwid == hwid))
    user = result.scalar_one_or_none()
    if not user:
        return {"credits": 0, "ref_credits": 0}
    return {"credits": user.credits, "ref_credits": user.ref_credits}
