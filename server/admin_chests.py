"""Админка → «Сундуки»: отчёт по ростерам (одна строка = ростер). Только чтение.
Счётчики — по chests.created_at (момент загрузки на сервер): collected_at — игровое время и для «загружено когда»
не годится. Дубли отсекает уникальный ключ в базе, поэтому повторная отправка счётчики не меняет.
«В базе» — это сундуки, которые лежат сейчас (старые чистятся при закрытии сезона), а не за всё время."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Chest, ChestCollector, User

ADMIN_TZ = ZoneInfo("Europe/Kyiv")  # «сегодня» = календарные сутки владельца (владелец 2026-10-23)
SORTS = ("today", "week", "total", "last", "clan", "kingdom")


def kyiv_day_start_utc(now: datetime) -> datetime:
    """Начало текущих суток по Киеву в UTC (с учётом летнего времени)."""
    local = now.astimezone(ADMIN_TZ)
    return local.replace(hour=0, minute=0, second=0, microsecond=0).astimezone(timezone.utc)


def _iso(value):
    return value.isoformat() if value else None


async def rosters_report(db: AsyncSession, *, now: datetime | None = None, q: str | None = None,
                         owner_id: int | None = None, sort: str = "week", order: str = "desc") -> dict:
    if sort not in SORTS or order not in ("asc", "desc"):
        raise ValueError("bad sort")
    now = now or datetime.now(timezone.utc)
    today_from = kyiv_day_start_utc(now)
    week_from = now - timedelta(days=7)  # скользящее окно: ровно 7 суток назад уже не входит

    today_n = func.coalesce(func.sum(case((Chest.created_at >= today_from, 1), else_=0)), 0)
    week_n = func.coalesce(func.sum(case((Chest.created_at > week_from, 1), else_=0)), 0)
    total_n = func.count(Chest.id)
    last_at = func.max(Chest.created_at)

    query = (
        select(ChestCollector.id, ChestCollector.kingdom, ChestCollector.clan, ChestCollector.slug,
               User.id, User.email, User.hwid, today_n, week_n, total_n, last_at)
        .join(User, User.id == ChestCollector.user_id)
        .outerjoin(Chest, Chest.collector_id == ChestCollector.id)
        .group_by(ChestCollector.id, User.id)
    )
    if owner_id is not None:
        query = query.where(ChestCollector.user_id == owner_id)
    if q and q.strip():
        like = f"%{q.strip().lower()}%"
        query = query.where(or_(func.lower(User.email).like(like), func.lower(ChestCollector.clan).like(like),
                                func.lower(ChestCollector.kingdom).like(like)))

    rows = [
        {"collector_id": cid, "kingdom": kingdom, "clan": clan, "slug": slug, "owner_id": uid,
         "owner_email": email, "owner_hwid": hwid, "today": int(t or 0), "week": int(w or 0), "total": int(tot or 0),
         "last_upload_at": _iso(last)}
        for cid, kingdom, clan, slug, uid, email, hwid, t, w, tot, last in (await db.execute(query)).all()
    ]

    key = {"today": lambda r: r["today"], "week": lambda r: r["week"], "total": lambda r: r["total"],
           "last": lambda r: r["last_upload_at"] or "", "clan": lambda r: (r["clan"] or "").lower(),
           "kingdom": lambda r: r["kingdom"] or ""}[sort]
    rows.sort(key=key, reverse=(order == "desc"))
    totals = {k: sum(r[k] for r in rows) for k in ("today", "week", "total")}
    return {"rows": rows, "totals": totals, "today_from": _iso(today_from), "week_from": _iso(week_from),
            "timezone": "Europe/Kyiv"}
