# Сундуки — backend-фундамент Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Реализовать таблицы и `POST /api/v1/chests/import` так, чтобы данные сундуков от
бота сохранялись с тенант-изоляцией по `[kingdom, clan, user_id]` и автокоррекцией OCR-имён/
типов сундуков через серверный alias-словарь.

**Architecture:** Новый роутер `server/chests.py` (по образцу `server/clan.py`), 4 новые
SQLAlchemy-модели в `server/models.py`, одна Alembic-миграция. Авторизация по `hwid` (как
`/use_credit`), не Bearer ADMIN_TOKEN — эндпоинт вызывают рядовые платящие пользователи бота.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL (prod) / aiosqlite (тесты), Alembic,
pytest + pytest-asyncio + httpx.AsyncClient.

## Global Constraints

- Тенант = `users.id` (найден по `hwid` из payload) — без новой сущности «Account».
- Алиасы нужны для ДВУХ полей: `sender` (имя игрока) и `chest_type` (тип сундука) —
  два отдельных словаря, симметричная логика.
- Идемпотентность импорта: повторная отправка одного и того же батча не создаёт дублей в
  `chests`. Реализуется через unique constraint `(collector_id, sender_raw, chest_type_raw,
  collected_at)` + pre-check существующих ключей перед bulk-insert (без `ON CONFLICT`/
  dialect-specific insert — чтобы тесты на SQLite и прод на PostgreSQL вели себя одинаково).
- `CREDIT_COST["chest"] = 10` в `server/main.py` (сейчас отсутствует → списывается 1).
- Один `commit()` на весь батч импорта — никаких двух `db.begin()` в одном эндпоинте.
- Источник правды по схеме — спека `docs/superpowers/specs/2026-06-18-chests-backend-foundation-design.md`.

---

### Task 1: Модели `ChestCollector`, `Chest`, `PlayerAlias`, `ChestTypeAlias`

**Files:**
- Modify: `server/models.py` (добавить новый раздел в конец файла, после `ClanMember`)
- Create: `server/alembic/versions/h7c8e9s0t1c2_add_chest_tables.py`

**Interfaces:**
- Produces: `ChestCollector(id, kingdom, clan, user_id, slug, created_at)`,
  `Chest(id, collector_id, chest_type_raw, chest_type_canonical, sender_raw,
  sender_canonical, collected_at, created_at)`,
  `PlayerAlias(id, collector_id, raw_name, canonical_name)`,
  `ChestTypeAlias(id, collector_id, raw_type, canonical_type)`.

- [ ] **Step 1: Добавить модели в `server/models.py`**

Вставить в конец файла (после класса `ClanMember`, строка ~373):

```python

# ─────────────────────────────────────────────
# Сундуки — tenant isolation + alias dictionary
# ─────────────────────────────────────────────

class ChestCollector(Base):
    """
    Один сборщик внутри одного клана/королевства — единица тенант-изоляции.
    slug — непредсказуемый публичный идентификатор для будущего дашборда (не в этой работе).
    """
    __tablename__ = "chest_collectors"
    __table_args__ = (
        UniqueConstraint("kingdom", "clan", "user_id", name="uq_chest_collectors_tenant"),
    )

    id         = Column(Integer, primary_key=True)
    kingdom    = Column(String(50),  nullable=False)
    clan       = Column(String(100), nullable=False)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    slug       = Column(String(32), nullable=False, unique=True)
    created_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        server_default=func.now())


class Chest(Base):
    """
    Одна открытая сундук-запись. Уникальность по содержимому+времени защищает от
    дублей при повторной отправке одного батча после обрыва сети.
    """
    __tablename__ = "chests"
    __table_args__ = (
        UniqueConstraint("collector_id", "sender_raw", "chest_type_raw", "collected_at",
                         name="uq_chests_idempotent"),
    )

    id                    = Column(Integer, primary_key=True)
    collector_id          = Column(Integer, ForeignKey("chest_collectors.id"),
                                   nullable=False, index=True)
    chest_type_raw        = Column(String(200), nullable=False)
    chest_type_canonical  = Column(String(200), nullable=False)
    sender_raw            = Column(String(100), nullable=False)
    sender_canonical       = Column(String(100), nullable=False)
    collected_at          = Column(TIMESTAMP(timezone=True), nullable=False)
    created_at            = Column(TIMESTAMP(timezone=True), nullable=False,
                                   server_default=func.now())


class PlayerAlias(Base):
    """Словарь исправлений OCR для имён игроков, отдельно на каждого сборщика."""
    __tablename__ = "player_aliases"
    __table_args__ = (
        UniqueConstraint("collector_id", "raw_name", name="uq_player_aliases_raw_name"),
    )

    id             = Column(Integer, primary_key=True)
    collector_id   = Column(Integer, ForeignKey("chest_collectors.id"),
                            nullable=False, index=True)
    raw_name       = Column(String(100), nullable=False)
    canonical_name = Column(String(100), nullable=False)


class ChestTypeAlias(Base):
    """Словарь исправлений OCR для названий типов сундуков, отдельно на каждого сборщика."""
    __tablename__ = "chest_type_aliases"
    __table_args__ = (
        UniqueConstraint("collector_id", "raw_type", name="uq_chest_type_aliases_raw_type"),
    )

    id             = Column(Integer, primary_key=True)
    collector_id   = Column(Integer, ForeignKey("chest_collectors.id"),
                            nullable=False, index=True)
    raw_type       = Column(String(200), nullable=False)
    canonical_type = Column(String(200), nullable=False)
```

