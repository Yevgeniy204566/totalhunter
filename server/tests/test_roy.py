"""
TDD tests — server/roy.py: rate limit /scan, dedup /report, kingdom filter /pool.
Run: python -m pytest server/tests/test_roy.py -v
"""
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from models import RoyPool, RoyBalance
from database import get_db


@pytest.fixture(autouse=True)
def clear_roy_rate_limits():
    """Сбрасываем in-memory rate-limit dicts между тестами."""
    import roy
    roy._report_rate.clear()
    if hasattr(roy, '_scan_rate'):
        roy._scan_rate.clear()
    yield
    roy._report_rate.clear()
    if hasattr(roy, '_scan_rate'):
        roy._scan_rate.clear()


# ── B1: rate limit на POST /roy/scan ────────────────────────────────────────

@pytest.mark.asyncio
async def test_scan_consecutive_same_hwid_second_is_rate_limited():
    """Два /scan подряд с одного HWID — второй возвращает note=rate_limited."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r1 = await c.post("/roy/scan", json={"hwid": "HWID_SCAN01"})
        r2 = await c.post("/roy/scan", json={"hwid": "HWID_SCAN01"})

    assert r1.json()["success"] is True
    assert r1.json().get("note") != "rate_limited"
    assert r2.json()["success"] is True
    assert r2.json().get("note") == "rate_limited"


@pytest.mark.asyncio
async def test_scan_rate_limited_request_does_not_accrue_balance():
    """Rate-limited /scan не начисляет 45 сек — баланс = 45, не 90."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/roy/scan", json={"hwid": "HWID_SCAN02"})   # засчитан
        await c.post("/roy/scan", json={"hwid": "HWID_SCAN02"})   # rate_limited

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import select
        row = (await db.execute(
            select(RoyBalance).where(RoyBalance.hwid == "HWID_SCAN02")
        )).scalar_one_or_none()
        assert row is not None
        assert row.balance_sec == 45  # только один скан, не два


@pytest.mark.asyncio
async def test_scan_different_hwids_both_accrue():
    """Два разных HWID могут обоими засчитать /scan независимо."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/roy/scan", json={"hwid": "HWID_SCAN03"})
        await c.post("/roy/scan", json={"hwid": "HWID_SCAN04"})

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import select
        rows = (await db.execute(select(RoyBalance))).scalars().all()
        hashed = {r.hwid: r.balance_sec for r in rows}
        assert hashed.get("HWID_SCAN03") == 45
        assert hashed.get("HWID_SCAN04") == 45


# ── B3+B4: дедупликация по (kingdom, x, y) в /report ────────────────────────

@pytest.mark.asyncio
async def test_report_same_coordinates_different_hwids_creates_one_entry():
    """Два репорта одной (K,X,Y) от разных HWID → одна запись в БД, percent обновлён."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/roy/report", json={
            "hwid": "HWID_REP01", "kingdom": 100, "x": 50, "y": 75, "percent": 30
        })
        await c.post("/roy/report", json={
            "hwid": "HWID_REP02", "kingdom": 100, "x": 50, "y": 75, "percent": 55
        })

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import select
        rows = (await db.execute(select(RoyPool))).scalars().all()
        assert len(rows) == 1
        assert rows[0].percent == 55


@pytest.mark.asyncio
async def test_report_different_coordinates_creates_two_entries():
    """Два репорта разных (X,Y) от разных HWID → две строки в БД."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        await c.post("/roy/report", json={
            "hwid": "HWID_REP03A", "kingdom": 100, "x": 50, "y": 75, "percent": 30
        })
        await c.post("/roy/report", json={
            "hwid": "HWID_REP03B", "kingdom": 100, "x": 60, "y": 80, "percent": 20
        })

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import select
        rows = (await db.execute(select(RoyPool))).scalars().all()
        assert len(rows) == 2


# ── R11: фильтр по kingdom в GET /pool ──────────────────────────────────────

@pytest.mark.asyncio
async def test_pool_with_kingdom_param_returns_only_matching(db_session):
    """GET /pool?kingdom=100 возвращает только биржи из ГОСа 100."""
    future = datetime.now(timezone.utc) + timedelta(minutes=10)
    now = datetime.now(timezone.utc)

    db_session.add(RoyBalance(hwid="HWID_POOL01", balance_sec=300))
    db_session.add(RoyPool(kingdom=100, x=10, y=20, percent=30,
                           reporter_hwid="OTHER1", expires_at=future, updated_at=now))
    db_session.add(RoyPool(kingdom=200, x=30, y=40, percent=50,
                           reporter_hwid="OTHER2", expires_at=future, updated_at=now))
    await db_session.flush()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/roy/pool", params={"hwid": "HWID_POOL01", "kingdom": 100})

    data = r.json()
    assert data["success"] is True
    assert len(data["pool"]) == 1
    assert data["pool"][0]["kingdom"] == 100


@pytest.mark.asyncio
async def test_pool_without_kingdom_param_returns_all(db_session):
    """GET /pool без kingdom возвращает биржи из всех ГОСов (обратная совместимость)."""
    future = datetime.now(timezone.utc) + timedelta(minutes=10)
    now = datetime.now(timezone.utc)

    db_session.add(RoyBalance(hwid="HWID_POOL02", balance_sec=300))
    db_session.add(RoyPool(kingdom=100, x=10, y=20, percent=30,
                           reporter_hwid="OTHER1", expires_at=future, updated_at=now))
    db_session.add(RoyPool(kingdom=200, x=30, y=40, percent=50,
                           reporter_hwid="OTHER2", expires_at=future, updated_at=now))
    await db_session.flush()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/roy/pool", params={"hwid": "HWID_POOL02"})

    data = r.json()
    assert data["success"] is True
    assert len(data["pool"]) == 2
