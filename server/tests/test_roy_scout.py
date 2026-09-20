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


@pytest.mark.asyncio
async def test_scout_find_creates_row(db_session):
    await _make_user(db_session)
    r = await _post(hwid="SCOUTUSER00001", kingdom=7, x=512, y=318)
    assert r.status_code == 200 and r.json()["success"] is True
    row = (await db_session.execute(select(RoyScoutFind))).scalar_one()
    assert (row.kingdom, row.x, row.y, row.reporter_hwid) == (7, 512, 318, "SCOUTUSER00001")


@pytest.mark.asyncio
async def test_scout_find_validates_xy_type_and_integer_range(db_session):
    await _make_user(db_session)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x="abc", y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=1, y="<b>")).status_code == 422
    # StrictInt: приведение типов запрещено (P-02, PA-2)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x="123", y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=True, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=1.5, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom="7", x=1, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=-5, y=0)).status_code == 200
    # P-02/PA-11: границы 32-битного Integer колонки
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=2147483647, y=-2147483648)).status_code == 200
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=2147483648, y=0)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=0, y=-2147483649)).status_code == 422


@pytest.mark.asyncio
async def test_scout_find_kingdom_lt_1_rejected(db_session):
    await _make_user(db_session)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=0, x=1, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=-1, x=1, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=1, x=1, y=1)).status_code == 200
    # верхняя граница 32-битного Integer колонки (P-02, PA-11)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=2147483647, x=1, y=1)).status_code == 200
    assert (await _post(hwid="SCOUTUSER00001", kingdom=2147483648, x=1, y=1)).status_code == 422
    # строгий int для kingdom (P-05, PT-08)
    assert (await _post(hwid="SCOUTUSER00001", kingdom="1", x=1, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=1.0, x=1, y=1)).status_code == 422
    assert (await _post(hwid="SCOUTUSER00001", kingdom=True, x=1, y=1)).status_code == 422


@pytest.mark.asyncio
async def test_scout_find_unknown_hwid_404():
    assert (await _post(hwid="NOSUCHHWID00001", kingdom=7, x=1, y=1)).status_code == 404


@pytest.mark.asyncio
async def test_scout_find_hwid_longer_than_16_404(db_session):
    """PT-07/2.6a: hwid длиннее колонки не найден среди users -> 404, вставки нет."""
    await _make_user(db_session)
    assert (await _post(hwid="SCOUTUSER00001EXTRA", kingdom=7, x=1, y=1)).status_code == 404
    assert (await db_session.execute(select(func.count(RoyScoutFind.id)))).scalar_one() == 0


@pytest.mark.asyncio
async def test_scout_find_banned_403(db_session):
    await _make_user(db_session, banned=True)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=1, y=1)).status_code == 403
    assert (await db_session.execute(select(func.count(RoyScoutFind.id)))).scalar_one() == 0


@pytest.mark.asyncio
async def test_scout_find_allows_repeated_identical_posts(db_session):
    """P-04: два одинаковых вызова подряд без паузы -> две строки (ни лимита, ни дедупа)."""
    await _make_user(db_session)
    for _ in range(2):
        assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=10, y=20)).status_code == 200
    assert (await db_session.execute(select(func.count(RoyScoutFind.id)))).scalar_one() == 2


@pytest.mark.asyncio
async def test_scout_find_does_not_touch_roy_pool(db_session, monkeypatch):
    """P-03/P-12: /roy/report, roy_pool, _report_rate и Telegram не задействованы."""
    import roy
    def _boom(*a, **k):
        raise AssertionError("send_telegram_alert must not be called")
    monkeypatch.setattr(roy, "send_telegram_alert", _boom)
    # Sentinel вместо clear(): доказываем не только "пусто после", а "содержимое НЕ ТРОНУТО" —
    # иначе тест доказывал бы только "scout-find ничего не добавил в уже пустой dict", а не
    # "scout-find не трогает существующие записи _report_rate чужого hwid".
    roy._report_rate.clear()
    roy._report_rate["SENTINEL_OTHER_HWID"] = 123.0
    await _make_user(db_session)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=1, y=1)).status_code == 200
    assert (await db_session.execute(select(func.count(RoyPool.id)))).scalar_one() == 0
    assert roy._report_rate == {"SENTINEL_OTHER_HWID": 123.0}


@pytest.mark.asyncio
async def test_scout_find_insert_deletes_expired(db_session):
    """P-13: вставка удаляет находки старше срока жизни, свежие остаются (не граница — общий случай,
    точная граница 30:00 — отдельный тест ниже)."""
    await _make_user(db_session)
    now = datetime.now(timezone.utc)
    db_session.add(RoyScoutFind(kingdom=1, x=1, y=1, reporter_hwid="OLD", found_at=now - timedelta(minutes=31)))
    db_session.add(RoyScoutFind(kingdom=2, x=2, y=2, reporter_hwid="FRESH", found_at=now - timedelta(minutes=5)))
    await db_session.commit()
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=3, y=3)).status_code == 200
    hwids = sorted((await db_session.execute(select(RoyScoutFind.reporter_hwid))).scalars().all())
    assert hwids == ["FRESH", "SCOUTUSER00001"]


