"""Игроки без сундуков 7 дней скрываются с публичной страницы и из списка «Игроки» кабинета
(владелец 2026-11-01). Профиль и алиас скрытого не стираются; вернулся сундук — имя вернулось."""
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import Chest, ChestCollector, ChestConfiguration, PlayerAlias, PlayerProfile, User
from web_routes import create_jwt


async def _setup(db):
    user = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6),
                email=f"{secrets.token_hex(4)}@example.com")
    db.add(user)
    await db.flush()
    c = ChestCollector(kingdom="K1", clan="ClanA", user_id=user.id, slug=secrets.token_urlsafe(16))
    db.add(c)
    await db.flush()
    db.add(ChestConfiguration(collector_id=c.id, catalog_id="Epic Arachne", points=40, is_in_pattern=True))
    return user, create_jwt(user.id, user.email), c


def _chest(c, name, days_ago):
    return Chest(collector_id=c.id, chest_type_raw="Epic Arachne", chest_type_canonical="Epic Arachne",
                 sender_raw=name, sender_canonical=name,
                 collected_at=datetime.now(timezone.utc) - timedelta(days=days_ago))


def _names(resp):
    return {p["name"] for p in resp.json()["players"]}


@pytest.mark.asyncio
async def test_public_summary_hides_players_without_chests_for_7_days(db_session):
    _, _, c = await _setup(db_session)
    db_session.add_all([_chest(c, "Fresh", 1), _chest(c, "Old", 9), _chest(c, "Old", 20)])
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/api/v1/chests/summary/{c.slug}")
    assert r.status_code == 200
    assert _names(r) == {"Fresh"}


@pytest.mark.asyncio
async def test_player_returns_when_new_chest_arrives(db_session):
    _, _, c = await _setup(db_session)
    db_session.add_all([_chest(c, "Back", 30), _chest(c, "Back", 0.1)])
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/api/v1/chests/summary/{c.slug}")
    assert _names(r) == {"Back"}


@pytest.mark.asyncio
async def test_stale_alias_groups_by_canonical_name(db_session):
    # два написания одного игрока: свежий сундук у одного из них оставляет игрока видимым
    _, _, c = await _setup(db_session)
    db_session.add_all([
        PlayerAlias(collector_id=c.id, raw_name="Arahna_ocr1", canonical_name="Arahna"),
        PlayerAlias(collector_id=c.id, raw_name="Arahna_ocr2", canonical_name="Arahna"),
        _chest(c, "Arahna_ocr1", 30), _chest(c, "Arahna_ocr2", 2),
    ])
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/api/v1/chests/summary/{c.slug}")
    assert _names(r) == {"Arahna"}


@pytest.mark.asyncio
async def test_cabinet_players_list_hides_stale_but_saving_keeps_their_profile(db_session):
    user, token, c = await _setup(db_session)
    db_session.add_all([
        _chest(c, "Fresh", 1), _chest(c, "Old", 10),
        PlayerAlias(collector_id=c.id, raw_name="Old", canonical_name="Old"),
        PlayerProfile(collector_id=c.id, canonical_name="Old", rank="Офицер", hero_level=350),
    ])
    await db_session.commit()
    auth = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get("/web/dashboard/chests", headers=auth)
        shown = {x["canonical_name"] for x in r.json()["collectors"][0]["player_alias_rows"]}
        assert shown == {"Fresh"}
        # кабинет сохраняет списки без скрытого — его алиас и профиль обязаны уцелеть
        await client.post("/web/dashboard/chests/player-aliases", headers=auth,
                          json={"collector_slug": c.slug,
                                "rows": [{"raw_name": "Fresh", "canonical_name": "Fresh"}]})
        await client.post("/web/dashboard/chests/player-profiles", headers=auth,
                          json={"collector_slug": c.slug, "rows": [{"canonical_name": "Fresh"}]})
    aliases = {a.canonical_name for a in (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == c.id))).scalars().all()}
    profiles = {p.canonical_name: p for p in (await db_session.execute(
        select(PlayerProfile).where(PlayerProfile.collector_id == c.id))).scalars().all()}
    assert aliases == {"Old", "Fresh"}
    assert profiles["Old"].rank == "Офицер" and profiles["Old"].hero_level == 350


