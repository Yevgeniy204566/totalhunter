"""
Избранные игроки в админке (владелец 2026-11-03): звёздочка у игрока, фильтр
«только избранные» и сортировка по звёздочке — чтобы старых знакомых, которым
начисляют алмазы, было видно сразу, а не искать в конце списка.
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import User

ADMIN = {"Authorization": f"Bearer {os.environ['ADMIN_TOKEN']}"}


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _user(db, email, fav=False):
    u = User(hwid=secrets.token_hex(8), email=email, ref_code=secrets.token_urlsafe(6), is_favorite=fav)
    db.add(u)
    await db.flush()
    return u


@pytest.mark.asyncio
async def test_new_user_not_favorite_and_row_has_flag(db_session):
    u = await _user(db_session, "f1@x.com")
    await db_session.commit()
    async with _client() as c:
        users = (await c.get("/admin/users", headers=ADMIN)).json()["users"]
    assert next(x for x in users if x["id"] == u.id)["is_favorite"] is False


@pytest.mark.asyncio
async def test_set_and_unset_favorite(db_session):
    u = await _user(db_session, "f2@x.com")
    await db_session.commit()
    async with _client() as c:
        r = await c.post(f"/admin/users/{u.id}/favorite?favorite=true", headers=ADMIN)
        assert r.status_code == 200 and r.json()["is_favorite"] is True
        users = (await c.get("/admin/users", headers=ADMIN)).json()["users"]
        assert next(x for x in users if x["id"] == u.id)["is_favorite"] is True
        r = await c.post(f"/admin/users/{u.id}/favorite?favorite=false", headers=ADMIN)
        assert r.json()["is_favorite"] is False


@pytest.mark.asyncio
async def test_favorite_unknown_user_404(db_session):
    async with _client() as c:
        r = await c.post("/admin/users/99999999/favorite?favorite=true", headers=ADMIN)
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_favorite_requires_admin(db_session):
    u = await _user(db_session, "f3@x.com")
    await db_session.commit()
    async with _client() as c:
        r = await c.post(f"/admin/users/{u.id}/favorite?favorite=true")
    assert r.status_code in (401, 403)


@pytest.mark.asyncio
async def test_favorites_only_filter(db_session):
    fav = await _user(db_session, "fav@x.com", fav=True)
    plain = await _user(db_session, "plain@x.com")
    await db_session.commit()
    async with _client() as c:
        users = (await c.get("/admin/users?favorites_only=1", headers=ADMIN)).json()["users"]
    ids = {x["id"] for x in users}
    assert fav.id in ids and plain.id not in ids


@pytest.mark.asyncio
async def test_favorites_filter_combines_with_search(db_session):
    a = await _user(db_session, "alpha@x.com", fav=True)
    b = await _user(db_session, "beta@x.com", fav=True)
    await db_session.commit()
    async with _client() as c:
        users = (await c.get("/admin/users?favorites_only=1&search=alpha", headers=ADMIN)).json()["users"]
    ids = {x["id"] for x in users}
    assert a.id in ids and b.id not in ids


@pytest.mark.asyncio
async def test_sort_by_favorite_puts_stars_first(db_session):
    plain = await _user(db_session, "p@x.com")
    fav = await _user(db_session, "s@x.com", fav=True)
    await db_session.commit()
    async with _client() as c:
        users = (await c.get("/admin/users?sort=is_favorite&sort_dir=desc", headers=ADMIN)).json()["users"]
    order = [x["id"] for x in users]
    assert order.index(fav.id) < order.index(plain.id)
