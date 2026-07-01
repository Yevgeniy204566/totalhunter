# Ancient Collector Hide + Inactivity Retention Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a 60-day inactivity timer that auto-purges only the Ancient-module
tables of a collector hidden via the Ancients dashboard (Chests data untouched),
and fix the existing 90-day stopped-collector cleanup so it also removes the
Ancient-module tables it currently orphans.

**Architecture:** One new nullable timestamp column (`ChestCollector.
ancient_hidden_at`) tracks "hidden since / last touched while hidden". The
`PATCH .../ancient-visibility` endpoint (already implemented this session)
sets it on hide and clears it on show. Two existing write endpoints
(`POST /api/v1/tournaments/import`, `POST /web/dashboard/ancients/{slug}/
calculate`) bump it forward whenever they touch a currently-hidden collector.
A new daily background tick (`server/ancient_retention.py`, mirroring the
existing tick pattern in `server/chest_history.py`) purges Ancient-only tables
for any collector whose `ancient_hidden_at` is more than 60 days in the past,
then resets the timestamp to `NULL` (nothing left to count down). A second,
independent fix touches the existing `run_stopped_collector_tick` in
`chest_history.py` to also delete the Ancient tables it currently misses.

**Tech Stack:** FastAPI, SQLAlchemy async (asyncpg in prod, aiosqlite in
tests), Alembic, pytest + pytest-asyncio + httpx `AsyncClient`/`ASGITransport`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-01-ancient-collector-retention-design.md`
  — every task below implements one part of it; read it once before starting
  if anything here is ambiguous.
- `PlayerAlias.collector_id` has NO `ondelete` rule on its FK to
  `chest_collectors.id` — never write code that deletes `ChestCollector` while
  leaving `PlayerAlias` rows pointing at it. This plan never does that: Task 4
  (new 60-day tick) never touches `ChestCollector` or `PlayerAlias` at all;
  Task 6 (90-day tick fix) keeps deleting `PlayerAlias` exactly as it does today.
  If future work adds a real `ondelete` rule instead, that is a separate,
  explicitly-approved change — not something to slip into this plan.
- Days, not calendar months: 60 and 90 are plain day counts, matching the
  existing `STOPPED_COLLECTOR_DAYS = 90` constant. Do not convert to
  `dateutil.relativedelta` or similar — unnecessary complexity for this.
- Run tests locally with `JWT_SECRET_KEY` set, e.g.:
  `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/ -q`
- Every DB-writing test must go through the `db_session` fixture from
  `server/tests/conftest.py` (in-memory SQLite, tables created fresh per test).
- Do not run `alembic upgrade head` against the real GCP database, and do not
  restart `totalhunter.service`, as part of this plan — deployment is a
  separate, explicitly-approved step (Task 7 documents the commands but is
  gated on the owner's go-ahead, per this project's CLAUDE.md deploy protocol).

---

## Task 1: `ancient_hidden_at` column + wire it into the visibility endpoint

**Files:**
- Modify: `server/models.py:381-412` (`ChestCollector` class)
- Create: `server/alembic/versions/h1d3n4t5c6l7_add_ancient_hidden_at.py`
- Modify: `server/ancients_dashboard.py` (`set_ancient_visibility`, currently ~line 210)
- Test: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Produces: `ChestCollector.ancient_hidden_at` — `Optional[datetime]`, timezone-aware.
  Every later task reads/writes this exact attribute name.

- [ ] **Step 1: Write the failing test**

Add to `server/tests/test_ancients_dashboard.py` (add `from datetime import
datetime, timezone` to the existing `datetime` import line at the top of the
file — currently the file does not import `datetime` at all, check the top of
the file and add a fresh `from datetime import datetime, timezone` import
line near the other imports):

```python
@pytest.mark.asyncio
async def test_hide_sets_ancient_hidden_at_unhide_clears_it(db_session):
    user, token = await _create_user_with_token(db_session, "hideat1@test.com")
    collector = await _create_collector(db_session, user.id, slug="hide-at-1")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.patch(
            "/web/dashboard/ancients/hide-at-1/ancient-visibility",
            json={"hidden": True},
            headers={"Authorization": f"Bearer {token}"},
        )
    await db_session.refresh(collector)
    assert collector.ancient_hidden_at is not None

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.patch(
            "/web/dashboard/ancients/hide-at-1/ancient-visibility",
            json={"hidden": False},
            headers={"Authorization": f"Bearer {token}"},
        )
    await db_session.refresh(collector)
    assert collector.ancient_hidden_at is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancients_dashboard.py::test_hide_sets_ancient_hidden_at_unhide_clears_it -q`
Expected: FAIL — `AttributeError: 'ChestCollector' object has no attribute 'ancient_hidden_at'`

- [ ] **Step 3: Add the column to the model**

In `server/models.py`, inside `class ChestCollector`, right after the
`ancient_hidden` line (added earlier this session):

```python
    ancient_hidden          = Column(Boolean, nullable=False, server_default=text("false"))
    ancient_hidden_at       = Column(TIMESTAMP(timezone=True), nullable=True)
