"""Tests for chest_dashboard.py — self-service chest mapping for the logged-in user."""
import os
import secrets
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import (
    Chest, ChestCollector, ChestConfiguration, ChestLocalization, ChestTypeAlias,
    ChestTypeCatalog, PlayerAlias, User,
)
from web_routes import create_jwt


async def _create_user_with_token(db, email="owner@example.com"):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6),
               email=email)
    db.add(user)
    await db.flush()
    token = create_jwt(user.id, email)
    return user, token


async def _create_collector(db, user_id, slug=None, language=None):
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=user_id,
                               slug=slug or secrets.token_urlsafe(16), language=language)
    db.add(collector)
    await db.flush()
    return collector


@pytest.mark.asyncio
async def test_get_chests_no_token_returns_401():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_chests_returns_only_own_collectors(db_session):
    user, token = await _create_user_with_token(db_session)
    other_user, _ = await _create_user_with_token(db_session, email="other@example.com")
    mine = await _create_collector(db_session, user.id, slug="mine-slug")
    await _create_collector(db_session, other_user.id, slug="not-mine-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    slugs = [c["slug"] for c in resp.json()["collectors"]]
    assert slugs == ["mine-slug"]


@pytest.mark.asyncio
async def test_get_chests_combines_alias_config_and_unmapped_raw(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="combo-slug", language="ru")
    # mapped + configured
    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="Raw1",
                                  catalog_id="Epic Arachne"))
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Epic Arachne",
                                      custom_name="Толстяк", points=40, is_in_pattern=True))
    # configured but never seen by the bot (manually added)
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Common Crypt 5",
                                      points=5, is_in_pattern=True))
    # seen by the bot, never mapped
    db_session.add(Chest(collector_id=collector.id, sender_raw="P1", sender_canonical="P1",
                         chest_type_raw="Raw2", chest_type_canonical="Raw2",
                         collected_at=datetime.fromisoformat("2026-06-20T10:00:00")))
    db_session.add(ChestTypeCatalog(canonical_type="Epic Arachne", pattern="T9", points=40))
    db_session.add(ChestLocalization(canonical_type="Epic Arachne", language="ru",
                                     display_text="Эпическая Арахна"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    collector_data = resp.json()["collectors"][0]
    rows = {(r["raw_type"], r["catalog_id"]) for r in collector_data["rows"]}
    assert ("Raw1", "Epic Arachne") in rows
    assert (None, "Common Crypt 5") in rows
    assert ("Raw2", None) in rows

    options = {o["catalog_id"]: o["label"] for o in collector_data["catalog_options"]}
    assert options["Epic Arachne"] == "Эпическая Арахна"


@pytest.mark.asyncio
async def test_post_rows_rejects_unknown_catalog_id(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="bad-catalog-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/rows",
            json={"collector_slug": "bad-catalog-slug",
                 "rows": [{"raw_type": "X", "catalog_id": "Not A Real Chest",
                           "custom_name": None, "points": 5, "is_in_pattern": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_post_rows_rejects_other_users_collector(db_session):
    user, token = await _create_user_with_token(db_session)
    other_user, _ = await _create_user_with_token(db_session, email="other2@example.com")
    await _create_collector(db_session, other_user.id, slug="someone-elses-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/rows",
            json={"collector_slug": "someone-elses-slug", "rows": []},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_post_rows_upserts_alias_and_configuration(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="upsert-slug")
    db_session.add(ChestTypeCatalog(canonical_type="Epic Arachne", pattern="T9", points=40))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/rows",
            json={"collector_slug": "upsert-slug",
                 "rows": [{"raw_type": "RawAB", "catalog_id": "Epic Arachne",
                           "custom_name": "Толстяк", "points": 99, "is_in_pattern": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    alias = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalar_one()
    assert alias.raw_type == "RawAB" and alias.catalog_id == "Epic Arachne"

    config = (await db_session.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalar_one()
    assert config.points == 99 and config.is_in_pattern is True
    assert config.custom_name == "Толстяк"


@pytest.mark.asyncio
async def test_post_rows_full_replace_removes_omitted_rows(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="full-replace-slug")
    db_session.add(ChestTypeCatalog(canonical_type="Epic Arachne", pattern="T9", points=40))
    db_session.add(ChestTypeCatalog(canonical_type="Common Crypt 5", pattern="T5", points=5))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/rows",
            json={"collector_slug": "full-replace-slug",
                 "rows": [{"raw_type": "RawA", "catalog_id": "Epic Arachne",
                           "custom_name": "Толстяк", "points": 40, "is_in_pattern": True},
                          {"raw_type": "RawB", "catalog_id": "Common Crypt 5",
                           "custom_name": None, "points": 5, "is_in_pattern": False}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    aliases = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalars().all()
    assert {a.catalog_id for a in aliases} == {"Epic Arachne", "Common Crypt 5"}
    configs = (await db_session.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalars().all()
    assert {c.catalog_id for c in configs} == {"Epic Arachne", "Common Crypt 5"}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/rows",
            json={"collector_slug": "full-replace-slug",
                 "rows": [{"raw_type": "RawA", "catalog_id": "Epic Arachne",
                           "custom_name": "Толстяк", "points": 40, "is_in_pattern": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    alias_b = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id,
                                     ChestTypeAlias.catalog_id == "Common Crypt 5")
    )).scalar_one_or_none()
    assert alias_b is None
    config_b = (await db_session.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id,
                                          ChestConfiguration.catalog_id == "Common Crypt 5")
    )).scalar_one_or_none()
    assert config_b is None

    alias_a = (await db_session.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id,
                                     ChestTypeAlias.catalog_id == "Epic Arachne")
    )).scalar_one()
    assert alias_a.raw_type == "RawA"
    config_a = (await db_session.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id,
                                          ChestConfiguration.catalog_id == "Epic Arachne")
    )).scalar_one()
    assert config_a.points == 40 and config_a.is_in_pattern is True
    assert config_a.custom_name == "Толстяк"


@pytest.mark.asyncio
async def test_management_token_then_claim_transfers_ownership(db_session):
    owner, owner_token = await _create_user_with_token(db_session, email="a@example.com")
    claimant, claimant_token = await _create_user_with_token(db_session, email="b@example.com")
    collector = await _create_collector(db_session, owner.id, slug="transferable-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        gen_resp = await client.post(
            "/web/dashboard/chests/management-token",
            json={"collector_slug": "transferable-slug"},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        assert gen_resp.status_code == 200
        code = gen_resp.json()["code"]

        claim_resp = await client.post(
            "/web/dashboard/chests/claim",
            json={"code": code},
            headers={"Authorization": f"Bearer {claimant_token}"},
        )
        assert claim_resp.status_code == 200

    await db_session.refresh(collector)
    assert collector.user_id == claimant.id
    assert collector.management_token is None


@pytest.mark.asyncio
async def test_claim_unknown_code_returns_404(db_session):
    _, token = await _create_user_with_token(db_session)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/claim",
            json={"code": "does-not-exist"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_patch_language_updates_own_collector(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="lang-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/chests/lang-slug/language",
            json={"language": "en"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    await db_session.refresh(collector)
    assert collector.language == "en"


@pytest.mark.asyncio
async def test_patch_language_rejects_other_users_collector(db_session):
    owner, _ = await _create_user_with_token(db_session, email="c@example.com")
    intruder, intruder_token = await _create_user_with_token(db_session, email="d@example.com")
    await _create_collector(db_session, owner.id, slug="protected-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/chests/protected-slug/language",
            json={"language": "en"},
            headers={"Authorization": f"Bearer {intruder_token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_get_chests_includes_unmapped_sender_as_player_alias_row(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="player-rows-slug")
    db_session.add(Chest(collector_id=collector.id, sender_raw="Araiina",
                         sender_canonical="Araiina", chest_type_raw="X",
                         chest_type_canonical="X",
                         collected_at=datetime.fromisoformat("2026-06-20T10:00:00")))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    collector_data = resp.json()["collectors"][0]
    assert collector_data["player_alias_rows"] == [
        {"raw_name": "Araiina", "canonical_name": None}
    ]


@pytest.mark.asyncio
async def test_get_chests_includes_existing_player_alias_with_canonical_name(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="player-alias-slug")
    db_session.add(Chest(collector_id=collector.id, sender_raw="Araiina",
                         sender_canonical="Arahna", chest_type_raw="X",
                         chest_type_canonical="X",
                         collected_at=datetime.fromisoformat("2026-06-20T10:00:00")))
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="Araiina",
                               canonical_name="Arahna"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    collector_data = resp.json()["collectors"][0]
    assert collector_data["player_alias_rows"] == [
        {"raw_name": "Araiina", "canonical_name": "Arahna"}
    ]


@pytest.mark.asyncio
async def test_post_player_aliases_rejects_other_users_collector(db_session):
    user, token = await _create_user_with_token(db_session)
    other_user, _ = await _create_user_with_token(db_session, email="other3@example.com")
    await _create_collector(db_session, other_user.id, slug="not-mine-pa-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/player-aliases",
            json={"collector_slug": "not-mine-pa-slug", "rows": []},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_post_player_aliases_creates_and_skips_empty_canonical(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="pa-create-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/player-aliases",
            json={"collector_slug": "pa-create-slug",
                 "rows": [{"raw_name": "Araiina", "canonical_name": "Arahna"},
                          {"raw_name": "Unfixed", "canonical_name": None},
                          {"raw_name": "AlsoUnfixed", "canonical_name": "  "}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    aliases = (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()
    assert len(aliases) == 1
    assert aliases[0].raw_name == "Araiina" and aliases[0].canonical_name == "Arahna"


@pytest.mark.asyncio
async def test_post_player_aliases_full_replace_removes_omitted_rows(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="pa-replace-slug")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="OldRaw",
                               canonical_name="OldCanon"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/player-aliases",
            json={"collector_slug": "pa-replace-slug",
                 "rows": [{"raw_name": "NewRaw", "canonical_name": "NewCanon"}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    aliases = (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()
    assert len(aliases) == 1
    assert aliases[0].raw_name == "NewRaw"


@pytest.mark.asyncio
async def test_collector_and_configuration_persist_new_season_columns(db_session):
    from datetime import datetime
    from models import ChestConfiguration

    user, _ = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="season-columns-slug")
    collector.timezone_offset_minutes = 180
    collector.period_start = datetime.fromisoformat("2026-06-21T00:00:00")
    collector.period_end = datetime.fromisoformat("2026-07-05T00:00:00")
    collector.target_points = 5000
    collector.target_chests = 50
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Epic Crypt 30",
                                      points=80, is_in_pattern=True, counts_toward_quota=True))
    await db_session.commit()

    reloaded = (await db_session.execute(
        select(ChestCollector).where(ChestCollector.slug == "season-columns-slug")
    )).scalar_one()
    assert reloaded.timezone_offset_minutes == 180
    assert reloaded.period_start == datetime.fromisoformat("2026-06-21T00:00:00")
    assert reloaded.period_end == datetime.fromisoformat("2026-07-05T00:00:00")
    assert reloaded.target_points == 5000
    assert reloaded.target_chests == 50

    config = (await db_session.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalar_one()
    assert config.counts_toward_quota is True


@pytest.mark.asyncio
async def test_new_season_columns_default_to_none_and_quota_defaults_to_false(db_session):
    from models import ChestConfiguration

    user, _ = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="season-defaults-slug")
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Rare Crypt 25",
                                      points=20, is_in_pattern=True))
    await db_session.commit()

    reloaded = (await db_session.execute(
        select(ChestCollector).where(ChestCollector.slug == "season-defaults-slug")
    )).scalar_one()
    assert reloaded.timezone_offset_minutes is None
    assert reloaded.period_start is None
    assert reloaded.period_end is None
    assert reloaded.target_points is None
    assert reloaded.target_chests is None

    config = (await db_session.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalar_one()
    assert config.counts_toward_quota is False
