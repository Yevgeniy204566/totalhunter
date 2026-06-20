"""Tests for chest_catalog.py — admin endpoints for the GLOBAL points catalog and
GLOBAL localizations (not scoped to a single collector)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import ChestLocalization, ChestTypeCatalog

ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]


@pytest.mark.asyncio
async def test_import_catalog_no_token_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/catalog/import", json={"entries": []})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_import_catalog_wrong_token_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/catalog/import", json={"entries": []},
            headers={"Authorization": "Bearer not-the-real-token"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_import_catalog_full_replace(db_session):
    db_session.add(ChestTypeCatalog(canonical_type="Old Chest", pattern="T9", points=1))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/catalog/import",
            json={"entries": [
                {"canonical_type": "Epic Fenrir", "pattern": "T9", "points": 5},
                {"canonical_type": "Common Crypt 25", "pattern": "T9", "points": 5},
            ]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "count": 2}

    rows = (await db_session.execute(select(ChestTypeCatalog))).scalars().all()
    assert {r.canonical_type for r in rows} == {"Epic Fenrir", "Common Crypt 25"}


@pytest.mark.asyncio
async def test_import_catalog_empty_clears_table(db_session):
    db_session.add(ChestTypeCatalog(canonical_type="Old Chest", pattern="T9", points=1))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/catalog/import", json={"entries": []},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "count": 0}
    rows = (await db_session.execute(select(ChestTypeCatalog))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_import_localizations_no_token_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/localizations/import", json={"entries": []})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_import_localizations_full_replace(db_session):
    db_session.add(ChestLocalization(canonical_type="Old Chest", language="ru",
                                     display_text="Старый"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/localizations/import",
            json={"entries": [
                {"canonical_type": "Epic Fenrir", "language": "ru",
                 "display_text": "Эпический Фенрир"},
            ]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "count": 1}

    rows = (await db_session.execute(select(ChestLocalization))).scalars().all()
    assert len(rows) == 1
    assert rows[0].canonical_type == "Epic Fenrir"
    assert rows[0].display_text == "Эпический Фенрир"


@pytest.mark.asyncio
async def test_import_localizations_empty_clears_table(db_session):
    db_session.add(ChestLocalization(canonical_type="Old Chest", language="ru",
                                     display_text="Старый"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/localizations/import", json={"entries": []},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    rows = (await db_session.execute(select(ChestLocalization))).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_import_catalog_duplicate_entry_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/catalog/import",
            json={"entries": [
                {"canonical_type": "Epic Fenrir", "pattern": "T9", "points": 5},
                {"canonical_type": "Epic Fenrir", "pattern": "T9", "points": 9},
            ]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_import_localizations_duplicate_entry_returns_400():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/localizations/import",
            json={"entries": [
                {"canonical_type": "Epic Fenrir", "language": "ru", "display_text": "A"},
                {"canonical_type": "Epic Fenrir", "language": "ru", "display_text": "B"},
            ]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 400
