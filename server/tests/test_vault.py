"""
TDD: GET /vault/sync/{hwid} должен обновлять last_seen на каждый цикл —
это единственный канал, который непрерывно работает пока бот открыт
(даже без активной охоты), поэтому "онлайн" в админке должен опираться
на него, а не на отдельный heartbeat, привязанный только к охоте.
"""
import asyncio
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import User
from vault import notify_balance_changed


@pytest.mark.asyncio
async def test_balance_sync_updates_last_seen_on_each_cycle(db_session):
    stale = datetime(2026, 7, 20, 9, 0, 0)
    u = User(hwid="hwidvault0001a", credits=10, ref_code="vault1", last_seen=stale)
    db_session.add(u)
    await db_session.commit()

    async def _call():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(f"/vault/sync/{u.hwid}")

    task = asyncio.create_task(_call())
    await asyncio.sleep(0.05)  # дать серверу зарегистрировать notifier
    notify_balance_changed(u.hwid)
    resp = await task

    assert resp.status_code == 200
    assert resp.json() == {"credits": 10, "ref_credits": 0}

    await db_session.refresh(u)
    assert u.last_seen is not None
    assert u.last_seen.replace(tzinfo=None) > stale


@pytest.mark.asyncio
async def test_balance_sync_returns_zero_for_unknown_hwid_without_crashing(db_session):
    async def _call():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get("/vault/sync/doesnotexist000")

    task = asyncio.create_task(_call())
    await asyncio.sleep(0.05)
    notify_balance_changed("doesnotexist000")
    resp = await task

    assert resp.status_code == 200
    assert resp.json() == {"credits": 0, "ref_credits": 0}
