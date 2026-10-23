"""Импорт сундуков читает только нужный диапазон реестра. Аудит 2026-10-24.
Дедупликация, списание «всё или ничего» и уникальный индекс не меняются."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

import chests as chests_module
from main import app
from models import Chest, ChestCollector
from tests.test_chests import _create_user, _payload


def _item(ts, sender="S1", ctype="A"):
    return {"chest_type": ctype, "sender": sender, "timestamp": ts}


async def _post(payload):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.post("/api/v1/chests/import", json=payload)


async def _collector(db, user):
    return (await db.execute(select(ChestCollector).where(ChestCollector.user_id == user.id))).scalar_one()


@pytest.mark.asyncio
async def test_load_existing_keys_reads_only_the_requested_range(db_session):
    user = await _create_user(db_session, "range0000000001", credits=100)
    await db_session.commit()
    await _post(_payload(user.hwid, items=[
        _item("2026-01-01T10:00:00", "Old"), _item("2026-06-18T10:00:00", "In"),
        _item("2026-12-31T10:00:00", "Future")]))
    col = await _collector(db_session, user)

    keys = await chests_module._load_existing_keys(
        col.id, db_session, datetime(2026, 6, 17), datetime(2026, 6, 19))
    assert keys == {("In", "A", datetime(2026, 6, 18, 10, 0, 0))}

    everything = await chests_module._load_existing_keys(col.id, db_session)
    assert len(everything) == 3                       # без границ — читается весь реестр (путь повтора)


@pytest.mark.asyncio
async def test_import_passes_batch_range_with_margin_to_the_loader(db_session, monkeypatch):
    user = await _create_user(db_session, "range0000000002", credits=100)
    await db_session.commit()
    calls = []
    real = chests_module._load_existing_keys

    async def spy(collector_id, db, lo=None, hi=None):
        calls.append((lo, hi))
        return await real(collector_id, db, lo, hi)

    monkeypatch.setattr(chests_module, "_load_existing_keys", spy)
    r = await _post(_payload(user.hwid, items=[
        _item("2026-06-18T10:00:00", "A1"), _item("2026-06-18T12:00:00", "A2")]))
    assert r.json()["count"] == 2
    lo, hi = calls[0]
    assert lo == datetime(2026, 6, 18, 10) - chests_module.IMPORT_RANGE_MARGIN
    assert hi == datetime(2026, 6, 18, 12) + chests_module.IMPORT_RANGE_MARGIN
    assert chests_module.IMPORT_RANGE_MARGIN >= timedelta(hours=24)   # шире любого часового пояса (±14 ч)


@pytest.mark.asyncio
async def test_resend_of_same_batch_is_a_noop_including_range_edges(db_session):
    user = await _create_user(db_session, "range0000000003", credits=100)
    await db_session.commit()
    items = [_item("2026-06-18T10:00:00", "Early"), _item("2026-06-18T12:00:00", "Late")]
    assert (await _post(_payload(user.hwid, items=items))).json()["count"] == 2
    await db_session.refresh(user)
    credits_after_first = user.credits

    again = await _post(_payload(user.hwid, items=items))        # самая ранняя и самая поздняя метки — на границах
    assert again.status_code == 200 and again.json()["count"] == 0
    await db_session.refresh(user)
    assert user.credits == credits_after_first                   # повтор не списывает
    col = await _collector(db_session, user)
    n = len((await db_session.execute(select(Chest).where(Chest.collector_id == col.id))).scalars().all())
    assert n == 2


@pytest.mark.asyncio
async def test_old_rows_outside_range_do_not_block_or_duplicate(db_session):
    user = await _create_user(db_session, "range0000000004", credits=100)
    await db_session.commit()
    await _post(_payload(user.hwid, items=[_item("2026-01-01T10:00:00", "Old")]))
    r = await _post(_payload(user.hwid, items=[
        _item("2026-06-18T10:00:00", "Old"), _item("2026-01-01T10:00:00", "Old")]))
    # второй пришёл с диапазоном, охватывающим и старую запись: она отсеивается как дубль, новая сохраняется
    assert r.json()["count"] == 1


def test_same_moment_in_different_timezone_formats_is_one_key_and_one_bound():
    """Нормализация приводит aware и naive формы одного момента к одному ключу и одной границе диапазона.
    (Сквозной тест через БД невозможен: SQLite отбрасывает смещение пояса, Postgres timestamptz — нет.)"""
    from types import SimpleNamespace as NS
    forms = ["2026-06-18T05:00:00+03:00", "2026-06-18T02:00:00", "2026-06-18T02:00:00+00:00", "2026-06-17T21:00:00-05:00"]
    assert {chests_module._normalize_ts(f) for f in forms} == {datetime(2026, 6, 18, 2)}
    bounds = {chests_module._batch_range([NS(timestamp=f)]) for f in forms}
    assert len(bounds) == 1
    keys = {("S", "A", chests_module._normalize_ts(f)) for f in forms}
    assert len(keys) == 1
    # ключ из БД (aware UTC, как отдаёт Postgres) совпадает с ключом батча
    assert chests_module._dedupe(
        [NS(sender="S", chest_type="A", timestamp="2026-06-18T05:00:00+03:00")],
        {("S", "A", chests_module._normalize_ts(datetime(2026, 6, 18, 2, tzinfo=timezone.utc)))}) == []


@pytest.mark.asyncio
async def test_mixed_aware_and_naive_batch_builds_a_range_covering_every_item(db_session, monkeypatch):
    user = await _create_user(db_session, "range0000000006", credits=100)
    await db_session.commit()
    seen = []
    real = chests_module._load_existing_keys

    async def spy(collector_id, db, lo=None, hi=None):
        seen.append((lo, hi))
        return await real(collector_id, db, lo, hi)

    monkeypatch.setattr(chests_module, "_load_existing_keys", spy)
    await _post(_payload(user.hwid, items=[
        _item("2026-06-18T23:00:00-05:00", "X"),     # = 19 июня 04:00 UTC
        _item("2026-06-18T01:00:00", "Y")]))
    lo, hi = seen[0]
    assert lo <= datetime(2026, 6, 18, 1) and hi >= datetime(2026, 6, 19, 4)


@pytest.mark.asyncio
async def test_retry_after_integrity_error_reads_the_whole_registry(db_session, monkeypatch):
    user = await _create_user(db_session, "range0000000007", credits=100)
    await db_session.commit()
    payload = _payload(user.hwid, items=[_item("2026-06-18T02:00:00")])
    assert (await _post(payload)).json()["count"] == 1

    real = chests_module._load_existing_keys
    calls = []

    async def flaky(collector_id, db, lo=None, hi=None):
        calls.append((lo, hi))
        if len(calls) == 1:
            return set()                                   # устаревший снимок → упор в уникальный индекс
        return await real(collector_id, db, lo, hi)

    monkeypatch.setattr(chests_module, "_load_existing_keys", flaky)
    second = await _post(payload)
    assert second.status_code == 200 and second.json()["count"] == 0
    assert calls[0][0] is not None                          # основной путь — с диапазоном
    assert calls[1] == (None, None)                         # повтор — полное чтение


@pytest.mark.asyncio
async def test_all_or_nothing_is_kept_when_credits_are_short(db_session):
    user = await _create_user(db_session, "range0000000008", credits=0)
    await db_session.commit()
    r = await _post(_payload(user.hwid, items=[_item("2026-06-18T10:00:00")]))
    assert r.status_code == 402
    col = (await db_session.execute(select(ChestCollector).where(ChestCollector.user_id == user.id))).scalar_one_or_none()
    if col is not None:
        assert (await db_session.execute(select(Chest).where(Chest.collector_id == col.id))).first() is None
