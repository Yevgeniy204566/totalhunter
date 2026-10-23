"""Привязка бота (/web/link/verify): бот-аккаунт сливается в аккаунт сайта и удаляется. Раньше падало 500
(FK), если у бот-аккаунта был ростер сундуков или другие связанные строки — сегодняшний баг пользователей."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import ChestCollector, Feedback, HwidHistory, User
from web_routes import create_jwt


async def _user(db, email=None, hwid=None):
    user = User(hwid=hwid or secrets.token_hex(8).upper(), ref_code=secrets.token_urlsafe(6), email=email)
    db.add(user)
    await db.flush()
    return user


async def _collector(db, user, clan):
    c = ChestCollector(kingdom="K1", clan=clan, user_id=user.id, slug=secrets.token_urlsafe(16), quotas=[])
    db.add(c)
    await db.flush()
    return c


async def _link(client, web, hwid):
    code = (await client.post("/web/link/generate", json={"hwid": hwid})).json()["code"]
    h = {"Authorization": f"Bearer {create_jwt(web.id, web.email)}"}
    return await client.post("/web/link/verify", json={"code": code}, headers=h)


@pytest.mark.asyncio
async def test_link_moves_chest_roster_and_other_rows_of_bot_account(db_session):
    bot = await _user(db_session)
    web = await _user(db_session, email=f"web{secrets.token_hex(3)}@example.com")
    coll = await _collector(db_session, bot, "BotClan")
    db_session.add(Feedback(user_id=bot.id, text="hi"))
    db_session.add(HwidHistory(hwid=bot.hwid, user_id=bot.id))
    await db_session.commit()
    bot_id, web_id, hwid, coll_id = bot.id, web.id, bot.hwid, coll.id

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _link(client, web, hwid)

    assert r.status_code == 200, r.text
    db_session.expire_all()
    assert (await db_session.get(ChestCollector, coll_id)).user_id == web_id
    assert await db_session.get(User, bot_id) is None
    assert (await db_session.execute(select(Feedback).where(Feedback.user_id == web_id))).scalars().all()


@pytest.mark.asyncio
async def test_link_refuses_when_both_accounts_have_chest_rosters(db_session):
    bot = await _user(db_session)
    web = await _user(db_session, email=f"web{secrets.token_hex(3)}@example.com")
    await _collector(db_session, bot, "BotClan")
    await _collector(db_session, web, "WebClan")
    await db_session.commit()
    bot_id, hwid = bot.id, bot.hwid

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _link(client, web, hwid)

    assert r.status_code == 409
    db_session.expire_all()
    assert await db_session.get(User, bot_id) is not None  # ничего не удалено
