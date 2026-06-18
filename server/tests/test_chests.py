"""Tests for chests.py — tenant isolation, alias dictionary, idempotent import."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app, CREDIT_COST


def test_credit_cost_chest_is_10():
    assert CREDIT_COST["chest"] == 10


import secrets
from sqlalchemy import select

from models import User, ChestCollector, Chest


async def _create_user(db, hwid, is_banned=False):
    u = User(hwid=hwid, ref_code=secrets.token_urlsafe(6), is_banned=is_banned)
    db.add(u)
    await db.flush()
    return u


def _payload(hwid, kingdom="K1", clan="ClanA", items=None):
    return {
        "hwid": hwid,
        "kingdom": kingdom,
        "clan": clan,
        "timestamp": "2026-06-18T12:00:00",
        "items": items if items is not None else [
            {"chest_type": "Сундук Эпического Монстра", "sender": "Игрок1",
             "timestamp": "2026-06-18T11:55:00"},
        ],
    }


@pytest.mark.asyncio
async def test_import_unknown_hwid_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/import", json=_payload("nohwid000000000"))
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_import_banned_user_returns_403(db_session):
    user = await _create_user(db_session, "banned00000000a", is_banned=True)
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/import", json=_payload(user.hwid))
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_import_empty_items_returns_400(db_session):
    user = await _create_user(db_session, "emptyitems000a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/import", json=_payload(user.hwid, items=[])
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_import_creates_collector_and_chest_row(db_session):
    user = await _create_user(db_session, "happypath0000a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/import", json=_payload(user.hwid))
    assert resp.status_code == 200
    body = resp.json()
    assert body["ok"] is True
    assert body["count"] == 1
    assert "collector_slug" in body and len(body["collector_slug"]) > 0

    collectors = (await db_session.execute(select(ChestCollector))).scalars().all()
    assert len(collectors) == 1
    assert collectors[0].kingdom == "K1" and collectors[0].clan == "ClanA"
    assert collectors[0].user_id == user.id

    chests = (await db_session.execute(select(Chest))).scalars().all()
    assert len(chests) == 1
    assert chests[0].sender_raw == "Игрок1"
    assert chests[0].sender_canonical == "Игрок1"  # нет алиаса → canonical = raw
    assert chests[0].chest_type_raw == "Сундук Эпического Монстра"


@pytest.mark.asyncio
async def test_import_same_tenant_twice_reuses_collector(db_session):
    user = await _create_user(db_session, "reuseuser0000a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, items=[{"chest_type": "A", "sender": "S1",
                               "timestamp": "2026-06-18T10:00:00"}]))
        await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, items=[{"chest_type": "B", "sender": "S2",
                               "timestamp": "2026-06-18T10:05:00"}]))

    collectors = (await db_session.execute(select(ChestCollector))).scalars().all()
    assert len(collectors) == 1
    chests = (await db_session.execute(select(Chest))).scalars().all()
    assert len(chests) == 2