```

- [ ] **Step 4: Write the migration**

Create `server/alembic/versions/h1d3n4t5c6l7_add_ancient_hidden_at.py`:

```python
"""add_ancient_hidden_at

Revision ID: h1d3n4t5c6l7
Revises: a9h2i3d4e5n6
Create Date: 2026-07-01

Timer for the "hidden and unused for 60 days -> Ancient data auto-purged"
retention rule. NULL means "not counting down" (visible, or never hidden).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'h1d3n4t5c6l7'
down_revision: Union[str, None] = 'a9h2i3d4e5n6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'chest_collectors',
        sa.Column('ancient_hidden_at', sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('chest_collectors', 'ancient_hidden_at')
```

- [ ] **Step 5: Wire it into the visibility endpoint**

In `server/ancients_dashboard.py`, find `set_ancient_visibility` (the
`@router.patch("/{slug}/ancient-visibility")` handler). Its body currently
reads:

```python
    collector = await _get_own_collector(db, slug, user)
    collector.ancient_hidden = payload.hidden
    await db.commit()
    return {"ok": True}
```

Change it to:

```python
    collector = await _get_own_collector(db, slug, user)
    collector.ancient_hidden = payload.hidden
    collector.ancient_hidden_at = datetime.now(timezone.utc) if payload.hidden else None
    await db.commit()
    return {"ok": True}
```

(`datetime` and `timezone` are already imported at the top of
`ancients_dashboard.py` via `from datetime import datetime, timedelta,
timezone` — no new import needed there.)

- [ ] **Step 6: Run test to verify it passes**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancients_dashboard.py -q`
Expected: PASS (all tests in the file, including the new one)

- [ ] **Step 7: Commit**

```bash
git add server/models.py server/alembic/versions/h1d3n4t5c6l7_add_ancient_hidden_at.py server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "feat(ancients): add ancient_hidden_at timer, set/clear on visibility toggle"
```

---

## Task 2: Touch `ancient_hidden_at` on tournament roster import

**Files:**
- Modify: `server/tournaments.py`
- Test: `server/tests/test_tournaments.py`

**Interfaces:**
- Consumes: `ChestCollector.ancient_hidden_at` (Task 1).

- [ ] **Step 1: Write the failing test**

Add to `server/tests/test_tournaments.py` (add `from datetime import
datetime, timedelta, timezone` near the top import block):

```python
@pytest.mark.asyncio
async def test_import_touches_ancient_hidden_at_when_hidden(db_session):
    user = await _create_user(db_session, "hwid7000000000a")
    collector = ChestCollector(
        kingdom="K229", clan="BERS7", user_id=user.id, slug="hidden-import-1",
        ancient_hidden=True,
        ancient_hidden_at=datetime.now(timezone.utc) - timedelta(days=55),
    )
    db_session.add(collector)
    await db_session.commit()
    old_touch = collector.ancient_hidden_at

    payload = _payload(user.hwid, clan="BERS7",
                       items=[{"name": "Иванов", "place": 1, "points": 100}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=payload)

    await db_session.refresh(collector)
    assert collector.ancient_hidden_at > old_touch
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_tournaments.py::test_import_touches_ancient_hidden_at_when_hidden -q`
Expected: FAIL — `assert <old timestamp> > <same old timestamp>` is False

- [ ] **Step 3: Implement the touch**

In `server/tournaments.py`, add the import near the top (after `import
difflib`):

```python
from datetime import datetime, timezone
```

Then in `import_tournament`, right after the line
`collector = await _get_or_create_collector(payload.kingdom, payload.clan, user.id, db)`:

```python
    collector = await _get_or_create_collector(payload.kingdom, payload.clan, user.id, db)
    if collector.ancient_hidden_at is not None:
        collector.ancient_hidden_at = datetime.now(timezone.utc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_tournaments.py -q`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add server/tournaments.py server/tests/test_tournaments.py
git commit -m "feat(ancients): reset hidden-retention timer on tournament roster import"
```

---

## Task 3: Touch `ancient_hidden_at` on quota calculation

**Files:**
- Modify: `server/ancients_dashboard.py` (`calculate`, currently ~line 320)
- Test: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `ChestCollector.ancient_hidden_at` (Task 1).

- [ ] **Step 1: Write the failing test**

Add to `server/tests/test_ancients_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_calculate_touches_ancient_hidden_at_when_hidden(db_session):
    user, token = await _create_user_with_token(db_session, "calctouch1@test.com")
    collector = await _create_collector(db_session, user.id, slug="calc-touch-1")
    collector.ancient_hidden = True
    collector.ancient_hidden_at = datetime.now(timezone.utc) - timedelta(days=55)
    await db_session.commit()
    old_touch = collector.ancient_hidden_at

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/calc-touch-1/calculate",
            json={"strategy": "A", "summon_levels": [81], "amplification_coef": 1.0,
                  "officer_count": 1, "veteran_count": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    await db_session.refresh(collector)
    assert collector.ancient_hidden_at > old_touch
```

(This test needs `from datetime import timedelta` too — the file already
imports `datetime`/`timezone` from Task 1's step, if `timedelta` is missing
add it to the same import line.)

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancients_dashboard.py::test_calculate_touches_ancient_hidden_at_when_hidden -q`
Expected: FAIL — `assert <old timestamp> > <same old timestamp>` is False

- [ ] **Step 3: Implement the touch**

In `server/ancients_dashboard.py`, in the `calculate` handler, right after
`collector = await _get_own_collector(db, slug, user)`:

```python
    collector = await _get_own_collector(db, slug, user)
    if collector.ancient_hidden_at is not None:
        collector.ancient_hidden_at = datetime.now(timezone.utc)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancients_dashboard.py -q`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "feat(ancients): reset hidden-retention timer on quota calculation"
```

---

## Task 4: New `ancient_retention.py` — the 60-day purge tick

**Files:**
- Create: `server/ancient_retention.py`
- Create: `server/tests/test_ancient_retention.py`

**Interfaces:**
- Consumes: `ChestCollector.ancient_hidden_at` (Task 1), models `AncientRoster`,
  `AncientNameMapping`, `AncientCalculation`, `AncientEditor`,
  `AncientInviteCode`, `Chest`, `PlayerAlias` (all in `server/models.py`,
  already exist), `database.AsyncSessionLocal`.
- Produces: `run_ancient_retention_tick(db: AsyncSession) -> int` (returns
  count of purged collectors), `ensure_background_tasks() -> None` (Task 5
  wires this into `main.py`).

- [ ] **Step 1: Write the failing tests**

Create `server/tests/test_ancient_retention.py`:

```python
"""Tests for ancient_retention.py — inactivity-based purge of Ancient-only
tables for hidden collectors. Chest/PlayerAlias/ChestCollector must survive."""
import os
import sys
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import select

from models import (
    AncientCalculation, AncientNameMapping, AncientRoster, Chest,
    ChestCollector, PlayerAlias,
)
from ancient_retention import run_ancient_retention_tick


async def _make_collector(db, **overrides):
    defaults = dict(kingdom="K1", clan="ClanA", user_id=1,
                    slug=f"slug-{datetime.utcnow().timestamp()}")
    defaults.update(overrides)
    c = ChestCollector(**defaults)
    db.add(c)
    await db.flush()
    return c


@pytest.mark.asyncio
async def test_tick_ignores_collector_hidden_recently(db_session):
    collector = await _make_collector(
        db_session, slug="recent-hide", ancient_hidden=True,
        ancient_hidden_at=datetime.now(timezone.utc) - timedelta(days=10),
    )
    db_session.add(AncientRoster(collector_id=collector.id, player_name="P1", place=1, points=10))
    await db_session.commit()

    purged = await run_ancient_retention_tick(db_session)

    assert purged == 0
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_tick_ignores_visible_collector(db_session):
    collector = await _make_collector(
        db_session, slug="visible-1", ancient_hidden=False, ancient_hidden_at=None,
    )
    db_session.add(AncientRoster(collector_id=collector.id, player_name="P1", place=1, points=10))
    await db_session.commit()

    purged = await run_ancient_retention_tick(db_session)

    assert purged == 0
    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_tick_purges_ancient_tables_for_stale_hidden_collector(db_session):
    collector = await _make_collector(
        db_session, slug="stale-hide", ancient_hidden=True,
        ancient_hidden_at=datetime.now(timezone.utc) - timedelta(days=61),
    )
    db_session.add(AncientRoster(collector_id=collector.id, player_name="P1", place=1, points=10))
    db_session.add(AncientNameMapping(collector_id=collector.id, raw_ocr_name="p1", canonical_name="P1"))
    db_session.add(AncientCalculation(
        collector_id=collector.id, strategy="A", summon_levels=[81],
        amplification_coef=1.0, officer_count=1, veteran_count=0,
        total_quota_millions=1.0, result_json={},
    ))
    db_session.add(Chest(
        collector_id=collector.id, chest_type_raw="Epic", chest_type_canonical="Epic",
        sender_raw="P1", sender_canonical="P1", collected_at=datetime.utcnow(),
    ))
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="p1raw", canonical_name="P1"))
    await db_session.commit()

    purged = await run_ancient_retention_tick(db_session)

    assert purged == 1
    assert (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all() == []
    assert (await db_session.execute(
        select(AncientNameMapping).where(AncientNameMapping.collector_id == collector.id)
    )).scalars().all() == []
    assert (await db_session.execute(
        select(AncientCalculation).where(AncientCalculation.collector_id == collector.id)
    )).scalars().all() == []
    assert len((await db_session.execute(
        select(Chest).where(Chest.collector_id == collector.id)
    )).scalars().all()) == 1
    assert len((await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()) == 1
    await db_session.refresh(collector)
    assert collector.ancient_hidden_at is None
    assert collector.ancient_hidden is True


def test_app_startup_schedules_ancient_retention_background_task(monkeypatch):
    import ancient_retention
    calls = []
    monkeypatch.setattr(ancient_retention, "ensure_background_tasks", lambda: calls.append(True))

    from starlette.testclient import TestClient
    from main import app
    with TestClient(app) as client:
        client.get("/version/latest")

    assert calls == [True]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancient_retention.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'ancient_retention'` (all
5 tests fail on collection)

- [ ] **Step 3: Create `server/ancient_retention.py`**

```python
"""
ancient_retention.py — авто-очистка данных «Древнего» для скрытых
неиспользуемых коллекторов.

