"""Tests for tournaments.py — tournament roster import endpoint for «Древний»."""
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import AncientRoster, ChestCollector, Log, PlayerAlias, User


async def _create_user(db, hwid, is_banned=False, credits=100):
    u = User(hwid=hwid, ref_code=secrets.token_urlsafe(6), is_banned=is_banned, credits=credits)
    db.add(u)
    await db.flush()
    return u


def _payload(hwid, kingdom="K229", clan="BERS", items=None, timestamp="2026-06-23T10:00:00"):
    return {
        "hwid": hwid,
        "kingdom": kingdom,
        "clan": clan,
        "timestamp": timestamp,
        "items": items if items is not None else [
            {"name": "Иванов", "place": 1, "points": 26000},
            {"name": "Петров", "place": 2, "points": 24000},
        ],
    }


@pytest.mark.asyncio
async def test_import_creates_roster(db_session):
    user = await _create_user(db_session, "hwid1000000000a")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/tournaments/import", json=_payload(user.hwid))
    assert resp.status_code == 200
    assert resp.json()["count"] == 2

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS")
    )).scalar_one()
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Иванов", "Петров"}


@pytest.mark.asyncio
async def test_import_logs_ancient_ocr_import_event(db_session):
    user = await _create_user(db_session, "hwidlogimport0a")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/tournaments/import", json=_payload(user.hwid))
    assert resp.status_code == 200

    logs = (await db_session.execute(
        select(Log).where(Log.hwid == user.hwid, Log.event_type == "ancient_ocr_import")
    )).scalars().all()
    assert len(logs) == 1


@pytest.mark.asyncio
async def test_reimport_preserves_troop_level_for_existing_player(db_session):
    user = await _create_user(db_session, "hwid2000000000a")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERS2",
        items=[{"name": "Иванов", "place": 1, "points": 100}],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

        collector = (await db_session.execute(
            select(ChestCollector).where(
                ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS2")
        )).scalar_one()
        row = (await db_session.execute(
            select(AncientRoster).where(
                AncientRoster.collector_id == collector.id,
                AncientRoster.player_name == "Иванов")
        )).scalar_one()
        row.troop_level = "G8 S8 M8"
        await db_session.commit()

        reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                                items=[{"name": "Иванов", "place": 3, "points": 50}])
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    await db_session.refresh(row)
    assert row.place == 3
    assert row.points == 50
    assert row.troop_level == "G8 S8 M8"


@pytest.mark.asyncio
async def test_reimport_drops_player_no_longer_present(db_session):
    user = await _create_user(db_session, "hwid3000000000a")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERS3",
        items=[
            {"name": "Иванов", "place": 1, "points": 100},
            {"name": "Уходящий", "place": 2, "points": 50},
        ],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

        reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                                items=[{"name": "Иванов", "place": 1, "points": 100}])
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS3")
    )).scalar_one()
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Иванов"}


@pytest.mark.asyncio
async def test_import_stores_raw_ocr_name(db_session):
    """Every imported row always carries the exact raw OCR text in
    raw_ocr_name, regardless of whether it resolved to a canonical name."""
    user = await _create_user(db_session, "hwid5000000000a")
    await db_session.commit()

    payload = _payload(
        user.hwid, clan="BERS5",
        items=[{"name": "Бандеролька __", "place": 5, "points": 1264203992}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS5")
    )).scalar_one()
    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.player_name == "Бандеролька __"
    assert row.raw_ocr_name == "Бандеролька __"


@pytest.mark.asyncio
async def test_import_ignores_unconfirmed_playeralias_similarity(db_session):
    """PlayerAlias (Chests) no longer drives any resolution on import —
    even an exact PlayerAlias.raw_name key hit must NOT auto-resolve.
    Only a confirmed AncientNameMapping does (see next test)."""
    user = await _create_user(db_session, "hwid6000000000a")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERS6",
        items=[{"name": "Иванов", "place": 1, "points": 100}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS6")
    )).scalar_one()
    db_session.add(PlayerAlias(collector_id=collector.id,
                               raw_name="ivanov_raw_ocr", canonical_name="Иванов"))
    await db_session.commit()

    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Marisha?", "place": 12, "points": 1155240852}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Marisha?"}


@pytest.mark.asyncio
async def test_import_resolves_via_confirmed_ancient_name_mapping(db_session):
    """A confirmed AncientNameMapping (set via the dashboard) DOES resolve
    the raw import name to the canonical one, writing straight into the
    canonical row instead of creating a duplicate raw row."""
    user = await _create_user(db_session, "hwid7000000000b")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERS7B",
        items=[{"name": "Кузнецов", "place": 1, "points": 10}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS7B")
    )).scalar_one()
    from models import AncientNameMapping
    db_session.add(AncientNameMapping(collector_id=collector.id,
                                      raw_ocr_name="Кузнецoв_VIP",
                                      canonical_name="Кузнецов", confirmed=True))
    await db_session.commit()

    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Кузнецoв_VIP", "place": 2, "points": 999}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].player_name == "Кузнецов"
    assert rows[0].raw_ocr_name == "Кузнецoв_VIP"
    assert rows[0].points == 999


