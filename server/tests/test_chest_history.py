"""Tests for chest_history.py — season archive/rollover, retention, history reads."""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import select

from models import Chest, ChestCollector, ChestConfiguration, ChestSeasonHistory
from chest_history import (
    is_due, archive_one, run_archive_tick, run_retention_tick,
    build_history_list, build_history_detail,
)


async def _make_collector(db, **overrides):
    defaults = dict(
        kingdom="K1", clan="ClanA", user_id=1, slug=f"slug-{datetime.utcnow().timestamp()}",
        timezone_offset_minutes=0, target_points=None, target_chests=None,
    )
    defaults.update(overrides)
    c = ChestCollector(**defaults)
    db.add(c)
    await db.flush()
    return c


async def _add_chest(db, collector, sender, chest_type, collected_at):
    db.add(Chest(
        collector_id=collector.id, chest_type_raw=chest_type, chest_type_canonical=chest_type,
        sender_raw=sender, sender_canonical=sender, collected_at=collected_at,
    ))
    db.add(ChestConfiguration(
        collector_id=collector.id, catalog_id=chest_type, points=10,
        is_in_pattern=True, counts_toward_quota=True,
    ))


@pytest.mark.asyncio
async def test_is_due_false_when_period_end_is_none(db_session):
    collector = await _make_collector(db_session, period_end=None)
    assert is_due(collector) is False


@pytest.mark.asyncio
async def test_is_due_false_when_period_start_is_none(db_session):
    # period_end alone (no period_start) is how update_season_settings can leave
    # a collector after a partial PATCH -- must not be treated as a valid season.
    collector = await _make_collector(
        db_session,
        period_start=None,
        period_end=datetime.utcnow() - timedelta(days=1),
    )
    assert is_due(collector) is False


@pytest.mark.asyncio
async def test_is_due_false_when_period_end_in_future(db_session):
    collector = await _make_collector(
        db_session,
        period_start=datetime.utcnow() - timedelta(days=1),
        period_end=datetime.utcnow() + timedelta(days=1),
    )
    assert is_due(collector) is False


@pytest.mark.asyncio
async def test_is_due_true_when_period_end_in_past(db_session):
    collector = await _make_collector(
        db_session,
        period_start=datetime.utcnow() - timedelta(days=15),
        period_end=datetime.utcnow() - timedelta(days=1),
    )
    assert is_due(collector) is True


@pytest.mark.asyncio
async def test_is_due_respects_timezone_offset_at_the_boundary(db_session):
    # period_end is 90 minutes in the "future" by naive UTC, but the clan is at
    # UTC+3 (180 min) -- clan-local "now" is already past period_end.
    collector = await _make_collector(
        db_session,
        timezone_offset_minutes=180,
        period_start=datetime.utcnow() - timedelta(days=13),
        period_end=datetime.utcnow() + timedelta(minutes=90),
    )
    assert is_due(collector) is True


@pytest.mark.asyncio
async def test_archive_one_creates_history_row_with_snapshot(db_session):
    start = datetime.utcnow() - timedelta(days=14)
    end = datetime.utcnow() - timedelta(hours=1)
    collector = await _make_collector(
        db_session, period_start=start, period_end=end,
        target_points=500, target_chests=10,
    )
    await _add_chest(db_session, collector, "Игрок1", "EpicCrypt", start + timedelta(days=1))
    await db_session.commit()

    await archive_one(db_session, collector)
    await db_session.commit()

    history = (await db_session.execute(select(ChestSeasonHistory))).scalars().all()
    assert len(history) == 1
    row = history[0]
    assert row.collector_id == collector.id
    assert row.target_points_snapshot == 500
    assert row.target_chests_snapshot == 10
    assert row.summary_json["players"][0]["name"] == "Игрок1"
    assert row.summary_json["totals"]["total_points"] == 10