@pytest.mark.asyncio
async def test_rename_to_name_that_is_only_in_dictionary_is_saved(db_session):
    # Живой случай 2026-11-01: «Мест Two» → «Megin Two». Правильное имя уже было в словаре
    # (чужой алиас без сундуков) и считалось скрытым, а сохранение молча выкидывало строку.
    user, token, c = await _setup(db_session)
    db_session.add_all([
        _chest(c, "Fresh", 1), _chest(c, "Мест Two", 1),
        PlayerAlias(collector_id=c.id, raw_name="Megin Tvvo", canonical_name="Megin Two"),
        PlayerProfile(collector_id=c.id, canonical_name="Megin Two", rank="Офицер"),
    ])
    await db_session.commit()
    auth = {"Authorization": f"Bearer {token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.post("/web/dashboard/chests/player-aliases", headers=auth,
                              json={"collector_slug": c.slug, "rows": [
                                  {"raw_name": "Fresh", "canonical_name": "Fresh"},
                                  {"raw_name": "Мест Two", "canonical_name": "Megin Two"}]})
        assert r.status_code == 200
        r = await client.post("/web/dashboard/chests/player-profiles", headers=auth,
                              json={"collector_slug": c.slug, "rows": [
                                  {"canonical_name": "Fresh"},
                                  {"canonical_name": "Megin Two", "rank": "Лидер"}]})
        assert r.status_code == 200
    by_raw = {a.raw_name: a.canonical_name for a in (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == c.id))).scalars().all()}
    assert by_raw["Мест Two"] == "Megin Two"
    prof = (await db_session.execute(select(PlayerProfile).where(
        PlayerProfile.collector_id == c.id, PlayerProfile.canonical_name == "Megin Two"))).scalars().all()
    assert len(prof) == 1 and prof[0].rank == "Лидер"


@pytest.mark.asyncio
async def test_name_pool_has_alias_and_past_season_names(db_session):
    from models import ChestSeasonHistory
    user, token, c = await _setup(db_session)
    now = datetime.now(timezone.utc)
    db_session.add_all([
        PlayerAlias(collector_id=c.id, raw_name="ККАКЕМ", canonical_name="КRАКЕN"),
        ChestSeasonHistory(collector_id=c.id, period_start=now - timedelta(days=30), period_end=now - timedelta(days=15),
                           summary_json={"players": [{"name": "Megin Two"}, {"name": "Finda"}]}),
    ])
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/web/dashboard/chests/{c.slug}/name-pool",
                             headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert set(r.json()["names"]) == {"КRАКЕN", "Megin Two", "Finda"}


@pytest.mark.asyncio
async def test_no_uploads_for_weeks_table_does_not_go_empty(db_session):
    # бот не заливал давно: все сундуки старые — таблица остаётся полной (отсчёт от последнего сундука клана)
    _, _, c = await _setup(db_session)
    db_session.add_all([_chest(c, "A", 30), _chest(c, "B", 31), _chest(c, "Lag", 45)])
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/api/v1/chests/summary/{c.slug}")
    assert _names(r) == {"A", "B"}   # Lag отстал от последнего сундука клана больше чем на 7 дней


@pytest.mark.asyncio
async def test_player_who_returns_within_season_keeps_all_his_chests(db_session):
    # пропал на 10 дней, потом вернулся: в таблице ВСЕ его сундуки сезона, включая до перерыва
    _, _, c = await _setup(db_session)
    c.period_start = datetime.now(timezone.utc) - timedelta(days=40)
    db_session.add_all([_chest(c, "Back", 30), _chest(c, "Back", 29), _chest(c, "Back", 0.2),
                        _chest(c, "Steady", 0.5)])
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/api/v1/chests/summary/{c.slug}")
    back = next(p for p in r.json()["players"] if p["name"] == "Back")
    assert back["total"] == 3, back


@pytest.mark.asyncio
async def test_player_absent_5_days_still_shown_absent_10_days_hidden_until_return(db_session):
    _, _, c = await _setup(db_session)
    db_session.add_all([_chest(c, "Gap5", 5), _chest(c, "Gap10", 10), _chest(c, "Steady", 0.1)])
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r = await client.get(f"/api/v1/chests/summary/{c.slug}")
    assert _names(r) == {"Gap5", "Steady"}


async def _cabinet_names(client, token):
    r = await client.get("/web/dashboard/chests", headers={"Authorization": f"Bearer {token}"})
    return {x["canonical_name"] for x in r.json()["collectors"][0]["player_alias_rows"]}


@pytest.mark.asyncio
async def test_cabinet_hides_alias_names_with_no_chests_when_clan_has_chests(db_session):
    # имя прошлого сезона: сундуки ушли в историю, алиас остался — в списке кабинета его быть не должно
    _, token, c = await _setup(db_session)
    db_session.add_all([_chest(c, "Fresh", 1),
                        PlayerAlias(collector_id=c.id, raw_name="Gone", canonical_name="Gone")])
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert await _cabinet_names(client, token) == {"Fresh"}


@pytest.mark.asyncio
async def test_new_roster_without_any_chests_is_not_hidden(db_session):
    _, token, c = await _setup(db_session)
    db_session.add(PlayerAlias(collector_id=c.id, raw_name="Manual", canonical_name="Manual"))
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert await _cabinet_names(client, token) == {"Manual"}


@pytest.mark.asyncio
async def test_cabinet_matches_public_table_when_season_started_recently(db_session):
    # сундук игрока за 2 дня до начала сезона: в таблице сезона его нет, значит и в списке кабинета нет
    _, token, c = await _setup(db_session)
    c.period_start = datetime.now(timezone.utc) - timedelta(days=1)
    db_session.add_all([_chest(c, "InSeason", 0.2), _chest(c, "BeforeSeason", 2)])
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        assert await _cabinet_names(client, token) == {"InSeason"}
        pub = await client.get(f"/api/v1/chests/summary/{c.slug}")
    assert _names(pub) == {"InSeason"}
