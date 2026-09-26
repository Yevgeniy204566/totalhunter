"""Квота EM с персональной целью (войска + уровень Героя) — спека 02.
docs/superpowers/specs/2026-09-26-chest-em-quota-hero-design-02.md"""
import csv
import io
import os
import secrets
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from chest_summary import personal_target
from main import app
from models import Chest, ChestCollector, ChestConfiguration, ChestTypeAlias, PlayerProfile, User
from web_routes import create_jwt


PP = {"slot": 2, "name": "EM", "target": 50, "mode": "per_player", "hero_k": 0, "hero_h0": 400}


# ── формула ────────────────────────────────────────────────────────────────

def test_per_player_defaults_equal_fixed():
    assert personal_target(PP, "G9 S9 M9", 550) == (50, False)


def test_per_player_formula_uses_hero_only():
    q = {**PP, "hero_k": 20, "hero_h0": 400}
    # 50 × (1 + 20/100 × (550 − 400)/100) = 50 × 1.3 = 65; войска на цель не влияют
    assert personal_target(q, "G9 S8 M7", 550) == (65, False)
    assert personal_target(q, "G1 S1 M1", 550) == (65, False)


def test_per_player_missing_hero_uses_base():
    q = {**PP, "hero_k": 50}
    assert personal_target(q, "G9 S9 M9", None) == (50, True)
    assert personal_target(q, None, None) == (50, True)


def test_per_player_target_never_negative():
    q = {**PP, "hero_k": 100, "hero_h0": 999}   # Герой 1 при среднем 999: формула уходит в минус
    assert personal_target(q, "G1 S1 M1", 1)[0] == 0


def test_fixed_quota_has_no_personal_target():
    assert personal_target({"slot": 1, "name": "X", "target": 10, "mode": "fixed"}, "G9 S9 M9", 500) == (None, False)


# ── API ────────────────────────────────────────────────────────────────────

async def _owner_with_em(db, email):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6), email=email)
    db.add(user)
    await db.flush()
    q = {**PP, "hero_k": 20}
    c = ChestCollector(kingdom="K8", clan="EMClan", user_id=user.id, slug=secrets.token_urlsafe(16),
                       quotas=[{"slot": 1, "name": "Склепы", "target": 3, "mode": "fixed"}, q],
                       period_start=datetime.fromisoformat("2026-09-20T00:00:00"),
                       period_end=datetime.fromisoformat("2026-10-20T00:00:00"))
    db.add(c)
    await db.flush()
    db.add(ChestTypeAlias(collector_id=c.id, raw_type="em", catalog_id="Epic Arachne"))
    db.add(ChestConfiguration(collector_id=c.id, catalog_id="Epic Arachne", points=40,
                              is_in_pattern=True, quota_slot=2))
    for i in range(4):
        db.add(Chest(collector_id=c.id, sender_raw="Olla", sender_canonical="Olla", chest_type_raw="em",
                     chest_type_canonical="em", collected_at=datetime.fromisoformat(f"2026-09-26T10:00:0{i}")))
    db.add(PlayerProfile(collector_id=c.id, canonical_name="Olla", troop_level="G9 S8 M7", hero_level=550))
    await db.commit()
    return c, {"Authorization": f"Bearer {create_jwt(user.id, email)}"}


@pytest.mark.asyncio
async def test_summary_has_personal_targets(db_session):
    c, _ = await _owner_with_em(db_session, "em1@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        olla = (await client.get(f"/api/v1/chests/summary/{c.slug}")).json()["players"][0]
    assert olla["quotas"]["2"] == 4
    assert olla["quota_targets"] == {"2": 65}
    assert olla["quota_targets_partial"] == {"2": False}


@pytest.mark.asyncio
async def test_close_season_snapshot_has_troop_and_hero(db_session):
    c, h = await _owner_with_em(db_session, "em2@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post(f"/web/dashboard/chests/{c.slug}/close-season", headers=h)).status_code == 200
        sid = (await client.get(f"/api/v1/chests/history/{c.slug}")).json()["seasons"][0]["id"]
        olla = (await client.get(f"/api/v1/chests/history/{c.slug}/{sid}")).json()["players"][0]
    assert olla["troop_level"] == "G9 S8 M7" and olla["hero_level"] == 550
    assert olla["quota_targets"] == {"2": 65}


@pytest.mark.asyncio
@pytest.mark.parametrize("bad", [
    {"hero_k": 101},
    {"hero_k": -101},
    {"hero_h0": 0},
])
async def test_per_player_invalid_coefficients_422(db_session, bad):
    c, h = await _owner_with_em(db_session, f"em3{secrets.token_hex(2)}@example.com")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.patch(f"/web/dashboard/chests/{c.slug}/season", headers=h,
                               json={"quotas": [{**PP, **bad}]})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_stats_csv_owner_only_and_has_rows(db_session):
    c, h = await _owner_with_em(db_session, "em4@example.com")
    other = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6), email="em4o@example.com")
    db_session.add(other)
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.get(f"/web/dashboard/chests/{c.slug}/stats.csv",
                                  headers={"Authorization": f"Bearer {create_jwt(other.id, 'em4o@example.com')}"})
        assert denied.status_code == 403
        await client.post(f"/web/dashboard/chests/{c.slug}/close-season", headers=h)
        r = await client.get(f"/web/dashboard/chests/{c.slug}/stats.csv", headers=h)
    assert r.status_code == 200
    rows = list(csv.DictReader(io.StringIO(r.text.lstrip("﻿"))))
    olla = [x for x in rows if x["player"] == "Olla"]
    assert olla and olla[0]["G"] == "9" and olla[0]["hero"] == "550" and olla[0]["EM"] == "4"


@pytest.mark.asyncio
async def test_stats_csv_legacy_season_blank_fields(db_session):
    from models import ChestSeasonHistory
    c, h = await _owner_with_em(db_session, "em5@example.com")
    db_session.add(ChestSeasonHistory(
        collector_id=c.id, period_start=datetime.fromisoformat("2026-08-01T00:00:00"),
        period_end=datetime.fromisoformat("2026-08-15T00:00:00"), target_points_snapshot=None,
        target_chests_snapshot=5, quotas_snapshot=None,
        summary_json={"players": [{"name": "Old", "points": 10, "quota_chests": 2, "counts": {}}]}))
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/web/dashboard/chests/{c.slug}/stats.csv", headers=h)
    rows = list(csv.DictReader(io.StringIO(r.text.lstrip("﻿"))))
    old = [x for x in rows if x["player"] == "Old"][0]
    assert old["G"] == "" and old["hero"] == ""
