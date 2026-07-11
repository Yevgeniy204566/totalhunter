"""Tests for ancients_public.py — no-auth public roster page for «Древний»."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import (
    AncientCalculation, AncientNameMapping, AncientRoster, ChestCollector,
    PlayerProfile, User,
)


async def _create_user(db):
    u = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6))
    db.add(u)
    await db.flush()
    return u


async def _create_collector(db, user_id, slug=None, clan="ClanA", **kwargs):
    collector = ChestCollector(kingdom="K1", clan=clan, user_id=user_id,
                               slug=slug or secrets.token_urlsafe(16), **kwargs)
    db.add(collector)
    await db.flush()
    return collector


@pytest.mark.asyncio
async def test_public_ancients_404_for_unknown_slug(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_ancients_returns_roster_without_mapping_fields(db_session):
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="pub-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100, rank="Офицер",
                                 troop_level="G8 S8 M8", source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/pub-1")
    assert resp.status_code == 200
    data = resp.json()
    assert data["kingdom"] == "K1"
    assert data["clan"] == "ClanA"
    row = data["roster"][0]
    assert row["player_name"] == "Иванов"
    assert row["rank"] == "Офицер"
    assert row["troop_level"] == "G8 S8 M8"
    assert row["points"] == 100
    assert "raw_ocr_name" not in row
    assert "mapped_name" not in row
    assert "suggested_name" not in row
    assert "mapping_confirmed" not in row


@pytest.mark.asyncio
async def test_public_ancients_falls_back_to_player_profile(db_session):
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="pub-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Сидоров",
                                 troop_level=None, rank=None, source="manual"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Сидоров",
                                 rank="Ветеран", troop_level="G7 S7 M7"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/pub-2")
    row = resp.json()["roster"][0]
    assert row["rank"] == "Ветеран"
    assert row["troop_level"] == "G7 S7 M7"


@pytest.mark.asyncio
async def test_public_ancients_includes_quota_and_shortfall(db_session):
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="pub-3")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 points=50, rank="Глава", source="manual"))
    db_session.add(AncientCalculation(
        collector_id=collector.id, strategy="A", summon_levels=[81],
        amplification_coef=1.0, officer_count=1, veteran_count=0,
        total_quota_millions=100.0,
        result_json={"officer_quota": 100.0, "veteran_quota": 0.0},
    ))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/pub-3")
    row = resp.json()["roster"][0]
    assert row["quota"] == pytest.approx(100.0)
    assert row["shortfall_pct"] == pytest.approx(50.0)


@pytest.mark.asyncio
async def test_public_ancients_includes_quota_thresholds(db_session):
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="pub-4",
                                        ancient_shortfall_light_pct=15.0,
                                        ancient_shortfall_medium_pct=40.0,
                                        ancient_shortfall_critical_pct=70.0)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/pub-4")
    assert resp.json()["quota_thresholds"] == {
        "light_pct": 15.0, "medium_pct": 40.0, "critical_pct": 70.0,
    }


@pytest.mark.asyncio
async def test_public_ancients_strategy_b_resolves_confirmed_mapping_not_yet_merged(db_session):
    """Regression: calculate()'s Strategy-B branch stores each player under
    the confirmed AncientNameMapping.canonical_name (mirroring _roster_rows'
    resolution) even when the roster row hasn't been physically merged yet
    (raw_ocr_name is still NULL/unset on the row, i.e. player_name IS the raw
    OCR name). The public endpoint must apply the same resolution to find
    the right lookup_name — matching raw player_name against result_json
    would miss the entry entirely and show quota: None, while the dashboard
    (_roster_rows) shows the correct quota for the identical calculation."""
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="pub-6")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Ivanov_raw",
                                 points=10, rank="Ветеран", source="ocr"))
    db_session.add(AncientNameMapping(collector_id=collector.id, raw_ocr_name="Ivanov_raw",
                                      canonical_name="Ivanov", confirmed=True))
    db_session.add(AncientCalculation(
        collector_id=collector.id, strategy="B", summon_levels=[81],
        amplification_coef=1.0, officer_count=0, veteran_count=1,
        total_quota_millions=42.0,
        result_json={"players": [{"name": "Ivanov", "quota": 42.0}]},
    ))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/pub-6")
    row = resp.json()["roster"][0]
    assert row["player_name"] == "Ivanov_raw"
    assert row["quota"] == pytest.approx(42.0)
    assert row["shortfall_pct"] == pytest.approx((42.0 - 10) / 42.0 * 100)
    assert "mapped_name" not in row
    assert "suggested_name" not in row
    assert "mapping_confirmed" not in row
    assert "raw_ocr_name" not in row


@pytest.mark.asyncio
async def test_public_ancients_visible_even_when_hidden_from_owner_dashboard(db_session):
    """ancient_hidden only affects the owner's own dashboard list — it must
    not block public access, same as documented for set_ancient_visibility."""
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="pub-5",
                                        ancient_hidden=True)
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Скрытый",
                                 source="manual"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/ancients/public/pub-5")
    assert resp.status_code == 200
    assert len(resp.json()["roster"]) == 1


@pytest.mark.asyncio
async def test_public_add_self_404_for_unknown_slug(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ancients/public/does-not-exist/roster",
            json={"player_name": "Новый", "rank": None, "troop_level": None},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_public_add_self_creates_manual_roster_entry(db_session):
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="addself-1")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ancients/public/addself-1/roster",
            json={"player_name": "Новичок", "rank": "Ветеран", "troop_level": "G7 S7 M7"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.player_name == "Новичок"
    assert row.rank == "Ветеран"
    assert row.troop_level == "G7 S7 M7"
    assert row.source == "manual"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        get_resp = await client.get("/api/v1/ancients/public/addself-1")
    assert get_resp.json()["roster"][0]["player_name"] == "Новичок"


@pytest.mark.asyncio
async def test_public_add_self_rejects_exact_duplicate(db_session):
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="addself-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Уже Есть", source="manual"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ancients/public/addself-2/roster",
            json={"player_name": "Уже Есть", "rank": None, "troop_level": None},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_public_add_self_rejects_similar_name(db_session):
    user = await _create_user(db_session)
    collector = await _create_collector(db_session, user.id, slug="addself-3")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Александров", source="manual"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ancients/public/addself-3/roster",
            json={"player_name": "Александрова", "rank": None, "troop_level": None},
        )
    assert resp.status_code == 409
    assert resp.json()["detail"]["similar_name"] == "Александров"


@pytest.mark.asyncio
async def test_public_add_self_rejects_invalid_troop_level(db_session):
    user = await _create_user(db_session)
    await _create_collector(db_session, user.id, slug="addself-4")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ancients/public/addself-4/roster",
            json={"player_name": "Игрок", "rank": None, "troop_level": "bad"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_public_add_self_rejects_blank_name(db_session):
    user = await _create_user(db_session)
    await _create_collector(db_session, user.id, slug="addself-5")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/ancients/public/addself-5/roster",
            json={"player_name": "  ", "rank": None, "troop_level": None},
        )
    assert resp.status_code == 400
