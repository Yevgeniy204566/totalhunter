"""
Просмотр норм клана без прав правки (владелец 2026-10-28).

Любой вошедший пользователь, у которого в «Профиле» сохранён клан и королевство, видит нормы этого клана
(общие и личные) только на чтение. Имён игроков, ростера, руководителей и токенов в ответе нет.
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import ChestCollector, ChestConfiguration, ChestManager, ChestTypeAlias, User
from web_routes import create_jwt

URL = "/web/dashboard/chests/view"


async def _user(db, email, links=None):
    u = User(hwid=secrets.token_urlsafe(8)[:16], ref_code=secrets.token_urlsafe(6), email=email,
             saved_chest_links=links or [])
    db.add(u)
    await db.flush()
    return u, {"Authorization": f"Bearer {create_jwt(u.id, email)}"}


async def _clan(db, owner_id, slug, kingdom="229", clan="Feniks"):
    c = ChestCollector(kingdom=kingdom, clan=clan, user_id=owner_id, slug=slug,
                       quotas=[{"slot": 1, "name": "Crypts", "target": 50, "mode": "fixed"}],
                       personal_scale={"crypts": True, "emc": False, "norm": 1, "weights": 1, "ranges": []})
    db.add(c)
    await db.flush()
    db.add(ChestTypeAlias(collector_id=c.id, raw_type="Epic Crypt 30", catalog_id="Epic Crypt 30"))
    db.add(ChestConfiguration(collector_id=c.id, catalog_id="Epic Crypt 30", points=90,
                              is_in_pattern=True, quota_slot=1))
    await db.flush()
    return c


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


@pytest.mark.asyncio
async def test_saved_clan_gives_read_only_norms_without_people(db_session):
    owner, _ = await _user(db_session, "owner@x.com")
    await _clan(db_session, owner.id, "roster-1")
    viewer, viewer_h = await _user(db_session, "viewer@x.com", links=[{"kingdom": "229", "clan": "Feniks"}])
    await db_session.commit()

    async with _client() as c:
        r = await c.get(URL, headers=viewer_h)
    assert r.status_code == 200
    cols = r.json()["collectors"]
    assert len(cols) == 1
    col = cols[0]
    assert col["clan"] == "Feniks" and col["kingdom"] == "229"
    assert col["quotas"][0]["target"] == 50
    assert col["personal_scale"]["crypts"] is True
    assert [(x["catalog_id"], x["points"], x["quota_slot"]) for x in col["rows"]] == [("Epic Crypt 30", 90, 1)]
    # никаких людей и служебных данных владельца
    for banned in ("player_alias_rows", "managers", "owner_label", "leader_canonical_name", "hidden_players",
                   "slug", "management_token", "user_id"):
        assert banned not in col, banned
    assert all("raw_type" not in x and "total_ever" not in x for x in col["rows"])


@pytest.mark.asyncio
async def test_no_saved_clan_gives_empty_list(db_session):
    owner, _ = await _user(db_session, "owner@x.com")
    await _clan(db_session, owner.id, "roster-1")
    nobody, nobody_h = await _user(db_session, "nobody@x.com")
    await db_session.commit()

    async with _client() as c:
        r = await c.get(URL, headers=nobody_h)
    assert r.status_code == 200 and r.json() == {"collectors": []}


@pytest.mark.asyncio
async def test_unknown_clan_is_skipped_and_auth_required(db_session):
    stranger, stranger_h = await _user(db_session, "s@x.com", links=[{"kingdom": "1", "clan": "Nope"}])
    await db_session.commit()

    async with _client() as c:
        assert (await c.get(URL, headers=stranger_h)).json() == {"collectors": []}
        assert (await c.get(URL)).status_code in (401, 403)


@pytest.mark.asyncio
async def test_own_and_managed_clans_are_not_duplicated_in_view(db_session):
    owner, owner_h = await _user(db_session, "owner@x.com", links=[{"kingdom": "229", "clan": "Feniks"}])
    other, other_h = await _user(db_session, "other@x.com")
    mine = await _clan(db_session, owner.id, "roster-1")
    theirs = await _clan(db_session, other.id, "roster-2", kingdom="300", clan="Start")
    owner.saved_chest_links = [{"kingdom": "229", "clan": "Feniks"}, {"kingdom": "300", "clan": "Start"}]
    db_session.add(ChestManager(collector_id=theirs.id, user_id=owner.id))
    await db_session.commit()

    async with _client() as c:
        r = await c.get(URL, headers=owner_h)
    assert r.json() == {"collectors": []}   # свой и управляемый ростер — в полном кабинете, не в просмотре
    assert mine.id and theirs.id
