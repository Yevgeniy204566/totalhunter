"""Tests for chests.py — tenant isolation, alias dictionary, idempotent import."""
import os
import sys
from datetime import datetime

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


@pytest.mark.asyncio
async def test_import_clan_name_case_difference_reuses_collector(db_session):
    user = await _create_user(db_session, "casediffuser0a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, clan="BERS", items=[{"chest_type": "A", "sender": "S1",
                                            "timestamp": "2026-06-18T10:00:00"}]))
        await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, clan="Bers", items=[{"chest_type": "B", "sender": "S2",
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
                                  catalog_id="Эпическая Арахна"))
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
    from models import ChestConfiguration

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

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id
        db_session.add(ChestConfiguration(collector_id=collector_id,
                                          catalog_id="Сундук Эпического Монстра",
                                          points=0, is_in_pattern=True))
        db_session.add(ChestConfiguration(collector_id=collector_id,
                                          catalog_id="Малый Сундук",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

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
async def test_summary_chest_types_sorted_by_total_count_descending(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "sortbytotal0a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K12", clan="SortClan",
            items=[
                {"chest_type": "Beta", "sender": "P1", "timestamp": "2026-06-18T13:00:00"},
                {"chest_type": "Zulu", "sender": "P1", "timestamp": "2026-06-18T13:01:00"},
                {"chest_type": "Zulu", "sender": "P1", "timestamp": "2026-06-18T13:02:00"},
                {"chest_type": "Zulu", "sender": "P1", "timestamp": "2026-06-18T13:03:00"},
                {"chest_type": "Alpha", "sender": "P1", "timestamp": "2026-06-18T13:04:00"},
                {"chest_type": "Alpha", "sender": "P1", "timestamp": "2026-06-18T13:05:00"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id
        for catalog_id in ("Zulu", "Alpha", "Beta"):
            db_session.add(ChestConfiguration(collector_id=collector_id, catalog_id=catalog_id,
                                              points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    # Zulu=3, Alpha=2, Beta=1 -> descending order, NOT alphabetical (Alpha, Beta, Zulu)
    assert body["chest_types"] == ["Zulu", "Alpha", "Beta"]


@pytest.mark.asyncio
async def test_summary_empty_collector_returns_empty_lists(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "emptysummary0a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K10", clan="EmptyClan",
            items=[{"chest_type": "Малый Сундук", "sender": "Соло",
                    "timestamp": "2026-06-18T12:00:00"}],
        ))
        slug = import_resp.json()["collector_slug"]

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id
        db_session.add(ChestConfiguration(collector_id=collector_id,
                                          catalog_id="Малый Сундук",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

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
    assert body["totals"] == {"grand_total": 0, "total_points": 0}


@pytest.mark.asyncio
async def test_summary_applies_alias_added_after_import_without_reimport(db_session):
    from models import PlayerAlias, ChestTypeAlias, ChestConfiguration

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
                                      catalog_id="Эпический отряд"))
        db_session.add(ChestConfiguration(collector_id=collector_id,
                                          catalog_id="Эпический отряд",
                                          points=0, is_in_pattern=True))
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
    from models import PlayerAlias, ChestConfiguration

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
        db_session.add(ChestConfiguration(collector_id=collector_id,
                                          catalog_id="Сундук Эпического Монстра",
                                          points=0, is_in_pattern=True))
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
async def test_summary_with_pattern_excludes_offcatalog_chests_entirely(db_session):
    from models import ChestConfiguration

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
        db_session.add(ChestConfiguration(collector_id=collector.id,
                                          catalog_id="Epic Fenrir",
                                          points=5, is_in_pattern=True))
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
    from models import ChestConfiguration

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
        db_session.add(ChestConfiguration(collector_id=collector.id,
                                          catalog_id="Epic Fenrir",
                                          points=5, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    body = resp.json()
    names = {p["name"] for p in body["players"]}
    assert names == {"Scored"}


@pytest.mark.asyncio
async def test_summary_uses_localization_when_present(db_session):
    from models import ChestLocalization, ChestConfiguration

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
        collector.language = "ru"
        db_session.add(ChestConfiguration(collector_id=collector.id,
                                          catalog_id="Epic Fenrir",
                                          points=5, is_in_pattern=True))
        db_session.add(ChestLocalization(canonical_type="Epic Fenrir", language="ru",
                                         display_text="Эпический Фенрир"))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    body = resp.json()
    assert body["chest_types"] == ["Эпический Фенрир"]
    assert "Эпический Фенрир" in body["players"][0]["counts"]


@pytest.mark.asyncio
async def test_summary_falls_back_to_english_when_no_localization(db_session):
    from models import ChestConfiguration

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
        collector.language = "ru"
        db_session.add(ChestConfiguration(collector_id=collector.id,
                                          catalog_id="Epic Fenrir",
                                          points=5, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    body = resp.json()
    assert body["chest_types"] == ["Epic Fenrir"]


@pytest.mark.asyncio
async def test_summary_uses_chest_configuration_points_and_custom_name(db_session):
    from models import ChestConfiguration, ChestTypeAlias, Chest

    user = await _create_user(db_session, hwid="hwid-cfg")
    collector = ChestCollector(kingdom="K1", clan="ClanCfg", user_id=user.id,
                               slug=secrets.token_urlsafe(16), language="ru")
    db_session.add(collector)
    await db_session.flush()

    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="RawX",
                                  catalog_id="Epic Arachne"))
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Epic Arachne",
                                      custom_name="Толстяк", points=40, is_in_pattern=True))
    db_session.add(Chest(collector_id=collector.id, sender_raw="P1", sender_canonical="P1",
                         chest_type_raw="RawX", chest_type_canonical="RawX",
                         collected_at=datetime.fromisoformat("2026-06-20T10:00:00")))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/summary/{collector.slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chest_types"] == ["Толстяк"]
    assert body["totals"] == {"Толстяк": 1, "grand_total": 1, "total_points": 40}
    assert body["players"][0] == {"name": "P1", "counts": {"Толстяк": 1}, "total": 1,
                                  "points": 40, "quota_chests": 0}


@pytest.mark.asyncio
async def test_summary_excludes_chest_not_in_pattern(db_session):
    from models import ChestConfiguration, ChestTypeAlias, Chest

    user = await _create_user(db_session, hwid="hwid-cfg2")
    collector = ChestCollector(kingdom="K1", clan="ClanCfg2", user_id=user.id,
                               slug=secrets.token_urlsafe(16))
    db_session.add(collector)
    await db_session.flush()

    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="RawY",
                                  catalog_id="Common Crypt 5"))
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Common Crypt 5",
                                      points=5, is_in_pattern=False))
    db_session.add(Chest(collector_id=collector.id, sender_raw="P1", sender_canonical="P1",
                         chest_type_raw="RawY", chest_type_canonical="RawY",
                         collected_at=datetime.fromisoformat("2026-06-20T10:00:00")))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/summary/{collector.slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["chest_types"] == []
    assert body["totals"] == {"grand_total": 0, "total_points": 0}
    assert body["players"] == []


@pytest.mark.asyncio
async def test_summary_no_configuration_returns_empty(db_session):
    from models import Chest

    user = await _create_user(db_session, hwid="hwid-cfg3")
    collector = ChestCollector(kingdom="K1", clan="ClanCfg3", user_id=user.id,
                               slug=secrets.token_urlsafe(16))
    db_session.add(collector)
    await db_session.flush()
    db_session.add(Chest(collector_id=collector.id, sender_raw="P1", sender_canonical="P1",
                         chest_type_raw="Unconfigured", chest_type_canonical="Unconfigured",
                         collected_at=datetime.fromisoformat("2026-06-20T10:00:00")))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/summary/{collector.slug}")
    assert resp.status_code == 200
    assert resp.json()["totals"] == {"grand_total": 0, "total_points": 0}


@pytest.mark.asyncio
async def test_summary_includes_updated_at_as_latest_chest_timestamp(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "updatedattest")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K13", clan="UpdatedAtClan",
            items=[
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T09:00:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T14:30:00"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id
        db_session.add(ChestConfiguration(collector_id=collector_id, catalog_id="Common",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    assert resp.json()["updated_at"] == "2026-06-18T14:30:00"


@pytest.mark.asyncio
async def test_summary_updated_at_is_none_for_collector_with_zero_chests(db_session):
    import secrets as _secrets
    user = await _create_user(db_session, "noupdatedat0a")
    collector = ChestCollector(kingdom="K14", clan="NoChestsClan", user_id=user.id,
                               slug=_secrets.token_urlsafe(16))
    db_session.add(collector)
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/summary/{collector.slug}")
    assert resp.status_code == 200
    assert resp.json()["updated_at"] is None


@pytest.mark.asyncio
async def test_summary_filters_chests_by_period_inclusive_both_ends(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "perioduser000a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K15", clan="PeriodClan",
            items=[
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-20T23:59:59"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-21T00:00:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-30T12:00:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-07-05T00:00:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-07-05T00:00:01"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one()
        collector.period_start = datetime.fromisoformat("2026-06-21T00:00:00")
        collector.period_end = datetime.fromisoformat("2026-07-05T00:00:00")
        db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Common",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    # In range (inclusive both ends): 06-21T00:00:00, 06-30T12:00:00, 07-05T00:00:00 = 3
    # Excluded: 06-20T23:59:59 (before start), 07-05T00:00:01 (after end)
    assert body["players"][0]["total"] == 3
    assert body["updated_at"] == "2026-07-05T00:00:00"


@pytest.mark.asyncio
async def test_summary_unconfigured_period_applies_no_filter(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "noperioduser0a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K16", clan="NoPeriodClan",
            items=[
                {"chest_type": "Common", "sender": "P1", "timestamp": "2020-01-01T00:00:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2030-12-31T23:59:59"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one()
        db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Common",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["players"][0]["total"] == 2
    assert body["updated_at"] == "2030-12-31T23:59:59"


@pytest.mark.asyncio
async def test_summary_quota_chests_counts_only_quota_marked_types(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "quotauser0000a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K17", clan="QuotaClan",
            items=[
                {"chest_type": "EpicCrypt", "sender": "P1", "timestamp": "2026-06-18T10:00:00"},
                {"chest_type": "EpicCrypt", "sender": "P1", "timestamp": "2026-06-18T10:01:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T10:02:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T10:03:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T10:04:00"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id
        db_session.add(ChestConfiguration(collector_id=collector_id, catalog_id="EpicCrypt",
                                          points=80, is_in_pattern=True,
                                          counts_toward_quota=True))
        db_session.add(ChestConfiguration(collector_id=collector_id, catalog_id="Common",
                                          points=5, is_in_pattern=True,
                                          counts_toward_quota=False))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    player = resp.json()["players"][0]
    assert player["quota_chests"] == 2
    assert player["total"] == 5
    assert player["points"] == 2 * 80 + 3 * 5


@pytest.mark.asyncio
async def test_summary_includes_season_metadata_when_configured(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "seasonmetauser")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K18", clan="SeasonMetaClan",
            items=[{"chest_type": "Common", "sender": "P1",
                    "timestamp": "2026-06-25T00:00:00"}],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one()
        collector.period_start = datetime.fromisoformat("2026-06-21T00:00:00")
        collector.period_end = datetime.fromisoformat("2026-07-05T00:00:00")
        collector.timezone_offset_minutes = 180
        collector.target_points = 5000
        collector.target_chests = 50
        db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Common",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["period_start"] == "2026-06-21T00:00:00"
    assert body["period_end"] == "2026-07-05T00:00:00"
    assert body["timezone_offset_minutes"] == 180
    assert body["targets"] == {"points": 5000, "chests": 50}


@pytest.mark.asyncio
async def test_summary_season_metadata_is_null_when_unconfigured(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "noseasonmeta0a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K19", clan="NoSeasonMetaClan",
            items=[{"chest_type": "Common", "sender": "P1",
                    "timestamp": "2026-06-25T00:00:00"}],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id
        db_session.add(ChestConfiguration(collector_id=collector_id, catalog_id="Common",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["period_start"] is None
    assert body["period_end"] is None
    assert body["timezone_offset_minutes"] is None
    assert body["targets"] == {"points": None, "chests": None}


@pytest.mark.asyncio
async def test_history_list_unknown_slug_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/chests/history/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_history_list_returns_archived_seasons(db_session):
    from datetime import datetime, timedelta
    from models import ChestCollector, ChestSeasonHistory
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=1, slug="hist-public-1")
    db_session.add(collector)
    await db_session.flush()
    db_session.add(ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow(),
        summary_json={"totals": {"total_points": 555}, "players": []},
    ))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/history/{collector.slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["seasons"]) == 1
    assert body["seasons"][0]["total_points"] == 555


@pytest.mark.asyncio
async def test_history_detail_unknown_season_returns_404(db_session):
    from models import ChestCollector
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=1, slug="hist-public-2")
    db_session.add(collector)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/history/{collector.slug}/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_history_detail_returns_full_summary(db_session):
    from datetime import datetime, timedelta
    from models import ChestCollector, ChestSeasonHistory
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=1, slug="hist-public-3")
    db_session.add(collector)
    await db_session.flush()
    row = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow(),
        target_points_snapshot=100,
        summary_json={"totals": {"total_points": 555}, "players": [], "chest_types": []},
    )
    db_session.add(row)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/history/{collector.slug}/{row.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["targets"]["points"] == 100
    assert body["totals"]["total_points"] == 555
