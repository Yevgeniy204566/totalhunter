"""
TDD: GET /vault/sync/{hwid} должен обновлять last_seen на каждый цикл —
это единственный канал, который непрерывно работает пока бот открыт
(даже без активной охоты), поэтому "онлайн" в админке должен опираться
на него, а не на отдельный heartbeat, привязанный только к охоте.
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta, timezone

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
async def test_balance_sync_sets_session_started_at_only_on_offline_to_online_transition(db_session):
    """Первый вызов после долгого отсутствия (или впервые) — session_started_at
    ставится в "сейчас". Повторный вызов, пока пользователь ещё онлайн, НЕ должен
    сдвигать session_started_at вперёд — иначе "Онлайн с HH:MM" будет врать,
    постоянно уезжая вместе с last_seen."""
    stale = datetime(2026, 7, 20, 9, 0, 0)
    u = User(hwid="hwidvault0002b", credits=5, ref_code="vault2", last_seen=stale)
    db_session.add(u)
    await db_session.commit()

    async def _call():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(f"/vault/sync/{u.hwid}")

    # Первый цикл — оффлайн → онлайн
    task = asyncio.create_task(_call())
    await asyncio.sleep(0.05)
    notify_balance_changed(u.hwid)
    await task

    await db_session.refresh(u)
    first_session_start = u.session_started_at
    assert first_session_start is not None
    assert first_session_start.replace(tzinfo=None) > stale

    # Второй цикл сразу же — пользователь уже онлайн, сессия та же
    task2 = asyncio.create_task(_call())
    await asyncio.sleep(0.05)
    notify_balance_changed(u.hwid)
    await task2

    await db_session.refresh(u)
    assert u.session_started_at == first_session_start


@pytest.mark.asyncio
async def test_balance_sync_backfills_session_started_at_when_null_even_if_recently_seen(db_session):
    """Реальный кейс после миграции: у уже онлайн-пользователей last_seen свежий
    (обновлялся старым кодом), но session_started_at ещё NULL (колонка новая).
    "Оффлайн→онлайн" условие по last_seen не сработает — нужен отдельный
    self-heal: session_started_at IS NULL тоже считается новой сессией."""
    recent = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(minutes=1)
    u = User(hwid="hwidvault0003c", credits=1, ref_code="vault3", last_seen=recent,
              session_started_at=None)
    db_session.add(u)
    await db_session.commit()

    async def _call():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(f"/vault/sync/{u.hwid}")

    task = asyncio.create_task(_call())
    await asyncio.sleep(0.05)
    notify_balance_changed(u.hwid)
    await task

    await db_session.refresh(u)
    assert u.session_started_at is not None


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