- [ ] **Step 2: Создать Alembic-миграцию**

Создать `server/alembic/versions/h7c8e9s0t1c2_add_chest_tables.py`:

```python
"""add chest tables (backend foundation: tenant isolation + alias dictionary)

Revision ID: h7c8e9s0t1c2
Revises: c1l2a3n4m5b6
Create Date: 2026-06-18

chest_collectors = tenant unit [kingdom, clan, user_id], slug for future public dashboard.
chests = one opened chest, unique on (collector_id, sender_raw, chest_type_raw, collected_at)
for idempotent re-import after network failure.
player_aliases / chest_type_aliases = OCR-correction dictionaries, scoped per collector.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'h7c8e9s0t1c2'
down_revision = 'c1l2a3n4m5b6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'chest_collectors',
        sa.Column('id',         sa.Integer(),                primary_key=True),
        sa.Column('kingdom',    sa.String(50),               nullable=False),
        sa.Column('clan',       sa.String(100),              nullable=False),
        sa.Column('user_id',    sa.Integer(),                nullable=False),
        sa.Column('slug',       sa.String(32),                nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),  nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name=op.f('fk_chest_collectors_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chest_collectors')),
        sa.UniqueConstraint('kingdom', 'clan', 'user_id',
                            name='uq_chest_collectors_tenant'),
        sa.UniqueConstraint('slug', name='uq_chest_collectors_slug'),
    )
    op.create_index(op.f('ix_chest_collectors_user_id'), 'chest_collectors', ['user_id'])

    op.create_table(
        'chests',
        sa.Column('id',                    sa.Integer(),               primary_key=True),
        sa.Column('collector_id',          sa.Integer(),               nullable=False),
        sa.Column('chest_type_raw',        sa.String(200),            nullable=False),
        sa.Column('chest_type_canonical',  sa.String(200),            nullable=False),
        sa.Column('sender_raw',            sa.String(100),            nullable=False),
        sa.Column('sender_canonical',      sa.String(100),            nullable=False),
        sa.Column('collected_at',          sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at',            sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
        sa.ForeignKeyConstraint(['collector_id'], ['chest_collectors.id'],
                                name=op.f('fk_chests_collector_id_chest_collectors')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chests')),
        sa.UniqueConstraint('collector_id', 'sender_raw', 'chest_type_raw', 'collected_at',
                            name='uq_chests_idempotent'),
    )
    op.create_index(op.f('ix_chests_collector_id'), 'chests', ['collector_id'])

    op.create_table(
        'player_aliases',
        sa.Column('id',             sa.Integer(),   primary_key=True),
        sa.Column('collector_id',   sa.Integer(),   nullable=False),
        sa.Column('raw_name',       sa.String(100), nullable=False),
        sa.Column('canonical_name', sa.String(100), nullable=False),
        sa.ForeignKeyConstraint(['collector_id'], ['chest_collectors.id'],
                                name=op.f('fk_player_aliases_collector_id_chest_collectors')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_player_aliases')),
        sa.UniqueConstraint('collector_id', 'raw_name', name='uq_player_aliases_raw_name'),
    )
    op.create_index(op.f('ix_player_aliases_collector_id'), 'player_aliases', ['collector_id'])

    op.create_table(
        'chest_type_aliases',
        sa.Column('id',             sa.Integer(),   primary_key=True),
        sa.Column('collector_id',   sa.Integer(),   nullable=False),
        sa.Column('raw_type',       sa.String(200), nullable=False),
        sa.Column('canonical_type', sa.String(200), nullable=False),
        sa.ForeignKeyConstraint(['collector_id'], ['chest_collectors.id'],
                                name=op.f('fk_chest_type_aliases_collector_id_chest_collectors')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_chest_type_aliases')),
        sa.UniqueConstraint('collector_id', 'raw_type', name='uq_chest_type_aliases_raw_type'),
    )
    op.create_index(op.f('ix_chest_type_aliases_collector_id'), 'chest_type_aliases',
                    ['collector_id'])


def downgrade() -> None:
    op.drop_table('chest_type_aliases')
    op.drop_table('player_aliases')
    op.drop_table('chests')
    op.drop_table('chest_collectors')
```