@pytest.mark.asyncio
async def test_import_does_not_charge_credits(db_session):
    user = await _create_user(db_session, "hwid4000000000a", credits=5)
    await db_session.commit()

    payload = _payload(
        user.hwid, clan="BERS4",
        items=[{"name": "Иванов", "place": 1, "points": 100}],
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/tournaments/import", json=payload)
    assert resp.status_code == 200

    await db_session.refresh(user)
    assert user.credits == 5  # unchanged — free feature


def _normalize_tz(dt):
    """Strip timezone for SQLite naive/aware comparison."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


@pytest.mark.asyncio
async def test_import_touches_ancient_hidden_at_when_hidden(db_session):
    user = await _create_user(db_session, "hwid7000000000a")
    collector = ChestCollector(
        kingdom="K229", clan="BERS7", user_id=user.id, slug="hidden-import-1",
        ancient_hidden=True,
        ancient_hidden_at=datetime.now(timezone.utc) - timedelta(days=55),
    )
    db_session.add(collector)
    await db_session.commit()
    old_touch = collector.ancient_hidden_at

    payload = _payload(user.hwid, clan="BERS7",
                       items=[{"name": "Иванов", "place": 1, "points": 100}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=payload)

    await db_session.refresh(collector)
    assert _normalize_tz(collector.ancient_hidden_at) > _normalize_tz(old_touch)


@pytest.mark.asyncio
async def test_import_rearms_timer_after_it_was_cleared_by_a_purge(db_session):
    user = await _create_user(db_session, "hwid8000000000a")
    collector = ChestCollector(
        kingdom="K229", clan="BERS8", user_id=user.id, slug="post-purge-import-1",
        ancient_hidden=True, ancient_hidden_at=None,
    )
    db_session.add(collector)
    await db_session.commit()

    payload = _payload(user.hwid, clan="BERS8",
                       items=[{"name": "Иванов", "place": 1, "points": 100}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=payload)

    await db_session.refresh(collector)
    assert collector.ancient_hidden_at is not None


@pytest.mark.asyncio
async def test_reimport_does_not_delete_manual_entry(db_session):
    """A manual roster row (no OCR name maps to it this cycle) survives a
    full tournament re-import, unlike normal OCR rows for players who left."""
    user = await _create_user(db_session, "hwid9000000000a")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERS9",
        items=[{"name": "Иванов", "place": 1, "points": 100}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS9")
    )).scalar_one()
    db_session.add(AncientRoster(collector_id=collector.id, player_name="РучнойИгрок",
                                 place=None, points=None, source="manual",
                                 manual_expires_at=datetime.now(timezone.utc) + timedelta(days=3)))
    await db_session.commit()

    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Иванов", "place": 1, "points": 100}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Иванов", "РучнойИгрок"}


@pytest.mark.asyncio
async def test_reimport_does_not_delete_chests_seeded_entry(db_session):
    """A row seeded by 'Populate from Chests' (source='chests') survives a
    full tournament re-import the same way a manual row does."""
    user = await _create_user(db_session, "hwidB000000000a")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERSB",
        items=[{"name": "Иванов", "place": 1, "points": 100}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERSB")
    )).scalar_one()
    db_session.add(AncientRoster(collector_id=collector.id, player_name="ИзСундуков",
                                 place=None, points=None, source="chests"))
    await db_session.commit()

    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Иванов", "place": 1, "points": 100}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Иванов", "ИзСундуков"}


@pytest.mark.asyncio
async def test_reimport_does_not_delete_merged_curated_row(db_session):
    """A row that was physically merged (has troop_level/rank from Chests,
    source='ocr' from the merge) must survive a later tournament reimport
    that doesn't mention that player — only its place/points reset, never
    the whole row deleted. Regression test for a data-loss bug where the
    reimport cleanup's source=='ocr' filter didn't distinguish curated
    merged rows from pure OCR junk rows."""
    user = await _create_user(db_session, "hwidC000000000a")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERSC",
        items=[{"name": "Иванов", "place": 1, "points": 100}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERSC")
    )).scalar_one()
    # Simulates a row already merged by _merge_roster_on_mapping_confirm:
    # curated troop_level/rank, but source ended up "ocr" from the merge.
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=5, points=80000, raw_ocr_name="Пeтрoв*VIP",
                                 troop_level="G8 S8 M8", rank="Офицер", source="ocr"))
    await db_session.commit()

    # Next tournament scan doesn't mention "Петров" at all (didn't
    # participate, or OCR read the name differently this round).
    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Иванов", "place": 1, "points": 100}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    row = (await db_session.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == "Петров")
    )).scalar_one_or_none()
    assert row is not None  # NOT deleted
    assert row.troop_level == "G8 S8 M8"
    assert row.rank == "Офицер"
    assert row.raw_ocr_name == "Пeтрoв*VIP"
    assert row.place is None  # place/points reset, since player wasn't in this scan
    assert row.points is None


@pytest.mark.asyncio
async def test_reimport_promotes_manual_entry_when_matched(db_session):
    """A manual entry whose name matches an incoming tournament row gets
    real place/points and its source flips to 'ocr' — no duplicate row, no
    more expiry."""
    user = await _create_user(db_session, "hwidA000000000a")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERSA",
        items=[{"name": "Петров", "place": 1, "points": 50}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERSA")
    )).scalar_one()
    db_session.add(AncientRoster(collector_id=collector.id, player_name="СталНоситьСундуки",
                                 place=None, points=None, source="manual",
                                 manual_expires_at=datetime.now(timezone.utc) + timedelta(days=3)))
    await db_session.commit()

    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[
                                {"name": "Петров", "place": 1, "points": 50},
                                {"name": "СталНоситьСундуки", "place": 5, "points": 20},
                            ])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 2
    promoted = next(r for r in rows if r.player_name == "СталНоситьСундуки")
    assert promoted.source == "ocr"
    assert promoted.manual_expires_at is None
    assert promoted.place == 5
    assert promoted.points == 20