@pytest.mark.asyncio
async def test_scout_find_insert_deletes_expired_at_exact_boundary(db_session, monkeypatch):
    """P-13: удаление на вставке — `found_at <= cutoff` (не `<`), граница ровно 30:00 удаляется, а не
    только «старше». Отдельно от test_scout_finds_excludes_older_than_ttl (файл 27, читающая сторона,
    `>` в SELECT) — здесь ДРУГОЙ код (delete на INSERT), с собственным `<=`, и его границу ничего кроме
    этого теста не защищает: смена `<=` на `<` в реализации прошла бы мимо test_scout_find_insert_deletes_expired
    (31 мин / 5 мин — не граница) незамеченной. Часы roy.datetime зафиксированы (frozen clock, образец
    test_scout_finds_excludes_older_than_ttl, файл 27) — иначе `now` теста и `now` внутри эндпоинта
    разойдутся на миллисекунды и граница 30:00 станет случайной (flaky)."""
    import roy
    await _make_user(db_session)
    frozen = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen

    monkeypatch.setattr(roy, "datetime", FixedDatetime)
    for k, age in ((1, timedelta(minutes=29, seconds=59)),   # остаётся
                   (2, timedelta(minutes=30)),                # удаляется (P-13: "≥ 30 мин удалена")
                   (3, timedelta(minutes=30, seconds=1))):     # удаляется
        db_session.add(RoyScoutFind(kingdom=k, x=k, y=k, reporter_hwid=f"H{k}", found_at=frozen - age))
    await db_session.commit()
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=9, y=9)).status_code == 200
    hwids = sorted((await db_session.execute(select(RoyScoutFind.reporter_hwid))).scalars().all())
    assert hwids == ["H1", "SCOUTUSER00001"]


@pytest.mark.asyncio
async def test_scout_finds_empty():
    r = await _get()
    assert r.status_code == 200 and r.json() == {"finds": []}


@pytest.mark.asyncio
async def test_scout_finds_response_has_no_hwid(db_session):
    db_session.add(RoyScoutFind(kingdom=7, x=1, y=2, reporter_hwid="SECRETHWID0001"))
    await db_session.commit()
    body = (await _get()).json()
    assert list(body["finds"][0].keys()) == ["kingdom", "x", "y", "found_at"]
    assert "SECRETHWID0001" not in (await _get()).text


@pytest.mark.asyncio
async def test_scout_finds_newest_first(db_session):
    now = datetime.now(timezone.utc)
    for k, mins in ((1, 10), (2, 1), (3, 5)):
        db_session.add(RoyScoutFind(kingdom=k, x=k, y=k, reporter_hwid="H",
                                    found_at=now - timedelta(minutes=mins)))
    await db_session.commit()
    assert [f["kingdom"] for f in (await _get()).json()["finds"]] == [2, 3, 1]


@pytest.mark.asyncio
async def test_scout_finds_excludes_older_than_ttl(db_session, monkeypatch):
    """P-13, PT-15: граница детерминирована — часы roy.datetime зафиксированы (образец test_roy.py)."""
    import roy
    frozen = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return frozen

    monkeypatch.setattr(roy, "datetime", FixedDatetime)
    for k, age in ((1, timedelta(minutes=29, seconds=59)),
                   (2, timedelta(minutes=30)),
                   (3, timedelta(minutes=30, seconds=1))):
        db_session.add(RoyScoutFind(kingdom=k, x=k, y=k, reporter_hwid="H", found_at=frozen - age))
    await db_session.commit()
    # видна только запись младше 30:00; ровно 30:00 и старше — нет (found_at > now - 30 мин)
    assert [f["kingdom"] for f in (await _get()).json()["finds"]] == [1]


@pytest.mark.asyncio
async def test_scout_endpoints_use_timezone_aware_utc_now(db_session, monkeypatch):
    """P-13, PT-19: now — строго aware UTC. SQLite наивное время не отвергает, прод (timestamptz) отвергнет."""
    import roy
    frozen = datetime(2026, 9, 18, 12, 0, 0, tzinfo=timezone.utc)
    seen = []

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            seen.append(tz)
            return frozen

    monkeypatch.setattr(roy, "datetime", FixedDatetime)
    await _make_user(db_session)
    assert (await _post(hwid="SCOUTUSER00001", kingdom=7, x=1, y=1)).status_code == 200
    assert (await _get()).status_code == 200
    assert seen and all(tz is timezone.utc for tz in seen)


@pytest.mark.asyncio
async def test_scout_finds_returns_at_most_limit_newest(db_session, monkeypatch):
    """P-09, PT-12: не более SCOUT_FINDS_LIMIT самых новых (малый лимит подставлен для теста)."""
    import roy
    monkeypatch.setattr(roy, "SCOUT_FINDS_LIMIT", 3)
    now = datetime.now(timezone.utc)
    for k in range(1, 6):  # k=5 — самая новая
        db_session.add(RoyScoutFind(kingdom=k, x=k, y=k, reporter_hwid="H",
                                    found_at=now - timedelta(minutes=10 - k)))
    await db_session.commit()
    assert [f["kingdom"] for f in (await _get()).json()["finds"]] == [5, 4, 3]


@pytest.mark.asyncio
async def test_scout_finds_tie_break_by_id_desc(db_session):
    """P-09, PT-12: при равном found_at более новая запись (больший id) идёт первой.
    Проверено эмпирически (sqlite3, in-memory): без ORDER BY id DESC ties отдаются в порядке
    вставки (id ASC) детерминированно, не «случайно» — поэтому поведенческий тест здесь надёжен
    и не привязан к тексту сгенерированного SQLAlchemy SQL (который ломается от рефакторинга/алиасов)."""
    now = datetime.now(timezone.utc)
    for k in (1, 2, 3):
        db_session.add(RoyScoutFind(kingdom=k, x=k, y=k, reporter_hwid="H", found_at=now))
    await db_session.commit()
    assert [f["kingdom"] for f in (await _get()).json()["finds"]] == [3, 2, 1]
