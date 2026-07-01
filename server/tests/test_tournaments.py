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
from models import AncientRoster, ChestCollector, PlayerAlias, User


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
async def test_fuzzy_match_uses_close_alias_canonical_name(db_session):
    user = await _create_user(db_session, "hwid5000000000a")
    await db_session.commit()

    # First import creates the collector and a baseline player.
    base_payload = _payload(
        user.hwid, clan="BERS5",
        items=[{"name": "Бандеролька", "place": 5, "points": 1264203992}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS5")
    )).scalar_one()
    # Leader already corrected this player's name once via the Chests dashboard.
    db_session.add(PlayerAlias(collector_id=collector.id,
                               raw_name="ban_d3r0lka_raw_ocr", canonical_name="Бандеролька"))
    await db_session.commit()

    # Next tournament scan reads the name with leftover VIP-badge noise — close to,
    # but not an exact match of, the confirmed canonical name.
    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Бандеролька __", "place": 5, "points": 1264203992}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Бандеролька"}


@pytest.mark.asyncio
async def test_fuzzy_match_does_not_match_dissimilar_name(db_session):
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

    # Cross-script OCR garble — must NOT be confidently matched to an unrelated alias.
    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Marisha?", "place": 12, "points": 1155240852}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Marisha?"}


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