Коллектор общий с Сундуками (ChestCollector), поэтому здесь удаляются ТОЛЬКО
таблицы Древнего (AncientRoster/AncientNameMapping/AncientCalculation/
AncientEditor/AncientInviteCode) — Chest, PlayerAlias и сам ChestCollector не
трогаются. Спека:
docs/superpowers/specs/2026-07-01-ancient-collector-retention-design.md

Таймер (ChestCollector.ancient_hidden_at) взводится при скрытии
(PATCH .../ancient-visibility {hidden:true}), сбрасывается в NULL при показе,
и сдвигается на текущий момент любой активностью (импорт ростера турнира,
расчёт квоты) пока коллектор скрыт — см. tournaments.py и
ancients_dashboard.py.
"""
import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from database import AsyncSessionLocal
from models import (
    AncientCalculation, AncientEditor, AncientInviteCode,
    AncientNameMapping, AncientRoster, ChestCollector,
)

HIDDEN_RETENTION_DAYS = 60      # 2 месяца
RETENTION_TICK_SEC     = 86400  # раз в сутки

logger = logging.getLogger(__name__)

_retention_task: asyncio.Task | None = None


async def purge_one(db: AsyncSession, collector: ChestCollector) -> None:
    cid = collector.id
    await db.execute(delete(AncientRoster).where(AncientRoster.collector_id == cid))
    await db.execute(delete(AncientNameMapping).where(AncientNameMapping.collector_id == cid))
    await db.execute(delete(AncientCalculation).where(AncientCalculation.collector_id == cid))
    await db.execute(delete(AncientEditor).where(AncientEditor.collector_id == cid))
    await db.execute(delete(AncientInviteCode).where(AncientInviteCode.collector_id == cid))
    collector.ancient_hidden_at = None


async def run_ancient_retention_tick(db: AsyncSession) -> int:
    """Чистит данные Древнего для коллекторов, скрытых >= HIDDEN_RETENTION_DAYS
    без активности. Возвращает количество очищенных коллекторов."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=HIDDEN_RETENTION_DAYS)
    collectors = (await db.execute(
        select(ChestCollector).where(
            ChestCollector.ancient_hidden_at.is_not(None),
            ChestCollector.ancient_hidden_at < cutoff,
        )
    )).scalars().all()
    purged = 0
    for collector in collectors:
        try:
            await purge_one(db, collector)
            await db.commit()
            purged += 1
        except Exception:
            await db.rollback()
            logger.exception(
                "ancient_retention: purge_one failed for collector_id=%s, skipping",
                collector.id,
            )
    return purged


