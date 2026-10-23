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
    # аккаунт сайта без привязанного бота не имеет hwid (привязка к нему выдаёт его); у бот-аккаунта hwid есть всегда
    user = User(hwid=None if email else (hwid or secrets.token_hex(8).upper()), ref_code=secrets.token_urlsafe(6), email=email)
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
async def test_link_refuses_when_both_accounts_have_a_roster_of_the_same_clan(db_session):
    bot = await _user(db_session)
    web = await _user(db_session, email=f"web{secrets.token_hex(3)}@example.com")
    await _collector(db_session, bot, "SameClan")
    await _collector(db_session, web, "SameClan")
    await db_session.commit()
    bot_id, hwid = bot.id, bot.hwid

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _link(client, web, hwid)

    assert r.status_code == 409
    db_session.expire_all()
    assert await db_session.get(User, bot_id) is not None  # ничего не удалено


def test_every_foreign_key_to_users_is_handled_by_the_merge():
    """Сторож: новая таблица со ссылкой на users.id ломает привязку бота (FK при DELETE), пока её не добавят в слияние."""
    from models import Base
    from web_routes import MERGE_USER_FKS
    found = {f"{t.name}.{fk.parent.name}" for t in Base.metadata.tables.values()
             for fk in t.foreign_keys if fk.column.table.name == "users"}
    assert found == MERGE_USER_FKS, f"не учтено слиянием: {found - MERGE_USER_FKS}, лишнее: {MERGE_USER_FKS - found}"
