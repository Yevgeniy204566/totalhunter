"""Несколько квот сундуков (владелец 2026-09-26): вместо тумблеров «В пресете»/«Считать в
квоту» — «Учёт» строки (не в учёте / в учёте / квота 1..3); до 3 квот с именем и целью.
Спека: docs/superpowers/specs/2026-09-26-chest-multi-quota-design-01.md"""
import os
import secrets
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from chest_summary import pivot_summary
from main import app
from models import Chest, ChestCatalogReference, ChestCollector, ChestConfiguration, ChestTypeAlias, User
from web_routes import create_jwt


async def _owner(db, email="quota-owner@example.com"):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6), email=email)
    db.add(user)
    await db.flush()
    return user, {"Authorization": f"Bearer {create_jwt(user.id, email)}"}


async def _known(db, *ids):
    # /rows принимает только сундуки из эталонного справочника
    existing = set((await db.execute(select(ChestCatalogReference.catalog_id))).scalars().all())
    for cid in ids:
        if cid not in existing:
            db.add(ChestCatalogReference(catalog_id=cid))


async def _collector(db, user_id, quotas=None, slug=None):
    await _known(db, "Epic Crypt 30", "Epic Crypt 25")
    c = ChestCollector(kingdom="K7", clan="QuotaClan", user_id=user_id,
                       slug=slug or secrets.token_urlsafe(16), quotas=quotas or [])
    db.add(c)
    await db.flush()
    return c


# ── pivot_summary ──────────────────────────────────────────────────────────

def _row(sender, t, points, slot, in_pattern, count):
    return (sender, t, t, points, slot, in_pattern, count)


def test_points_sum_ignores_quota_and_each_quota_counts_separately():
    rows = [
        _row("A", "Epic Crypt 30", 80, 1, 1, 2),
        _row("A", "Epic Monster", 60, 2, 1, 3),
        _row("A", "Infernus", 30, None, 1, 1),
        _row("A", "Common Crypt 25", 15, None, 0, 5),   # не в учёте
    ]
    s = pivot_summary("K", "C", rows, quota_slots=frozenset({1, 2}))
    p = s["players"][0]
    assert p["points"] == 2 * 80 + 3 * 60 + 30
    assert p["quotas"] == {"1": 2, "2": 3}
    assert p["quota_chests"] == 2          # совместимость со старым сайтом: слот 1
    assert "Common Crypt 25" not in s["chest_types"]


def test_removed_quota_rows_keep_points():
    rows = [_row("A", "Epic Monster", 60, 2, 1, 3)]
    s = pivot_summary("K", "C", rows, quota_slots=frozenset({1}))   # квоты 2 больше нет
    p = s["players"][0]
    assert p["points"] == 180
    assert p["quotas"] == {"1": 0}


def test_legacy_bool_flag_is_slot_one_by_default():
    rows = [("A", "Epic Crypt 30", "Epic Crypt 30", 80, 1, 1, 4)]
    s = pivot_summary("K", "C", rows)
    assert s["players"][0]["quota_chests"] == 4


# ── строки кабинета ────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_row_slot_forces_in_account_and_is_returned(db_session):
    user, h = await _owner(db_session)
    c = await _collector(db_session, user.id)
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/web/dashboard/chests/rows", headers=h, json={
            "collector_slug": c.slug, "rows": [
                {"catalog_id": "Epic Crypt 30", "points": 80, "is_in_pattern": False, "quota_slot": 2},
                {"catalog_id": "Epic Crypt 25", "points": 45, "is_in_pattern": True, "quota_slot": None},
            ]})
        assert r.status_code == 200
        rows = (await client.get("/web/dashboard/chests", headers=h)).json()["collectors"][0]["rows"]
    by_id = {x["catalog_id"]: x for x in rows}
    assert by_id["Epic Crypt 30"]["quota_slot"] == 2
    assert by_id["Epic Crypt 30"]["is_in_pattern"] is True
    assert by_id["Epic Crypt 25"]["quota_slot"] is None


@pytest.mark.asyncio
async def test_row_rejects_slot_4(db_session):
    user, h = await _owner(db_session, "q4@example.com")
    c = await _collector(db_session, user.id)
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/web/dashboard/chests/rows", headers=h, json={
            "collector_slug": c.slug,
            "rows": [{"catalog_id": "Epic Crypt 30", "points": 80, "quota_slot": 4}]})
    assert r.status_code == 422


