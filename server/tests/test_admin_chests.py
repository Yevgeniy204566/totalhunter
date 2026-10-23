"""Админка → «Сундуки»: таблица ростеров (одна строка = ростер) со счётчиками загрузок за сегодня (сутки по Киеву),
за скользящие 7×24 часа и «в базе»; источник — chests.created_at (момент загрузки), не collected_at (игровое время)."""
import os
import secrets
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from admin_chests import kyiv_day_start_utc, rosters_report
from main import app
from models import Chest, ChestCollector, User

ADMIN = {"Authorization": f"Bearer {os.environ['ADMIN_TOKEN']}"}
UTC = timezone.utc
NOW = datetime(2026, 10, 23, 12, 0, 0, tzinfo=UTC)  # 15:00 по Киеву (UTC+3 до 25.10)


async def _user(db, email=None):
    u = User(hwid=secrets.token_hex(8).upper(), ref_code=secrets.token_hex(5), email=email)
    db.add(u)
    await db.flush()
    return u


async def _roster(db, user, kingdom, clan, uploads):
    """uploads — список datetime загрузки (chests.created_at)."""
    c = ChestCollector(kingdom=kingdom, clan=clan, user_id=user.id, slug=secrets.token_urlsafe(16), quotas=[])
    db.add(c)
    await db.flush()
    for i, ts in enumerate(uploads):
        db.add(Chest(collector_id=c.id, chest_type_raw="A", chest_type_canonical="A", sender_raw=f"P{i}",
                     sender_canonical=f"P{i}", collected_at=ts - timedelta(minutes=5), created_at=ts))
    await db.flush()
    return c


def test_kyiv_day_start_handles_summer_and_winter_time():
    summer = kyiv_day_start_utc(datetime(2026, 7, 10, 12, 0, tzinfo=UTC))   # EEST = UTC+3
    assert summer == datetime(2026, 7, 9, 21, 0, tzinfo=UTC)
    winter = kyiv_day_start_utc(datetime(2026, 12, 10, 12, 0, tzinfo=UTC))  # EET = UTC+2
    assert winter == datetime(2026, 12, 9, 22, 0, tzinfo=UTC)
    # 00:30 по Киеву (21:30 UTC накануне) — день уже новый
    assert kyiv_day_start_utc(datetime(2026, 10, 22, 21, 30, tzinfo=UTC)) == datetime(2026, 10, 22, 21, 0, tzinfo=UTC)


@pytest.mark.asyncio
async def test_rows_are_per_roster_with_separate_counters(db_session):
    owner = await _user(db_session, f"own{secrets.token_hex(3)}@x.test")
    start = kyiv_day_start_utc(NOW)
    await _roster(db_session, owner, "100", "Alpha", [start + timedelta(minutes=1), NOW - timedelta(days=3)])
    await _roster(db_session, owner, "200", "Beta", [NOW - timedelta(days=10)])
    await db_session.commit()

    rep = await rosters_report(db_session, now=NOW, q=owner.email)
    by_clan = {r["clan"]: r for r in rep["rows"]}
    assert (by_clan["Alpha"]["today"], by_clan["Alpha"]["week"], by_clan["Alpha"]["total"]) == (1, 2, 2)
    assert (by_clan["Beta"]["today"], by_clan["Beta"]["week"], by_clan["Beta"]["total"]) == (0, 0, 1)
    assert by_clan["Alpha"]["kingdom"] == "100" and by_clan["Beta"]["kingdom"] == "200"
    assert rep["totals"] == {"today": 1, "week": 2, "total": 3}


@pytest.mark.asyncio
async def test_time_boundaries_today_and_seven_days(db_session):
    owner = await _user(db_session, f"b{secrets.token_hex(3)}@x.test")
    start = kyiv_day_start_utc(NOW)
    await _roster(db_session, owner, "300", "Edge", [
        start,                                   # ровно полночь по Киеву — «сегодня»
        start - timedelta(seconds=1),            # секундой раньше — уже вчера
        NOW - timedelta(days=7),                 # ровно 7 суток — за границей
        NOW - timedelta(days=7) + timedelta(seconds=1),  # на секунду внутри окна
    ])
    await db_session.commit()
    row = (await rosters_report(db_session, now=NOW, q="Edge"))["rows"][0]
    assert row["today"] == 1
    assert row["week"] == 3      # полночь, полночь−1с, 7 суток−1с (ровно 7 суток исключены)
    assert row["total"] == 4


@pytest.mark.asyncio
async def test_last_upload_is_latest_created_at_not_collected_at(db_session):
    owner = await _user(db_session, f"l{secrets.token_hex(3)}@x.test")
    last = NOW - timedelta(hours=2)
    await _roster(db_session, owner, "400", "Last", [NOW - timedelta(days=2), last])
    await db_session.commit()
    row = (await rosters_report(db_session, now=NOW, q="Last"))["rows"][0]
    assert datetime.fromisoformat(row["last_upload_at"]).replace(tzinfo=None) == last.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_roster_without_chests_and_bot_only_owner(db_session):
    bot = await _user(db_session)  # без почты
    await _roster(db_session, bot, "500", "Empty", [])
    await db_session.commit()
    row = (await rosters_report(db_session, now=NOW, q="Empty"))["rows"][0]
    assert row["owner_email"] is None and row["owner_hwid"] == bot.hwid
    assert (row["today"], row["week"], row["total"], row["last_upload_at"]) == (0, 0, 0, None)


@pytest.mark.asyncio
async def test_search_filter_and_sort(db_session):
    a = await _user(db_session, f"a{secrets.token_hex(3)}@x.test")
    b = await _user(db_session, f"b{secrets.token_hex(3)}@x.test")
    tag = secrets.token_hex(3)
    await _roster(db_session, a, "611", f"Few{tag}", [NOW - timedelta(hours=1)])
    await _roster(db_session, b, "612", f"Many{tag}", [NOW - timedelta(hours=1), NOW - timedelta(hours=2),
                                                      NOW - timedelta(hours=3)])
    await db_session.commit()

    by_clan = await rosters_report(db_session, now=NOW, q=tag, sort="total", order="desc")
    assert [r["clan"] for r in by_clan["rows"]] == [f"Many{tag}", f"Few{tag}"]
    asc = await rosters_report(db_session, now=NOW, q=tag, sort="total", order="asc")
    assert [r["clan"] for r in asc["rows"]] == [f"Few{tag}", f"Many{tag}"]
    by_kingdom = await rosters_report(db_session, now=NOW, q="612")
    assert [r["clan"] for r in by_kingdom["rows"]] == [f"Many{tag}"]
    by_email = await rosters_report(db_session, now=NOW, q=a.email)
    assert [r["clan"] for r in by_email["rows"]] == [f"Few{tag}"]
    owner_only = await rosters_report(db_session, now=NOW, owner_id=b.id)
    assert [r["clan"] for r in owner_only["rows"]] == [f"Many{tag}"]


@pytest.mark.asyncio
async def test_endpoint_requires_admin_and_returns_report(db_session):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        denied = await client.get("/admin/chests/rosters")
        ok = await client.get("/admin/chests/rosters", headers=ADMIN, params={"sort": "today"})
        bad = await client.get("/admin/chests/rosters", headers=ADMIN, params={"sort": "nope"})
    assert denied.status_code in (401, 403)
    assert ok.status_code == 200 and {"rows", "totals", "today_from", "week_from"} <= set(ok.json())
    assert bad.status_code == 400