- [ ] **Step 3: Проверить, что models.py импортируется без ошибок**

Run: `cd server && python -c "import models"`
Expected: без вывода, без traceback (exit code 0)

- [ ] **Step 4: Commit**

```bash
git add server/models.py server/alembic/versions/h7c8e9s0t1c2_add_chest_tables.py
git commit -m "feat(server): add chest tables — tenant isolation + alias dictionaries"
```

---

### Task 2: `CREDIT_COST["chest"] = 10`

**Files:**
- Modify: `server/main.py:93-96` (словарь `CREDIT_COST`)
- Test: `server/tests/test_chests.py` (новый файл — создаётся в этом таске, остальные тесты добавляются в Task 3)

**Interfaces:**
- Consumes: ничего нового.
- Produces: `CREDIT_COST["chest"] == 10` — используется существующим `/use_credit` без изменений
  его кода.

- [ ] **Step 1: Написать падающий тест**

Создать `server/tests/test_chests.py`:

```python
"""Tests for chests.py — tenant isolation, alias dictionary, idempotent import."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app, CREDIT_COST


def test_credit_cost_chest_is_10():
    assert CREDIT_COST["chest"] == 10
```

- [ ] **Step 2: Запустить тест, убедиться что падает**

Run: `cd server && python -m pytest tests/test_chests.py::test_credit_cost_chest_is_10 -v`
Expected: FAIL — `KeyError: 'chest'`

- [ ] **Step 3: Исправить `CREDIT_COST` в `server/main.py`**

Найти (строка ~93):
```python
CREDIT_COST = {
    "exchange": 10,
    "crypt": 1,
}
```

Заменить на:
```python
CREDIT_COST = {
    "exchange": 10,
    "crypt": 1,
    "chest": 10,
}
```

- [ ] **Step 4: Запустить тест, убедиться что проходит**

Run: `cd server && python -m pytest tests/test_chests.py::test_credit_cost_chest_is_10 -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add server/main.py server/tests/test_chests.py
git commit -m "fix(server): chest import costs 10 credits, was defaulting to 1"
```

---

### Task 3: Роутер `server/chests.py` — happy path (создание коллектора + импорт без алиасов)

**Files:**
- Create: `server/chests.py`
- Modify: `server/tests/test_chests.py` (добавить тесты после Task 2)

**Interfaces:**
- Consumes: `User` модель из `models.py` (поля `id, hwid, is_banned`), `get_db` из `database.py`.
- Produces: `router = APIRouter(prefix="/api/v1/chests", tags=["chests"])` с эндпоинтом
  `POST /api/v1/chests/import`. Helper `_get_or_create_collector(kingdom, clan, user_id, db)
  -> ChestCollector` — переиспользуется в Task 4/5.

- [ ] **Step 1: Написать падающие тесты**

Добавить в `server/tests/test_chests.py` (после `test_credit_cost_chest_is_10`):

```python
import secrets
from sqlalchemy import select

from models import User, ChestCollector, Chest


async def _create_user(db, hwid, is_banned=False):
    u = User(hwid=hwid, ref_code=secrets.token_urlsafe(6), is_banned=is_banned)
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
```

- [ ] **Step 2: Запустить тесты, убедиться что падают**

Run: `cd server && python -m pytest tests/test_chests.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'chests'` (или `ImportError`)

- [ ] **Step 3: Реализовать `server/chests.py`**

Создать `server/chests.py`:

