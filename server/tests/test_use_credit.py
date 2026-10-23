"""POST /use_credit — списание за находку бота. Регрессия аудита 2026-10-23: для неизвестного hunt_type сумма бралась
из запроса без проверки, отрицательная сумма НАЧИСЛЯЛА алмазы (достаточно знать HWID)."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app, CREDIT_COST
from models import Hunt, Transaction, User


async def _user(db, credits=100, banned=False):
    u = User(hwid=secrets.token_hex(8).upper(), ref_code=secrets.token_hex(5), credits=credits, is_banned=banned)
    db.add(u)
    await db.commit()
    return u


async def _post(body):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.post("/use_credit", json=body)


async def _balance(db, user):
    await db.refresh(user)
    return user.credits


def test_only_crypt_and_exchange_have_a_price():
    assert set(CREDIT_COST) == {"crypt", "exchange"}


@pytest.mark.asyncio
async def test_known_types_charge_fixed_price(db_session):
    u = await _user(db_session, credits=100)
    assert (await _post({"hwid": u.hwid, "hunt_type": "crypt"})).status_code == 200
    assert await _balance(db_session, u) == 99
    assert (await _post({"hwid": u.hwid, "hunt_type": "exchange"})).status_code == 200
    assert await _balance(db_session, u) == 89
    kinds = (await db_session.execute(select(Hunt.hunt_type).where(Hunt.user_id == u.id))).scalars().all()
    assert sorted(kinds) == ["crypt", "exchange"]


@pytest.mark.asyncio
@pytest.mark.parametrize("amount", [-1000000, -1, 0, 5, 999])
async def test_amount_in_request_never_changes_the_price_of_known_types(db_session, amount):
    u = await _user(db_session, credits=100)
    r = await _post({"hwid": u.hwid, "hunt_type": "crypt", "amount": amount})
    if r.status_code == 200:
        assert await _balance(db_session, u) == 99  # цена из таблицы, не из запроса
    else:
        assert r.status_code == 422 and await _balance(db_session, u) == 100


@pytest.mark.asyncio
@pytest.mark.parametrize("hunt_type", ["chest", "roulette", "free", "", "CRYPT", "crypt "])
@pytest.mark.parametrize("amount", [-1000000, -1, 1, 50])
async def test_unknown_hunt_type_is_rejected_and_balance_is_untouched(db_session, hunt_type, amount):
    u = await _user(db_session, credits=100)
    r = await _post({"hwid": u.hwid, "hunt_type": hunt_type, "amount": amount})
    assert r.status_code in (400, 422)
    assert await _balance(db_session, u) == 100
    assert (await db_session.execute(select(Transaction).where(Transaction.user_id == u.id))).scalars().all() == []


@pytest.mark.asyncio
async def test_balance_can_never_grow_through_use_credit(db_session):
    u = await _user(db_session, credits=100)
    for ht in ("x", "chest", "crypt", "exchange"):
        for amount in (-5000, -1, 0):
            await _post({"hwid": u.hwid, "hunt_type": ht, "amount": amount})
    assert await _balance(db_session, u) <= 100


@pytest.mark.asyncio
async def test_not_enough_credits_returns_402_with_required(db_session):
    u = await _user(db_session, credits=3)
    r = await _post({"hwid": u.hwid, "hunt_type": "exchange"})
    assert r.status_code == 402
    assert r.json()["detail"]["required"] == 10 and r.json()["detail"]["credits"] == 3
    assert await _balance(db_session, u) == 3


@pytest.mark.asyncio
async def test_banned_and_unknown_users(db_session):
    banned = await _user(db_session, credits=100, banned=True)
    assert (await _post({"hwid": banned.hwid, "hunt_type": "crypt"})).status_code == 403
    assert await _balance(db_session, banned) == 100
    assert (await _post({"hwid": "NOSUCHHWID0000000", "hunt_type": "crypt"})).status_code == 404


@pytest.mark.asyncio
async def test_second_charge_within_two_seconds_is_rate_limited(db_session):
    u = await _user(db_session, credits=100)
    assert (await _post({"hwid": u.hwid, "hunt_type": "crypt"})).status_code == 200
    assert (await _post({"hwid": u.hwid, "hunt_type": "crypt"})).status_code == 429
    assert await _balance(db_session, u) == 99


@pytest.mark.asyncio
async def test_unknown_types_do_not_fill_the_rate_limit_table(db_session):
    from main import _credit_ratelimit
    before = len(_credit_ratelimit)
    u = await _user(db_session)
    for i in range(20):
        await _post({"hwid": u.hwid, "hunt_type": f"junk{i}"})
    assert len(_credit_ratelimit) == before
