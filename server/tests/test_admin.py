"""Tests for GET /admin/activity/{metric} — per-player usage breakdown tabs
(Рулетка/Сундуки/Крипты/Биржи/Древний) in the admin panel."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import Hunt, Log, Transaction, User

ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]


async def _create_user(db, hwid, email=None, username=None, credits=100):
    u = User(hwid=hwid, email=email, username=username,
             ref_code=secrets.token_urlsafe(6), credits=credits)
    db.add(u)
    await db.flush()
    return u


@pytest.mark.asyncio
async def test_activity_requires_admin_token(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/activity/crypt")
    assert resp.status_code == 401  # HTTPBearer auto_error: missing header -> 401, bad token -> 403

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/activity/crypt",
                                headers={"Authorization": "Bearer wrong-token"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_activity_rejects_unknown_metric(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/activity/nonsense",
                                headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_activity_crypt_counts_hunts_per_user(db_session):
    u1 = await _create_user(db_session, "hwidcrypt0000a", email="a@test.com")
    u2 = await _create_user(db_session, "hwidcrypt0000b", email="b@test.com")
    db_session.add_all([
        Hunt(user_id=u1.id, hunt_type="crypt"),
        Hunt(user_id=u1.id, hunt_type="crypt"),
        Hunt(user_id=u1.id, hunt_type="exchange"),  # different metric, must not count
        Hunt(user_id=u2.id, hunt_type="crypt"),
    ])
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/activity/crypt",
                                headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert resp.status_code == 200
    rows = {r["hwid"]: r["count"] for r in resp.json()["rows"]}
    assert rows["hwidcrypt0000a"] == 2
    assert rows["hwidcrypt0000b"] == 1


@pytest.mark.asyncio
async def test_activity_roulette_counts_spins_and_credits(db_session):
    u1 = await _create_user(db_session, "hwidroulette0a", email="c@test.com")
    db_session.add_all([
        Transaction(user_id=u1.id, type="ad_reward", amount=5),
        Transaction(user_id=u1.id, type="ad_reward", amount=50),
        Transaction(user_id=u1.id, type="purchase", amount=1000),  # different type, must not count
    ])
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/activity/roulette",
                                headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert resp.status_code == 200
    row = next(r for r in resp.json()["rows"] if r["hwid"] == "hwidroulette0a")
    assert row["count"] == 2
    assert row["credits_total"] == 55


@pytest.mark.asyncio
async def test_activity_ancient_counts_imports_and_calcs_separately(db_session):
    u1 = await _create_user(db_session, "hwidancient00a", email="d@test.com")
    db_session.add_all([
        Log(hwid=u1.hwid, event_type="ancient_ocr_import"),
        Log(hwid=u1.hwid, event_type="ancient_ocr_import"),
        Log(hwid=u1.hwid, event_type="ancient_quota_calc"),
    ])
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/activity/ancient",
                                headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert resp.status_code == 200
    row = next(r for r in resp.json()["rows"] if r["hwid"] == "hwidancient00a")
    assert row["ocr_imports"] == 2
    assert row["quota_calcs"] == 1
