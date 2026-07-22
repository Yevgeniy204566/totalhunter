"""
vault.py — Long-polling balance sync.

GET /vault/sync/{hwid} — бот подключается и ждёт изменения баланса.
notify_balance_changed(hwid) вызывается после начисления → мгновенно будит бота.
"""

import asyncio
from datetime import datetime, timedelta, timezone
from typing import Dict

from fastapi import APIRouter, Depends
from sqlalchemy import case, update
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

    # UPDATE вместо SELECT — этот long-poll работает непрерывно, пока бот
    # открыт (даже без охоты), поэтому заодно служит heartbeat'ом для
    # "онлайн"-статуса в админке, без единого лишнего запроса.
    # session_started_at ставится только на переходе оффлайн→онлайн, чтобы
    # админка могла показать "Онлайн с HH:MM", а не время последнего пинга.
    now = datetime.now(timezone.utc)
    threshold = now - timedelta(minutes=5)
    async with db.begin():
        row = (await db.execute(
            update(User).where(User.hwid == hwid)
            .values(
                session_started_at=case(
                    (User.last_seen.is_(None) | (User.last_seen < threshold), now),
                    else_=User.session_started_at,
                ),
                last_seen=now,
            )
            .returning(User.credits, User.ref_credits)
        )).first()

    if not row:
        return {"credits": 0, "ref_credits": 0}
    return {"credits": row.credits, "ref_credits": row.ref_credits}
