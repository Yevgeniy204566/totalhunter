"""Tests for chest_aliases.py — admin endpoint for syncing alias dictionaries."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import ChestCollector, PlayerAlias, ChestTypeAlias, User

ADMIN_TOKEN = os.environ["ADMIN_TOKEN"]


async def _create_collector(db, slug=None):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6))
    db.add(user)
    await db.flush()
    collector = ChestCollector(
        kingdom="K1", clan="ClanA", user_id=user.id,
        slug=slug or secrets.token_urlsafe(16),
    )
    db.add(collector)
    await db.flush()
    return collector


@pytest.mark.asyncio
async def test_import_aliases_no_token_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/aliases/import", json={
            "collector_slug": "whatever", "player_aliases": [], "chest_aliases": [],
        })
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_import_aliases_wrong_token_returns_403():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": "whatever", "player_aliases": [], "chest_aliases": []},
            headers={"Authorization": "Bearer not-the-real-token"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_import_aliases_unknown_slug_returns_404(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": "does-not-exist", "player_aliases": [], "chest_aliases": []},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_import_aliases_full_replace(db_session):
    collector = await _create_collector(db_session)
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="OldRaw",
                               canonical_name="OldCanon"))
    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="OldRawType",
                                  catalog_id="OldCatalogId"))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={
                "collector_slug": slug,
                "player_aliases": [{"raw_name": "Machet", "canonical_name": "MACHETE"}],
                "chest_aliases": [{"raw_type": "Эпический отр", "canonical_type": "Epic Arachne"}],
            },
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body == {"ok": True, "player_aliases": 1, "chest_aliases": 1}

    player_rows = (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()
    assert len(player_rows) == 1
    assert player_rows[0].raw_name == "Machet"
    assert player_rows[0].canonical_name == "MACHETE"

    type_rows = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalars().all()
    assert len(type_rows) == 1
    assert type_rows[0].raw_type == "Эпический отр"
    assert type_rows[0].catalog_id == "Epic Arachne"


@pytest.mark.asyncio
async def test_import_aliases_empty_lists_clear_existing(db_session):
    collector = await _create_collector(db_session)
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="OldRaw",
                               canonical_name="OldCanon"))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [], "chest_aliases": []},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "player_aliases": 0, "chest_aliases": 0}

    remaining = (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_import_aliases_sets_pattern_and_language(db_session):
    collector = await _create_collector(db_session)
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [], "chest_aliases": [],
                  "pattern": "T9", "language": "ru"},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200

    await db_session.refresh(collector)
    assert collector.pattern == "T9"
    assert collector.language == "ru"


@pytest.mark.asyncio
async def test_import_aliases_omitted_pattern_leaves_existing_value(db_session):
    collector = await _create_collector(db_session)
    collector.pattern = "T9"
    collector.language = "ru"
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [], "chest_aliases": []},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200

    await db_session.refresh(collector)
    assert collector.pattern == "T9"
    assert collector.language == "ru"
