"""Tests for:
1) POST /check_auth updating last_seen on real login (not just hunt-engine heartbeat)
2) GET /admin/users sort/sort_dir params (per-column sorting in the admin panel)
"""
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import User

ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]


async def _create_user(db, hwid, email=None, username=None, credits=100,
                        bot_version=None, last_seen=None):
    u = User(hwid=hwid, email=email, username=username,
             ref_code=secrets.token_urlsafe(6), credits=credits,
             bot_version=bot_version, last_seen=last_seen)
    db.add(u)
    await db.flush()
    return u


@pytest.mark.asyncio
async def test_check_auth_updates_last_seen_on_login(db_session):
    """Root-cause fix: last_seen must reflect the real login event (/check_auth),
    not only the hunt-engine heartbeat that fires while actively hunting."""
    stale = datetime(2026, 7, 20, 9, 0, 0)
    u = await _create_user(db_session, "hwidlogin0000a", last_seen=stale)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/check_auth", json={"hwid": "hwidlogin0000a", "bot_version": "1.9.0"})
    assert resp.status_code == 200

    await db_session.refresh(u)
    assert u.last_seen is not None
    assert u.last_seen.replace(tzinfo=None) > stale


@pytest.mark.asyncio
async def test_check_auth_sets_session_started_at_on_new_session_only(db_session):
    """session_started_at должен ставиться при переходе оффлайн→онлайн, но НЕ
    сдвигаться на повторных check_auth в рамках уже идущей сессии (например,
    activate_referral/claim_trial тоже дёргают check_auth) — иначе "Онлайн с
    HH:MM" будет постоянно врать, уезжая вперёд на каждое действие."""
    stale = datetime(2026, 7, 20, 9, 0, 0)
    u = await _create_user(db_session, "hwidsession001", last_seen=stale)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/check_auth", json={"hwid": "hwidsession001"})
    await db_session.refresh(u)
    first_start = u.session_started_at
    assert first_start is not None
    assert first_start.replace(tzinfo=None) > stale

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/check_auth", json={"hwid": "hwidsession001"})
    await db_session.refresh(u)
    assert u.session_started_at == first_start


@pytest.mark.asyncio
async def test_admin_users_sort_by_credits_desc(db_session):
    await _create_user(db_session, "hwidsortc0001a", credits=10)
    await _create_user(db_session, "hwidsortc0002b", credits=500)
    await _create_user(db_session, "hwidsortc0003c", credits=100)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/users?sort=credits&sort_dir=desc",
                                 headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert resp.status_code == 200
    hwids = [r["hwid"] for r in resp.json()["users"] if r["hwid"].startswith("hwidsortc")]
    assert hwids == ["hwidsortc0002b", "hwidsortc0003c", "hwidsortc0001a"]


@pytest.mark.asyncio
async def test_admin_users_sort_by_bot_version_asc(db_session):
    await _create_user(db_session, "hwidsortv0001a", bot_version="1.9.0")
    await _create_user(db_session, "hwidsortv0002b", bot_version="1.2.0")
    await _create_user(db_session, "hwidsortv0003c", bot_version="1.5.0")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/users?sort=bot_version&sort_dir=asc",
                                 headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert resp.status_code == 200
    hwids = [r["hwid"] for r in resp.json()["users"] if r["hwid"].startswith("hwidsortv")]
    assert hwids == ["hwidsortv0002b", "hwidsortv0003c", "hwidsortv0001a"]


@pytest.mark.asyncio
async def test_admin_users_sort_by_bot_version_is_numeric_not_lexicographic(db_session):
    """Real bug hit in prod: '1.8.9' < '1.8.12' numerically, but '1.8.9' > '1.8.12'
    as a plain string ('9' > '1'). Sorting must compare version parts as integers."""
    await _create_user(db_session, "hwidsortx0001a", bot_version="1.8.9")
    await _create_user(db_session, "hwidsortx0002b", bot_version="1.8.12")
    await _create_user(db_session, "hwidsortx0003c", bot_version="1.8.6")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/users?sort=bot_version&sort_dir=asc",
                                 headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert resp.status_code == 200
    hwids = [r["hwid"] for r in resp.json()["users"] if r["hwid"].startswith("hwidsortx")]
    assert hwids == ["hwidsortx0003c", "hwidsortx0001a", "hwidsortx0002b"]


@pytest.mark.asyncio
async def test_admin_users_sort_by_username_asc(db_session):
    await _create_user(db_session, "hwidsortn0001a", username="Zeta")
    await _create_user(db_session, "hwidsortn0002b", username="Alpha")
    await _create_user(db_session, "hwidsortn0003c", username="Mike")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/users?sort=username&sort_dir=asc",
                                 headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert resp.status_code == 200
    hwids = [r["hwid"] for r in resp.json()["users"] if r["hwid"].startswith("hwidsortn")]
    assert hwids == ["hwidsortn0002b", "hwidsortn0003c", "hwidsortn0001a"]


@pytest.mark.asyncio
async def test_admin_users_sort_by_last_seen_desc_default(db_session):
    now = datetime.now(timezone.utc)
    await _create_user(db_session, "hwidsorts0001a", last_seen=now - timedelta(days=2))
    await _create_user(db_session, "hwidsorts0002b", last_seen=now)
    await _create_user(db_session, "hwidsorts0003c", last_seen=now - timedelta(days=1))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/users?sort=last_seen&sort_dir=desc",
                                 headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert resp.status_code == 200
    hwids = [r["hwid"] for r in resp.json()["users"] if r["hwid"].startswith("hwidsorts")]
    assert hwids == ["hwidsorts0002b", "hwidsorts0003c", "hwidsorts0001a"]


@pytest.mark.asyncio
async def test_admin_users_rejects_unknown_sort_column(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/admin/users?sort=is_banned",
                                 headers={"Authorization": f"Bearer {ADMIN_TOKEN}"})
    assert resp.status_code == 400
