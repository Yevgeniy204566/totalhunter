"""Квота режима emc_table — личная цель EMC по таблице уровней Героя с множителями
(рычаги хранятся у квоты клана; саму цель считает страница, чтобы формула жила в одном месте)."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import ChestCollector, User
from web_routes import create_jwt

EMC = {
    "global": 1.2,
    "monsters": {"hydra": 1.1, "undead": 1.0, "arachna": 0.8, "shadow": 1.2},
    "ranges": [{"from": 100, "to": 399, "k": 1.0}, {"from": 400, "to": 600, "k": 1.1}],
}
Q = {"slot": 2, "name": "EMC", "target": 50, "mode": "emc_table", "emc": EMC}


async def _owner(db, email):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6), email=email)
    db.add(user)
    await db.flush()
    c = ChestCollector(kingdom="K9", clan="EmcClan", user_id=user.id, slug=secrets.token_urlsafe(16),
                       quotas=[{"slot": 2, "name": "EMC", "target": 50, "mode": "fixed"}])
    db.add(c)
    await db.commit()
    return c, {"Authorization": f"Bearer {create_jwt(user.id, email)}"}


async def _patch(client, c, h, quota, emc_on=True):
    # режим emc_table слот 2 получает от тумблера personal.emc (спека 2026-10-20), не из тела квоты
    return await client.patch(f"/web/dashboard/chests/{c.slug}/season", headers=h,
                              json={"quotas": [quota], "personal": {"emc": emc_on}})


@pytest.mark.asyncio
async def test_emc_settings_saved_and_exposed_publicly(db_session):
    c, h = await _owner(db_session, f"emc1{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await _patch(client, c, h, Q)).status_code == 200
        pub = (await client.get(f"/api/v1/chests/summary/{c.slug}")).json()
    q = pub["targets"]["quotas"][0]
    assert q["mode"] == "emc_table"
    assert q["emc"]["global"] == 1.2
    assert q["emc"]["monsters"]["arachna"] == 0.8
    assert q["emc"]["ranges"][1] == {"from": 400, "to": 600, "k": 1.1}


@pytest.mark.asyncio
async def test_switching_back_to_fixed_keeps_emc_levers(db_session):
    c, h = await _owner(db_session, f"emc2{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _patch(client, c, h, Q)
        await _patch(client, c, h, Q, emc_on=False)
        q = (await client.get(f"/api/v1/chests/summary/{c.slug}")).json()["targets"]["quotas"][0]
    assert q["mode"] == "fixed" and q["emc"]["global"] == 1.2


@pytest.mark.asyncio
async def test_emc_without_settings_uses_defaults_when_saved(db_session):
    c, h = await _owner(db_session, f"emc3{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, {"slot": 2, "name": "EMC", "mode": "emc_table"})
        q = (await client.get(f"/api/v1/chests/summary/{c.slug}")).json()["targets"]["quotas"][0]
    assert r.status_code == 200
    assert q["emc"]["global"] == 1 and q["emc"]["monsters"]["hydra"] == 1


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    {"global": 1500},
    {"global": 0.001},
    {"monsters": {"hydra": 1, "undead": 1, "arachna": 1, "shadow": 1500}},
    {"ranges": [{"from": 50, "to": 300, "k": 1}]},
    {"ranges": [{"from": 500, "to": 300, "k": 1}]},
    {"ranges": [{"from": 100, "to": 600, "k": 1500}]},
    {"ranges": [{"from": 100 + i, "to": 100 + i, "k": 1} for i in range(11)]},
])
async def test_emc_invalid_settings_422(db_session, bad):
    c, h = await _owner(db_session, f"emc4{secrets.token_hex(3)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, {**Q, "emc": {**EMC, **bad}})
    assert r.status_code == 422
