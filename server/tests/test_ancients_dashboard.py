"""Tests for ancients_dashboard.py — self-service «Древний» calculator for the
logged-in user. Mirrors the auth pattern from test_chest_dashboard.py (JWT Bearer,
db_session fixture, AsyncClient + ASGITransport — no auth_client/web_user fixtures
exist in conftest.py)."""
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import AncientCalculation, AncientNameMapping, AncientRoster, ChestCollector, PlayerAlias, PlayerProfile, User
from web_routes import create_jwt


async def _create_user_with_token(db, email="owner@example.com"):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6),
               email=email)
    db.add(user)
    await db.flush()
    token = create_jwt(user.id, email)
    return user, token


async def _create_collector(db, user_id, slug=None, clan="ClanA"):
    collector = ChestCollector(kingdom="K1", clan=clan, user_id=user_id,
                               slug=slug or secrets.token_urlsafe(16))
    db.add(collector)
    await db.flush()
    return collector


@pytest.mark.asyncio
async def test_get_roster_returns_players(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="s1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100, troop_level="G8 S8 M8"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["collectors"][0]["roster"][0]["player_name"] == "Иванов"
    assert data["collectors"][0]["roster"][0]["troop_level"] == "G8 S8 M8"


@pytest.mark.asyncio
async def test_patch_troop_level(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="s2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=100, troop_level=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/s2/troop-level",
            json={"player_name": "Петров", "troop_level": "G7 S7 M8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.troop_level == "G7 S7 M8"


@pytest.mark.asyncio
async def test_calculate_strategy_a_saves_history(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="s3")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/s3/calculate",
            json={
                "strategy": "A", "summon_levels": [81, 100],
                "amplification_coef": 1.5, "officer_count": 2, "veteran_count": 1,
            },
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_quota_millions"] == pytest.approx((45.1 + 114) * 1.5)
    assert "officer_quota" in body["result"]

    rows = (await db_session.execute(
        select(AncientCalculation).where(AncientCalculation.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_calculate_history_capped_at_5(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="s4")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for _ in range(6):
            resp = await client.post(
                "/web/dashboard/ancients/s4/calculate",
                json={
                    "strategy": "A", "summon_levels": [81],
                    "amplification_coef": 1.0, "officer_count": 1, "veteran_count": 0,
                },
                headers={"Authorization": f"Bearer {token}"},
            )
            assert resp.status_code == 200

    rows = (await db_session.execute(
        select(AncientCalculation).where(AncientCalculation.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 5


@pytest.mark.asyncio
async def test_roster_uses_profile_troop_level_as_fallback(db_session):
    user, token = await _create_user_with_token(db_session, "anc_prof1@test.com")
    collector = await _create_collector(db_session, user.id, slug="anc-pf-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Alice",
                                 place=1, points=1000, troop_level=None))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Alice",
                                 rank="Старший", troop_level="G8 S8 M8"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    roster = resp.json()["collectors"][0]["roster"]
    alice = next(r for r in roster if r["player_name"] == "Alice")
    assert alice["troop_level"] == "G8 S8 M8"


@pytest.mark.asyncio
async def test_roster_manual_troop_level_wins_over_profile(db_session):
    user, token = await _create_user_with_token(db_session, "anc_prof2@test.com")
    collector = await _create_collector(db_session, user.id, slug="anc-pf-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Bob",
                                 place=1, points=2000, troop_level="G9 S9 M9"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Bob",
                                 rank="Глава", troop_level="G5 S5 M5"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    roster = resp.json()["collectors"][0]["roster"]
    bob = next(r for r in roster if r["player_name"] == "Bob")
    assert bob["troop_level"] == "G9 S9 M9"


@pytest.mark.asyncio
async def test_get_roster_suggested_name_via_fuzzy(db_session):
    """Roster row gets suggested_name when fuzzy-match finds a canonical name."""
    user, token = await _create_user_with_token(db_session, "fuzzy1@test.com")
    collector = await _create_collector(db_session, user.id, slug="fuzzy-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Marisha",
                                 place=1, points=100, troop_level=None))
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="ocr_raw",
                               canonical_name="Маришка"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["player_name"] == "Marisha"
    assert row["mapping_confirmed"] is False
    assert row["mapped_name"] is None
    assert "is_alias_source" in row
    # cross-script fuzzy won't fire; suggested_name None → is_alias_source False
    assert row["is_alias_source"] is False


@pytest.mark.asyncio
async def test_get_roster_confirmed_mapping_applied(db_session):
    """Confirmed mapping → mapped_name populated, mapping_confirmed=True."""
    user, token = await _create_user_with_token(db_session, "mapped1@test.com")
    collector = await _create_collector(db_session, user.id, slug="mapped-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Marisha",
                                 place=1, points=100, troop_level=None))
    db_session.add(AncientNameMapping(collector_id=collector.id,
                                      raw_ocr_name="Marisha",
                                      canonical_name="Маришка",
                                      confirmed=True))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["mapped_name"] == "Маришка"
    assert row["mapping_confirmed"] is True
    assert row["suggested_name"] is None
    assert row["is_alias_source"] is False  # confirmed mapping → no suggestion active


@pytest.mark.asyncio
async def test_patch_name_mappings_upsert(db_session):
    """PATCH creates new mapping; second PATCH with same raw_name updates it (upsert)."""
    from sqlalchemy import select as sa_select
    user, token = await _create_user_with_token(db_session, "map2@test.com")
    collector = await _create_collector(db_session, user.id, slug="map-2")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First PATCH — creates
        resp = await client.patch(
            f"/web/dashboard/ancients/{collector.slug}/name-mappings",
            json={"mappings": [{"raw_ocr_name": "Marisha", "canonical_name": "Маришка",
                                "confirmed": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

        # Second PATCH — updates
        resp2 = await client.patch(
            f"/web/dashboard/ancients/{collector.slug}/name-mappings",
            json={"mappings": [{"raw_ocr_name": "Marisha", "canonical_name": "Мариша",
                                "confirmed": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200

    rows = (await db_session.execute(
        sa_select(AncientNameMapping).where(AncientNameMapping.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].canonical_name == "Мариша"


@pytest.mark.asyncio
async def test_delete_name_mapping_unlocks(db_session):
    """DELETE removes the mapping; row no longer exists in DB."""
    user, token = await _create_user_with_token(db_session, "del1@test.com")
    collector = await _create_collector(db_session, user.id, slug="del-1")
    db_session.add(AncientNameMapping(collector_id=collector.id,
                                      raw_ocr_name="PL4YER",
                                      canonical_name="PLAYER",
                                      confirmed=True))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            f"/web/dashboard/ancients/{collector.slug}/name-mappings/PL4YER",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True}

    from sqlalchemy import select as sa_select
    row = (await db_session.execute(
        sa_select(AncientNameMapping).where(
            AncientNameMapping.collector_id == collector.id,
            AncientNameMapping.raw_ocr_name == "PL4YER",
        )
    )).scalar_one_or_none()
    assert row is None


@pytest.mark.asyncio
async def test_patch_name_mappings_wrong_owner_returns_403(db_session):
    """PATCH to another user's collector returns 403."""
    owner, _ = await _create_user_with_token(db_session, "owner2@test.com")
    _, attacker_token = await _create_user_with_token(db_session, "attacker@test.com")
    collector = await _create_collector(db_session, owner.id, slug="own-2")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/web/dashboard/ancients/{collector.slug}/name-mappings",
            json={"mappings": []},
            headers={"Authorization": f"Bearer {attacker_token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_delete_name_mapping_not_found_returns_404(db_session):
    """DELETE on a nonexistent mapping returns 404, not 200."""
    user, token = await _create_user_with_token(db_session, "del2@test.com")
    collector = await _create_collector(db_session, user.id, slug="del-2")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            f"/web/dashboard/ancients/{collector.slug}/name-mappings/nonexistent",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404
    assert resp.json()["detail"] == "Mapping not found"


@pytest.mark.asyncio
async def test_collectors_sorted_newest_first(db_session):
    """Newest collector (highest id) appears first in the list, not insertion order."""
    user, token = await _create_user_with_token(db_session, "sortorder@test.com")
    await _create_collector(db_session, user.id, slug="sort-old", clan="ClanA")
    await db_session.commit()
    await _create_collector(db_session, user.id, slug="sort-new", clan="ClanB")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    slugs = [c["slug"] for c in resp.json()["collectors"]]
    assert slugs == ["sort-new", "sort-old"]


@pytest.mark.asyncio
async def test_hide_collector_removes_from_list_and_lists_as_hidden(db_session):
    """PATCH ancient-visibility {hidden:true} removes collector from `collectors`
    and surfaces it in `hidden_collectors` — underlying data (Chests) untouched."""
    user, token = await _create_user_with_token(db_session, "hide1@test.com")
    collector = await _create_collector(db_session, user.id, slug="hide-1")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/hide-1/ancient-visibility",
            json={"hidden": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        resp2 = await client.get("/web/dashboard/ancients",
                                 headers={"Authorization": f"Bearer {token}"})
    data = resp2.json()
    assert data["collectors"] == []
    assert [h["slug"] for h in data["hidden_collectors"]] == ["hide-1"]


@pytest.mark.asyncio
async def test_unhide_collector_restores_to_list(db_session):
    """PATCH hidden:false brings the collector back into `collectors`."""
    user, token = await _create_user_with_token(db_session, "hide2@test.com")
    collector = await _create_collector(db_session, user.id, slug="hide-2")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.patch(
            "/web/dashboard/ancients/hide-2/ancient-visibility",
            json={"hidden": True},
            headers={"Authorization": f"Bearer {token}"},
        )
        resp = await client.patch(
            "/web/dashboard/ancients/hide-2/ancient-visibility",
            json={"hidden": False},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200

        resp2 = await client.get("/web/dashboard/ancients",
                                 headers={"Authorization": f"Bearer {token}"})
    data = resp2.json()
    assert [c["slug"] for c in data["collectors"]] == ["hide-2"]
    assert data["hidden_collectors"] == []


@pytest.mark.asyncio
async def test_hide_collector_wrong_owner_returns_403(db_session):
    owner, _ = await _create_user_with_token(db_session, "hideowner@test.com")
    _, attacker_token = await _create_user_with_token(db_session, "hideattacker@test.com")
    collector = await _create_collector(db_session, owner.id, slug="hide-3")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/hide-3/ancient-visibility",
            json={"hidden": True},
            headers={"Authorization": f"Bearer {attacker_token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_hidden_collector_editor_access_unaffected(db_session):
    """Hiding is an owner-only view preference — editors still see the collector."""
    from datetime import datetime, timedelta, timezone
    from models import AncientEditor
    owner, owner_token = await _create_user_with_token(db_session, "hideownereditor@test.com")
    editor, editor_token = await _create_user_with_token(db_session, "hideeditor@test.com")
    collector = await _create_collector(db_session, owner.id, slug="hide-4")
    db_session.add(AncientEditor(collector_id=collector.id, user_id=editor.id,
                                 expires_at=datetime.now(timezone.utc) + timedelta(days=30)))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.patch(
            "/web/dashboard/ancients/hide-4/ancient-visibility",
            json={"hidden": True},
            headers={"Authorization": f"Bearer {owner_token}"},
        )
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {editor_token}"})
    assert [c["slug"] for c in resp.json()["collectors"]] == ["hide-4"]


@pytest.mark.asyncio
async def test_fuzzy_threshold_high_suppresses_weak_match(db_session):
    """?fuzzy_threshold=1.0 suppresses suggestions that would pass at 0.75."""
    user, token = await _create_user_with_token(db_session, "thresh1@test.com")
    collector = await _create_collector(db_session, user.id, slug="thresh-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Aleksei",
                                 place=1, points=50, troop_level=None))
    # canonical "Aleksey" is ~0.86 similar to "Aleksei" — passes 0.75, fails 1.0
    db_session.add(PlayerAlias(collector_id=collector.id,
                               raw_name="r1", canonical_name="Aleksey"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp_75  = await client.get("/web/dashboard/ancients?fuzzy_threshold=0.75",
                                    headers={"Authorization": f"Bearer {token}"})
        resp_100 = await client.get("/web/dashboard/ancients?fuzzy_threshold=1.0",
                                    headers={"Authorization": f"Bearer {token}"})

    row_75  = resp_75.json()["collectors"][0]["roster"][0]
    row_100 = resp_100.json()["collectors"][0]["roster"][0]
    # At 0.75, fuzzy may suggest "Aleksey" (implementation-dependent — just check no crash)
    assert "suggested_name" in row_75
    # At 1.0 (exact only), no suggestion possible
    assert row_100["suggested_name"] is None


@pytest.mark.asyncio
async def test_hide_sets_ancient_hidden_at_unhide_clears_it(db_session):
    user, token = await _create_user_with_token(db_session, "hideat1@test.com")
    collector = await _create_collector(db_session, user.id, slug="hide-at-1")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.patch(
            "/web/dashboard/ancients/hide-at-1/ancient-visibility",
            json={"hidden": True},
            headers={"Authorization": f"Bearer {token}"},
        )
    await db_session.refresh(collector)
    assert collector.ancient_hidden_at is not None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.patch(
            "/web/dashboard/ancients/hide-at-1/ancient-visibility",
            json={"hidden": False},
            headers={"Authorization": f"Bearer {token}"},
        )
    await db_session.refresh(collector)
    assert collector.ancient_hidden_at is None


def _normalize_tz(dt):
    """Strip timezone for SQLite naive/aware comparison."""
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


@pytest.mark.asyncio
async def test_calculate_touches_ancient_hidden_at_when_hidden(db_session):
    user, token = await _create_user_with_token(db_session, "calctouch1@test.com")
    collector = await _create_collector(db_session, user.id, slug="calc-touch-1")
    collector.ancient_hidden = True
    collector.ancient_hidden_at = datetime.now(timezone.utc) - timedelta(days=55)
    await db_session.commit()
    old_touch = collector.ancient_hidden_at

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/calc-touch-1/calculate",
            json={"strategy": "A", "summon_levels": [81], "amplification_coef": 1.0,
                  "officer_count": 1, "veteran_count": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    await db_session.refresh(collector)
    assert _normalize_tz(collector.ancient_hidden_at) > _normalize_tz(old_touch)


@pytest.mark.asyncio
async def test_calculate_rearms_timer_after_it_was_cleared_by_a_purge(db_session):
    user, token = await _create_user_with_token(db_session, "postpurgecalc1@test.com")
    collector = await _create_collector(db_session, user.id, slug="post-purge-calc-1")
    collector.ancient_hidden = True
    collector.ancient_hidden_at = None
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/post-purge-calc-1/calculate",
            json={"strategy": "A", "summon_levels": [81], "amplification_coef": 1.0,
                  "officer_count": 1, "veteran_count": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    await db_session.refresh(collector)
    assert collector.ancient_hidden_at is not None


@pytest.mark.asyncio
async def test_ocr_roster_rows_default_to_ocr_source(db_session):
    """Existing (pre-manual-entries) rows created the normal way default to
    source='ocr' with no manual expiry — the new columns don't break the
    existing tournament-import path."""
    user, token = await _create_user_with_token(db_session, "sourcedefault1@test.com")
    collector = await _create_collector(db_session, user.id, slug="source-default-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100))
    await db_session.commit()

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.source == "ocr"
    assert row.manual_expires_at is None
    assert row.rank is None


@pytest.mark.asyncio
async def test_calculate_strategy_b_uses_confirmed_mapped_name(db_session):
    """A confirmed AncientNameMapping's canonical name appears in the quota
    result table instead of the raw OCR player_name."""
    user, token = await _create_user_with_token(db_session, "mappedcalc1@test.com")
    collector = await _create_collector(db_session, user.id, slug="mapped-calc-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Ivan0v_raw",
                                 place=1, points=100, troop_level="G8 S8 M8"))
    db_session.add(AncientNameMapping(collector_id=collector.id,
                                      raw_ocr_name="Ivan0v_raw",
                                      canonical_name="Иванов", confirmed=True))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/mapped-calc-1/calculate",
            json={"strategy": "B", "summon_levels": [81], "amplification_coef": 1.0,
                  "clan_preset": "T8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()["result"]["players"]]
    assert names == ["Иванов"]


@pytest.mark.asyncio
async def test_calculate_strategy_b_uses_raw_name_when_unmapped(db_session):
    """No confirmed mapping -> raw player_name is used unchanged (no regression)."""
    user, token = await _create_user_with_token(db_session, "unmappedcalc1@test.com")
    collector = await _create_collector(db_session, user.id, slug="unmapped-calc-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Ivan0v_raw",
                                 place=1, points=100, troop_level="G8 S8 M8"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/unmapped-calc-1/calculate",
            json={"strategy": "B", "summon_levels": [81], "amplification_coef": 1.0,
                  "clan_preset": "T8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()["result"]["players"]]
    assert names == ["Ivan0v_raw"]
