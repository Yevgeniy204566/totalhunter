"""
Игровой ник (users.game_nick) в админке рядом с почтой и ID (владелец 2026-10-28):
список пользователей, активность (Сундуки/Склепы/Биржи/…) и ростеры сундуков.
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import Chest, ChestCollector, Hunt, User

ADMIN = {"Authorization": f"Bearer {os.environ['ADMIN_TOKEN']}"}


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _user(db, email, nick):
    u = User(hwid=secrets.token_hex(8), email=email, ref_code=secrets.token_urlsafe(6), game_nick=nick)
    db.add(u)
    await db.flush()
    return u


@pytest.mark.asyncio
async def test_users_list_has_game_nick(db_session):
    u = await _user(db_session, "a@x.com", "GOLDEN")
    await db_session.commit()
    async with _client() as c:
        users = (await c.get("/admin/users", headers=ADMIN)).json()["users"]
    row = next(x for x in users if x["id"] == u.id)
    assert row["game_nick"] == "GOLDEN" and row["email"] == "a@x.com"


@pytest.mark.asyncio
async def test_activity_rows_have_id_and_game_nick(db_session):
    u = await _user(db_session, "b@x.com", "Vasya")
    db_session.add(Hunt(user_id=u.id, hunt_type="chest"))
    await db_session.commit()
    async with _client() as c:
        rows = (await c.get("/admin/activity/chest", headers=ADMIN)).json()["rows"]
    row = next(x for x in rows if x["hwid"] == u.hwid)
    assert row["id"] == u.id and row["game_nick"] == "Vasya" and row["email"] == "b@x.com"


@pytest.mark.asyncio
async def test_rosters_owner_has_game_nick(db_session):
    u = await _user(db_session, "c@x.com", "Boss")
    col = ChestCollector(kingdom="229", clan="Feniks", user_id=u.id, slug="r-1")
    db_session.add(col)
    await db_session.commit()
    async with _client() as c:
        rows = (await c.get("/admin/chests/rosters", headers=ADMIN)).json()["rows"]
    row = next(x for x in rows if x["owner_id"] == u.id)
    assert row["owner_nick"] == "Boss" and row["owner_email"] == "c@x.com"
