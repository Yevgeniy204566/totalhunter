"""
roy.py — Система РОЙ: Proof of Scan + пул координат бирж.

Эндпоинты:
    POST /roy/report     — репорт координат биржи (K, X, Y, %)
    POST /roy/scan       — фиксация активности (+45 сек баланса за 30 сек скана)
    GET  /roy/pool       — получить актуальный пул координат
    GET  /roy/balance/{hwid} — текущий баланс времени
"""

import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import RoyBalance, RoyPool

router = APIRouter(prefix="/roy", tags=["roy"])

POOL_TTL_MIN      = 20   # координата живёт 20 минут
SCAN_REWARD_SEC   = 45   # 30 сек скана → 45 сек баланса (1.5x)
POOL_COST_SEC     = 60   # стоимость одного запроса пула
PERCENT_THRESHOLD = 90   # >= 90% — биржа выкуплена, не показываем
RATE_LIMIT_SEC    = 10   # минимальный интервал репортов с одного hwid

# in-memory rate limiter: hwid → unix timestamp последнего репорта
_report_rate: dict[str, float] = {}


# ── Pydantic ──────────────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    hwid:    str
    kingdom: int
    x:       int
    y:       int
    percent: int


class ScanRequest(BaseModel):
    hwid: str


# ── POST /roy/report ──────────────────────────────────────────────────────────

@router.post("/report")
async def report_exchange(req: ReportRequest, db: AsyncSession = Depends(get_db)):
    """
    Принимает координаты биржи от бота.
    - Rate limit: не чаще 1 раза в 10 сек с одного hwid
    - Дедупликация: если K:X:Y уже есть в пуле — обновляем % и продлеваем TTL
    - Если % >= 90 и запись есть — помечаем как выкупленную (обновляем %)
    """
    now_ts = time.time()
    if now_ts - _report_rate.get(req.hwid, 0) < RATE_LIMIT_SEC:
        return {"success": True, "note": "rate_limited"}
    _report_rate[req.hwid] = now_ts

    now     = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=POOL_TTL_MIN)

    async with db.begin():
        existing = (await db.execute(
            select(RoyPool).where(
                RoyPool.kingdom   == req.kingdom,
                RoyPool.x         == req.x,
                RoyPool.y         == req.y,
                RoyPool.expires_at > now,
            )
        )).scalar_one_or_none()

        if existing:
            existing.percent    = req.percent
            existing.updated_at = now
            existing.expires_at = expires
        else:
            db.add(RoyPool(
                kingdom=req.kingdom, x=req.x, y=req.y,
                percent=req.percent, reporter_hwid=req.hwid,
                expires_at=expires,
            ))

    return {"success": True}


# ── POST /roy/scan ────────────────────────────────────────────────────────────

@router.post("/scan")
async def report_scan(req: ScanRequest, db: AsyncSession = Depends(get_db)):
    """
    Вызывается ботом каждые 30 сек во время активного сканирования.
    Начисляет 45 сек баланса (1.5x коэффициент).
    """
    now = datetime.now(timezone.utc)

    async with db.begin():
        row = (await db.execute(
            select(RoyBalance).where(RoyBalance.hwid == req.hwid)
        )).scalar_one_or_none()

        if row:
            row.balance_sec += SCAN_REWARD_SEC
            row.updated_at   = now
        else:
            db.add(RoyBalance(hwid=req.hwid, balance_sec=SCAN_REWARD_SEC))

    return {"success": True}


# ── GET /roy/pool ─────────────────────────────────────────────────────────────

@router.get("/pool")
async def get_pool(hwid: str, consume: bool = False, db: AsyncSession = Depends(get_db)):
    """
    Возвращает актуальные координаты бирж (<90%, не истёкшие).
    Требует balance_sec > 0.
    consume=true — списывает POOL_COST_SEC (60 сек) за запрос.
    """
    now = datetime.now(timezone.utc)

    bal_row = (await db.execute(
        select(RoyBalance).where(RoyBalance.hwid == hwid)
    )).scalar_one_or_none()

    balance = bal_row.balance_sec if bal_row else 0

    if balance <= 0:
        return {"success": False, "reason": "no_balance", "balance_sec": 0, "pool": []}

    entries = (await db.execute(
        select(RoyPool).where(
            RoyPool.expires_at > now,
            RoyPool.percent    < PERCENT_THRESHOLD,
        ).order_by(RoyPool.updated_at.desc()).limit(50)
    )).scalars().all()

    if consume and bal_row:
        async with db.begin():
            bal_row.balance_sec = max(0, bal_row.balance_sec - POOL_COST_SEC)
            bal_row.updated_at  = now

    return {
        "success":     True,
        "balance_sec": balance,
        "pool": [
            {
                "kingdom":    e.kingdom,
                "x":          e.x,
                "y":          e.y,
                "percent":    e.percent,
                "updated_at": e.updated_at.isoformat() if e.updated_at else None,
            }
            for e in entries
        ],
    }


# ── GET /roy/balance/{hwid} ───────────────────────────────────────────────────

@router.get("/balance/{hwid}")
async def get_balance(hwid: str, db: AsyncSession = Depends(get_db)):
    """Текущий баланс времени доступа к Рою."""
    row = (await db.execute(
        select(RoyBalance).where(RoyBalance.hwid == hwid)
    )).scalar_one_or_none()

    return {
        "hwid":        hwid,
        "balance_sec": row.balance_sec if row else 0,
    }