@pytest.mark.asyncio
async def test_archive_one_deletes_archived_chests(db_session):
    start = datetime.utcnow() - timedelta(days=14)
    end = datetime.utcnow() - timedelta(hours=1)
    collector = await _make_collector(db_session, period_start=start, period_end=end)
    await _add_chest(db_session, collector, "Игрок1", "EpicCrypt", start + timedelta(days=1))
    await db_session.commit()

    await archive_one(db_session, collector)
    await db_session.commit()

    remaining = (await db_session.execute(
        select(Chest).where(Chest.collector_id == collector.id)
    )).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_archive_one_rolls_period_forward_by_same_duration(db_session):
    start = datetime.utcnow() - timedelta(days=14)
    end = datetime.utcnow() - timedelta(hours=1)
    collector = await _make_collector(db_session, period_start=start, period_end=end)
    await db_session.commit()

    await archive_one(db_session, collector)
    await db_session.commit()

    assert collector.period_start == end
    assert collector.period_end == end + (end - start)


@pytest.mark.asyncio
async def test_archive_one_handles_empty_season_without_error(db_session):
    start = datetime.utcnow() - timedelta(days=14)
    end = datetime.utcnow() - timedelta(hours=1)
    collector = await _make_collector(db_session, period_start=start, period_end=end)
    await db_session.commit()

    await archive_one(db_session, collector)
    await db_session.commit()

    history = (await db_session.execute(select(ChestSeasonHistory))).scalars().all()
    assert len(history) == 1
    assert history[0].summary_json["players"] == []


@pytest.mark.asyncio
async def test_run_archive_tick_archives_only_due_collectors(db_session):
    due = await _make_collector(
        db_session, slug="due-collector", clan="ClanDue",
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow() - timedelta(hours=1),
    )
    not_due = await _make_collector(
        db_session, slug="not-due-collector", clan="ClanNotDue",
        period_start=datetime.utcnow() - timedelta(days=1),
        period_end=datetime.utcnow() + timedelta(days=13),
    )
    no_season = await _make_collector(db_session, slug="no-season-collector", clan="ClanNoSeason", period_end=None)
    await db_session.commit()

    archived_count = await run_archive_tick(db_session)

    assert archived_count == 1
    history = (await db_session.execute(select(ChestSeasonHistory))).scalars().all()
    assert len(history) == 1
    assert history[0].collector_id == due.id


@pytest.mark.asyncio
async def test_run_archive_tick_continues_after_one_collector_throws(db_session, monkeypatch):
    # A broken collector (e.g. period_start somehow None despite is_due passing,
    # or any other unexpected failure inside archive_one) must not poison the
    # whole tick -- other due collectors still get archived and committed.
    import chest_history

    good = await _make_collector(
        db_session, slug="good-collector", clan="ClanGood",
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow() - timedelta(hours=1),
    )
    bad = await _make_collector(
        db_session, slug="bad-collector", clan="ClanBad",
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow() - timedelta(hours=1),
    )
    await db_session.commit()

    real_archive_one = chest_history.archive_one

    async def flaky_archive_one(db, collector):
        if collector.id == bad.id:
            raise RuntimeError("boom")
        await real_archive_one(db, collector)

    monkeypatch.setattr(chest_history, "archive_one", flaky_archive_one)

    archived_count = await chest_history.run_archive_tick(db_session)

    assert archived_count == 1
    history = (await db_session.execute(select(ChestSeasonHistory))).scalars().all()
    assert len(history) == 1
    assert history[0].collector_id == good.id


@pytest.mark.asyncio
async def test_run_retention_tick_deletes_old_rows_keeps_recent(db_session):
    collector = await _make_collector(db_session)
    await db_session.commit()
    old_row = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=120),
        period_end=datetime.utcnow() - timedelta(days=106),
        summary_json={"players": []},
        closed_at=datetime.utcnow() - timedelta(days=100),
    )
    recent_row = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=20),
        period_end=datetime.utcnow() - timedelta(days=6),
        summary_json={"players": []},
        closed_at=datetime.utcnow() - timedelta(days=5),
    )
    db_session.add_all([old_row, recent_row])
    await db_session.commit()

    deleted_count = await run_retention_tick(db_session)

    assert deleted_count == 1
    remaining = (await db_session.execute(select(ChestSeasonHistory))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].closed_at == recent_row.closed_at


