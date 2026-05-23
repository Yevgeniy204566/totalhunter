"""
roy.py — Система РОЙ: Proof of Scan + пул координат бирж + статус королевств.

Эндпоинты:
    POST /roy/report          — репорт координат биржи (K, X, Y, %)
    POST /roy/scan            — фиксация активности (+45 сек баланса за 30 сек скана)
    POST /roy/stop            — сигнал остановки поиска в королевстве
    GET  /roy/pool            — получить актуальный пул координат
    GET  /roy/balance/{hwid}  — текущий баланс времени
    GET  /roy/kingdoms        — список королевств с active_count (для сайта)
    GET  /roy/status-stream   — SSE-поток обновлений статуса королевств
"""

import asyncio
import json
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal, get_db
from models import RoyBalance, RoyKingdomStatus, RoyPool

router = APIRouter(prefix="/roy", tags=["roy"])

POOL_TTL_MIN      = 20    # координата живёт 20 минут
SCAN_REWARD_SEC   = 45    # 30 сек скана → 45 сек баланса (1.5x)
POOL_COST_SEC     = 60    # стоимость одного запроса пула
PERCENT_THRESHOLD = 90    # >= 90% — биржа выкуплена, не показываем
RATE_LIMIT_SEC    = 10    # минимальный интервал репортов с одного hwid
SESSION_TTL_SEC   = 300   # 5 минут без пинга = сессия считается мёртвой

# in-memory rate limiter: hwid → unix timestamp последнего репорта
_report_rate:  dict[str, float]             = {}
# активные сессии: (hwid, kingdom) → timestamp последнего пинга
_hwid_kingdom: dict[tuple[str, int], float] = {}
# подписчики SSE
_sse_queues:   list[asyncio.Queue]          = []
# ссылка на фоновую задачу очистки
_cleanup_task: asyncio.Task | None          = None


# ── Internal helpers ──────────────────────────────────────────────────────────

def _active_count(kingdom: int) -> int:
    """Количество активных ботов в ГОСе по данным в памяти."""
    cutoff = time.time() - SESSION_TTL_SEC
    return sum(1 for (h, k), ts in _hwid_kingdom.items() if k == kingdom and ts > cutoff)


async def _kingdoms_payload(db: AsyncSession) -> str:
    """JSON-строка со списком всех королевств и их live-счётчиками."""
    rows = (await db.execute(select(RoyKingdomStatus))).scalars().all()
    return json.dumps([
        {
            "kingdom":      row.kingdom,
            "active_count": _active_count(row.kingdom),
            "active":       _active_count(row.kingdom) > 0,
        }
        for row in rows
    ])


async def _broadcast(db: AsyncSession) -> None:
    """Разослать актуальное состояние всем SSE-подписчикам."""
    if not _sse_queues:
        return
    payload = await _kingdoms_payload(db)
    for q in list(_sse_queues):
        await q.put(payload)


async def _upsert_kingdom(db: AsyncSession, kingdom: int) -> None:
    """Upsert строки RoyKingdomStatus. Создаёт запись только если count > 0."""
    row = (await db.execute(
        select(RoyKingdomStatus).where(RoyKingdomStatus.kingdom == kingdom)
    )).scalar_one_or_none()
    now   = datetime.now(timezone.utc)
    count = _active_count(kingdom)
    if row:
        row.active_count = count
        row.last_seen_at = now
    elif count > 0:
        db.add(RoyKingdomStatus(kingdom=kingdom, active_count=count, last_seen_at=now))


def _ensure_cleanup() -> None:
    """Ленивый старт фоновой задачи очистки (один раз за жизнь процесса)."""
    global _cleanup_task
    if _cleanup_task is None or _cleanup_task.done():
        _cleanup_task = asyncio.create_task(_cleanup_loop())