```python
"""
chests.py — Сундуки (Chests) import endpoint.

POST /api/v1/chests/import — принимает батч сундуков от бота, изолирует данные по
тенанту [kingdom, clan, user_id] (ChestCollector) и применяет alias-словари сборщика
к имени игрока и типу сундука перед записью.

Auth: hwid в payload → User (как /use_credit), НЕ Bearer ADMIN_TOKEN — вызывается
рядовыми платящими пользователями бота, а не админ-скриптами.
"""
import secrets
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Chest, ChestCollector, ChestTypeAlias, PlayerAlias, User

router = APIRouter(prefix="/api/v1/chests", tags=["chests"])


class ChestItemIn(BaseModel):
    chest_type: str
    sender: str
    timestamp: str


class ChestImportPayload(BaseModel):
    hwid: str
    kingdom: str
    clan: str
    timestamp: str
    items: List[ChestItemIn]


async def _get_or_create_collector(kingdom: str, clan: str, user_id: int,
                                   db: AsyncSession) -> ChestCollector:
    existing = (await db.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == kingdom,
            ChestCollector.clan == clan,
            ChestCollector.user_id == user_id,
        )
    )).scalar_one_or_none()
    if existing:
        return existing

    collector = ChestCollector(
        kingdom=kingdom, clan=clan, user_id=user_id,
        slug=secrets.token_urlsafe(16),
    )
    db.add(collector)
    await db.flush()
    return collector


@router.post("/import")
async def import_chests(payload: ChestImportPayload, db: AsyncSession = Depends(get_db)):
    if not payload.items:
        raise HTTPException(status_code=400, detail="items is empty")

    user = (await db.execute(
        select(User).where(User.hwid == payload.hwid)
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.is_banned:
        raise HTTPException(status_code=403, detail="Banned")

    collector = await _get_or_create_collector(payload.kingdom, payload.clan, user.id, db)

    player_aliases = {
        row.raw_name: row.canonical_name
        for row in (await db.execute(
            select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
        )).scalars().all()
    }
    type_aliases = {
        row.raw_type: row.canonical_type
        for row in (await db.execute(
            select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
        )).scalars().all()
    }

    existing_keys = {
        (row.sender_raw, row.chest_type_raw, row.collected_at.isoformat())
        for row in (await db.execute(
            select(Chest).where(Chest.collector_id == collector.id)
        )).scalars().all()
    }

    inserted = 0
    for item in payload.items:
        key = (item.sender, item.chest_type, item.timestamp)
        if key in existing_keys:
            continue
        existing_keys.add(key)
        db.add(Chest(
            collector_id=collector.id,
            chest_type_raw=item.chest_type,
            chest_type_canonical=type_aliases.get(item.chest_type, item.chest_type),
            sender_raw=item.sender,
            sender_canonical=player_aliases.get(item.sender, item.sender),
            collected_at=item.timestamp,
        ))
        inserted += 1

    await db.commit()

    return {"ok": True, "count": inserted, "collector_slug": collector.slug}
```

- [ ] **Step 4: Подключить роутер к `app` — иначе тесты бьют 404 от FastAPI, а не от бизнес-логики**

В `server/main.py` найти блок (строка ~78-84):
```python
app.include_router(web_router)
app.include_router(payments_router)
app.include_router(vault_router)
app.include_router(earn_router)
app.include_router(roy_router)
app.include_router(debug_router)
app.include_router(clan_router)
```

Добавить импорт рядом с остальными роутерами (искать `from clan import router as clan_router`
выше этого блока):
```python
from chests import router as chests_router
```

И добавить строку подключения в конец блока `include_router`:
```python
app.include_router(chests_router)
```

- [ ] **Step 5: Запустить тесты, убедиться что проходят**

Run: `cd server && python -m pytest tests/test_chests.py -v`
Expected: PASS (все 6 тестов, включая `test_credit_cost_chest_is_10` из Task 2)

- [ ] **Step 6: Commit**

```bash
git add server/chests.py server/main.py server/tests/test_chests.py
git commit -m "feat(server): POST /api/v1/chests/import with tenant isolation"
```

---

### Task 4: Alias-словарь и изоляция между сборщиками — тесты + проверка поведения

**Files:**
- Modify: `server/tests/test_chests.py`

**Interfaces:**
- Consumes: `_get_or_create_collector`, `PlayerAlias`, `ChestTypeAlias` из Task 1/3 — без
  изменений кода `chests.py` (логика alias-lookup уже реализована в Task 3, здесь только
  тесты на неё и на изоляцию).

- [ ] **Step 1: Написать тесты**

Добавить в `server/tests/test_chests.py`:

```python
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
```

- [ ] **Step 2: Запустить тесты**

Run: `cd server && python -m pytest tests/test_chests.py -v`
Expected: PASS — все тесты файла (10 тестов суммарно)

- [ ] **Step 3: Запустить весь набор тестов сервера — проверить отсутствие регрессий**

Run: `cd server && python -m pytest -v`
Expected: PASS — все тесты проекта, включая `test_chests.py`, зелёные

- [ ] **Step 4: Commit**

```bash
git add server/tests/test_chests.py
git commit -m "test(server): cover chest alias dictionary and tenant isolation"
```

---

## Что не входит в этот план (будущие подсистемы)

- Веб-редактор `player_aliases` / `chest_type_aliases`.
- Публичный дашборд клана по `collector_slug`.
- Ownership Transfer (PIN-код, перепривязка `collector.user_id`).
- Деплой на GCP (`git pull` + `systemctl restart` + `alembic upgrade head`) — выполняется
  отдельно, по явной команде пользователя, после ревью этого плана на проде не запускать
  автоматически.
