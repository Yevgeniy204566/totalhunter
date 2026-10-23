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

import vault
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
    assert resp.json() == {"credits": 10, "ref_credits": 0, "linked": False}

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
async def test_balance_sync_unknown_hwid_gets_fast_404_without_waiting(db_session):
    """Неизвестный HWID не держит соединение 50 с. 404, а не 200: бот переподключается после 200
    без паузы (бесконечный цикл), после ошибки — через BALANCE_RETRY_PAUSE_SEC."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await asyncio.wait_for(client.get("/vault/sync/0123456789ABCDEF"), timeout=2.0)

    assert resp.status_code == 404
    assert "0123456789ABCDEF" not in vault._notifiers


@pytest.mark.asyncio
async def test_balance_sync_known_hwid_still_waits_for_wakeup(db_session):
    """Регрессия действующего клиента: зарегистрированный HWID по-прежнему ждёт пробуждения."""
    u = User(hwid="ABCDEF0123456789", credits=7, ref_code="vault9")
    db_session.add(u)
    await db_session.commit()

    async def _call():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(f"/vault/sync/{u.hwid}")

    task = asyncio.create_task(_call())
    await asyncio.sleep(0.2)
    assert not task.done()                      # не отвечает сразу — long-poll
    assert u.hwid in vault._notifiers
    notify_balance_changed(u.hwid)
    resp = await task

    assert resp.status_code == 200
    assert resp.json() == {"credits": 7, "ref_credits": 0, "linked": False}


@pytest.mark.asyncio
async def test_balance_sync_releases_connection_before_long_wait(db_session, monkeypatch):
    """SELECT проверки HWID не должен держать соединение пула все 50 с ожидания."""
    from sqlalchemy.ext.asyncio import AsyncSession

    u = User(hwid="1111222233334444", credits=1, ref_code="vault8")
    db_session.add(u)
    await db_session.commit()

    rollbacks = []
    orig_rollback = AsyncSession.rollback

    async def _spy_rollback(self):
        rollbacks.append(1)
        return await orig_rollback(self)

    monkeypatch.setattr(AsyncSession, "rollback", _spy_rollback)

    rollbacks_at_wait = []
    orig_wait_for = vault.asyncio.wait_for

    async def _spy_wait_for(aw, timeout):
        rollbacks_at_wait.append(len(rollbacks))
        return await orig_wait_for(aw, timeout=0.01)   # не ждать 50 с

    monkeypatch.setattr(vault.asyncio, "wait_for", _spy_wait_for)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/vault/sync/{u.hwid}")

    assert resp.status_code == 200
    assert rollbacks_at_wait and rollbacks_at_wait[0] >= 1   # откат выполнен ДО ожидания


@pytest.mark.asyncio
async def test_balance_sync_reports_linked_when_account_has_email(db_session):
    """Бот ждёт привязку не опросом раз в 5 с, а через этот long-poll: linked — состояние из БД
    в КАЖДОМ ответе, поэтому потерянное пробуждение догоняется следующим циклом (≤50 с)."""
    u = User(hwid="hwidvault0004d", credits=3, ref_code="vault4", email="linked@example.com")
    db_session.add(u)
    await db_session.commit()

    async def _call():
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            return await client.get(f"/vault/sync/{u.hwid}")

    task = asyncio.create_task(_call())
    await asyncio.sleep(0.05)
    notify_balance_changed(u.hwid)
    resp = await task

    assert resp.json() == {"credits": 3, "ref_credits": 0, "linked": True}
