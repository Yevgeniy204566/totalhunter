"""Tests for ancients_dashboard.py — self-service «Древний» calculator for the
logged-in user. Mirrors the auth pattern from test_chest_dashboard.py (JWT Bearer,
db_session fixture, AsyncClient + ASGITransport — no auth_client/web_user fixtures
exist in conftest.py)."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import AncientCalculation, AncientNameMapping, AncientRoster, ChestCollector, PlayerAlias, PlayerProfile, User
from web_routes import create_jwt


async def _create_user_with_token(db, email="owner@example.com"):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6),
               email=email)
    db.add(user)
    await db.flush()
    token = create_jwt(user.id, email)
    return user, token


async def _create_collector(db, user_id, slug=None):
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=user_id,
                               slug=slug or secrets.token_urlsafe(16))
    db.add(collector)
    await db.flush()
    return collector


@pytest.mark.asyncio
async def test_get_roster_returns_players(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="s1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100, troop_level="G8 S8 M8"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["collectors"][0]["roster"][0]["player_name"] == "Иванов"
    assert data["collectors"][0]["roster"][0]["troop_level"] == "G8 S8 M8"


@pytest.mark.asyncio
async def test_patch_troop_level(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="s2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=100, troop_level=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/s2/troop-level",
            json={"player_name": "Петров", "troop_level": "G7 S7 M8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.troop_level == "G7 S7 M8"


@pytest.mark.asyncio
async def test_calculate_strategy_a_saves_history(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="s3")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/s3/calculate",
            json={
                "strategy": "A", "summon_levels": [81, 100],
                "amplification_coef": 1.5, "officer_count": 2, "veteran_count": 1,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_quota_millions"] == pytest.approx((45.1 + 114) * 1.5)
    assert "officer_quota" in body["result"]

    rows = (await db_session.execute(
        select(AncientCalculation).where(AncientCalculation.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_calculate_history_capped_at_5(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="s4")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(6):
            resp = await client.post(
                "/web/dashboard/ancients/s4/calculate",
                json={
                    "strategy": "A", "summon_levels": [81],
                    "amplification_coef": 1.0, "officer_count": 1, "veteran_count": 0,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    rows = (await db_session.execute(
        select(AncientCalculation).where(AncientCalculation.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 5


@pytest.mark.asyncio
async def test_roster_uses_profile_troop_level_as_fallback(db_session):
    user, token = await _create_user_with_token(db_session, "anc_prof1@test.com")
    collector = await _create_collector(db_session, user.id, slug="anc-pf-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Alice",
                                 place=1, points=1000, troop_level=None))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Alice",
                                 rank="Старший", troop_level="G8 S8 M8"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    roster = resp.json()["collectors"][0]["roster"]
    alice = next(r for r in roster if r["player_name"] == "Alice")
    assert alice["troop_level"] == "G8 S8 M8"


@pytest.mark.asyncio
async def test_roster_manual_troop_level_wins_over_profile(db_session):
    user, token = await _create_user_with_token(db_session, "anc_prof2@test.com")
    collector = await _create_collector(db_session, user.id, slug="anc-pf-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Bob",
                                 place=1, points=2000, troop_level="G9 S9 M9"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Bob",
                                 rank="Глава", troop_level="G5 S5 M5"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    roster = resp.json()["collectors"][0]["roster"]
    bob = next(r for r in roster if r["player_name"] == "Bob")
    assert bob["troop_level"] == "G9 S9 M9"


@pytest.mark.asyncio
async def test_get_roster_suggested_name_via_fuzzy(db_session):
    """Roster row gets suggested_name when fuzzy-match finds a canonical name."""
    user, token = await _create_user_with_token(db_session, "fuzzy1@test.com")
    collector = await _create_collector(db_session, user.id, slug="fuzzy-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Marisha",
                                 place=1, points=100, troop_level=None))
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="ocr_raw",
                               canonical_name="Маришка"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["player_name"] == "Marisha"
    assert row["mapping_confirmed"] is False
    assert row["mapped_name"] is None
    assert "is_alias_source" in row
    # cross-script fuzzy won't fire; suggested_name None → is_alias_source False
    assert row["is_alias_source"] is False


@pytest.mark.asyncio
async def test_get_roster_confirmed_mapping_applied(db_session):
    """Confirmed mapping → mapped_name populated, mapping_confirmed=True."""
    user, token = await _create_user_with_token(db_session, "mapped1@test.com")
    collector = await _create_collector(db_session, user.id, slug="mapped-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Marisha",
                                 place=1, points=100, troop_level=None))
    db_session.add(AncientNameMapping(collector_id=collector.id,
                                      raw_ocr_name="Marisha",
                                      canonical_name="Маришка",
                                      confirmed=True))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["mapped_name"] == "Маришка"
    assert row["mapping_confirmed"] is True
    assert row["suggested_name"] is None
    assert row["is_alias_source"] is False  # confirmed mapping → no suggestion active