def ensure_background_tasks() -> None:
    """Запускается раз за жизнь процесса из main.py при старте приложения."""
    global _retention_task
    if _retention_task is None or _retention_task.done():
        _retention_task = asyncio.create_task(_retention_loop())


async def _retention_loop() -> None:
    while True:
        await asyncio.sleep(RETENTION_TICK_SEC)
        async with AsyncSessionLocal() as db:
            await run_ancient_retention_tick(db)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancient_retention.py -q`
Expected: 3 of 4 pass; `test_app_startup_schedules_ancient_retention_background_task`
still FAILS with `assert [] == [True]` — `main.py` doesn't call
`ancient_retention.ensure_background_tasks()` yet (that's Task 5).

- [ ] **Step 5: Commit**

```bash
git add server/ancient_retention.py server/tests/test_ancient_retention.py
git commit -m "feat(ancients): add 60-day inactivity purge tick for hidden collectors"
```

---

## Task 5: Wire the new tick into app startup

**Files:**
- Modify: `server/main.py:58,104-106`

**Interfaces:**
- Consumes: `ancient_retention.ensure_background_tasks()` (Task 4).

- [ ] **Step 1: Verify the still-failing test from Task 4**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancient_retention.py::test_app_startup_schedules_ancient_retention_background_task -q`
Expected: FAIL — `assert [] == [True]`

