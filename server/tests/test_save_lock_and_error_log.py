"""Сессия 2026-11-14: (1) вчера в 22:10 UTC серия одновременных «Сохранить имена» дала 500 UniqueViolation
(delete+insert без блокировки) — сохранения одного клана теперь идут по очереди (SELECT … FOR UPDATE по
строке клана); (2) ошибки 500 сервера раньше жили только в Telegram и journalctl — теперь ещё и в таблице
logs (видны на странице «Логи» админки), без секретов, с защитой от лавины."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.dialects import postgresql

import chest_dashboard
import error_alerts
from main import app
from models import ChestCollector, Log
from tests.test_chest_dashboard import _create_user_with_token, _create_collector


# ── блокировка клана ─────────────────────────────────────────────────────────────────────

def test_lock_statement_is_select_for_update_on_collector_row():
    stmt = chest_dashboard._lock_collector_stmt(42)
    sql = str(stmt.compile(dialect=postgresql.dialect(), compile_kwargs={"literal_binds": True}))
    assert "FOR UPDATE" in sql and "chest_collectors" in sql and "42" in sql


@pytest.mark.asyncio
@pytest.mark.parametrize("path,body", [
    ("/web/dashboard/chests/player-aliases", {"rows": []}),
    ("/web/dashboard/chests/player-profiles", {"rows": []}),
    ("/web/dashboard/chests/rows", {"rows": []}),
])
async def test_replace_endpoints_take_the_collector_lock(db_session, monkeypatch, path, body):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="lock-slug")
    await db_session.commit()
    locked = []
    real = chest_dashboard._lock_collector

    async def spy(db, collector_id):
        locked.append(collector_id)
        await real(db, collector_id)
    monkeypatch.setattr(chest_dashboard, "_lock_collector", spy)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(path, json={"collector_slug": "lock-slug", **body},
                                 headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200, resp.text
    assert locked == [collector.id]


@pytest.mark.asyncio
async def test_repeated_save_of_same_aliases_is_idempotent(db_session):
    """Тот самый сценарий вчера: один и тот же список имён отправлен несколько раз подряд."""
    user, token = await _create_user_with_token(db_session)
    await _create_collector(db_session, user.id, slug="idem-slug")
    await db_session.commit()
    payload = {"collector_slug": "idem-slug",
               "rows": [{"raw_name": "Puuen", "canonical_name": "Puuen"},
                        {"raw_name": "TheWoodler a", "canonical_name": "TheWoodler"}]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(4):
            resp = await client.post("/web/dashboard/chests/player-aliases", json=payload,
                                     headers={"Authorization": f"Bearer {token}"})
            assert resp.status_code == 200
    from models import PlayerAlias
    rows = (await db_session.execute(select(PlayerAlias))).scalars().all()
    assert len(rows) == 2


# ── ошибки 500 → таблица logs ────────────────────────────────────────────────────────────

@pytest.fixture
def _alerts_clean(monkeypatch):
    error_alerts._last_sent.clear(); error_alerts._suppressed.clear()
    error_alerts._last_logged.clear(); error_alerts._logged_suppressed.clear()
    monkeypatch.setattr(error_alerts, "_send_debug_sync", lambda text: None)


@pytest.mark.asyncio
async def test_server_error_is_saved_to_logs_table(db_session, monkeypatch, _alerts_clean):
    async def factory_session():
        return db_session
    monkeypatch.setattr(error_alerts, "_log_session", factory_session)
    try:
        raise RuntimeError("boom for bob@example.com token=SECRETVALUE")
    except RuntimeError as exc:
        await error_alerts.notify_server_error("POST", "/web/x", exc)
    rows = (await db_session.execute(select(Log).where(Log.event_type == "server_error"))).scalars().all()
    assert len(rows) == 1
    text = rows[0].payload
    assert "POST /web/x" in text and "RuntimeError" in text and "boom" in text
    assert "bob@example.com" not in text and "SECRETVALUE" not in text
    assert len(text) <= 2200


@pytest.mark.asyncio
async def test_repeated_server_error_is_throttled_in_logs(db_session, monkeypatch, _alerts_clean):
    async def factory_session():
        return db_session
    monkeypatch.setattr(error_alerts, "_log_session", factory_session)
    for _ in range(5):
        try:
            raise ValueError("same")
        except ValueError as exc:
            await error_alerts.notify_server_error("GET", "/same", exc)
    rows = (await db_session.execute(select(Log).where(Log.event_type == "server_error"))).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_failure_to_write_log_never_breaks_the_response(monkeypatch, _alerts_clean):
    async def broken():
        raise RuntimeError("db down")
    monkeypatch.setattr(error_alerts, "_log_session", broken)
    try:
        raise KeyError("x")
    except KeyError as exc:
        await error_alerts.notify_server_error("GET", "/x", exc)   # не бросает
