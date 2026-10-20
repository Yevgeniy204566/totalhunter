"""Квота режима hero_points — «Общий учёт» всех сундуков в очках по уровню Героя.
Рычаги хранятся у квоты клана; вес типа и норму считает страница (lib/heroQuota.js)."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from chest_summary import pivot_summary
from main import app
from models import ChestCollector, User
from web_routes import create_jwt

HERO = {"norm": 1.2, "weights": 0.9, "ranges": [{"from": 100, "to": 399, "k": 1.0}, {"from": 400, "to": 600, "k": 1.1}]}
Q = {"slot": 3, "name": "Общий учёт", "mode": "hero_points", "hero": HERO}


async def _owner(db, email):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6), email=email)
    db.add(user)
    await db.flush()
    c = ChestCollector(kingdom="K9", clan="HeroClan", user_id=user.id, slug=secrets.token_urlsafe(16),
                       quotas=[{"slot": 3, "name": "Общий учёт", "target": 0, "mode": "fixed"}])
    db.add(c)
    await db.commit()
    return c, {"Authorization": f"Bearer {create_jwt(user.id, email)}"}


async def _patch(client, c, h, quota):
    return await client.patch(f"/web/dashboard/chests/{c.slug}/season", headers=h, json={"quotas": [quota]})


@pytest.mark.asyncio
async def test_hero_points_saved_and_exposed_publicly(db_session):
    c, h = await _owner(db_session, f"hp1{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await _patch(client, c, h, Q)).status_code == 200
        q = (await client.get(f"/api/v1/chests/summary/{c.slug}")).json()["targets"]["quotas"][0]
    assert q["mode"] == "hero_points"
    assert q["hero"]["norm"] == 1.2 and q["hero"]["weights"] == 0.9
    assert q["hero"]["ranges"][1] == {"from": 400, "to": 600, "k": 1.1}


@pytest.mark.asyncio
async def test_hero_points_without_settings_uses_defaults(db_session):
    c, h = await _owner(db_session, f"hp2{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, {"slot": 3, "name": "Общий учёт", "mode": "hero_points"})
        q = (await client.get(f"/api/v1/chests/summary/{c.slug}")).json()["targets"]["quotas"][0]
    assert r.status_code == 200
    assert q["hero"] == {"norm": 1.0, "weights": 1.0, "ranges": []}


@pytest.mark.asyncio
async def test_switching_back_to_fixed_drops_hero_settings(db_session):
    c, h = await _owner(db_session, f"hp3{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _patch(client, c, h, Q)
        await _patch(client, c, h, {"slot": 3, "name": "Общий учёт", "target": 10, "mode": "fixed"})
        q = (await client.get(f"/api/v1/chests/summary/{c.slug}")).json()["targets"]["quotas"][0]
    assert q["mode"] == "fixed" and "hero" not in q


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    {"norm": 3.5}, {"norm": 0.05}, {"weights": 9},
    {"ranges": [{"from": 50, "to": 300, "k": 1}]},
    {"ranges": [{"from": 500, "to": 300, "k": 1}]},
    {"ranges": [{"from": 100 + i, "to": 100 + i, "k": 1} for i in range(11)]},
])
async def test_hero_points_invalid_settings_422(db_session, bad):
    c, h = await _owner(db_session, f"hp4{secrets.token_hex(3)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, {**Q, "hero": {**HERO, **bad}})
    assert r.status_code == 422


def test_pivot_exposes_type_meta_for_hero_points():
    # (sender, chest_type_en, display, points, quota_slot, is_in_pattern, count)
    rows = [("Ann", "Epic Crypt 35", "Эпик 35", 135, None, 1, 2),
            ("Ann", "Rare Crypt 25", "Редкий 25", 20, None, 1, 1)]
    out = pivot_summary("K", "C", rows)
    assert out["chest_type_meta"] == {"Эпик 35": {"id": "Epic Crypt 35", "points": 135},
                                      "Редкий 25": {"id": "Rare Crypt 25", "points": 20}}