- [ ] **Step 2: Wire it up**

In `server/main.py`, next to the existing `import chest_history` (line 58),
add:

```python
import ancient_retention
```

And in `_start_background_tasks` (lines 104-106), change:

```python
@app.on_event("startup")
async def _start_background_tasks() -> None:
    chest_history.ensure_background_tasks()
```

to:

```python
@app.on_event("startup")
async def _start_background_tasks() -> None:
    chest_history.ensure_background_tasks()
    ancient_retention.ensure_background_tasks()
```

- [ ] **Step 3: Run test to verify it passes**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_ancient_retention.py -q`
Expected: PASS (all 4 tests)

- [ ] **Step 4: Commit**

```bash
git add server/main.py
git commit -m "feat(ancients): start the ancient-retention background tick on app startup"
```

---

## Task 6: Fix `run_stopped_collector_tick` to also clean up Ancient tables

**Files:**
- Modify: `server/chest_history.py`
- Test: `server/tests/test_chest_history.py`

**Interfaces:**
- Consumes: `AncientRoster`, `AncientNameMapping`, `AncientCalculation`,
  `AncientEditor`, `AncientInviteCode` (all in `server/models.py`).
- Does NOT change: `PlayerAlias` is still deleted exactly as before (see
  Global Constraints — this is deliberate, confirmed with the owner after
  finding the FK constraint issue).

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_chest_history.py` (the file already imports
`select`, `datetime`, `timedelta`, and `Chest`/`ChestCollector`/
`ChestConfiguration`/`ChestSeasonHistory` — add the extra model imports
inside each test function to keep the top-level import list unchanged):

