"""Привязка устройства (/web/link/*): защита кода и аккаунтов. Аудит 2026-10-23.
Срок жизни кода (10 лет) по решению владельца не меняется; защита — криптостойкий код, одноразовость, лимит неверных
попыток, понятные отказы вместо слияния чужих аккаунтов."""
import asyncio
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

import web_routes
from main import app
from models import ChestCollector, LinkCode, User
from web_routes import create_jwt


@pytest.fixture(autouse=True)
def _clear_fail_registry():
    web_routes._link_fails.clear()
    yield
    web_routes._link_fails.clear()


async def _user(db, email=None, hwid=None):
    u = User(hwid=hwid or secrets.token_hex(8).upper(), ref_code=secrets.token_urlsafe(6), email=email)
    if hwid == "":
        u.hwid = None
    db.add(u)
    await db.flush()
    return u


def _auth(user):
    return {"Authorization": f"Bearer {create_jwt(user.id, user.email or 'x@x.test')}"}


async def _gen(client, hwid):
    return (await client.post("/web/link/generate", json={"hwid": hwid})).json()["code"]


async def _verify(client, user, code):
    return await client.post("/web/link/verify", json={"code": code}, headers=_auth(user))


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


def _roster(db, user, clan, kingdom="K1"):
    c = ChestCollector(kingdom=kingdom, clan=clan, user_id=user.id, slug=secrets.token_urlsafe(16), quotas=[])
    db.add(c)
    return c


# ── код ────────────────────────────────────────────────────────────────────────────────────────────────────

def test_link_code_comes_from_secrets_not_random(monkeypatch):
    monkeypatch.setattr(web_routes._secrets, "choice", lambda alphabet: "7")
    assert web_routes._generate_link_code() == "777777"
    code = web_routes._generate_link_code.__wrapped__() if hasattr(web_routes._generate_link_code, "__wrapped__") else None
    assert code is None or len(code) == 6


@pytest.mark.asyncio
async def test_generated_code_never_collides_with_a_live_code(db_session, monkeypatch):
    first_hwid, second_hwid = secrets.token_hex(8).upper(), secrets.token_hex(8).upper()
    seq = iter(["111111", "111111", "222222"])
    monkeypatch.setattr(web_routes, "_generate_link_code", lambda: next(seq))
    async with _client() as c:
        a = await _gen(c, first_hwid)
        b = await _gen(c, second_hwid)     # первый выпавший код совпал с живым — берётся следующий, а не 500
    assert (a, b) == ("111111", "222222")


@pytest.mark.asyncio
async def test_code_is_single_use_and_dies_after_linking(db_session):
    web = await _user(db_session, email=f"w{secrets.token_hex(3)}@x.test", hwid="")
    bot = await _user(db_session)
    await db_session.commit()
    async with _client() as c:
        code = await _gen(c, bot.hwid)
        assert (await _verify(c, web, code)).status_code == 200
        other = await _user(db_session, email=f"o{secrets.token_hex(3)}@x.test", hwid="")
        await db_session.commit()
        again = await _verify(c, other, code)           # тот же код второй раз — уже недействителен
    assert again.status_code == 404 and again.json()["detail"]["code"] == "code_not_found"
    assert (await db_session.execute(select(LinkCode).where(LinkCode.code == code))).first() is None


