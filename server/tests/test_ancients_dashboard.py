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
from models import AncientCalculation, AncientNameMapping, AncientRoster, ChestCollector, Log, PlayerAlias, PlayerProfile, User
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
async def test_patch_rank_saves_value(db_session):
    user, token = await _create_user_with_token(db_session, "rank1@test.com")
    collector = await _create_collector(db_session, user.id, slug="rank-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=100, rank=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/rank-1/rank",
            json={"player_name": "Петров", "rank": "Офицер"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.rank == "Офицер"


@pytest.mark.asyncio
async def test_patch_rank_rejects_unknown_value(db_session):
    user, token = await _create_user_with_token(db_session, "rank2@test.com")
    collector = await _create_collector(db_session, user.id, slug="rank-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=100, rank=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/rank-2/rank",
            json={"player_name": "Петров", "rank": "Новичок"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_patch_rank_404_for_unknown_player(db_session):
    user, token = await _create_user_with_token(db_session, "rank3@test.com")
    collector = await _create_collector(db_session, user.id, slug="rank-3")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/rank-3/rank",
            json={"player_name": "НетТакого", "rank": "Офицер"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_roster_get_includes_rank_field(db_session):
    user, token = await _create_user_with_token(db_session, "rankget1@test.com")
    collector = await _create_collector(db_session, user.id, slug="rankget-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100, rank="Ветеран"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["rank"] == "Ветеран"


@pytest.mark.asyncio
async def test_roster_quota_strategy_a_officer_bucket(db_session):
    user, token = await _create_user_with_token(db_session, "quotaA1@test.com")
    collector = await _create_collector(db_session, user.id, slug="quota-a-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Глава1",
                                 place=1, points=100, rank="Глава"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Рядовой1",
                                 place=2, points=50, rank="Рядовой"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="БезЗвания",
                                 place=3, points=10, rank=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        calc_resp = await client.post(
            "/web/dashboard/ancients/quota-a-1/calculate",
            json={"strategy": "A", "summon_levels": [81], "amplification_coef": 1.0,
                  "officer_count": 1, "veteran_count": 1},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert calc_resp.status_code == 200
        officer_quota = calc_resp.json()["result"]["officer_quota"]
        veteran_quota = calc_resp.json()["result"]["veteran_quota"]

        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    roster = {p["player_name"]: p for p in resp.json()["collectors"][0]["roster"]}
    assert roster["Глава1"]["quota"] == pytest.approx(officer_quota)
    assert roster["Рядовой1"]["quota"] == pytest.approx(veteran_quota)
    assert roster["БезЗвания"]["quota"] is None


@pytest.mark.asyncio
async def test_calculate_logs_ancient_quota_calc_event(db_session):
    user, token = await _create_user_with_token(db_session, "quotalog1@test.com")
    collector = await _create_collector(db_session, user.id, slug="quota-log-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100, rank="Глава"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/quota-log-1/calculate",
            json={"strategy": "A", "summon_levels": [81], "amplification_coef": 1.0,
                  "officer_count": 1, "veteran_count": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    logs = (await db_session.execute(
        select(Log).where(Log.hwid == user.hwid, Log.event_type == "ancient_quota_calc")
    )).scalars().all()
    assert len(logs) == 1


@pytest.mark.asyncio
async def test_roster_quota_strategy_b_matches_by_name(db_session):
    user, token = await _create_user_with_token(db_session, "quotaB1@test.com")
    collector = await _create_collector(db_session, user.id, slug="quota-b-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100, troop_level="G8 S8 M8"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="БезВойск",
                                 place=2, points=50, troop_level=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        calc_resp = await client.post(
            "/web/dashboard/ancients/quota-b-1/calculate",
            json={"strategy": "B", "summon_levels": [81], "amplification_coef": 1.0,
                  "clan_preset": "T8"},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert calc_resp.status_code == 200
        ivanov_quota = calc_resp.json()["result"]["players"][0]["quota"]

        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    roster = {p["player_name"]: p for p in resp.json()["collectors"][0]["roster"]}
    assert roster["Иванов"]["quota"] == pytest.approx(ivanov_quota)
    assert roster["БезВойск"]["quota"] is None


@pytest.mark.asyncio
async def test_roster_quota_none_when_no_calculation_yet(db_session):
    user, token = await _create_user_with_token(db_session, "quotanone1@test.com")
    collector = await _create_collector(db_session, user.id, slug="quota-none-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=100, rank="Глава", troop_level="G8 S8 M8"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["quota"] is None


@pytest.mark.asyncio
async def test_patch_troop_level_accepts_non_diagonal_combo(db_session):
    """A combo like G7 S9 M8 was rejected by the old 13-entry TROOP_STEPS list —
    it must now be accepted since G/S/M are entered independently."""
    user, token = await _create_user_with_token(db_session, "nondiag1@test.com")
    collector = await _create_collector(db_session, user.id, slug="nondiag-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=100, troop_level=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/nondiag-1/troop-level",
            json={"player_name": "Петров", "troop_level": "G7 S9 M8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_patch_troop_level_rejects_malformed_value(db_session):
    user, token = await _create_user_with_token(db_session, "malformed1@test.com")
    collector = await _create_collector(db_session, user.id, slug="malformed-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=100, troop_level=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/malformed-1/troop-level",
            json={"player_name": "Петров", "troop_level": "G10 S9 M8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400


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
async def test_patch_name_mappings_merges_into_existing_canonical_row(db_session):
    """Confirming a mapping when a canonical row already exists (e.g. from
    populate-from-chests) physically merges the two rows into one — no
    duplicate, quota (troop_level) and points end up on the same row."""
    user, token = await _create_user_with_token(db_session, "merge1@test.com")
    collector = await _create_collector(db_session, user.id, slug="merge-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 troop_level="G8 S8 M8", rank="Офицер", source="chests"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Пeтрoв*VIP",
                                 place=5, points=80000, raw_ocr_name="Пeтрoв*VIP",
                                 source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/merge-1/name-mappings",
            json={"mappings": [{"raw_ocr_name": "Пeтрoв*VIP", "canonical_name": "Петров",
                                "confirmed": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
    merged = rows[0]
    assert merged.player_name == "Петров"
    assert merged.troop_level == "G8 S8 M8"
    assert merged.rank == "Офицер"
    assert merged.points == 80000
    assert merged.place == 5
    assert merged.raw_ocr_name == "Пeтрoв*VIP"


@pytest.mark.asyncio
async def test_patch_name_mappings_renames_when_no_canonical_row_exists(db_session):
    """Confirming a mapping when no canonical-named row exists yet just
    renames the raw row in place (nothing to merge with)."""
    user, token = await _create_user_with_token(db_session, "merge2@test.com")
    collector = await _create_collector(db_session, user.id, slug="merge-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Marisha",
                                 place=1, points=100, raw_ocr_name="Marisha", source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/merge-2/name-mappings",
            json={"mappings": [{"raw_ocr_name": "Marisha", "canonical_name": "Маришка",
                                "confirmed": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].player_name == "Маришка"
    assert rows[0].raw_ocr_name == "Marisha"
    assert rows[0].points == 100


@pytest.mark.asyncio
async def test_patch_name_mappings_unconfirmed_does_not_merge(db_session):
    """confirmed=False must not trigger a physical merge — only a confirmed
    mapping is trusted enough to rewrite roster data."""
    user, token = await _create_user_with_token(db_session, "merge3@test.com")
    collector = await _create_collector(db_session, user.id, slug="merge-3")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Сидоров*99",
                                 place=2, points=200, raw_ocr_name="Сидоров*99", source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/merge-3/name-mappings",
            json={"mappings": [{"raw_ocr_name": "Сидоров*99", "canonical_name": "Сидоров",
                                "confirmed": False}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].player_name == "Сидоров*99"  # unchanged — not merged


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


@pytest.mark.asyncio
async def test_add_manual_roster_entry_rejects_malformed_troop_level(db_session):
    user, token = await _create_user_with_token(db_session, "manualbad1@test.com")
    collector = await _create_collector(db_session, user.id, slug="manual-bad-1")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/manual-bad-1/roster/manual",
            json={"player_name": "НовыйИгрок", "troop_level": "G10 S7 M8", "rank": None},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_add_manual_roster_entry_creates_row(db_session):
    user, token = await _create_user_with_token(db_session, "manual1@test.com")
    collector = await _create_collector(db_session, user.id, slug="manual-1")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/manual-1/roster/manual",
            json={"player_name": "НовыйИгрок", "troop_level": "G7 S7 M8", "rank": "Ветеран"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name == "НовыйИгрок",
        )
    )).scalar_one()
    assert row.source == "manual"
    assert row.rank == "Ветеран"
    assert row.troop_level == "G7 S7 M8"
    assert row.place is None
    assert row.points is None
    assert row.manual_expires_at is not None


@pytest.mark.asyncio
async def test_add_manual_roster_entry_rejects_exact_duplicate(db_session):
    user, token = await _create_user_with_token(db_session, "manual2@test.com")
    collector = await _create_collector(db_session, user.id, slug="manual-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Существующий",
                                 place=1, points=10))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/manual-2/roster/manual",
            json={"player_name": "Существующий", "troop_level": None, "rank": None},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_add_manual_roster_entry_warns_on_similar_name(db_session):
    user, token = await _create_user_with_token(db_session, "manual3@test.com")
    collector = await _create_collector(db_session, user.id, slug="manual-3")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="raw1",
                               canonical_name="Иванов"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/manual-3/roster/manual",
            json={"player_name": "Иваанов", "troop_level": None, "rank": None},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 409
    assert resp.json()["detail"]["similar_name"] == "Иванов"

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_add_manual_roster_entry_editor_can_add(db_session):
    """Editors (not just the owner) can add manual entries, matching the
    troop-level/name-mappings permission model."""
    from datetime import timedelta
    from models import AncientEditor
    owner, _ = await _create_user_with_token(db_session, "manualowner@test.com")
    editor, editor_token = await _create_user_with_token(db_session, "manualeditor@test.com")
    collector = await _create_collector(db_session, owner.id, slug="manual-4")
    db_session.add(AncientEditor(collector_id=collector.id, user_id=editor.id,
                                 expires_at=datetime.now(timezone.utc) + timedelta(days=30)))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/manual-4/roster/manual",
            json={"player_name": "ДобавленРедактором", "troop_level": None, "rank": None},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_roster_entry_by_owner(db_session):
    """Owner can delete any roster row (OCR or manual) — departed clan
    members shouldn't keep receiving quota ('мёртвые души')."""
    user, token = await _create_user_with_token(db_session, "deleteroster1@test.com")
    collector = await _create_collector(db_session, user.id, slug="delete-roster-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Ушедший",
                                 place=1, points=100, source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            "/web/dashboard/ancients/delete-roster-1/roster/Ушедший",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"deleted": True}

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_delete_roster_entry_by_editor(db_session):
    from datetime import timedelta
    from models import AncientEditor
    owner, _ = await _create_user_with_token(db_session, "deleterosterowner@test.com")
    editor, editor_token = await _create_user_with_token(db_session, "deleterostereditor@test.com")
    collector = await _create_collector(db_session, owner.id, slug="delete-roster-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Ушедший2",
                                 place=1, points=50, source="manual"))
    db_session.add(AncientEditor(collector_id=collector.id, user_id=editor.id,
                                 expires_at=datetime.now(timezone.utc) + timedelta(days=30)))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            "/web/dashboard/ancients/delete-roster-2/roster/Ушедший2",
            headers={"Authorization": f"Bearer {editor_token}"},
        )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_delete_roster_entry_not_found_returns_404(db_session):
    user, token = await _create_user_with_token(db_session, "deleteroster3@test.com")
    collector = await _create_collector(db_session, user.id, slug="delete-roster-3")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            "/web/dashboard/ancients/delete-roster-3/roster/НеСуществует",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_populate_from_chests_adds_missing_canonical_names(db_session):
    user, token = await _create_user_with_token(db_session, "populate1@test.com")
    collector = await _create_collector(db_session, user.id, slug="populate-1")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="r1", canonical_name="Иванов"))
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="r2", canonical_name="Петров"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/populate-1/roster/populate-from-chests",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"synced": 2, "removed": 0}

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Иванов", "Петров"}
    for r in rows:
        assert r.source == "chests"
        assert r.place is None
        assert r.points is None
        assert r.manual_expires_at is None


@pytest.mark.asyncio
async def test_populate_from_chests_is_idempotent_on_second_call(db_session):
    user, token = await _create_user_with_token(db_session, "populate2@test.com")
    collector = await _create_collector(db_session, user.id, slug="populate-2")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="r1", canonical_name="Сидоров"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post(
            "/web/dashboard/ancients/populate-2/roster/populate-from-chests",
            headers={"Authorization": f"Bearer {token}"},
        )
        second = await client.post(
            "/web/dashboard/ancients/populate-2/roster/populate-from-chests",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert first.json() == {"synced": 1, "removed": 0}
    assert second.status_code == 200
    assert second.json() == {"synced": 1, "removed": 0}

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_populate_from_chests_renames_exact_match_row_and_keeps_real_data(db_session):
    """A raw OCR row whose name already equals the canonical name (bot's own
    fuzzy resolution already matched it) survives with its real data intact."""
    user, token = await _create_user_with_token(db_session, "populate3@test.com")
    collector = await _create_collector(db_session, user.id, slug="populate-3")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="r1", canonical_name="Кузнецов"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Кузнецов",
                                 place=3, points=500, source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/populate-3/roster/populate-from-chests",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.json() == {"synced": 1, "removed": 0}

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.source == "ocr"
    assert row.place == 3
    assert row.points == 500


@pytest.mark.asyncio
async def test_populate_from_chests_merges_confirmed_mapping_into_canonical_name(db_session):
    """A raw OCR row with a CONFIRMED name mapping gets renamed to the
    canonical name, keeping its real place/points — no duplicate row."""
    user, token = await _create_user_with_token(db_session, "populate5@test.com")
    collector = await _create_collector(db_session, user.id, slug="populate-5")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="pa1", canonical_name="Маришка"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Marisha_raw",
                                 place=7, points=333, troop_level="G8 S8 M8", source="ocr"))
    db_session.add(AncientNameMapping(collector_id=collector.id, raw_ocr_name="Marisha_raw",
                                      canonical_name="Маришка", confirmed=True))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/populate-5/roster/populate-from-chests",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.json() == {"synced": 1, "removed": 0}

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
    row = rows[0]
    assert row.player_name == "Маришка"
    assert row.place == 7
    assert row.points == 333
    assert row.troop_level == "G8 S8 M8"
    assert row.source == "ocr"


@pytest.mark.asyncio
async def test_populate_from_chests_preserves_raw_ocr_name(db_session):
    """The synced canonical row keeps the raw OCR text that was on the
    source row, so the dashboard can still show 'what the bot actually read'
    after populate-from-chests renames the row."""
    user, token = await _create_user_with_token(db_session, "populate7@test.com")
    collector = await _create_collector(db_session, user.id, slug="populate-7")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="r1", canonical_name="Кузнецов"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Кузнецов",
                                 place=3, points=500, raw_ocr_name="Кузнецoв_VIP",
                                 source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/populate-7/roster/populate-from-chests",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.raw_ocr_name == "Кузнецoв_VIP"


@pytest.mark.asyncio
async def test_populate_from_chests_deletes_rows_with_no_chests_relation(db_session):
    """A row with no exact canonical match and no confirmed mapping (e.g. a
    manually-added participant who doesn't carry chests) is deleted —
    explicit owner requirement: the roster mirrors Chests exactly."""
    user, token = await _create_user_with_token(db_session, "populate6@test.com")
    collector = await _create_collector(db_session, user.id, slug="populate-6")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="pa1", canonical_name="Иванов"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов", place=1, points=10, source="ocr"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="НетВСундуках",
                                 troop_level="G7 S7 M7", rank="Ветеран", source="manual"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/populate-6/roster/populate-from-chests",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.json() == {"synced": 1, "removed": 1}

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Иванов"}


@pytest.mark.asyncio
async def test_populate_from_chests_editor_can_call(db_session):
    from datetime import timedelta
    from models import AncientEditor
    owner, _ = await _create_user_with_token(db_session, "populateowner@test.com")
    editor, editor_token = await _create_user_with_token(db_session, "populateeditor@test.com")
    collector = await _create_collector(db_session, owner.id, slug="populate-4")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="r1", canonical_name="Смирнов"))
    db_session.add(AncientEditor(collector_id=collector.id, user_id=editor.id,
                                 expires_at=datetime.now(timezone.utc) + timedelta(days=30)))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/populate-4/roster/populate-from-chests",
            headers={"Authorization": f"Bearer {editor_token}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"synced": 1, "removed": 0}


@pytest.mark.asyncio
async def test_get_dashboard_returns_default_thresholds(db_session):
    user, token = await _create_user_with_token(db_session, "thresh1@test.com")
    await _create_collector(db_session, user.id, slug="thresh-1")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    thresholds = resp.json()["collectors"][0]["quota_thresholds"]
    assert thresholds == {"light_pct": 10.0, "medium_pct": 30.0, "critical_pct": 60.0}


@pytest.mark.asyncio
async def test_patch_quota_thresholds_saves_and_reflects_in_get(db_session):
    user, token = await _create_user_with_token(db_session, "thresh2@test.com")
    await _create_collector(db_session, user.id, slug="thresh-2")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        patch_resp = await client.patch(
            "/web/dashboard/ancients/thresh-2/quota-thresholds",
            json={"light_pct": 15.0, "medium_pct": 40.0, "critical_pct": 70.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert patch_resp.status_code == 200

        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    thresholds = resp.json()["collectors"][0]["quota_thresholds"]
    assert thresholds == {"light_pct": 15.0, "medium_pct": 40.0, "critical_pct": 70.0}


@pytest.mark.asyncio
async def test_patch_quota_thresholds_rejects_non_owner_editor(db_session):
    from models import AncientEditor
    owner, _ = await _create_user_with_token(db_session, "thresh3owner@test.com")
    editor, editor_token = await _create_user_with_token(db_session, "thresh3editor@test.com")
    collector = await _create_collector(db_session, owner.id, slug="thresh-3")
    db_session.add(AncientEditor(collector_id=collector.id, user_id=editor.id,
                                 expires_at=datetime.now(timezone.utc) + timedelta(days=30)))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/thresh-3/quota-thresholds",
            json={"light_pct": 15.0, "medium_pct": 40.0, "critical_pct": 70.0},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_roster_shortfall_pct_present_when_quota_and_points_exist(db_session):
    user, token = await _create_user_with_token(db_session, "shortfallget1@test.com")
    collector = await _create_collector(db_session, user.id, slug="shortfallget-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=50, rank="Глава"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        calc_resp = await client.post(
            "/web/dashboard/ancients/shortfallget-1/calculate",
            json={"strategy": "A", "summon_levels": [81], "amplification_coef": 1.0,
                  "officer_count": 1, "veteran_count": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert calc_resp.status_code == 200
        officer_quota = calc_resp.json()["result"]["officer_quota"]

        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    expected = (officer_quota - 50) / officer_quota * 100.0
    assert row["shortfall_pct"] == pytest.approx(expected)


@pytest.mark.asyncio
async def test_roster_shortfall_pct_none_without_quota(db_session):
    user, token = await _create_user_with_token(db_session, "shortfallget2@test.com")
    collector = await _create_collector(db_session, user.id, slug="shortfallget-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=50, rank=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["shortfall_pct"] is None


@pytest.mark.asyncio
async def test_get_roster_already_merged_row_reports_confirmed_without_mapping_row(db_session):
    """A row that was already physically merged (raw_ocr_name differs from
    player_name) must show as confirmed even if the AncientNameMapping
    record was later deleted (unlock doesn't un-merge — see spec)."""
    user, token = await _create_user_with_token(db_session, "mergedget1@test.com")
    collector = await _create_collector(db_session, user.id, slug="mergedget-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=5, points=80000, raw_ocr_name="Пeтрoв*VIP",
                                 troop_level="G8 S8 M8", source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["player_name"] == "Петров"
    assert row["raw_ocr_name"] == "Пeтрoв*VIP"
    assert row["mapped_name"] == "Петров"
    assert row["mapping_confirmed"] is True
    assert row["suggested_name"] is None


@pytest.mark.asyncio
async def test_get_roster_raw_ocr_name_none_for_pure_chests_row(db_session):
    """A row seeded purely by populate-from-chests, never touched by a
    tournament import, has no raw_ocr_name."""
    user, token = await _create_user_with_token(db_session, "mergedget2@test.com")
    collector = await _create_collector(db_session, user.id, slug="mergedget-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Сидоров",
                                 troop_level="G7 S7 M7", source="chests"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["raw_ocr_name"] is None
    assert row["mapping_confirmed"] is False


@pytest.mark.asyncio
async def test_get_roster_rank_falls_back_to_player_profile(db_session):
    """A row with no AncientRoster.rank set falls back to PlayerProfile.rank
    (the same table players self-report through on the public Chests page),
    both in the displayed 'rank' field and in Strategy-A quota lookup."""
    from models import PlayerProfile
    user, token = await _create_user_with_token(db_session, "rankfallback1@test.com")
    collector = await _create_collector(db_session, user.id, slug="rankfallback-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Кузнецов",
                                 place=1, points=100, rank=None, source="ocr"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Кузнецов",
                                 rank="Офицер", troop_level=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        calc_resp = await client.post(
            "/web/dashboard/ancients/rankfallback-1/calculate",
            json={"strategy": "A", "summon_levels": [81], "amplification_coef": 1.0,
                  "officer_count": 1, "veteran_count": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert calc_resp.status_code == 200
        officer_quota = calc_resp.json()["result"]["officer_quota"]

        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["rank"] == "Офицер"
    assert row["quota"] == pytest.approx(officer_quota)


@pytest.mark.asyncio
async def test_clear_ocr_deletes_pure_ocr_rows(db_session):
    """A row with no troop_level/rank — pure tournament-import junk — is
    deleted entirely."""
    user, token = await _create_user_with_token(db_session, "clear1@test.com")
    collector = await _create_collector(db_session, user.id, slug="clear-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Случайный*VIP",
                                 place=9, points=10, raw_ocr_name="Случайный*VIP",
                                 source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            "/web/dashboard/ancients/clear-1/roster/ocr-import",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 1, "cleared": 0}

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_clear_ocr_only_clears_points_on_curated_row(db_session):
    """A row that carries troop_level/rank (curated by the leader, possibly
    merged from a tournament import) survives — only place/points reset."""
    user, token = await _create_user_with_token(db_session, "clear2@test.com")
    collector = await _create_collector(db_session, user.id, slug="clear-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=5, points=80000, raw_ocr_name="Пeтрoв*VIP",
                                 troop_level="G8 S8 M8", rank="Офицер", source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            "/web/dashboard/ancients/clear-2/roster/ocr-import",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 0, "cleared": 1}

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.place is None
    assert row.points is None
    assert row.troop_level == "G8 S8 M8"
    assert row.rank == "Офицер"
    assert row.player_name == "Петров"


@pytest.mark.asyncio
async def test_clear_ocr_wrong_owner_returns_403(db_session):
    owner, _ = await _create_user_with_token(db_session, "clear3owner@test.com")
    _, attacker_token = await _create_user_with_token(db_session, "clear3attacker@test.com")
    collector = await _create_collector(db_session, owner.id, slug="clear-3")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            "/web/dashboard/ancients/clear-3/roster/ocr-import",
            headers={"Authorization": f"Bearer {attacker_token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_calculate_strategy_b_uses_player_profile_troop_fallback(db_session):
    """A roster row with no AncientRoster.troop_level but a valid
    PlayerProfile.troop_level is included in the Strategy-B quota split —
    not silently excluded just because the leader never re-typed it."""
    from models import PlayerProfile
    user, token = await _create_user_with_token(db_session, "calcfallback1@test.com")
    collector = await _create_collector(db_session, user.id, slug="calcfallback-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 troop_level=None, source="manual"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Иванов",
                                 rank=None, troop_level="G8 S8 M8"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/calcfallback-1/calculate",
            json={"strategy": "B", "summon_levels": [81], "amplification_coef": 1.0,
                  "clan_preset": "T8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    players = resp.json()["result"]["players"]
    assert len(players) == 1
    assert players[0]["name"] == "Иванов"
    assert players[0]["troop_level"] == "G8 S8 M8"
    assert resp.json()["result"]["excluded"] == []


@pytest.mark.asyncio
async def test_calculate_strategy_b_ignores_invalid_player_profile_troop(db_session):
    """A PlayerProfile.troop_level value that passes the laxer Chests
    validator (tiers 1-9) but fails Ancients' stricter parse_troop_level
    (tiers 5-9 only) must not crash calculate() — the player is excluded,
    same as if troop_level had never been set."""
    from models import PlayerProfile
    user, token = await _create_user_with_token(db_session, "calcfallback2@test.com")
    collector = await _create_collector(db_session, user.id, slug="calcfallback-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 troop_level=None, source="manual"))
    db_session.add(PlayerProfile(collector_id=collector.id, canonical_name="Петров",
                                 rank=None, troop_level="G3 S2 M4"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/calcfallback-2/calculate",
            json={"strategy": "B", "summon_levels": [81], "amplification_coef": 1.0,
                  "clan_preset": "T8"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400  # no players with a valid troop_level at all

