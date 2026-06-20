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


async def _create_user(db, hwid, is_banned=False, credits=100):
    u = User(hwid=hwid, ref_code=secrets.token_urlsafe(6), is_banned=is_banned, credits=credits)
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


from models import PlayerAlias, ChestTypeAlias


@pytest.mark.asyncio
async def test_alias_lookup_corrects_sender_and_chest_type(db_session):
    user = await _create_user(db_session, "aliasuser0000a")
    await db_session.commit()

    # Первый импорт создаёт коллектора без алиасов
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, items=[{"chest_type": "X", "sender": "X",
                               "timestamp": "2026-06-18T09:00:00"}]))

    collector = (await db_session.execute(select(ChestCollector))).scalar_one()
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="Араiiна",
                               canonical_name="Арахна"))
    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="Эпическая Араiiна",
                                  canonical_type="Эпическая Арахна"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, items=[{"chest_type": "Эпическая Араiiна", "sender": "Араiiна",
                               "timestamp": "2026-06-18T09:05:00"}]))
    assert resp.status_code == 200

    chests = (await db_session.execute(
        select(Chest).where(Chest.sender_raw == "Араiiна")
    )).scalars().all()
    assert len(chests) == 1
    assert chests[0].sender_canonical == "Арахна"
    assert chests[0].chest_type_canonical == "Эпическая Арахна"


@pytest.mark.asyncio
async def test_same_kingdom_clan_different_users_get_isolated_collectors(db_session):
    user_a = await _create_user(db_session, "isoluserA0000")
    user_b = await _create_user(db_session, "isoluserB0000")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/chests/import", json=_payload(
            user_a.hwid, kingdom="K9", clan="SameClan",
            items=[{"chest_type": "A", "sender": "S1", "timestamp": "2026-06-18T08:00:00"}]))
        await client.post("/api/v1/chests/import", json=_payload(
            user_b.hwid, kingdom="K9", clan="SameClan",
            items=[{"chest_type": "B", "sender": "S2", "timestamp": "2026-06-18T08:05:00"}]))

    collectors = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K9", ChestCollector.clan == "SameClan"
        )
    )).scalars().all()
    assert len(collectors) == 2
    assert {c.user_id for c in collectors} == {user_a.id, user_b.id}
    assert collectors[0].slug != collectors[1].slug

    collector_a = next(c for c in collectors if c.user_id == user_a.id)
    chests_a = (await db_session.execute(
        select(Chest).where(Chest.collector_id == collector_a.id)
    )).scalars().all()
    assert len(chests_a) == 1
    assert chests_a[0].sender_raw == "S1"


@pytest.mark.asyncio
async def test_resending_same_batch_does_not_duplicate(db_session):
    user = await _create_user(db_session, "resenduser000")
    await db_session.commit()
    payload = _payload(user.hwid, items=[
        {"chest_type": "A", "sender": "S1", "timestamp": "2026-06-18T07:00:00"},
        {"chest_type": "B", "sender": "S2", "timestamp": "2026-06-18T07:01:00"},
    ])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/api/v1/chests/import", json=payload)
        second = await client.post("/api/v1/chests/import", json=payload)

    assert first.json()["count"] == 2
    assert second.json()["count"] == 0  # все ключи уже существуют

    chests = (await db_session.execute(select(Chest))).scalars().all()
    assert len(chests) == 2


from models import Hunt, Transaction


@pytest.mark.asyncio
async def test_import_charges_10_credits_on_new_data(db_session):
    user = await _create_user(db_session, "chargeuser000a", credits=100)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, items=[
                {"chest_type": "A", "sender": "S1", "timestamp": "2026-06-18T05:00:00"},
                {"chest_type": "B", "sender": "S2", "timestamp": "2026-06-18T05:01:00"},
            ]))
    assert resp.status_code == 200
    assert resp.json()["count"] == 2

    await db_session.refresh(user)
    assert user.credits == 90  # списано один раз за батч, не за штуку

    txns = (await db_session.execute(
        select(Transaction).where(Transaction.user_id == user.id)
    )).scalars().all()
    assert len(txns) == 1
    assert txns[0].amount == -10

    hunts = (await db_session.execute(
        select(Hunt).where(Hunt.user_id == user.id, Hunt.hunt_type == "chest")
    )).scalars().all()
    assert len(hunts) == 1