@pytest.mark.asyncio
async def test_rows_ignores_legacy_quota_flag(db_session):
    user, h = await _owner(db_session, "legacyflag@example.com")
    c = await _collector(db_session, user.id)
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/web/dashboard/chests/rows", headers=h, json={
            "collector_slug": c.slug, "rows": [{"catalog_id": "Epic Crypt 30", "points": 80,
                                                 "is_in_pattern": True, "counts_toward_quota": True}]})
    cfg = (await db_session.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == c.id))).scalar_one()
    assert cfg.quota_slot is None


# ── настройки квот ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_quotas_saved_and_returned(db_session):
    user, h = await _owner(db_session, "qsave@example.com")
    c = await _collector(db_session, user.id)
    await db_session.commit()
    quotas = [{"slot": 1, "name": "Склепы", "target": 200}, {"slot": 2, "name": "EM", "target": 50}]
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.patch(f"/web/dashboard/chests/{c.slug}/season", headers=h, json={"quotas": quotas})
        assert r.status_code == 200
        got = (await client.get("/web/dashboard/chests", headers=h)).json()["collectors"][0]["quotas"]
    assert got == [{"slot": 1, "name": "Склепы", "target": 200, "mode": "fixed"},
                   {"slot": 2, "name": "EM", "target": 50, "mode": "fixed"}]


@pytest.mark.asyncio
@pytest.mark.parametrize("quotas", [
    [{"slot": s, "name": f"Q{s}", "target": 1} for s in (1, 2, 3, 3)],          # 4 квоты / дубль
    [{"slot": 1, "name": "A", "target": 1}, {"slot": 1, "name": "B", "target": 2}],
    [{"slot": 0, "name": "A", "target": 1}],
    [{"slot": 1, "name": "", "target": 1}],
    [{"slot": 1, "name": "A", "target": -1}],
])
async def test_quotas_invalid_rejected(db_session, quotas):
    user, h = await _owner(db_session, f"qbad{secrets.token_hex(3)}@example.com")
    c = await _collector(db_session, user.id)
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.patch(f"/web/dashboard/chests/{c.slug}/season", headers=h, json={"quotas": quotas})
    assert r.status_code == 422


# ── публичная сводка и архив ───────────────────────────────────────────────

async def _seed_two_quotas(db, user_id):
    c = await _collector(db, user_id, quotas=[
        {"slot": 1, "name": "Склепы", "target": 2, "mode": "fixed"},
        {"slot": 2, "name": "EM", "target": 5, "mode": "fixed"}])
    for raw, cat, pts, slot in (("r1", "Epic Crypt 30", 80, 1), ("r2", "Epic Arachne", 40, 2)):
        db.add(ChestTypeAlias(collector_id=c.id, raw_type=raw, catalog_id=cat))
        db.add(ChestConfiguration(collector_id=c.id, catalog_id=cat, points=pts,
                                  is_in_pattern=True, quota_slot=slot))
    for i, raw in enumerate(("r1", "r1", "r2")):
        db.add(Chest(collector_id=c.id, sender_raw="Olla", sender_canonical="Olla",
                     chest_type_raw=raw, chest_type_canonical=raw,
                     collected_at=datetime.fromisoformat(f"2026-09-26T10:00:0{i}")))
    await db.flush()
    return c


@pytest.mark.asyncio
async def test_summary_has_player_quotas_and_targets(db_session):
    user, _ = await _owner(db_session, "qsum@example.com")
    c = await _seed_two_quotas(db_session, user.id)
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        data = (await client.get(f"/api/v1/chests/summary/{c.slug}")).json()
    olla = data["players"][0]
    assert olla["points"] == 2 * 80 + 40
    assert olla["quotas"] == {"1": 2, "2": 1}
    assert [q["name"] for q in data["targets"]["quotas"]] == ["Склепы", "EM"]


@pytest.mark.asyncio
async def test_close_season_snapshots_quotas(db_session):
    user, h = await _owner(db_session, "qarch@example.com")
    c = await _seed_two_quotas(db_session, user.id)
    c.period_start = datetime.fromisoformat("2026-09-20T00:00:00")
    c.period_end = datetime.fromisoformat("2026-10-20T00:00:00")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert (await client.post(f"/web/dashboard/chests/{c.slug}/close-season", headers=h)).status_code == 200
        seasons = (await client.get(f"/api/v1/chests/history/{c.slug}")).json()["seasons"]
        detail = (await client.get(f"/api/v1/chests/history/{c.slug}/{seasons[0]['id']}")).json()
    assert [q["slot"] for q in detail["targets"]["quotas"]] == [1, 2]
    assert detail["players"][0]["quotas"] == {"1": 2, "2": 1}
