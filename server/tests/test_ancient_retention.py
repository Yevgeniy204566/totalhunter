"""Tests for ancient_retention.py — inactivity-based purge of Ancient-only
tables for hidden collectors. Chest/PlayerAlias/ChestCollector must survive."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import select

from models import (
    AncientCalculation, AncientNameMapping, AncientRoster, Chest,
    ChestCollector, PlayerAlias,
)
from ancient_retention import run_ancient_retention_tick, run_manual_entry_expiry_tick


async def _make_collector(db, **overrides):
    defaults = dict(kingdom="K1", clan="ClanA", user_id=1,
                    slug=f"slug-{datetime.utcnow().timestamp()}")
    defaults.update(overrides)
    c = ChestCollector(**defaults)
    db.add(c)
    await db.flush()
    return c


@pytest.mark.asyncio
async def test_tick_ignores_collector_hidden_recently(db_session):
    collector = await _make_collector(
        db_session, slug="recent-hide", ancient_hidden=True,
        ancient_hidden_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    db_session.add(AncientRoster(collector_id=collector.id, player_name="P1", place=1, points=10))
    await db_session.commit()

    purged = await run_ancient_retention_tick(db_session)

    assert purged == 0
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_tick_ignores_visible_collector(db_session):
    collector = await _make_collector(
        db_session, slug="visible-1", ancient_hidden=False, ancient_hidden_at=None,
    )
    db_session.add(AncientRoster(collector_id=collector.id, player_name="P1", place=1, points=10))
    await db_session.commit()

    purged = await run_ancient_retention_tick(db_session)

    assert purged == 0
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_tick_purges_ancient_tables_for_stale_hidden_collector(db_session):
    collector = await _make_collector(
        db_session, slug="stale-hide", ancient_hidden=True,
        ancient_hidden_at=datetime.now(timezone.utc) - timedelta(days=61),
    )
    db_session.add(AncientRoster(collector_id=collector.id, player_name="P1", place=1, points=10))
    db_session.add(AncientNameMapping(collector_id=collector.id, raw_ocr_name="p1", canonical_name="P1"))
    db_session.add(AncientCalculation(
        collector_id=collector.id, strategy="A", summon_levels=[81],
        amplification_coef=1.0, officer_count=1, veteran_count=0,
        total_quota_millions=1.0, result_json={},
    ))
    db_session.add(Chest(
        collector_id=collector.id, chest_type_raw="Epic", chest_type_canonical="Epic",
        sender_raw="P1", sender_canonical="P1", collected_at=datetime.utcnow(),
    ))
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="p1raw", canonical_name="P1"))
    await db_session.commit()

    purged = await run_ancient_retention_tick(db_session)

    assert purged == 1
    assert (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all() == []
    assert (await db_session.execute(
        select(AncientNameMapping).where(AncientNameMapping.collector_id == collector.id)
    )).scalars().all() == []
    assert (await db_session.execute(
        select(AncientCalculation).where(AncientCalculation.collector_id == collector.id)
    )).scalars().all() == []
    assert len((await db_session.execute(
        select(Chest).where(Chest.collector_id == collector.id)
    )).scalars().all()) == 1
    assert len((await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()) == 1
    await db_session.refresh(collector)
    assert collector.ancient_hidden_at is None
    assert collector.ancient_hidden is True


@pytest.mark.asyncio
async def test_expiry_tick_deletes_expired_manual_entry(db_session):
    collector = await _make_collector(db_session, slug="expired-manual-1")
    db_session.add(AncientRoster(
        collector_id=collector.id, player_name="Просрочен",
        source="manual", manual_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    ))
    await db_session.commit()

    deleted = await run_manual_entry_expiry_tick(db_session)

    assert deleted == 1
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_expiry_tick_ignores_not_yet_expired_manual_entry(db_session):
    collector = await _make_collector(db_session, slug="fresh-manual-1")
    db_session.add(AncientRoster(
        collector_id=collector.id, player_name="Свежий",
        source="manual", manual_expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
    ))
    await db_session.commit()

    deleted = await run_manual_entry_expiry_tick(db_session)

    assert deleted == 0
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_expiry_tick_ignores_ocr_rows_regardless_of_dates(db_session):
    """source='ocr' rows never have manual_expires_at set, and must never be
    touched by this tick even if some future bug set a past timestamp on one."""
    collector = await _make_collector(db_session, slug="ocr-with-past-date-1")
    db_session.add(AncientRoster(
        collector_id=collector.id, player_name="ОбычныйИгрок",
        source="ocr", manual_expires_at=datetime.now(timezone.utc) - timedelta(hours=1),
    ))
    await db_session.commit()

    deleted = await run_manual_entry_expiry_tick(db_session)

    assert deleted == 0
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1


def test_app_startup_schedules_ancient_retention_background_task(monkeypatch):
    import ancient_retention
    calls = []
    monkeypatch.setattr(ancient_retention, "ensure_background_tasks", lambda: calls.append(True))

    from starlette.testclient import TestClient
    from main import app
    with TestClient(app) as client:
        client.get("/version/latest")

    assert calls == [True]