@pytest.mark.asyncio
async def test_import_insufficient_credits_returns_402(db_session):
    user = await _create_user(db_session, "poorerguy0000", credits=5)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/api/v1/chests/import", json=_payload(user.hwid))
    assert resp.status_code == 402
    assert resp.json()["detail"]["required"] == 10
    assert resp.json()["detail"]["credits"] == 5

    await db_session.refresh(user)
    assert user.credits == 5  # не списано

    chests = (await db_session.execute(select(Chest))).scalars().all()
    assert len(chests) == 0  # ничего не записано


@pytest.mark.asyncio
async def test_resend_full_duplicate_does_not_charge_again(db_session):
    user = await _create_user(db_session, "noreuser00000", credits=100)
    await db_session.commit()
    payload = _payload(user.hwid, items=[
        {"chest_type": "A", "sender": "S1", "timestamp": "2026-06-18T04:00:00"},
    ])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/api/v1/chests/import", json=payload)
        second = await client.post("/api/v1/chests/import", json=payload)

    assert first.json()["count"] == 1
    assert second.json()["count"] == 0

    await db_session.refresh(user)
    assert user.credits == 90  # списано один раз, повторная отправка бесплатна


@pytest.mark.asyncio
async def test_partial_duplicate_charges_once_not_per_item(db_session):
    user = await _create_user(db_session, "partialuser00", credits=100)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, items=[{"chest_type": "A", "sender": "S1",
                               "timestamp": "2026-06-18T03:00:00"}]))
        second = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, items=[
                {"chest_type": "A", "sender": "S1", "timestamp": "2026-06-18T03:00:00"},  # дубль
                {"chest_type": "B", "sender": "S2", "timestamp": "2026-06-18T03:05:00"},  # новый
            ]))

    assert second.json()["count"] == 1
    await db_session.refresh(user)
    assert user.credits == 80  # 10 за первый запрос + 10 за второй (флэт за батч, не за штуку)


@pytest.mark.asyncio
async def test_concurrent_duplicate_recovers_without_500(db_session, monkeypatch):
    import chests as chests_module

    user = await _create_user(db_session, "raceuser00000", credits=100)
    await db_session.commit()
    payload = _payload(user.hwid, items=[
        {"chest_type": "A", "sender": "S1", "timestamp": "2026-06-18T02:00:00"},
    ])

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        first = await client.post("/api/v1/chests/import", json=payload)
    assert first.json()["count"] == 1

    # Simulate the race window: the in-memory existing-keys snapshot is stale on its
    # first read (as if another concurrent request had just committed the same row),
    # forcing our commit() to hit the DB unique constraint instead of catching it
    # via the pre-check.
    real_load = chests_module._load_existing_keys
    calls = {"n": 0}

    async def flaky_load(collector_id, db):
        calls["n"] += 1
        if calls["n"] == 1:
            return set()
        return await real_load(collector_id, db)

    monkeypatch.setattr(chests_module, "_load_existing_keys", flaky_load)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        second = await client.post("/api/v1/chests/import", json=payload)

    assert second.status_code == 200
    assert second.json()["count"] == 0

    await db_session.refresh(user)
    assert user.credits == 90  # заряжен один раз за первый (настоящий) импорт, не за гонку


