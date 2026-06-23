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
from models import AncientCalculation, AncientRoster, ChestCollector, User
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