async def _cleanup_loop() -> None:
    """Каждые 2 мин удаляет мёртвые сессии и обновляет DB + SSE."""
    while True:
        await asyncio.sleep(120)
        cutoff  = time.time() - SESSION_TTL_SEC
        stale   = [key for key, ts in list(_hwid_kingdom.items()) if ts < cutoff]
        if not stale:
            continue
        changed = {k for _, k in stale}
        for key in stale:
            _hwid_kingdom.pop(key, None)
        async with AsyncSessionLocal() as db:
            async with db.begin():
                for kingdom in changed:
                    row = (await db.execute(
                        select(RoyKingdomStatus).where(RoyKingdomStatus.kingdom == kingdom)
                    )).scalar_one_or_none()
                    if row:
                        row.active_count = _active_count(kingdom)
            await _broadcast(db)


# ── Pydantic ──────────────────────────────────────────────────────────────────

class ReportRequest(BaseModel):
    hwid:    str
    kingdom: int
    x:       int
    y:       int
    percent: int


class ScanRequest(BaseModel):
    hwid:    str
    kingdom: int | None = None  # None = старый клиент (backward compat)


class StopRequest(BaseModel):
    hwid:    str
    kingdom: int


# ── POST /roy/report ──────────────────────────────────────────────────────────

@router.post("/report")
async def report_exchange(req: ReportRequest, db: AsyncSession = Depends(get_db)):
    """
    Принимает координаты биржи от бота.
    Rate limit 10 сек / hwid. Дедупликация по K:X:Y с продлением TTL.
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
    Начисляет 45 сек баланса (1.5x).
    Если передан kingdom — обновляет статус ГОСа и уведомляет SSE.
    """
    _ensure_cleanup()
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

        if req.kingdom is not None:
            _hwid_kingdom[(req.hwid, req.kingdom)] = time.time()
            await _upsert_kingdom(db, req.kingdom)

    if req.kingdom is not None:
        await _broadcast(db)

    return {"success": True}


# ── POST /roy/stop ────────────────────────────────────────────────────────────

@router.post("/stop")
async def stop_scan(req: StopRequest, db: AsyncSession = Depends(get_db)):
    """
    Бот сообщает о завершении поиска в ГОСе (кнопка Stop или закрытие программы).
    Декрементирует active_count и уведомляет SSE.
    """
    _hwid_kingdom.pop((req.hwid, req.kingdom), None)

    async with db.begin():
        await _upsert_kingdom(db, req.kingdom)

    await _broadcast(db)
    return {"success": True}


# ── GET /roy/kingdoms ─────────────────────────────────────────────────────────

@router.get("/kingdoms")
async def get_kingdoms(db: AsyncSession = Depends(get_db)):
    """Список всех королевств с live-счётчиком активных искателей."""
    rows = (await db.execute(select(RoyKingdomStatus))).scalars().all()
    return {
        "kingdoms": [
            {
                "kingdom":      row.kingdom,
                "active_count": _active_count(row.kingdom),
                "active":       _active_count(row.kingdom) > 0,
            }
            for row in rows
        ]
    }


# ── GET /roy/status-stream (SSE) ──────────────────────────────────────────────

@router.get("/status-stream")
async def kingdom_status_stream():
    """
    Server-Sent Events: фронтенд подписывается и получает обновления статуса
    реактивно — без polling. Keepalive каждые 25 сек.
    """
    q: asyncio.Queue = asyncio.Queue()
    _sse_queues.append(q)

    async def generate():
        try:
            async with AsyncSessionLocal() as db:
                initial = await _kingdoms_payload(db)
            yield f"data: {initial}\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=25)
                    yield f"data: {payload}\n\n"
                except asyncio.TimeoutError:
                    yield ": keepalive\n\n"
        except Exception:
            pass
        finally:
            if q in _sse_queues:
                _sse_queues.remove(q)

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


# ── GET /roy/pool ─────────────────────────────────────────────────────────────

@router.get("/pool")
async def get_pool(hwid: str, consume: bool = False, db: AsyncSession = Depends(get_db)):
    """
    Возвращает актуальные координаты бирж (<90%, не истёкшие).
    consume=true — списывает 60 сек баланса за запрос.
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
