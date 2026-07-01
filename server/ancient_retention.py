"""
ancient_retention.py — авто-очистка данных «Древнего» для скрытых
неиспользуемых коллекторов.

Коллектор общий с Сундуками (ChestCollector), поэтому здесь удаляются ТОЛЬКО
таблицы Древнего (AncientRoster/AncientNameMapping/AncientCalculation/
AncientEditor/AncientInviteCode) — Chest, PlayerAlias и сам ChestCollector не
трогаются. Спека:
docs/superpowers/specs/2026-07-01-ancient-collector-retention-design.md

Таймер (ChestCollector.ancient_hidden_at) взводится при скрытии
(PATCH .../ancient-visibility {hidden:true}), сбрасывается в NULL при показе,
и сдвигается на текущий момент любой активностью (импорт ростера турнира,
расчёт квоты) пока коллектор скрыт — см. tournaments.py и
ancients_dashboard.py.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import (
    AncientCalculation, AncientEditor, AncientInviteCode,
    AncientNameMapping, AncientRoster, ChestCollector,
)

HIDDEN_RETENTION_DAYS = 60      # 2 месяца
RETENTION_TICK_SEC     = 86400  # раз в сутки

logger = logging.getLogger(__name__)

_retention_task: asyncio.Task | None = None


async def purge_one(db: AsyncSession, collector: ChestCollector) -> None:
    cid = collector.id
    await db.execute(delete(AncientRoster).where(AncientRoster.collector_id == cid))
    await db.execute(delete(AncientNameMapping).where(AncientNameMapping.collector_id == cid))
    await db.execute(delete(AncientCalculation).where(AncientCalculation.collector_id == cid))
    await db.execute(delete(AncientEditor).where(AncientEditor.collector_id == cid))
    await db.execute(delete(AncientInviteCode).where(AncientInviteCode.collector_id == cid))
    collector.ancient_hidden_at = None


async def run_ancient_retention_tick(db: AsyncSession) -> int:
    """Чистит данные Древнего для коллекторов, скрытых >= HIDDEN_RETENTION_DAYS
    без активности. Возвращает количество очищенных коллекторов."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=HIDDEN_RETENTION_DAYS)
    collectors = (await db.execute(
        select(ChestCollector).where(
            ChestCollector.ancient_hidden_at.is_not(None),
            ChestCollector.ancient_hidden_at < cutoff,
        )
    )).scalars().all()
    purged = 0
    for collector in collectors:
        try:
            await purge_one(db, collector)
            await db.commit()
            purged += 1
        except Exception:
            await db.rollback()
            logger.exception(
                "ancient_retention: purge_one failed for collector_id=%s, skipping",
                collector.id,
            )
    return purged


async def run_manual_entry_expiry_tick(db: AsyncSession) -> int:
    """Удаляет вручную добавленные строки ростера, чьё время жизни истекло
    (ближайшее завершение «Торговых Путей» на момент добавления прошло, а
    реальные данные так и не подтвердили игрока). Возвращает количество
    удалённых строк."""
    now = datetime.now(timezone.utc)
    result = await db.execute(
        delete(AncientRoster).where(
            AncientRoster.source == "manual",
            AncientRoster.manual_expires_at.is_not(None),
            AncientRoster.manual_expires_at < now,
        )
    )
    await db.commit()
    return result.rowcount or 0


def ensure_background_tasks() -> None:
    """Запускается раз за жизнь процесса из main.py при старте приложения."""
    global _retention_task
    if _retention_task is None or _retention_task.done():
        _retention_task = asyncio.create_task(_retention_loop())


async def _retention_loop() -> None:
    while True:
        await asyncio.sleep(RETENTION_TICK_SEC)
        async with AsyncSessionLocal() as db:
            await run_ancient_retention_tick(db)
            await run_manual_entry_expiry_tick(db)