@pytest.mark.asyncio
async def test_build_history_list_returns_seasons_newest_first(db_session):
    collector = await _make_collector(db_session)
    await db_session.commit()
    older = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=28),
        period_end=datetime.utcnow() - timedelta(days=14),
        summary_json={"totals": {"total_points": 100}, "players": []},
    )
    newer = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow(),
        summary_json={"totals": {"total_points": 200}, "players": []},
    )
    db_session.add_all([older, newer])
    await db_session.commit()

    seasons = await build_history_list(db_session, collector.id)

    assert [s["total_points"] for s in seasons] == [200, 100]


@pytest.mark.asyncio
async def test_build_history_detail_returns_none_for_other_collector(db_session):
    owner = await _make_collector(db_session, slug="owner-collector", clan="ClanOwner")
    other = await _make_collector(db_session, slug="other-collector", clan="ClanOther")
    await db_session.commit()
    row = ChestSeasonHistory(
        collector_id=owner.id,
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow(),
        summary_json={"players": []},
    )
    db_session.add(row)
    await db_session.commit()

    detail = await build_history_detail(db_session, other.id, row.id)

    assert detail is None


@pytest.mark.asyncio
async def test_build_history_detail_includes_target_snapshot(db_session):
    collector = await _make_collector(db_session)
    await db_session.commit()
    row = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow(),
        target_points_snapshot=777,
        target_chests_snapshot=8,
        summary_json={"players": [], "totals": {"total_points": 0}},
    )
    db_session.add(row)
    await db_session.commit()

    detail = await build_history_detail(db_session, collector.id, row.id)

    assert detail["targets"] == {"points": 777, "chests": 8}
    assert "period_start" in detail and "period_end" in detail


@pytest.mark.asyncio
async def test_stopped_collector_tick_deletes_ancient_tables_too(db_session):
    from models import AncientCalculation, AncientNameMapping, AncientRoster, PlayerAlias
    from chest_history import run_stopped_collector_tick

    collector = await _make_collector(
        db_session, slug="stopped-with-ancient",
        stopped_at=datetime.utcnow() - timedelta(days=91),
    )
    db_session.add(AncientRoster(collector_id=collector.id, player_name="P1", place=1, points=10))
    db_session.add(AncientNameMapping(collector_id=collector.id, raw_ocr_name="p1", canonical_name="P1"))
    db_session.add(AncientCalculation(
        collector_id=collector.id, strategy="A", summon_levels=[81],
        amplification_coef=1.0, officer_count=1, veteran_count=0,
        total_quota_millions=1.0, result_json={},
    ))
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="p1raw", canonical_name="P1"))
    await db_session.commit()

    deleted = await run_stopped_collector_tick(db_session)

    assert deleted == 1
    assert (await db_session.execute(
        select(ChestCollector).where(ChestCollector.id == collector.id)
    )).scalar_one_or_none() is None
    assert (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all() == []
    assert (await db_session.execute(
        select(AncientNameMapping).where(AncientNameMapping.collector_id == collector.id)
    )).scalars().all() == []
    assert (await db_session.execute(
        select(AncientCalculation).where(AncientCalculation.collector_id == collector.id)
    )).scalars().all() == []
    # PlayerAlias behavior unchanged — still deleted with the collector.
    assert (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all() == []


@pytest.mark.asyncio
async def test_stopped_collector_tick_ignores_recent_stop(db_session):
    from chest_history import run_stopped_collector_tick
    collector = await _make_collector(
        db_session, slug="stopped-recent",
        stopped_at=datetime.utcnow() - timedelta(days=10),
    )
    await db_session.commit()

    deleted = await run_stopped_collector_tick(db_session)

    assert deleted == 0
    assert (await db_session.execute(
        select(ChestCollector).where(ChestCollector.id == collector.id)
    )).scalar_one_or_none() is not None


def test_app_startup_schedules_archive_background_tasks(monkeypatch):
    import chest_history
    calls = []
    monkeypatch.setattr(chest_history, "ensure_background_tasks", lambda: calls.append(True))

    from starlette.testclient import TestClient
    from main import app
    with TestClient(app) as client:
        client.get("/version/latest")

    assert calls == [True]