```python
@pytest.mark.asyncio
async def test_stopped_collector_tick_deletes_ancient_tables_too(db_session):
    from models import AncientCalculation, AncientNameMapping, AncientRoster, PlayerAlias
    from chest_history import run_stopped_collector_tick

    collector = await _make_collector(
        db_session, slug="stopped-with-ancient",
        stopped_at=datetime.utcnow() - timedelta(days=91),
    )
    db_session.add(AncientRoster(collector_id=collector.id, player_name="P1", place=1, points=10))
    db_session.add(AncientNameMapping(collector_id=collector.id, raw_ocr_name="p1", canonical_name="P1"))
    db_session.add(AncientCalculation(
        collector_id=collector.id, strategy="A", summon_levels=[81],
        amplification_coef=1.0, officer_count=1, veteran_count=0,
        total_quota_millions=1.0, result_json={},
    ))
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="p1raw", canonical_name="P1"))
    await db_session.commit()

    deleted = await run_stopped_collector_tick(db_session)

    assert deleted == 1
    assert (await db_session.execute(
        select(ChestCollector).where(ChestCollector.id == collector.id)
    )).scalar_one_or_none() is None
    assert (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all() == []
    assert (await db_session.execute(
        select(AncientNameMapping).where(AncientNameMapping.collector_id == collector.id)
    )).scalars().all() == []
    assert (await db_session.execute(
        select(AncientCalculation).where(AncientCalculation.collector_id == collector.id)
    )).scalars().all() == []
    # PlayerAlias behavior unchanged — still deleted with the collector.
    assert (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all() == []


@pytest.mark.asyncio
async def test_stopped_collector_tick_ignores_recent_stop(db_session):
    from chest_history import run_stopped_collector_tick
    collector = await _make_collector(
        db_session, slug="stopped-recent",
        stopped_at=datetime.utcnow() - timedelta(days=10),
    )
    await db_session.commit()

    deleted = await run_stopped_collector_tick(db_session)

    assert deleted == 0
    assert (await db_session.execute(
        select(ChestCollector).where(ChestCollector.id == collector.id)
    )).scalar_one_or_none() is not None
```

- [ ] **Step 2: Run tests to verify the first one fails**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_chest_history.py::test_stopped_collector_tick_deletes_ancient_tables_too tests/test_chest_history.py::test_stopped_collector_tick_ignores_recent_stop -q`
Expected: `test_stopped_collector_tick_deletes_ancient_tables_too` FAILS —
`sqlalchemy.exc.IntegrityError` (deleting `chest_collectors` row while
`ancient_roster`/etc. rows still reference it via FK) or, depending on SQLite
FK enforcement, silently leaves orphan rows and the `AncientRoster` assertion
fails. `test_stopped_collector_tick_ignores_recent_stop` passes already (no
behavior change needed for that path).

- [ ] **Step 3: Fix `run_stopped_collector_tick`**

In `server/chest_history.py`, the top-level import currently reads:

```python
from models import (
    Chest, ChestCollector, ChestConfiguration, ChestSeasonHistory,
    ChestTypeAlias, PlayerAlias,
)
```

Change it to add the Ancient models (keep `PlayerAlias` — its delete stays):

```python
from models import (
    AncientCalculation, AncientEditor, AncientInviteCode, AncientNameMapping,
    AncientRoster, Chest, ChestCollector, ChestConfiguration,
    ChestSeasonHistory, ChestTypeAlias, PlayerAlias,
)
```

Then in `run_stopped_collector_tick`, the deletion block currently reads:

```python
            await db.execute(delete(ChestSeasonHistory).where(ChestSeasonHistory.collector_id == cid))
            await db.execute(delete(Chest).where(Chest.collector_id == cid))
            await db.execute(delete(ChestTypeAlias).where(ChestTypeAlias.collector_id == cid))
            await db.execute(delete(ChestConfiguration).where(ChestConfiguration.collector_id == cid))
            await db.execute(delete(PlayerAlias).where(PlayerAlias.collector_id == cid))
            await db.execute(delete(ChestCollector).where(ChestCollector.id == cid))
