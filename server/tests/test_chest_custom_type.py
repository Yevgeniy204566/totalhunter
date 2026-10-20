"""Свой тип сундука («Тыква»): владелец вводит английское каноническое имя, которого нет в общем
каталоге, — тип сохраняется только за этим кланом, вес и учёт работают как у обычных."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import ChestCollector, User
from web_routes import create_jwt


async def _owner(db, email):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6), email=email)
    db.add(user)
    await db.flush()
    c = ChestCollector(kingdom="K9", clan="PumpClan", user_id=user.id, slug=secrets.token_urlsafe(16))
    db.add(c)
    await db.commit()
    return c, {"Authorization": f"Bearer {create_jwt(user.id, email)}"}


def _row(catalog_id, **kw):
    return {"raw_type": "Тыква", "catalog_id": catalog_id, "custom_name": None, "points": 12,
            "is_in_pattern": True, **kw}


async def _post(client, c, h, rows):
    return await client.post("/web/dashboard/chests/rows", headers=h,
                             json={"collector_slug": c.slug, "rows": rows})


async def _mine(client, c, h):
    data = (await client.get("/web/dashboard/chests", headers=h)).json()
    return next(x for x in data["collectors"] if x["slug"] == c.slug)


@pytest.mark.asyncio
async def test_custom_type_saved_with_weight_and_listed_for_this_clan(db_session):
    c, h = await _owner(db_session, f"cu1{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _post(client, c, h, [_row("Pumpkin Chest", is_custom=True)])
        mine = await _mine(client, c, h)
    assert r.status_code == 200
    row = next(x for x in mine["rows"] if x["catalog_id"] == "Pumpkin Chest")
    assert row["points"] == 12 and row["is_in_pattern"] is True and row["is_custom"] is True
    assert "Pumpkin Chest" in {o["catalog_id"] for o in mine["catalog_options"]}


@pytest.mark.asyncio
async def test_custom_type_not_visible_to_other_clans(db_session):
    c, h = await _owner(db_session, f"cu2{secrets.token_hex(2)}@example.com")
    other, oh = await _owner(db_session, f"cu3{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _post(client, c, h, [_row("Pumpkin Chest", is_custom=True)])
        theirs = await _mine(client, other, oh)
    assert "Pumpkin Chest" not in {o["catalog_id"] for o in theirs["catalog_options"]}


@pytest.mark.asyncio
async def test_unflagged_unknown_catalog_id_still_rejected(db_session):
    c, h = await _owner(db_session, f"cu4{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _post(client, c, h, [_row("Pumpkin Chest")])
    assert r.status_code == 400


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", ["", "   ", "x;drop table", "Тыква", "A" * 61, "<b>x</b>"])
async def test_custom_type_invalid_name_rejected(db_session, bad):
    c, h = await _owner(db_session, f"cu5{secrets.token_hex(3)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _post(client, c, h, [_row(bad, is_custom=True)])
    assert r.status_code in (400, 422)


@pytest.mark.asyncio
async def test_custom_type_survives_resave_round_trip(db_session):
    c, h = await _owner(db_session, f"cu6{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await _post(client, c, h, [_row("Pumpkin Chest", is_custom=True)])
        rows = (await _mine(client, c, h))["rows"]
        r = await _post(client, c, h, rows)          # кабинет шлёт строки обратно как пришли
        again = (await _mine(client, c, h))["rows"]
    assert r.status_code == 200
    assert any(x["catalog_id"] == "Pumpkin Chest" and x["points"] == 12 for x in again)


@pytest.mark.asyncio
async def test_custom_type_whitespace_is_normalised(db_session):
    c, h = await _owner(db_session, f"cu7{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await _post(client, c, h, [_row("  Pumpkin   Chest ", is_custom=True)])
        rows = (await _mine(client, c, h))["rows"]
    assert r.status_code == 200
    assert any(x["catalog_id"] == "Pumpkin Chest" for x in rows)
