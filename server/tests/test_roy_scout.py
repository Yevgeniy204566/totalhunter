"""Публикация находок Биржи 2.0 в РОЙ (спека exchange-scout-roy-publication-design-01.md)."""
import pytest
from datetime import datetime, timedelta, timezone
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select, func

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from models import RoyPool, RoyScoutFind, User


# _make_user/_post/_get и импорты RoyPool/User/app/timedelta ниже Task 1 сам НЕ использует —
# они здесь заранее, потому что Task 2 (файл 26) и Task 3 (файл 27) дописывают тесты В ЭТОТ ЖЕ
# файл (`server/tests/test_roy_scout.py`) и полагаются на эти хелперы как на общий scaffold,
# без повторного редактирования шапки файла в каждой следующей части. Это одна общая точка
# определения, не забытый после Task 1 мусор.
async def _make_user(db, hwid="SCOUTUSER00001", banned=False):
    db.add(User(hwid=hwid, credits=10, ref_code=hwid[-8:], is_banned=banned))
    await db.commit()


async def _post(**payload):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.post("/roy/scout-find", json=payload)


async def _get():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        return await c.get("/roy/scout-finds")


@pytest.mark.asyncio
async def test_scout_find_model_roundtrip(db_session):
    db_session.add(RoyScoutFind(kingdom=7, x=512, y=318, reporter_hwid="SCOUTUSER00001"))
    await db_session.commit()
    row = (await db_session.execute(select(RoyScoutFind))).scalar_one()
    assert (row.kingdom, row.x, row.y) == (7, 512, 318)
    assert row.found_at is not None


def test_scout_find_found_at_is_indexed():
    """PT-20, P-13: DELETE/SELECT по found_at не должны сканировать всю таблицу.
    Design (architecture-04.md:12,14) прямо требует: found_at — ЕДИНСТВЕННЫЙ индекс таблицы
    (kingdom явно БЕЗ индекса — GET /roy/scout-finds не фильтрует по kingdom). Проверяем обе
    стороны контракта, не только наличие found_at, иначе случайный index=True на другой колонке
    пройдёт тест незамеченным. Синхронный тест (нет await) — обычный def, без
    @pytest.mark.asyncio, по образцу test_next_trade_routes_end_during_*_window в test_roy.py:270,286."""
    indexed = {c.name for idx in RoyScoutFind.__table__.indexes for c in idx.columns}
    assert indexed == {"found_at"}


def test_scout_find_migration_creates_expected_schema():
    """Реальный migration runtime-тест (Alembic Operations.context — официальный способ юнит-
    тестировать миграцию без полного env.py), а не только ORM-roundtrip через
    Base.metadata.create_all. Проверяет СТРУКТУРУ (колонки, единственный индекс found_at,
    downgrade убирает таблицу) на SQLite — НЕ проверяет server_default=sa.text('now()')
    (Postgres-специфичная функция, SQLite её не знает): приложение всегда передаёт found_at
    явно (architecture-04.md:14, P-13), server_default — только fallback, который в реальной
    вставке не участвует, поэтому его недоступность на SQLite не имитирует прод-поведение
    и намеренно не тестируется здесь."""
    import importlib.util
    from pathlib import Path
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import create_engine, inspect

    mig_path = (Path(__file__).parent.parent / "alembic" / "versions"
                / "s3c4o5u6t7f8_add_roy_scout_finds.py")
    spec = importlib.util.spec_from_file_location("_mig_scout_finds", mig_path)
    mig = importlib.util.module_from_spec(spec)
    engine = create_engine("sqlite://")
    with engine.connect() as conn:
        ctx = MigrationContext.configure(conn)
        with Operations.context(ctx):
            spec.loader.exec_module(mig)
            mig.upgrade()
        insp = inspect(conn)
        assert {c["name"] for c in insp.get_columns("roy_scout_finds")} == \
            {"id", "kingdom", "x", "y", "reporter_hwid", "found_at"}
        idx_names = {i["name"] for i in insp.get_indexes("roy_scout_finds")}
        idx_cols = {c for i in insp.get_indexes("roy_scout_finds") for c in i["column_names"]}
        assert idx_names == {"ix_roy_scout_finds_found_at"}
        assert idx_cols == {"found_at"}
        with Operations.context(ctx):
            mig.downgrade()
        assert "roy_scout_finds" not in inspect(conn).get_table_names()