@pytest.mark.asyncio
async def test_summary_unknown_slug_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/chests/summary/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_summary_aggregates_players_and_chest_types(db_session):
    user = await _create_user(db_session, "summarytest00a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K9", clan="ClanSummary",
            items=[
                {"chest_type": "Сундук Эпического Монстра", "sender": "Игрок1",
                 "timestamp": "2026-06-18T11:00:00"},
                {"chest_type": "Сундук Эпического Монстра", "sender": "Игрок1",
                 "timestamp": "2026-06-18T11:05:00"},
                {"chest_type": "Малый Сундук", "sender": "Игрок1",
                 "timestamp": "2026-06-18T11:10:00"},
                {"chest_type": "Сундук Эпического Монстра", "sender": "Игрок2",
                 "timestamp": "2026-06-18T11:15:00"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["kingdom"] == "K9"
    assert body["clan"] == "ClanSummary"
    assert sorted(body["chest_types"]) == ["Малый Сундук", "Сундук Эпического Монстра"]

    players_by_name = {p["name"]: p for p in body["players"]}
    assert players_by_name["Игрок1"]["counts"]["Сундук Эпического Монстра"] == 2
    assert players_by_name["Игрок1"]["counts"]["Малый Сундук"] == 1
    assert players_by_name["Игрок1"]["total"] == 3
    assert players_by_name["Игрок2"]["counts"]["Сундук Эпического Монстра"] == 1
    assert players_by_name["Игрок2"]["total"] == 1

    # sorted by total descending
    assert body["players"][0]["name"] == "Игрок1"

    assert body["totals"]["Сундук Эпического Монстра"] == 3
    assert body["totals"]["Малый Сундук"] == 1
    assert body["totals"]["grand_total"] == 4


@pytest.mark.asyncio
async def test_summary_empty_collector_returns_empty_lists(db_session):
    user = await _create_user(db_session, "emptysummary0a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K10", clan="EmptyClan",
            items=[{"chest_type": "Малый Сундук", "sender": "Соло",
                    "timestamp": "2026-06-18T12:00:00"}],
        ))
        slug = import_resp.json()["collector_slug"]
        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chest_types"] == ["Малый Сундук"]
    assert body["players"][0]["total"] == 1


@pytest.mark.asyncio
async def test_summary_collector_with_zero_chests_returns_empty_lists(db_session):
    import secrets as _secrets
    user = await _create_user(db_session, "zerochests000a")
    collector = ChestCollector(kingdom="K11", clan="ZeroClan", user_id=user.id,
                               slug=_secrets.token_urlsafe(16))
    db_session.add(collector)
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/summary/{collector.slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chest_types"] == []
    assert body["players"] == []
    assert body["totals"] == {"grand_total": 0}


@pytest.mark.asyncio
async def test_summary_applies_alias_added_after_import_without_reimport(db_session):
    from models import PlayerAlias, ChestTypeAlias

    user = await _create_user(db_session, "aliasafterimp0a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K12", clan="AliasClan",
            items=[
                {"chest_type": "Эпический отр", "sender": "Machet",
                 "timestamp": "2026-06-18T13:00:00"},
                {"chest_type": "Эпический отр", "sender": "Machet",
                 "timestamp": "2026-06-18T13:05:00"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id

        # Alias added AFTER the import already happened — no re-import follows.
        db_session.add(PlayerAlias(collector_id=collector_id, raw_name="Machet",
                                    canonical_name="MACHETE"))
        db_session.add(ChestTypeAlias(collector_id=collector_id, raw_type="Эпический отр",
                                      canonical_type="Эпический отряд"))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chest_types"] == ["Эпический отряд"]
    assert body["players"][0]["name"] == "MACHETE"
    assert body["players"][0]["counts"]["Эпический отряд"] == 2


@pytest.mark.asyncio
async def test_summary_collapses_many_raw_senders_aliased_to_same_canonical(db_session):
    """Two different raw sender names aliased to one canonical name must
    collapse into a single player row in the summary, with combined total —
    this is the entire reason GROUP BY runs on the coalesced expression
    rather than on the raw sender column."""
    from models import PlayerAlias

    user = await _create_user(db_session, "manytoone0000a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K13", clan="ManyToOneClan",
            items=[
                {"chest_type": "Сундук Эпического Монстра", "sender": "Araiina",
                 "timestamp": "2026-06-18T14:00:00"},
                {"chest_type": "Сундук Эпического Монстра", "sender": "Araiina",
                 "timestamp": "2026-06-18T14:05:00"},
                {"chest_type": "Сундук Эпического Монстра", "sender": "Arahna_OCR_typo",
                 "timestamp": "2026-06-18T14:10:00"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id

        # Two different raw sender names, both aliased to the same canonical name.
        db_session.add(PlayerAlias(collector_id=collector_id, raw_name="Araiina",
                                    canonical_name="Арахна"))
        db_session.add(PlayerAlias(collector_id=collector_id, raw_name="Arahna_OCR_typo",
                                    canonical_name="Арахна"))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()

    arahna_entries = [p for p in body["players"] if p["name"] == "Арахна"]
    assert len(arahna_entries) == 1, (
        f"expected exactly one collapsed 'Арахна' entry, got {arahna_entries}"
    )
    assert arahna_entries[0]["total"] == 3


@pytest.mark.asyncio
async def test_summary_no_pattern_has_no_points_key(db_session):
    user = await _create_user(db_session, "nopattern0000a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K20", clan="NoPatternClan",
            items=[{"chest_type": "Anything", "sender": "P1",
                    "timestamp": "2026-06-18T14:00:00"}],
        ))
        slug = import_resp.json()["collector_slug"]
        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert "points" not in body["players"][0]
    assert "total_points" not in body["totals"]


@pytest.mark.asyncio
async def test_summary_with_pattern_excludes_offcatalog_chests_entirely(db_session):
    from models import ChestTypeCatalog

    user = await _create_user(db_session, "withpattern00a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K21", clan="PatternClan",
            items=[
                {"chest_type": "Epic Fenrir", "sender": "P1",
                 "timestamp": "2026-06-18T14:00:00"},
                {"chest_type": "Epic Fenrir", "sender": "P1",
                 "timestamp": "2026-06-18T14:05:00"},
                {"chest_type": "Off Catalog Chest", "sender": "P1",
                 "timestamp": "2026-06-18T14:10:00"},
            ],
        ))
        slug = import_resp.json()["collector_slug"]
        collector = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one()
        collector.pattern = "T9"
        db_session.add(ChestTypeCatalog(canonical_type="Epic Fenrir", pattern="T9",
                                        points=5))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chest_types"] == ["Epic Fenrir"]
    assert body["players"][0]["name"] == "P1"
    assert body["players"][0]["total"] == 2
    assert body["players"][0]["points"] == 10
    assert body["totals"]["grand_total"] == 2
    assert body["totals"]["total_points"] == 10


@pytest.mark.asyncio
async def test_summary_player_with_only_offcatalog_chests_is_excluded(db_session):
    from models import ChestTypeCatalog

    user = await _create_user(db_session, "onlyoffcat000a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K22", clan="OffCatClan",
            items=[
                {"chest_type": "Epic Fenrir", "sender": "Scored",
                 "timestamp": "2026-06-18T15:00:00"},
                {"chest_type": "Off Catalog Chest", "sender": "Excluded",
                 "timestamp": "2026-06-18T15:05:00"},
            ],
        ))
        slug = import_resp.json()["collector_slug"]
        collector = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one()
        collector.pattern = "T9"
        db_session.add(ChestTypeCatalog(canonical_type="Epic Fenrir", pattern="T9",
                                        points=5))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    body = resp.json()
    names = {p["name"] for p in body["players"]}
    assert names == {"Scored"}


@pytest.mark.asyncio
async def test_summary_uses_localization_when_present(db_session):
    from models import ChestLocalization, ChestTypeCatalog

    user = await _create_user(db_session, "withlocaliz00a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K23", clan="LocalizedClan",
            items=[{"chest_type": "Epic Fenrir", "sender": "P1",
                    "timestamp": "2026-06-18T16:00:00"}],
        ))
        slug = import_resp.json()["collector_slug"]
        collector = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one()
        collector.pattern = "T9"
        collector.language = "ru"
        db_session.add(ChestTypeCatalog(canonical_type="Epic Fenrir", pattern="T9",
                                        points=5))
        db_session.add(ChestLocalization(canonical_type="Epic Fenrir", language="ru",
                                         display_text="Эпический Фенрир"))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    body = resp.json()
    assert body["chest_types"] == ["Эпический Фенрир"]
    assert "Эпический Фенрир" in body["players"][0]["counts"]


@pytest.mark.asyncio
async def test_summary_falls_back_to_english_when_no_localization(db_session):
    from models import ChestTypeCatalog

    user = await _create_user(db_session, "nolocaliz0000a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K24", clan="NoLocalizationClan",
            items=[{"chest_type": "Epic Fenrir", "sender": "P1",
                    "timestamp": "2026-06-18T17:00:00"}],
        ))
        slug = import_resp.json()["collector_slug"]
        collector = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one()
        collector.pattern = "T9"
        collector.language = "ru"
        db_session.add(ChestTypeCatalog(canonical_type="Epic Fenrir", pattern="T9",
                                        points=5))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    body = resp.json()
    assert body["chest_types"] == ["Epic Fenrir"]
