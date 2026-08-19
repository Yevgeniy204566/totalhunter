"""Tests for POST /claim_trial — 300 free trial credits, once per HWID.

Root cause this guards against: старая реализация была check-then-act
(`if user.trial_used: ...; user.credits += 300; user.trial_used = True`)
без атомарности — два параллельных вызова (двойной клик, два открытых бота
на одном HWID) могли оба пройти проверку `trial_used == False` до того, как
любой из них закоммитится, и начислить 600 вместо 300.
"""
import os
import asyncio
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import User


ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]


async def _create_user(db, hwid, credits=0, trial_used=False):
    u = User(hwid=hwid, ref_code=secrets.token_urlsafe(6),
             credits=credits, trial_used=trial_used)
    db.add(u)
    await db.flush()
    return u


@pytest.mark.asyncio
async def test_claim_trial_credits_new_user(db_session):
    await _create_user(db_session, "trialhwid0001a")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/claim_trial", json={"hwid": "trialhwid0001a"})

    assert resp.status_code == 200
    data = resp.json()
    assert data["success"] is True
    assert data["credits"] == 300


@pytest.mark.asyncio
async def test_claim_trial_second_call_does_not_double_credit(db_session):
    await _create_user(db_session, "trialhwid0002b")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/claim_trial", json={"hwid": "trialhwid0002b"})
        second = await client.post("/claim_trial", json={"hwid": "trialhwid0002b"})

    assert first.json()["success"] is True
    assert first.json()["credits"] == 300

    second_data = second.json()
    assert second_data["success"] is False
    assert second_data["credits"] == 300  # баланс не изменился повторным вызовом


@pytest.mark.asyncio
async def test_claim_trial_already_used_flag_blocks_immediately(db_session):
    """Пользователь, у которого trial_used уже True (например, восстановлен из
    бэкапа/перенесён вручную), не должен получить кредиты даже с первого вызова
    в рамках теста."""
    await _create_user(db_session, "trialhwid0003c", credits=50, trial_used=True)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/claim_trial", json={"hwid": "trialhwid0003c"})

    data = resp.json()
    assert data["success"] is False
    assert data["credits"] == 50


@pytest.mark.asyncio
async def test_claim_trial_concurrent_calls_credit_exactly_once(db_session):
    """Гонка: два параллельных запроса на один HWID (двойной клик по кнопке /
    два открытых бота) должны начислить 300 суммарно, а не 600."""
    await _create_user(db_session, "trialhwid0004d")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        results = await asyncio.gather(
            client.post("/claim_trial", json={"hwid": "trialhwid0004d"}),
            client.post("/claim_trial", json={"hwid": "trialhwid0004d"}),
        )

    successes = [r for r in results if r.json()["success"] is True]
    failures = [r for r in results if r.json()["success"] is False]
    assert len(successes) == 1
    assert len(failures) == 1

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        check = await client.post("/check_auth", json={"hwid": "trialhwid0004d"})
    assert check.json()["credits"] == 300


@pytest.mark.asyncio
async def test_check_auth_reports_trial_used_flag(db_session):
    """GUI прячет кнопку трайла между запусками бота по этому полю — оно
    обязано быть в /check_auth, единственном эндпоинте, который бот дёргает
    при каждом старте до всякого клика пользователя."""
    await _create_user(db_session, "trialhwid0005e")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        before = await client.post("/check_auth", json={"hwid": "trialhwid0005e"})
        assert before.json()["trial_used"] is False

        await client.post("/claim_trial", json={"hwid": "trialhwid0005e"})

        after = await client.post("/check_auth", json={"hwid": "trialhwid0005e"})
        assert after.json()["trial_used"] is True
