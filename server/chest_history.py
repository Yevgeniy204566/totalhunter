"""
chest_history.py — Архив закрытых сезонов сундуков.

Авто-цикл: каждый chest_collectors с заданным period_end проверяется
независимо (не общий таймер для всех кланов). Когда "время клана"
(utcnow() + timezone_offset_minutes) переваливает за period_end — сезон
архивируется (готовый summary_json + снимок целей) в chest_season_history,
сырые Chest-строки за период удаляются, и сразу открывается новый период
той же длительности.

Сравнение буквальное (naive), без повторного TZ-сдвига — period_end хранится
как буквальные цифры с клиента (как и Chest.collected_at), не настоящий UTC.
См. ANTI-PATTERNS.md "Время на публичной странице сундуков" — тот же класс
бага воспроизводится здесь, если сравнивать через aware datetime.

Отдельный суточный тик удаляет записи chest_season_history старше
RETENTION_DAYS (3 месяца), считая от closed_at (момент архивации), не от
period_end.
"""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from chest_summary import pivot_summary, query_summary_rows
from database import AsyncSessionLocal
from models import Chest, ChestCollector, ChestSeasonHistory

ARCHIVE_TICK_SEC   = 300    # 5 минут — сезоны измеряются неделями, чаще не нужно
RETENTION_DAYS     = 90     # 3 месяца хранения истории
RETENTION_TICK_SEC = 86400  # раз в сутки

_archive_task:   asyncio.Task | None = None
_retention_task: asyncio.Task | None = None


def _clan_now(timezone_offset_minutes: int | None) -> datetime:
    return datetime.utcnow() + timedelta(minutes=timezone_offset_minutes or 0)


def _strip_tz(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def is_due(collector: ChestCollector) -> bool:
    if collector.period_end is None:
        return False
    return _clan_now(collector.timezone_offset_minutes) >= _strip_tz(collector.period_end)


async def archive_one(db: AsyncSession, collector: ChestCollector) -> None:
    period_start = collector.period_start
    period_end = collector.period_end

    rows = await query_summary_rows(db, collector, period_start, period_end)
    summary = pivot_summary(collector.kingdom, collector.clan, rows)

    db.add(ChestSeasonHistory(
        collector_id=collector.id,
        period_start=period_start,
        period_end=period_end,
        target_points_snapshot=collector.target_points,
        target_chests_snapshot=collector.target_chests,
        summary_json=summary,
    ))
    await db.execute(
        delete(Chest).where(
            Chest.collector_id == collector.id,
            Chest.collected_at >= period_start,
            Chest.collected_at <= period_end,
        )
    )
    duration = period_end - period_start
    collector.period_start = period_end
    collector.period_end = period_end + duration


async def run_archive_tick(db: AsyncSession) -> int:
    """Проходит по всем коллекторам с заданным period_end, архивирует просроченные.
    Возвращает количество заархивированных сезонов."""
    collectors = (await db.execute(
        select(ChestCollector).where(ChestCollector.period_end.is_not(None))
    )).scalars().all()
    archived = 0
    for collector in collectors:
        if is_due(collector):
            await archive_one(db, collector)
            archived += 1
    if archived:
        await db.commit()
    return archived


async def run_retention_tick(db: AsyncSession) -> int:
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    result = await db.execute(
        delete(ChestSeasonHistory).where(ChestSeasonHistory.closed_at < cutoff)
    )
    await db.commit()
    return result.rowcount or 0


async def build_history_list(db: AsyncSession, collector_id: int) -> list[dict]:
    rows = (await db.execute(
        select(ChestSeasonHistory)
        .where(ChestSeasonHistory.collector_id == collector_id)
        .order_by(ChestSeasonHistory.period_end.desc())
    )).scalars().all()
    return [
        {
            "id": r.id,
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
            "total_points": r.summary_json.get("totals", {}).get("total_points", 0),
        }
        for r in rows
    ]


async def build_history_detail(db: AsyncSession, collector_id: int,
                               season_id: int) -> dict | None:
    season = (await db.execute(
        select(ChestSeasonHistory).where(
            ChestSeasonHistory.id == season_id,
            ChestSeasonHistory.collector_id == collector_id,
        )
    )).scalar_one_or_none()
    if not season:
        return None
    result = dict(season.summary_json)
    result["period_start"] = season.period_start.isoformat()
    result["period_end"] = season.period_end.isoformat()
    result["targets"] = {
        "points": season.target_points_snapshot,
        "chests": season.target_chests_snapshot,
    }
    return result


def ensure_background_tasks() -> None:
    """Запускается раз за жизнь процесса из main.py при старте приложения."""
    global _archive_task, _retention_task
    if _archive_task is None or _archive_task.done():
        _archive_task = asyncio.create_task(_archive_loop())
    if _retention_task is None or _retention_task.done():
        _retention_task = asyncio.create_task(_retention_loop())


async def _archive_loop() -> None:
    while True:
        await asyncio.sleep(ARCHIVE_TICK_SEC)
        async with AsyncSessionLocal() as db:
            await run_archive_tick(db)


async def _retention_loop() -> None:
    while True:
        await asyncio.sleep(RETENTION_TICK_SEC)
        async with AsyncSessionLocal() as db:
            await run_retention_tick(db)
