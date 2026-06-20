"""Tests for chest_aliases.py — admin endpoint for syncing alias dictionaries."""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import ChestCollector, PlayerAlias, ChestTypeAlias, ChestTypeCatalog, ChestLocalization, User

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
                                  canonical_type="OldCanonType"))
    db_session.add(ChestTypeCatalog(canonical_type="Эпический отряд", pattern="T9", points=1))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={
                "collector_slug": slug,
                "player_aliases": [{"raw_name": "Machet", "canonical_name": "MACHETE"}],
                "chest_aliases": [{"raw_type": "Эпический отр", "canonical_type": "Эпический отряд"}],
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
    assert type_rows[0].canonical_type == "Эпический отряд"


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
async def test_import_aliases_chest_alias_defaults_to_enabled(db_session):
    collector = await _create_collector(db_session)
    db_session.add(ChestTypeCatalog(canonical_type="Epic X", pattern="T9", points=1))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "X", "canonical_type": "Epic X"}]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalar_one()
    assert row.enabled is True


@pytest.mark.asyncio
async def test_import_aliases_chest_alias_can_be_disabled(db_session):
    collector = await _create_collector(db_session)
    db_session.add(ChestTypeCatalog(canonical_type="Y", pattern="T9", points=1))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "Y", "canonical_type": "Y", "enabled": False}]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalar_one()
    assert row.enabled is False


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


@pytest.mark.asyncio
async def test_import_aliases_resolves_native_text_via_localizations(db_session):
    collector = await _create_collector(db_session)
    collector.language = "ru"
    db_session.add(ChestLocalization(canonical_type="Yogwai", language="ru",
                                     display_text="Ёкай"))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "Exon", "canonical_type": "Ёкай"}]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalar_one()
    assert row.raw_type == "Exon"
    assert row.canonical_type == "Yogwai"


@pytest.mark.asyncio
async def test_import_aliases_accepts_known_english_literal_without_language(db_session):
    collector = await _create_collector(db_session)
    db_session.add(ChestTypeCatalog(canonical_type="Epic Crypt 25", pattern="T9", points=45))
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "Crpt25", "canonical_type": "Epic Crypt 25"}]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalar_one()
    assert row.canonical_type == "Epic Crypt 25"


@pytest.mark.asyncio
async def test_import_aliases_unresolved_text_falls_back_to_submitted_text(db_session):
    collector = await _create_collector(db_session)
    collector.language = "ru"
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [
                      {"raw_type": "Exon", "canonical_type": "Ёкай"},
                      {"raw_type": "Zzz", "canonical_type": "Незнакомый сундук"},
                  ]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True, "player_aliases": 0, "chest_aliases": 2}

    rows = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
        .order_by(ChestTypeAlias.raw_type)
    )).scalars().all()
    assert [(r.raw_type, r.canonical_type) for r in rows] == [
        ("Exon", "Ёкай"), ("Zzz", "Незнакомый сундук"),
    ]


@pytest.mark.asyncio
async def test_import_aliases_unresolved_text_falls_back_without_collector_language(db_session):
    collector = await _create_collector(db_session)
    await db_session.commit()
    slug = collector.slug

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/chests/aliases/import",
            json={"collector_slug": slug, "player_aliases": [],
                  "chest_aliases": [{"raw_type": "Exon", "canonical_type": "Ёкай"}]},
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalar_one()
    assert row.canonical_type == "Ёкай"
