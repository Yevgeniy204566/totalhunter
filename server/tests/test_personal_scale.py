"""Тумблер «Персонализированный учёт по Герою»: квот две (Crypts, EMC), слот 2 в режиме emc_table
⇔ тумблер включён; рычаги шкалы и EMC сохраняются при выключении; «Всего» — не квота."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import ChestCollector, User
from web_routes import create_jwt

Q1 = {"slot": 1, "name": "Crypts", "target": 200, "mode": "fixed"}
Q2 = {"slot": 2, "name": "EMC", "target": 50, "mode": "fixed"}
ON = {"crypts": True, "emc": True, "norm": 1.2, "weights": 0.9, "ranges": [{"from": 400, "to": 600, "k": 1.1}]}


async def _owner(db, email, quotas=None):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6), email=email)
    db.add(user)
    await db.flush()
    c = ChestCollector(kingdom="K9", clan="PsClan", user_id=user.id, slug=secrets.token_urlsafe(16),
                       quotas=quotas or [])
    db.add(c)
    await db.commit()
    return c, {"Authorization": f"Bearer {create_jwt(user.id, email)}"}


async def _patch(client, c, h, body):
    return await client.patch(f"/web/dashboard/chests/{c.slug}/season", headers=h, json=body)


async def _public(client, c):
    return (await client.get(f"/api/v1/chests/summary/{c.slug}")).json()["targets"]


@pytest.mark.asyncio
async def test_toggle_on_makes_slot2_emc_table_and_exposes_personal(db_session):
    c, h = await _owner(db_session, f"ps1{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, {"quotas": [Q1, Q2], "personal": ON})
        t = await _public(client, c)
    assert r.status_code == 200
    q2 = next(q for q in t["quotas"] if q["slot"] == 2)
    assert q2["mode"] == "emc_table" and q2["emc"]["global"] == 1
    assert next(q for q in t["quotas"] if q["slot"] == 1)["mode"] == "fixed"
    assert t["personal"]["norm"] == 1.2 and t["personal"]["ranges"][0] == {"from": 400, "to": 600, "k": 1.1}


@pytest.mark.asyncio
async def test_toggle_on_creates_missing_emc_slot(db_session):
    c, h = await _owner(db_session, f"ps2{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _patch(client, c, h, {"quotas": [Q1], "personal": ON})
        t = await _public(client, c)
    assert [q["slot"] for q in t["quotas"]] == [1, 2] and t["quotas"][1]["mode"] == "emc_table"


@pytest.mark.asyncio
async def test_toggle_off_goes_back_to_fixed_but_keeps_levers(db_session):
    c, h = await _owner(db_session, f"ps3{secrets.token_hex(2)}@example.com")
    emc = {"global": 1.3, "monsters": {"hydra": 1, "undead": 1, "arachna": 1, "shadow": 1}, "ranges": []}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _patch(client, c, h, {"quotas": [Q1, {**Q2, "emc": emc}], "personal": ON})
        await _patch(client, c, h, {"personal": {**ON, "crypts": False, "emc": False}})
        t = await _public(client, c)
        await _patch(client, c, h, {"personal": ON})
        again = await _public(client, c)
    q2 = next(q for q in t["quotas"] if q["slot"] == 2)
    assert q2["mode"] == "fixed" and q2["emc"]["global"] == 1.3 and t["personal"] is None
    assert next(q for q in again["quotas"] if q["slot"] == 2)["emc"]["global"] == 1.3


@pytest.mark.asyncio
async def test_third_quota_not_allowed(db_session):
    c, h = await _owner(db_session, f"ps4{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, {"quotas": [Q1, Q2, {"slot": 3, "name": "ALL", "target": 1}]})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_crypts_only_leaves_emc_fixed(db_session):
    c, h = await _owner(db_session, f"ps8{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _patch(client, c, h, {"quotas": [Q1, Q2], "personal": {**ON, "emc": False}})
        t = await _public(client, c)
    assert t["personal"]["crypts"] is True and t["personal"]["emc"] is False
    assert next(q for q in t["quotas"] if q["slot"] == 2)["mode"] == "fixed"


@pytest.mark.asyncio
async def test_emc_only_makes_slot2_personal(db_session):
    c, h = await _owner(db_session, f"ps9{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _patch(client, c, h, {"quotas": [Q1, Q2], "personal": {**ON, "crypts": False}})
        t = await _public(client, c)
    assert t["personal"]["emc"] is True and t["personal"]["crypts"] is False
    assert next(q for q in t["quotas"] if q["slot"] == 2)["mode"] == "emc_table"


@pytest.mark.asyncio
async def test_old_modes_rejected(db_session):
    c, h = await _owner(db_session, f"ps5{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for mode in ("per_player", "hero_points"):
            r = await _patch(client, c, h, {"quotas": [{**Q1, "mode": mode}]})
            assert r.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [{"norm": 1500}, {"weights": 0.001},
                                 {"ranges": [{"from": 500, "to": 300, "k": 1}]}])
async def test_personal_levers_validated(db_session, bad):
    c, h = await _owner(db_session, f"ps6{secrets.token_hex(3)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, {"personal": {**ON, **bad}})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_cabinet_returns_personal_scale(db_session):
    c, h = await _owner(db_session, f"ps7{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _patch(client, c, h, {"personal": ON})
        data = (await client.get("/web/dashboard/chests", headers=h)).json()
    mine = next(x for x in data["collectors"] if x["slug"] == c.slug)
    assert mine["personal_scale"]["crypts"] is True and mine["personal_scale"]["weights"] == 0.9


@pytest.mark.asyncio
async def test_row_in_missing_quota_slot_creates_default_quota(db_session):
    c, h = await _owner(db_session, f"ps10{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/web/dashboard/chests/rows", headers=h, json={
            "collector_slug": c.slug,
            "rows": [{"raw_type": "x", "catalog_id": "Epic Crypt 30", "is_custom": True, "points": 80,
                      "is_in_pattern": True, "quota_slot": 1}]})
        t = await _public(client, c)
    assert r.status_code == 200
    assert t["quotas"] == [{"slot": 1, "name": "Crypts", "target": None, "mode": "fixed"}]


MIX = {"w": {"Epic Crypt 35": {"on": True, "all": 1.2, "bands": {"380": 0.5}},
             "Common Crypt 25": {"on": False}},
       "c": {"Epic Crypt 30": {"all": 1.4, "bands": {"300": 2.0}}},
       "epic": {"all": 1.5}}


@pytest.mark.asyncio
async def test_mixer_values_saved_and_exposed(db_session):
    c, h = await _owner(db_session, f"ps11{secrets.token_hex(2)}@example.com")
    emc = {"global": 1.0, "monsters": {"hydra": 1, "undead": 1, "arachna": 1, "shadow": 1}, "ranges": [],
           "cells": {"hydra": {"400": 0.5}}, "off": ["undead"]}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, {"quotas": [Q1, {**Q2, "emc": emc}], "personal": {**ON, "mix": MIX}})
        t = await _public(client, c)
    assert r.status_code == 200
    assert t["personal"]["mix"]["w"]["Epic Crypt 35"]["bands"] == {"380": 0.5}
    assert t["personal"]["mix"]["w"]["Common Crypt 25"]["on"] is False
    assert t["personal"]["mix"]["c"]["Epic Crypt 30"]["bands"] == {"300": 2.0}
    q2 = next(q for q in t["quotas"] if q["slot"] == 2)
    assert q2["emc"]["cells"] == {"hydra": {"400": 0.5}} and q2["emc"]["off"] == ["undead"]


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_mix", [
    {"w": {"Epic Crypt 35": {"all": 1500}}},
    {"w": {"Epic Crypt 35": {"all": 0.001}}},
    {"w": {"Epic Crypt 35": {"bands": {"385": 1.0}}}},        # ступень — только 100,110…600
    {"w": {"Epic Crypt 35": {"bands": {"650": 1.0}}}},
    {"w": {"Epic Crypt 35": {"bands": {"400": 1500}}}},
    {"w": {"x" * 61: {"all": 1}}},
    {"w": {f"T{i}": {"all": 1} for i in range(81)}},
    {"c": {"Epic Crypt 30": {"all": 1500}}},
    {"c": {"Epic Crypt 30": {"bands": {"305": 1}}}},
])
async def test_mixer_invalid_values_422(db_session, bad_mix):
    c, h = await _owner(db_session, f"ps12{secrets.token_hex(3)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, {"personal": {**ON, "mix": bad_mix}})
    assert r.status_code == 422


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_emc", [
    {"cells": {"dragon": {"400": 1.0}}},
    {"cells": {"hydra": {"405": 1.0}}},
    {"cells": {"hydra": {"400": 1500}}},
    {"off": ["dragon"]},
])
async def test_emc_cells_invalid_422(db_session, bad_emc):
    c, h = await _owner(db_session, f"ps13{secrets.token_hex(3)}@example.com")
    emc = {"global": 1.0, "monsters": {"hydra": 1, "undead": 1, "arachna": 1, "shadow": 1}, "ranges": [], **bad_emc}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, {"quotas": [{**Q2, "emc": emc}]})
    assert r.status_code == 422


PRESET = {"name": "Мой клан", "norm": 1.1, "weights": 0.9,
          "mix": {"w": {"Epic Crypt 35": {"all": 1.2}}, "c": {"Rare Crypt 30": {"set": 25}}},
          "emc": {"global": 1.2, "monsters": {"hydra": 1, "undead": 1, "arachna": 1, "shadow": 1},
                  "ranges": [], "cells": {}, "off": []}}


@pytest.mark.asyncio
async def test_presets_saved_in_three_slots(db_session):
    c, h = await _owner(db_session, f"ps14{secrets.token_hex(2)}@example.com")
    body = {"personal": {**ON, "presets": {"1": PRESET, "3": {**PRESET, "name": "Строгий"}}}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, body)
        data = (await client.get("/web/dashboard/chests", headers=h)).json()
    mine = next(x for x in data["collectors"] if x["slug"] == c.slug)
    assert r.status_code == 200
    pre = mine["personal_scale"]["presets"]
    assert set(pre) == {"1", "3"} and pre["3"]["name"] == "Строгий"
    assert pre["1"]["mix"]["c"]["Rare Crypt 30"]["set"] == 25 and pre["1"]["emc"]["global"] == 1.2


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    {"4": PRESET},                                   # слотов только 3
    {"1": {**PRESET, "name": "x" * 31}},
    {"1": {**PRESET, "norm": 1500}},
    {"1": {**PRESET, "mix": {"c": {"A": {"set": -1}}}}},
    {"1": {**PRESET, "mix": {"c": {"A": {"set": 100000}}}}},
])
async def test_presets_invalid_422(db_session, bad):
    c, h = await _owner(db_session, f"ps15{secrets.token_hex(3)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _patch(client, c, h, {"personal": {**ON, "presets": bad}})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_mixer_accepts_up_to_80_types(db_session):
    c, h = await _owner(db_session, f"ps16{secrets.token_hex(2)}@example.com")
    mix = {"w": {f"Type {i}": {"all": 1.1} for i in range(80)}}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        ok = await _patch(client, c, h, {"personal": {**ON, "mix": mix}})
        too_many = await _patch(client, c, h, {"personal": {**ON, "mix": {"w": {f"T{i}": {} for i in range(81)}}}})
    assert ok.status_code == 200 and too_many.status_code == 422
