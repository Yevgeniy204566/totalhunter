"""
Руководители ростера сундуков (владелец 2026-09-27).

Правило владельца: ростер наполняет ТОЛЬКО хозяин (чей бот собирает сундуки) — хозяин всегда
один. Хозяин приглашает руководителя кодом; руководитель помогает вести ЭТОТ ростер на сайте
(участники, звания/войска/Герой, очки и учёт сундуков, пресеты, Древний, история/CSV), но не
трогает сезон/квоты сезона, досрочное закрытие, удаление ростера, настройки владельца и список
руководителей. Роль постоянная (без срока), пока хозяин не уберёт или руководитель не выйдет.
Сундуки из бота руководителя идут в ЕГО собственный ростер, как и раньше.
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

from main import app
from models import ChestCollector, ChestManager, User
from web_routes import create_jwt

BASE = "/web/dashboard/chests"


async def _user(db, email):
    u = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6), email=email)
    db.add(u)
    await db.flush()
    return u, {"Authorization": f"Bearer {create_jwt(u.id, email)}"}


async def _collector(db, user_id, slug, kingdom="229", clan="Feniks"):
    c = ChestCollector(kingdom=kingdom, clan=clan, user_id=user_id, slug=slug)
    db.add(c)
    await db.flush()
    return c


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _make_manager(client, owner_h, manager_h, slug, nick="Vasya"):
    code = (await client.post(f"{BASE}/{slug}/managers/invite", headers=owner_h)).json()["code"]
    r = await client.post(f"{BASE}/managers/join", json={"code": code, "game_nick": nick},
                          headers=manager_h)
    assert r.status_code == 200, r.text
    return r


@pytest.mark.asyncio
async def test_invite_makes_manager_and_owner_stays_the_only_owner(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    vasya, vasya_h = await _user(db_session, "vasya@x.com")
    col = await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()

    async with _client() as c:
        r = await _make_manager(c, owner_h, vasya_h, "roster-1")
        assert r.json()["slug"] == "roster-1"

    await db_session.refresh(col)
    assert col.user_id == owner.id                     # хозяин не сменился
    assert col.management_token is None                # код одноразовый
    rows = (await db_session.execute(select(ChestManager))).scalars().all()
    assert [(m.collector_id, m.user_id) for m in rows] == [(col.id, vasya.id)]


@pytest.mark.asyncio
async def test_code_is_one_time_and_owner_cannot_join_own_roster(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    vasya, vasya_h = await _user(db_session, "vasya@x.com")
    petya, petya_h = await _user(db_session, "petya@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()

    async with _client() as c:
        code = (await c.post(f"{BASE}/roster-1/managers/invite", headers=owner_h)).json()["code"]
        assert (await c.post(f"{BASE}/managers/join", json={"code": code},
                             headers=owner_h)).status_code == 400
        assert (await c.post(f"{BASE}/managers/join", json={"code": code, "game_nick": "Vasya"},
                             headers=vasya_h)).status_code == 200
        assert (await c.post(f"{BASE}/managers/join", json={"code": code, "game_nick": "Petya"},
                             headers=petya_h)).status_code == 404
        assert (await c.post(f"{BASE}/managers/join", json={"code": "nope"},
                             headers=petya_h)).status_code == 404


@pytest.mark.asyncio
async def test_manager_sees_roster_in_dashboard_with_role(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    vasya, vasya_h = await _user(db_session, "vasya@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await _collector(db_session, vasya.id, "vasya-own", clan="Vasya")
    await db_session.commit()

    async with _client() as c:
        await _make_manager(c, owner_h, vasya_h, "roster-1")
        mine = {x["slug"]: x for x in (await c.get(BASE, headers=vasya_h)).json()["collectors"]}
        owners = {x["slug"]: x for x in (await c.get(BASE, headers=owner_h)).json()["collectors"]}

    assert mine["vasya-own"]["role"] == "owner"
    assert mine["roster-1"]["role"] == "manager"
    assert mine["roster-1"]["owner_label"] is None      # у хозяина ещё нет ника
    assert "managers" not in mine["roster-1"] or mine["roster-1"]["managers"] is None
    assert owners["roster-1"]["role"] == "owner"
    assert [(m["user_id"], m["nick"]) for m in owners["roster-1"]["managers"]] == [(vasya.id, "Vasya")]


@pytest.mark.asyncio
async def test_manager_can_edit_players_points_language_and_read_history(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    vasya, vasya_h = await _user(db_session, "vasya@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()

    async with _client() as c:
        await _make_manager(c, owner_h, vasya_h, "roster-1")
        allowed = [
            c.post(f"{BASE}/rows", json={"collector_slug": "roster-1", "rows": []}, headers=vasya_h),
            c.post(f"{BASE}/player-aliases", json={"collector_slug": "roster-1", "rows": []},
                   headers=vasya_h),
            c.post(f"{BASE}/player-profiles", json={"collector_slug": "roster-1", "rows": []},
                   headers=vasya_h),
            c.patch(f"{BASE}/roster-1/language", json={"language": "en"}, headers=vasya_h),
            c.get(f"{BASE}/roster-1/stats.csv", headers=vasya_h),
            c.get(f"{BASE}/roster-1/history", headers=vasya_h),
        ]
        for req in allowed:
            r = await req
            assert r.status_code == 200, (r.request.url, r.status_code, r.text)


@pytest.mark.asyncio
async def test_manager_cannot_touch_owner_only_actions(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    vasya, vasya_h = await _user(db_session, "vasya@x.com")
    petya, _ = await _user(db_session, "petya@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()

    async with _client() as c:
        await _make_manager(c, owner_h, vasya_h, "roster-1")
        forbidden = [
            c.patch(f"{BASE}/roster-1/season", json={"target_points": 100}, headers=vasya_h),
            c.post(f"{BASE}/roster-1/close-season", headers=vasya_h),
            c.patch(f"{BASE}/roster-1/leader", json={"leader_canonical_name": "X"}, headers=vasya_h),
            c.delete(f"{BASE}/roster-1", headers=vasya_h),
            c.post(f"{BASE}/roster-1/managers/invite", headers=vasya_h),
            c.delete(f"{BASE}/roster-1/managers/{petya.id}", headers=vasya_h),
        ]
        for req in forbidden:
            r = await req
            assert r.status_code == 403, (r.request.url, r.status_code, r.text)

    assert (await db_session.execute(
        select(ChestCollector).where(ChestCollector.slug == "roster-1"))).scalar_one().user_id == owner.id


@pytest.mark.asyncio
async def test_stranger_has_no_access(db_session):
    owner, _ = await _user(db_session, "owner@x.com")
    _, stranger_h = await _user(db_session, "stranger@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()
    async with _client() as c:
        r = await c.post(f"{BASE}/rows", json={"collector_slug": "roster-1", "rows": []},
                         headers=stranger_h)
        assert r.status_code == 403
        slugs = [x["slug"] for x in (await c.get(BASE, headers=stranger_h)).json()["collectors"]]
        assert "roster-1" not in slugs


@pytest.mark.asyncio
async def test_owner_removes_manager_and_access_is_gone(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    vasya, vasya_h = await _user(db_session, "vasya@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()

    async with _client() as c:
        await _make_manager(c, owner_h, vasya_h, "roster-1")
        assert (await c.delete(f"{BASE}/roster-1/managers/{vasya.id}",
                               headers=owner_h)).status_code == 200
        r = await c.post(f"{BASE}/rows", json={"collector_slug": "roster-1", "rows": []},
                         headers=vasya_h)
        assert r.status_code == 403
        slugs = [x["slug"] for x in (await c.get(BASE, headers=vasya_h)).json()["collectors"]]
        assert "roster-1" not in slugs


@pytest.mark.asyncio
async def test_manager_can_leave(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    vasya, vasya_h = await _user(db_session, "vasya@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()

    async with _client() as c:
        await _make_manager(c, owner_h, vasya_h, "roster-1")
        assert (await c.post(f"{BASE}/roster-1/managers/leave", headers=vasya_h)).status_code == 200
        owners = {x["slug"]: x for x in (await c.get(BASE, headers=owner_h)).json()["collectors"]}
    assert owners["roster-1"]["managers"] == []


@pytest.mark.asyncio
async def test_deleting_roster_removes_its_managers(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    vasya, vasya_h = await _user(db_session, "vasya@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()

    async with _client() as c:
        await _make_manager(c, owner_h, vasya_h, "roster-1")
        assert (await c.delete(f"{BASE}/roster-1", headers=owner_h)).status_code == 200
    assert (await db_session.execute(select(ChestManager))).scalars().all() == []


@pytest.mark.asyncio
async def test_old_transfer_endpoints_are_gone(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()
    async with _client() as c:
        r1 = await c.post(f"{BASE}/management-token", json={"collector_slug": "roster-1"},
                          headers=owner_h)
        r2 = await c.post(f"{BASE}/claim", json={"code": "x"}, headers=owner_h)
    assert r1.status_code in (404, 405) and r2.status_code in (404, 405)


# ── Древний ──────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_manager_works_with_ancients_but_not_owner_only_parts(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    vasya, vasya_h = await _user(db_session, "vasya@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()
    A = "/web/dashboard/ancients"

    async with _client() as c:
        await _make_manager(c, owner_h, vasya_h, "roster-1")
        slugs = [x["slug"] for x in (await c.get(A, headers=vasya_h)).json()["collectors"]]
        assert "roster-1" in slugs
        r = await c.post(f"{A}/roster-1/roster/manual", json={"player_name": "Bob", "troop_level": "G9 S9 M9"}, headers=vasya_h)
        assert r.status_code == 200, r.text
        r = await c.post(f"{A}/roster-1/calculate",
                         json={"strategy": "B", "summon_levels": [81], "amplification_coef": 1.0, "clan_preset": "T9"},
                         headers=vasya_h)
        assert r.status_code == 200, r.text
        for req in (c.patch(f"{A}/roster-1/ancient-visibility", json={"hidden": True}, headers=vasya_h),
                    c.patch(f"{A}/roster-1/quota-thresholds", json={"light_pct": 10, "medium_pct": 20, "critical_pct": 30}, headers=vasya_h),
                    c.delete(f"{A}/roster-1/roster/ocr-import", headers=vasya_h),
                    c.post(f"{A}/roster-1/invite", headers=vasya_h)):
            r = await req
            assert r.status_code == 403, (r.request.url, r.status_code, r.text)



# ── Игровые ники вместо почт (владелец 2026-09-27: хозяин хочет быть анонимом) ──────

@pytest.mark.asyncio
async def test_nobody_sees_other_peoples_email_only_nicks(db_session):
    owner, owner_h = await _user(db_session, "owner.secret@x.com")
    owner.game_nick = "Hozyain"
    vasya, vasya_h = await _user(db_session, "vasya.secret@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()

    async with _client() as c:
        await _make_manager(c, owner_h, vasya_h, "roster-1", nick="VasyaNick")
        as_manager = (await c.get(BASE, headers=vasya_h)).text
        as_owner = (await c.get(BASE, headers=owner_h)).text
        mine = {x["slug"]: x for x in (await c.get(BASE, headers=vasya_h)).json()["collectors"]}

    assert "owner.secret" not in as_manager and "@x.com" not in as_manager.replace("vasya.secret@x.com", "")
    assert "vasya.secret" not in as_owner
    assert mine["roster-1"]["owner_label"] == "Hozyain"
    assert "VasyaNick" in as_owner


@pytest.mark.asyncio
async def test_join_requires_game_nick_when_account_has_none(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    vasya, vasya_h = await _user(db_session, "vasya@x.com")
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()

    async with _client() as c:
        code = (await c.post(f"{BASE}/roster-1/managers/invite", headers=owner_h)).json()["code"]
        r = await c.post(f"{BASE}/managers/join", json={"code": code}, headers=vasya_h)
        assert r.status_code == 400 and r.json()["detail"] == "nick_required"
        r = await c.post(f"{BASE}/managers/join", json={"code": code, "game_nick": "  Vasya  "},
                         headers=vasya_h)
        assert r.status_code == 200
    await db_session.refresh(vasya)
    assert vasya.game_nick == "Vasya"


@pytest.mark.asyncio
async def test_join_without_nick_ok_when_account_already_has_one(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com")
    vasya, vasya_h = await _user(db_session, "vasya@x.com")
    vasya.game_nick = "Vasya"
    await _collector(db_session, owner.id, "roster-1")
    await db_session.commit()
    async with _client() as c:
        code = (await c.post(f"{BASE}/roster-1/managers/invite", headers=owner_h)).json()["code"]
        assert (await c.post(f"{BASE}/managers/join", json={"code": code},
                             headers=vasya_h)).status_code == 200


@pytest.mark.asyncio
async def test_game_nick_saved_in_profile_and_returned_by_me(db_session):
    _, h = await _user(db_session, "someone@x.com")
    await db_session.commit()
    async with _client() as c:
        assert (await c.put("/web/game-nick", json={"game_nick": "  Dragon  "}, headers=h)).status_code == 200
        assert (await c.get("/web/me", headers=h)).json()["game_nick"] == "Dragon"
        assert (await c.put("/web/game-nick", json={"game_nick": "x" * 33}, headers=h)).status_code == 422
        assert (await c.put("/web/game-nick", json={"game_nick": ""}, headers=h)).status_code == 200
        assert (await c.get("/web/me", headers=h)).json()["game_nick"] is None
        mine = (await c.get(BASE, headers=h)).json()
        assert "my_nick" in mine