```

Change it to (inserting the Ancient deletes before the final `ChestCollector`
delete, after `PlayerAlias`):

```python
            await db.execute(delete(ChestSeasonHistory).where(ChestSeasonHistory.collector_id == cid))
            await db.execute(delete(Chest).where(Chest.collector_id == cid))
            await db.execute(delete(ChestTypeAlias).where(ChestTypeAlias.collector_id == cid))
            await db.execute(delete(ChestConfiguration).where(ChestConfiguration.collector_id == cid))
            await db.execute(delete(PlayerAlias).where(PlayerAlias.collector_id == cid))
            await db.execute(delete(AncientRoster).where(AncientRoster.collector_id == cid))
            await db.execute(delete(AncientNameMapping).where(AncientNameMapping.collector_id == cid))
            await db.execute(delete(AncientCalculation).where(AncientCalculation.collector_id == cid))
            await db.execute(delete(AncientEditor).where(AncientEditor.collector_id == cid))
            await db.execute(delete(AncientInviteCode).where(AncientInviteCode.collector_id == cid))
            await db.execute(delete(ChestCollector).where(ChestCollector.id == cid))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/test_chest_history.py -q`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add server/chest_history.py server/tests/test_chest_history.py
git commit -m "fix(chests): stop orphaning Ancient tables in the 90-day stopped-collector cleanup"
```

---

## Task 7: Full local test suite + deploy (gated on owner approval)

**Files:** none (verification + deployment only)

- [ ] **Step 1: Run the full server test suite**

Run: `cd server && JWT_SECRET_KEY=test_secret_for_local_pytest python -m pytest tests/ -q`
Expected: PASS, no regressions in any other test file (in particular
`test_ancients_dashboard.py`, `test_tournaments.py`, `test_chest_history.py`,
`test_ancient_retention.py` all green together).

- [ ] **Step 2: Do NOT deploy automatically**

Per this project's CLAUDE.md deploy protocol, do not run
`alembic upgrade head` on the GCP database or `git pull` +
`systemctl restart totalhunter` until the owner explicitly asks for it in
this session. When they do, the commands are:

```bash
# On GCP, from /opt/totalhunter:
sudo git clean -fd server/alembic/versions/ && sudo git pull origin main
# then apply the two new migrations (a9h2i3d4e5n6 was added earlier this
# session and is not yet deployed either — both go out together):
cd /opt/totalhunter/server && sudo -u totalhunter env DATABASE_URL=<from override.conf> \
  ../venv/bin/alembic upgrade head
sudo systemctl restart totalhunter
```

No commit for this task — it's a verification + deployment checklist, not a
code change.

---

## Self-Review Notes

- **Spec coverage:** Part 1 (hide/show) — already implemented and tested
  before this plan was written, not repeated here. Part 2 (timer + tick) —
  Tasks 1-5. Part 3 (90-day tick fix) — Task 6, revised per the FK finding
  (PlayerAlias behavior unchanged, only Ancient tables added).
- **Type consistency:** `ancient_hidden_at` is `Optional[datetime]`
  (timezone-aware) everywhere it's touched — Task 1 (model + endpoint),
  Task 2 (tournaments.py), Task 3 (calculate), Task 4 (retention tick read +
  reset to `None`). Function name `run_ancient_retention_tick` and
  `ensure_background_tasks` are used identically in Task 4 (definition),
  Task 5 (wiring), and their respective tests.
- **No placeholders:** every step above has literal file paths, complete code,
  and exact pytest commands with the expected pass/fail reason.