@pytest.mark.asyncio
async def test_expired_code_is_not_found(db_session):
    web = await _user(db_session, email=f"w{secrets.token_hex(3)}@x.test", hwid="")
    db_session.add(LinkCode(hwid=secrets.token_hex(8).upper(), code="424242",
                            expires_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    await db_session.commit()
    async with _client() as c:
        r = await _verify(c, web, "424242")
    assert r.status_code == 404 and r.json()["detail"]["code"] == "code_not_found"


# ── лимит неверных попыток ─────────────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_wrong_codes_are_limited_per_account_even_for_a_valid_code(db_session, monkeypatch):
    alerts = []

    async def _alert(**kw):
        alerts.append(kw)

    monkeypatch.setattr(web_routes, "send_security_alert", _alert)
    web = await _user(db_session, email=f"w{secrets.token_hex(3)}@x.test", hwid="")
    bot = await _user(db_session)
    await db_session.commit()
    async with _client() as c:
        good = await _gen(c, bot.hwid)
        wrong = "000000" if good != "000000" else "000001"
        for _ in range(web_routes.LINK_FAIL_LIMIT):
            assert (await _verify(c, web, wrong)).status_code == 404
        blocked = await _verify(c, web, good)            # правильный код при превышении лимита тоже не принимается
    await asyncio.sleep(0)                               # дать выполниться фоновой задаче уведомления
    assert blocked.status_code == 429 and blocked.json()["detail"]["code"] == "too_many_attempts"
    assert len(alerts) == 1                              # владельцу — одно уведомление о подборе
    assert (await db_session.execute(select(LinkCode).where(LinkCode.code == good))).first() is not None


@pytest.mark.asyncio
async def test_limit_does_not_touch_other_accounts_and_expires(db_session, monkeypatch):
    monkeypatch.setattr(web_routes, "send_security_alert", lambda **kw: _noop())
    a = await _user(db_session, email=f"a{secrets.token_hex(3)}@x.test", hwid="")
    b = await _user(db_session, email=f"b{secrets.token_hex(3)}@x.test", hwid="")
    bot = await _user(db_session)
    await db_session.commit()
    fake = {"t": 5_000_000.0}
    monkeypatch.setattr(web_routes.time, "time", lambda: fake["t"])
    async with _client() as c:
        good = await _gen(c, bot.hwid)
        for _ in range(web_routes.LINK_FAIL_LIMIT):
            await _verify(c, a, "000000" if good != "000000" else "000001")
        assert (await _verify(c, a, good)).status_code == 429
        fake["t"] += web_routes.LINK_FAIL_WINDOW + 1       # через час счётчик обнуляется
        ok = await _verify(c, a, good)
        assert ok.status_code == 200
        # другой аккаунт и не замечал блока
        assert (await _verify(c, b, "123123")).status_code == 404


async def _noop():
    return None


@pytest.mark.asyncio
async def test_successful_attempts_do_not_count_as_failures(db_session):
    web = await _user(db_session, email=f"w{secrets.token_hex(3)}@x.test", hwid="")
    bot = await _user(db_session)
    await db_session.commit()
    async with _client() as c:
        good = await _gen(c, bot.hwid)
        assert (await _verify(c, web, good)).status_code == 200
    assert web_routes._link_fails.get(web.id, []) == []


# ── перепривязка и чужие аккаунты ──────────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_account_with_a_linked_device_needs_unlink_before_a_new_code(db_session):
    web = await _user(db_session, email=f"w{secrets.token_hex(3)}@x.test")      # уже есть своё устройство
    old_hwid = web.hwid
    new_bot = await _user(db_session)
    await db_session.commit()
    async with _client() as c:
        code = await _gen(c, new_bot.hwid)
        r = await _verify(c, web, code)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "device_already_linked"
    await db_session.refresh(web)
    assert web.hwid == old_hwid                                                  # ничего не изменилось
    assert (await db_session.execute(select(LinkCode).where(LinkCode.code == code))).first() is not None   # код не потрачен


@pytest.mark.asyncio
async def test_unlink_then_new_code_works(db_session):
    web = await _user(db_session, email=f"w{secrets.token_hex(3)}@x.test")
    new_bot = await _user(db_session)
    await db_session.commit()
    async with _client() as c:
        assert (await c.post("/web/hwid/reset", headers=_auth(web))).status_code == 200
        code = await _gen(c, new_bot.hwid)
        assert (await _verify(c, web, code)).status_code == 200
    await db_session.refresh(web)
    assert web.hwid == new_bot.hwid


@pytest.mark.asyncio
async def test_device_of_another_site_account_is_never_merged_automatically(db_session):
    owner = await _user(db_session, email=f"own{secrets.token_hex(3)}@x.test")          # устройство уже у этого аккаунта
    other = await _user(db_session, email=f"oth{secrets.token_hex(3)}@x.test", hwid="")
    owner_credits = owner.credits
    await db_session.commit()
    async with _client() as c:
        code = await _gen(c, owner.hwid)
        r = await _verify(c, other, code)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "device_linked_to_other_account"
    assert await db_session.get(User, owner.id) is not None and (await db_session.get(User, owner.id)).credits == owner_credits


# ── ростеры: мешает только один и тот же клан ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rosters_of_different_clans_are_both_kept(db_session):
    web = await _user(db_session, email=f"w{secrets.token_hex(3)}@x.test", hwid="")
    bot = await _user(db_session)
    _roster(db_session, bot, "BotClan")
    _roster(db_session, web, "WebClan")
    await db_session.commit()
    web_id = web.id
    async with _client() as c:
        code = await _gen(c, bot.hwid)
        r = await _verify(c, web, code)
    assert r.status_code == 200, r.text
    clans = (await db_session.execute(select(ChestCollector.clan).where(ChestCollector.user_id == web_id))).scalars().all()
    assert sorted(clans) == ["BotClan", "WebClan"]


@pytest.mark.asyncio
async def test_same_clan_on_both_accounts_is_refused_with_a_clear_code_and_nothing_moves(db_session):
    web = await _user(db_session, email=f"w{secrets.token_hex(3)}@x.test", hwid="")
    bot = await _user(db_session)
    _roster(db_session, bot, "SameClan", kingdom="K7")
    _roster(db_session, web, "sameclan", kingdom="k7")         # тот же клан, другой регистр
    await db_session.commit()
    bot_id = bot.id
    async with _client() as c:
        code = await _gen(c, bot.hwid)
        r = await _verify(c, web, code)
    assert r.status_code == 409 and r.json()["detail"]["code"] == "roster_conflict"
    assert await db_session.get(User, bot_id) is not None
