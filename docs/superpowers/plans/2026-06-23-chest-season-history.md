# Chest Season History Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When a clan's chest-collection season ends, archive a frozen summary snapshot into a new `chest_season_history` table, purge the raw `chests` rows for that period, auto-roll the collector into a new season of the same duration, and let owners/clan members browse past seasons on both the dashboard and the public page. History older than 90 days is purged automatically.

**Architecture:** A new shared `chest_summary.py` module holds the pivot/query logic that both the live `/chests/summary/{slug}` endpoint and the new archiver need (breaks what would otherwise be a circular import between `chests.py` and the new `chest_history.py`). `chest_history.py` holds the archive-or-not decision, the archive operation, retention purge, and two background `asyncio` loops started at FastAPI startup — the same pattern already used by `roy.py`'s `_cleanup_loop`. Two thin read-only endpoint pairs (public in `chests.py`, authenticated in `chest_dashboard.py`) call shared list/detail builder functions in `chest_history.py`. On the frontend, the existing inline table JSX in `ChestSummaryPage.jsx` is extracted into a reusable `ChestSummaryTable` component so both the live view and a new "History" tab (added to both the public page and the dashboard's `ChestsPage.jsx`) render through the same code path.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, PostgreSQL (Alembic migration) / SQLite (pytest), React (no test framework on the frontend — manual `npm run build` + visual check on deploy).

## Global Constraints

- Season auto-close/re-open trigger is independent per `chest_collectors` row — never a single global timer for all clans (owner confirmed).
- `PATCH /chests/{slug}/season` (existing manual "Запустить сезон" button) must remain a pure field-update with **no** archiving side effect, even when the admin re-applies the same dates the auto-tick already rolled forward to (owner confirmed invariant).
- Any comparison involving `period_end`/`period_start`/`collected_at` must use literal (naive) datetime math, mirroring the already-fixed frontend bug (see `ANTI-PATTERNS.md` "Время на публичной странице сундуков") — **never** compare an aware Postgres-returned timestamp against a real UTC-aware `datetime.now(timezone.utc)` directly, or the same +3h-class bug reappears server-side.
- `summary_json` and the target snapshots freeze the season's numbers forever — they must never be recomputed from live `ChestConfiguration`/`chest_collectors.target_points` after archiving (owner-approved design rationale in the spec).
- Retention: history rows are deleted 90 days after `closed_at`, not after `period_end`.

---

## Task 1: `chest_season_history` table — model + migration

**Files:**
- Modify: `server/models.py` (add `ChestSeasonHistory` class, after `Chest` class around line 428)
- Create: `server/alembic/versions/h1s2t3o4r5y6_add_chest_season_history.py`

**Interfaces:**
- Produces: `ChestSeasonHistory` model with columns `id, collector_id, period_start, period_end, target_points_snapshot, target_chests_snapshot, summary_json, closed_at`. Later tasks import this from `models`.

- [ ] **Step 1: Add the model to `server/models.py`**

Insert immediately after the `Chest` class (after line 428, before the blank-line gap that currently precedes `chest_collectors.__table_args__` block — i.e. right after the `Chest` class body ends):

```python
class ChestSeasonHistory(Base):
    """Архив закрытого сезона сборщика сундуков — готовый снимок итогов и целей на
    момент закрытия. Не пересчитывается при будущих изменениях ChestConfiguration
    или chest_collectors.target_points/target_chests — числа зафиксированы навсегда."""
    __tablename__ = "chest_season_history"

    id                      = Column(Integer, primary_key=True)
    collector_id            = Column(Integer, ForeignKey("chest_collectors.id"),
                                     nullable=False, index=True)
    period_start            = Column(TIMESTAMP(timezone=True), nullable=False)
    period_end              = Column(TIMESTAMP(timezone=True), nullable=False)
    target_points_snapshot  = Column(Integer, nullable=True)
    target_chests_snapshot  = Column(Integer, nullable=True)
    summary_json            = Column(JSON, nullable=False)
    closed_at               = Column(TIMESTAMP(timezone=True), nullable=False,
                                     server_default=func.now())
```

- [ ] **Step 2: Verify the model loads (SQLite test DB creates it automatically)**

Run: `cd server && python -c "from models import ChestSeasonHistory; print(ChestSeasonHistory.__tablename__)"`
Expected output: `chest_season_history`

- [ ] **Step 3: Find the current Alembic head**

Run: `cd server && python -m alembic heads`
Expected output: `s1e2a3s4o5n6 (head)`

- [ ] **Step 4: Write the migration**

Create `server/alembic/versions/h1s2t3o4r5y6_add_chest_season_history.py`:

```python
"""add chest_season_history table

Revision ID: h1s2t3o4r5y6
Revises: s1e2a3s4o5n6
Create Date: 2026-06-23

Frozen per-season snapshot — summary_json + target snapshots never get
recomputed after insert. Raw chests rows for an archived period are deleted
by the application code (chest_history.py), not by this migration.
"""
from alembic import op
import sqlalchemy as sa

revision      = 'h1s2t3o4r5y6'
down_revision = 's1e2a3s4o5n6'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.create_table(
        'chest_season_history',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('collector_id', sa.Integer(),
                  sa.ForeignKey('chest_collectors.id'), nullable=False),
        sa.Column('period_start', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('period_end', sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column('target_points_snapshot', sa.Integer(), nullable=True),
        sa.Column('target_chests_snapshot', sa.Integer(), nullable=True),
        sa.Column('summary_json', sa.JSON(), nullable=False),
        sa.Column('closed_at', sa.TIMESTAMP(timezone=True), nullable=False,
                  server_default=sa.text('now()')),
    )
    op.create_index('ix_chest_season_history_collector_id',
                    'chest_season_history', ['collector_id'])


def downgrade() -> None:
    op.drop_index('ix_chest_season_history_collector_id',
                  table_name='chest_season_history')
    op.drop_table('chest_season_history')
```

- [ ] **Step 5: Verify the new head**

Run: `cd server && python -m alembic heads`
Expected output: `h1s2t3o4r5y6 (head)`

- [ ] **Step 6: Commit**

```bash
git add server/models.py server/alembic/versions/h1s2t3o4r5y6_add_chest_season_history.py
git commit -m "feat(chests): add chest_season_history table for season archival"
```

---

## Task 2: Extract shared summary logic into `chest_summary.py`

**Why this task exists:** `chests.py`'s `_pivot_summary` and the row-querying code inside `get_chest_summary` need to be reused by the new archiver (Task 3). The archiver also needs functions that will themselves be imported back into `chests.py` for the history endpoints (Task 5) — importing `chest_history` from `chests.py` while `chest_history` imports from `chests.py` would be a circular import. Pulling the shared logic into a third module with no dependency on either breaks the cycle.

**Files:**
- Create: `server/chest_summary.py`
- Modify: `server/chests.py:201-329` (replace `_pivot_summary` + the query-building body of `get_chest_summary` with calls into `chest_summary.py`)
- Test: `server/tests/test_chests.py` (no new tests — existing summary tests are the regression check)

**Interfaces:**
- Produces: `pivot_summary(kingdom: str, clan: str, rows) -> dict` and `async def query_summary_rows(db: AsyncSession, collector: ChestCollector, period_start, period_end) -> Sequence[Row]` in `chest_summary.py`. Task 3 (`chest_history.py`) and Task 5 (history endpoints) both import these.

- [ ] **Step 1: Run the existing test suite to capture the baseline (must already be green)**

Run: `cd server && python -m pytest tests/test_chests.py -v`
Expected: all tests pass (this file has ~30 tests covering `_pivot_summary`/`get_chest_summary` behavior in depth — they are the regression safety net for this refactor, no new tests needed).

- [ ] **Step 2: Create `server/chest_summary.py`**

```python
"""
chest_summary.py — shared pivot/query logic for chest summaries.

Used by both the live GET /chests/summary/{slug} endpoint (chests.py) and the
season archiver (chest_history.py). Lives in its own module — neither of those
two may import from the other without creating a circular import, since
chests.py needs chest_history.py's history endpoints helpers and
chest_history.py needs this module's summary-building logic.
"""
from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from models import Chest, ChestConfiguration, ChestCollector, ChestLocalization, ChestTypeAlias, PlayerAlias


def pivot_summary(kingdom: str, clan: str, rows) -> dict:
    """rows: iterable of (sender, chest_type_en, display_name, points_per_unit,
    counts_toward_quota, count).

    chest_type_en is used as the internal dedup/grouping key (stable, language-
    independent) — display_name is only substituted in at the very end, so two
    different chest types that happen to share an identical translation can never be
    merged into one row by mistake.
    """
    chest_type_order: list[str] = []
    seen_types = set()
    display_names: dict[str, str] = {}
    per_player: dict[str, dict[str, int]] = {}
    player_points: dict[str, int] = {}
    player_quota: dict[str, int] = {}
    totals: dict[str, int] = {}
    grand_total = 0
    total_points = 0

    for sender, chest_type_en, display_name, points, counts_toward_quota, count in rows:
        if chest_type_en not in seen_types:
            seen_types.add(chest_type_en)
            chest_type_order.append(chest_type_en)
            display_names[chest_type_en] = display_name
        per_player.setdefault(sender, {})
        per_player[sender][chest_type_en] = per_player[sender].get(chest_type_en, 0) + count
        player_points[sender] = player_points.get(sender, 0) + count * points
        if counts_toward_quota:
            player_quota[sender] = player_quota.get(sender, 0) + count
        totals[chest_type_en] = totals.get(chest_type_en, 0) + count
        grand_total += count
        total_points += count * points

    chest_type_order_sorted = sorted(
        seen_types, key=lambda t: (-totals[t], display_names[t])
    )
    chest_types = [display_names[t] for t in chest_type_order_sorted]
    players = []
    for sender, counts_by_en in per_player.items():
        counts = {display_names[t]: c for t, c in counts_by_en.items()}
        players.append({
            "name": sender,
            "counts": counts,
            "total": sum(counts_by_en.values()),
            "points": player_points[sender],
            "quota_chests": player_quota.get(sender, 0),
        })
    players.sort(key=lambda p: (-p["points"], p["name"]))

    totals_out = {display_names[t]: c for t, c in totals.items()}
    totals_out["grand_total"] = grand_total
    totals_out["total_points"] = total_points

    return {
        "kingdom": kingdom,
        "clan": clan,
        "chest_types": chest_types,
        "players": players,
        "totals": totals_out,
    }


async def query_summary_rows(db: AsyncSession, collector: ChestCollector,
                             period_start, period_end):
    sender_expr = func.coalesce(PlayerAlias.canonical_name, Chest.sender_raw)
    chest_type_expr = func.coalesce(ChestTypeAlias.catalog_id, Chest.chest_type_raw)
    display_expr = func.coalesce(ChestConfiguration.custom_name,
                                 ChestLocalization.display_text, chest_type_expr)

    rows_query = (
        select(sender_expr, chest_type_expr, display_expr, ChestConfiguration.points,
               ChestConfiguration.counts_toward_quota, func.count())
        .select_from(Chest)
        .outerjoin(
            PlayerAlias,
            and_(PlayerAlias.collector_id == Chest.collector_id,
                 PlayerAlias.raw_name == Chest.sender_raw),
        )
        .outerjoin(
            ChestTypeAlias,
            and_(ChestTypeAlias.collector_id == Chest.collector_id,
                 ChestTypeAlias.raw_type == Chest.chest_type_raw),
        )
        .join(
            ChestConfiguration,
            and_(ChestConfiguration.collector_id == Chest.collector_id,
                 ChestConfiguration.catalog_id == chest_type_expr,
                 ChestConfiguration.is_in_pattern.is_(True)),
        )
        .outerjoin(
            ChestLocalization,
            and_(ChestLocalization.canonical_type == chest_type_expr,
                 ChestLocalization.language == collector.language),
        )
        .where(Chest.collector_id == collector.id)
    )
    if period_start is not None:
        rows_query = rows_query.where(Chest.collected_at >= period_start)
    if period_end is not None:
        rows_query = rows_query.where(Chest.collected_at <= period_end)

    rows_query = rows_query.group_by(sender_expr, chest_type_expr, display_expr,
                                     ChestConfiguration.points,
                                     ChestConfiguration.counts_toward_quota)
    return (await db.execute(rows_query)).all()
```

- [ ] **Step 3: Rewire `server/chests.py` to use the new module**

In `server/chests.py`, remove the `_pivot_summary` function (lines 201-260) and the query-building body inside `get_chest_summary` (lines 271-316), replacing the whole `get_chest_summary` function with:

```python
@router.get("/summary/{slug}")
async def get_chest_summary(slug: str, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")

    rows = await query_summary_rows(db, collector, collector.period_start, collector.period_end)

    updated_at_query = select(func.max(Chest.collected_at)).where(
        Chest.collector_id == collector.id)
    if collector.period_start is not None:
        updated_at_query = updated_at_query.where(Chest.collected_at >= collector.period_start)
    if collector.period_end is not None:
        updated_at_query = updated_at_query.where(Chest.collected_at <= collector.period_end)
    updated_at = (await db.execute(updated_at_query)).scalar_one_or_none()

    result = pivot_summary(collector.kingdom, collector.clan, rows)
    result["updated_at"] = updated_at.isoformat() if updated_at else None
    result["period_start"] = collector.period_start.isoformat() if collector.period_start else None
    result["period_end"] = collector.period_end.isoformat() if collector.period_end else None
    result["timezone_offset_minutes"] = collector.timezone_offset_minutes
    result["targets"] = {
        "points": collector.target_points,
        "chests": collector.target_chests,
    }
    return result
```

And add the import near the top of `chests.py` (next to the existing `from models import (...)` block):

```python
from chest_summary import pivot_summary, query_summary_rows
```

`ChestConfiguration` and `ChestLocalization` are no longer used directly in `chests.py` after this change (they're only used inside `chest_summary.py` now) — remove them from `chests.py`'s `from models import (...)` line if no other code in the file references them. `ChestTypeAlias` and `PlayerAlias` are still used by `_load_aliases`/`_build_chest_rows`, keep those.

- [ ] **Step 4: Run the full regression suite**

Run: `cd server && python -m pytest tests/test_chests.py -v`
Expected: same pass count as Step 1 — all green, identical behavior.

- [ ] **Step 5: Commit**

```bash
git add server/chest_summary.py server/chests.py
git commit -m "refactor(chests): extract pivot_summary/query_summary_rows into chest_summary.py to enable reuse by the season archiver without a circular import"
```

---

## Task 3: Archive logic — `chest_history.py`

**Files:**
- Create: `server/chest_history.py`
- Test: `server/tests/test_chest_history.py`

**Interfaces:**
- Consumes: `pivot_summary`, `query_summary_rows` from `chest_summary.py` (Task 2); `Chest`, `ChestCollector`, `ChestSeasonHistory` from `models.py` (Task 1).
- Produces: `is_due(collector) -> bool`, `async def archive_one(db, collector) -> None`, `async def run_archive_tick(db) -> int`, `async def run_retention_tick(db) -> int`, `async def build_history_list(db, collector_id) -> list[dict]`, `async def build_history_detail(db, collector_id, season_id) -> dict | None`. Tasks 4, 5 import these.

- [ ] **Step 1: Write the failing tests**

Create `server/tests/test_chest_history.py`:

```python
"""Tests for chest_history.py — season archive/rollover, retention, history reads."""
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from sqlalchemy import select

from models import Chest, ChestCollector, ChestConfiguration, ChestSeasonHistory
from chest_history import (
    is_due, archive_one, run_archive_tick, run_retention_tick,
    build_history_list, build_history_detail,
)


async def _make_collector(db, **overrides):
    defaults = dict(
        kingdom="K1", clan="ClanA", user_id=1, slug=f"slug-{datetime.utcnow().timestamp()}",
        timezone_offset_minutes=0, target_points=None, target_chests=None,
    )
    defaults.update(overrides)
    c = ChestCollector(**defaults)
    db.add(c)
    await db.flush()
    return c


async def _add_chest(db, collector, sender, chest_type, collected_at):
    db.add(Chest(
        collector_id=collector.id, chest_type_raw=chest_type, chest_type_canonical=chest_type,
        sender_raw=sender, sender_canonical=sender, collected_at=collected_at,
    ))
    db.add(ChestConfiguration(
        collector_id=collector.id, catalog_id=chest_type, points=10,
        is_in_pattern=True, counts_toward_quota=True,
    ))


@pytest.mark.asyncio
async def test_is_due_false_when_period_end_is_none(db_session):
    collector = await _make_collector(db_session, period_end=None)
    assert is_due(collector) is False


@pytest.mark.asyncio
async def test_is_due_false_when_period_end_in_future(db_session):
    collector = await _make_collector(
        db_session,
        period_start=datetime.utcnow() - timedelta(days=1),
        period_end=datetime.utcnow() + timedelta(days=1),
    )
    assert is_due(collector) is False


@pytest.mark.asyncio
async def test_is_due_true_when_period_end_in_past(db_session):
    collector = await _make_collector(
        db_session,
        period_start=datetime.utcnow() - timedelta(days=15),
        period_end=datetime.utcnow() - timedelta(days=1),
    )
    assert is_due(collector) is True


@pytest.mark.asyncio
async def test_is_due_respects_timezone_offset_at_the_boundary(db_session):
    # period_end is 90 minutes in the "future" by naive UTC, but the clan is at
    # UTC+3 (180 min) -- clan-local "now" is already past period_end.
    collector = await _make_collector(
        db_session,
        timezone_offset_minutes=180,
        period_start=datetime.utcnow() - timedelta(days=13),
        period_end=datetime.utcnow() + timedelta(minutes=90),
    )
    assert is_due(collector) is True


@pytest.mark.asyncio
async def test_archive_one_creates_history_row_with_snapshot(db_session):
    start = datetime.utcnow() - timedelta(days=14)
    end = datetime.utcnow() - timedelta(hours=1)
    collector = await _make_collector(
        db_session, period_start=start, period_end=end,
        target_points=500, target_chests=10,
    )
    await _add_chest(db_session, collector, "Игрок1", "EpicCrypt", start + timedelta(days=1))
    await db_session.commit()

    await archive_one(db_session, collector)
    await db_session.commit()

    history = (await db_session.execute(select(ChestSeasonHistory))).scalars().all()
    assert len(history) == 1
    row = history[0]
    assert row.collector_id == collector.id
    assert row.target_points_snapshot == 500
    assert row.target_chests_snapshot == 10
    assert row.summary_json["players"][0]["name"] == "Игрок1"
    assert row.summary_json["totals"]["total_points"] == 10


@pytest.mark.asyncio
async def test_archive_one_deletes_archived_chests(db_session):
    start = datetime.utcnow() - timedelta(days=14)
    end = datetime.utcnow() - timedelta(hours=1)
    collector = await _make_collector(db_session, period_start=start, period_end=end)
    await _add_chest(db_session, collector, "Игрок1", "EpicCrypt", start + timedelta(days=1))
    await db_session.commit()

    await archive_one(db_session, collector)
    await db_session.commit()

    remaining = (await db_session.execute(
        select(Chest).where(Chest.collector_id == collector.id)
    )).scalars().all()
    assert remaining == []


@pytest.mark.asyncio
async def test_archive_one_rolls_period_forward_by_same_duration(db_session):
    start = datetime.utcnow() - timedelta(days=14)
    end = datetime.utcnow() - timedelta(hours=1)
    collector = await _make_collector(db_session, period_start=start, period_end=end)
    await db_session.commit()

    await archive_one(db_session, collector)
    await db_session.commit()

    assert collector.period_start == end
    assert collector.period_end == end + timedelta(days=14, hours=1)


@pytest.mark.asyncio
async def test_archive_one_handles_empty_season_without_error(db_session):
    start = datetime.utcnow() - timedelta(days=14)
    end = datetime.utcnow() - timedelta(hours=1)
    collector = await _make_collector(db_session, period_start=start, period_end=end)
    await db_session.commit()

    await archive_one(db_session, collector)
    await db_session.commit()

    history = (await db_session.execute(select(ChestSeasonHistory))).scalars().all()
    assert len(history) == 1
    assert history[0].summary_json["players"] == []


@pytest.mark.asyncio
async def test_run_archive_tick_archives_only_due_collectors(db_session):
    due = await _make_collector(
        db_session, slug="due-collector",
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow() - timedelta(hours=1),
    )
    not_due = await _make_collector(
        db_session, slug="not-due-collector",
        period_start=datetime.utcnow() - timedelta(days=1),
        period_end=datetime.utcnow() + timedelta(days=13),
    )
    no_season = await _make_collector(db_session, slug="no-season-collector", period_end=None)
    await db_session.commit()

    archived_count = await run_archive_tick(db_session)

    assert archived_count == 1
    history = (await db_session.execute(select(ChestSeasonHistory))).scalars().all()
    assert len(history) == 1
    assert history[0].collector_id == due.id


@pytest.mark.asyncio
async def test_run_retention_tick_deletes_old_rows_keeps_recent(db_session):
    collector = await _make_collector(db_session)
    await db_session.commit()
    old_row = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=120),
        period_end=datetime.utcnow() - timedelta(days=106),
        summary_json={"players": []},
        closed_at=datetime.utcnow() - timedelta(days=100),
    )
    recent_row = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=20),
        period_end=datetime.utcnow() - timedelta(days=6),
        summary_json={"players": []},
        closed_at=datetime.utcnow() - timedelta(days=5),
    )
    db_session.add_all([old_row, recent_row])
    await db_session.commit()

    deleted_count = await run_retention_tick(db_session)

    assert deleted_count == 1
    remaining = (await db_session.execute(select(ChestSeasonHistory))).scalars().all()
    assert len(remaining) == 1
    assert remaining[0].closed_at == recent_row.closed_at


@pytest.mark.asyncio
async def test_build_history_list_returns_seasons_newest_first(db_session):
    collector = await _make_collector(db_session)
    await db_session.commit()
    older = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=28),
        period_end=datetime.utcnow() - timedelta(days=14),
        summary_json={"totals": {"total_points": 100}, "players": []},
    )
    newer = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow(),
        summary_json={"totals": {"total_points": 200}, "players": []},
    )
    db_session.add_all([older, newer])
    await db_session.commit()

    seasons = await build_history_list(db_session, collector.id)

    assert [s["total_points"] for s in seasons] == [200, 100]


@pytest.mark.asyncio
async def test_build_history_detail_returns_none_for_other_collector(db_session):
    owner = await _make_collector(db_session, slug="owner-collector")
    other = await _make_collector(db_session, slug="other-collector")
    await db_session.commit()
    row = ChestSeasonHistory(
        collector_id=owner.id,
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow(),
        summary_json={"players": []},
    )
    db_session.add(row)
    await db_session.commit()

    detail = await build_history_detail(db_session, other.id, row.id)

    assert detail is None


@pytest.mark.asyncio
async def test_build_history_detail_includes_target_snapshot(db_session):
    collector = await _make_collector(db_session)
    await db_session.commit()
    row = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow(),
        target_points_snapshot=777,
        target_chests_snapshot=8,
        summary_json={"players": [], "totals": {"total_points": 0}},
    )
    db_session.add(row)
    await db_session.commit()

    detail = await build_history_detail(db_session, collector.id, row.id)

    assert detail["targets"] == {"points": 777, "chests": 8}
    assert "period_start" in detail and "period_end" in detail
```

- [ ] **Step 2: Run to verify failure**

Run: `cd server && python -m pytest tests/test_chest_history.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'chest_history'`

- [ ] **Step 3: Write `server/chest_history.py`**

```python
"""
chest_history.py — Архив закрытых сезонов сундуков.

Авто-цикл: каждый chest_collectors с заданным period_end проверяется
независимо (не общий таймер для всех кланов). Когда "время клана"
(utcnow() + timezone_offset_minutes) переваливает за period_end — сезон
архивируется (готовый summary_json + снимок целей) в chest_season_history,
сырые Chest-строки за период удаляются, и сразу открывается новый период
той же длительности.

Сравнение буквальное (naive), без повторного TZ-сдвига — period_end хранится
как буквальные цифры с клиента (как и Chest.collected_at), не настоящий UTC.
См. ANTI-PATTERNS.md "Время на публичной странице сундуков" — тот же класс
бага воспроизводится здесь, если сравнивать через aware datetime.

Отдельный суточный тик удаляет записи chest_season_history старше
RETENTION_DAYS (3 месяца), считая от closed_at (момент архивации), не от
period_end.
"""
import asyncio
from datetime import datetime, timedelta

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from chest_summary import pivot_summary, query_summary_rows
from database import AsyncSessionLocal
from models import Chest, ChestCollector, ChestSeasonHistory

ARCHIVE_TICK_SEC   = 300    # 5 минут — сезоны измеряются неделями, чаще не нужно
RETENTION_DAYS     = 90     # 3 месяца хранения истории
RETENTION_TICK_SEC = 86400  # раз в сутки

_archive_task:   asyncio.Task | None = None
_retention_task: asyncio.Task | None = None


def _clan_now(timezone_offset_minutes: int | None) -> datetime:
    return datetime.utcnow() + timedelta(minutes=timezone_offset_minutes or 0)


def _strip_tz(dt: datetime) -> datetime:
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def is_due(collector: ChestCollector) -> bool:
    if collector.period_end is None:
        return False
    return _clan_now(collector.timezone_offset_minutes) >= _strip_tz(collector.period_end)


async def archive_one(db: AsyncSession, collector: ChestCollector) -> None:
    period_start = collector.period_start
    period_end = collector.period_end

    rows = await query_summary_rows(db, collector, period_start, period_end)
    summary = pivot_summary(collector.kingdom, collector.clan, rows)

    db.add(ChestSeasonHistory(
        collector_id=collector.id,
        period_start=period_start,
        period_end=period_end,
        target_points_snapshot=collector.target_points,
        target_chests_snapshot=collector.target_chests,
        summary_json=summary,
    ))
    await db.execute(
        delete(Chest).where(
            Chest.collector_id == collector.id,
            Chest.collected_at >= period_start,
            Chest.collected_at <= period_end,
        )
    )
    duration = period_end - period_start
    collector.period_start = period_end
    collector.period_end = period_end + duration


async def run_archive_tick(db: AsyncSession) -> int:
    """Проходит по всем коллекторам с заданным period_end, архивирует просроченные.
    Возвращает количество заархивированных сезонов."""
    collectors = (await db.execute(
        select(ChestCollector).where(ChestCollector.period_end.is_not(None))
    )).scalars().all()
    archived = 0
    for collector in collectors:
        if is_due(collector):
            await archive_one(db, collector)
            archived += 1
    if archived:
        await db.commit()
    return archived


async def run_retention_tick(db: AsyncSession) -> int:
    cutoff = datetime.utcnow() - timedelta(days=RETENTION_DAYS)
    result = await db.execute(
        delete(ChestSeasonHistory).where(ChestSeasonHistory.closed_at < cutoff)
    )
    await db.commit()
    return result.rowcount or 0


async def build_history_list(db: AsyncSession, collector_id: int) -> list[dict]:
    rows = (await db.execute(
        select(ChestSeasonHistory)
        .where(ChestSeasonHistory.collector_id == collector_id)
        .order_by(ChestSeasonHistory.period_end.desc())
    )).scalars().all()
    return [
        {
            "id": r.id,
            "period_start": r.period_start.isoformat(),
            "period_end": r.period_end.isoformat(),
            "total_points": r.summary_json.get("totals", {}).get("total_points", 0),
        }
        for r in rows
    ]


async def build_history_detail(db: AsyncSession, collector_id: int,
                               season_id: int) -> dict | None:
    season = (await db.execute(
        select(ChestSeasonHistory).where(
            ChestSeasonHistory.id == season_id,
            ChestSeasonHistory.collector_id == collector_id,
        )
    )).scalar_one_or_none()
    if not season:
        return None
    result = dict(season.summary_json)
    result["period_start"] = season.period_start.isoformat()
    result["period_end"] = season.period_end.isoformat()
    result["targets"] = {
        "points": season.target_points_snapshot,
        "chests": season.target_chests_snapshot,
    }
    return result


def ensure_background_tasks() -> None:
    """Запускается раз за жизнь процесса из main.py при старте приложения."""
    global _archive_task, _retention_task
    if _archive_task is None or _archive_task.done():
        _archive_task = asyncio.create_task(_archive_loop())
    if _retention_task is None or _retention_task.done():
        _retention_task = asyncio.create_task(_retention_loop())


async def _archive_loop() -> None:
    while True:
        await asyncio.sleep(ARCHIVE_TICK_SEC)
        async with AsyncSessionLocal() as db:
            await run_archive_tick(db)


async def _retention_loop() -> None:
    while True:
        await asyncio.sleep(RETENTION_TICK_SEC)
        async with AsyncSessionLocal() as db:
            await run_retention_tick(db)
```

- [ ] **Step 4: Run to verify all pass**

Run: `cd server && python -m pytest tests/test_chest_history.py -v`
Expected: all tests PASS

- [ ] **Step 5: Commit**

```bash
git add server/chest_history.py server/tests/test_chest_history.py
git commit -m "feat(chests): season archive/rollover, 90-day retention, and history list/detail builders"
```

---

## Task 4: Wire background tasks into `main.py`

**Files:**
- Modify: `server/main.py` (add startup event after `app.include_router(...)` block, around line 92)
- Test: `server/tests/test_chest_history.py` (append one test using TestClient lifespan)

**Interfaces:**
- Consumes: `ensure_background_tasks` from `chest_history.py` (Task 3).

- [ ] **Step 1: Write the failing test**

Append to `server/tests/test_chest_history.py`:

```python
@pytest.mark.asyncio
async def test_app_startup_schedules_archive_background_tasks(monkeypatch):
    import chest_history
    calls = []
    monkeypatch.setattr(chest_history, "ensure_background_tasks", lambda: calls.append(True))

    from httpx import AsyncClient, ASGITransport
    from main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.get("/version/latest")

    assert calls == [True]
```

- [ ] **Step 2: Run to verify it fails**

Run: `cd server && python -m pytest tests/test_chest_history.py::test_app_startup_schedules_archive_background_tasks -v`
Expected: FAIL — `ensure_background_tasks` was never called (no startup hook exists yet)

- [ ] **Step 3: Add the startup event in `server/main.py`**

Add the import next to the other router imports (after line 50, `from chest_dashboard import router as chest_dashboard_router`):

```python
from chest_history import ensure_background_tasks
```

Add the startup hook right after the `app.include_router(chest_dashboard_router)` line (line 92):

```python
@app.on_event("startup")
async def _start_background_tasks() -> None:
    ensure_background_tasks()
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd server && python -m pytest tests/test_chest_history.py -v`
Expected: all PASS, including the new startup test

- [ ] **Step 5: Run the full test suite to check nothing else broke**

Run: `cd server && python -m pytest -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add server/main.py server/tests/test_chest_history.py
git commit -m "feat(chests): start season-archive and retention background loops on app startup"
```

---

## Task 5: Public + dashboard history endpoints

**Files:**
- Modify: `server/chests.py` (add two `GET` routes near the end of the file, after `get_chest_summary`)
- Modify: `server/chest_dashboard.py` (add two `GET` routes after the `update_season_settings` endpoint)
- Test: `server/tests/test_chests.py` (public endpoints)
- Test: `server/tests/test_chest_dashboard.py` (authenticated endpoints)

**Interfaces:**
- Consumes: `build_history_list`, `build_history_detail` from `chest_history.py` (Task 3); `_get_own_collector` already defined in `chest_dashboard.py`.

- [ ] **Step 1: Write the failing public-endpoint tests**

Append to `server/tests/test_chests.py`:

```python
@pytest.mark.asyncio
async def test_history_list_unknown_slug_returns_404():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/api/v1/chests/history/does-not-exist")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_history_list_returns_archived_seasons(db_session):
    from datetime import datetime, timedelta
    from models import ChestCollector, ChestSeasonHistory
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=1, slug="hist-public-1")
    db_session.add(collector)
    await db_session.flush()
    db_session.add(ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow(),
        summary_json={"totals": {"total_points": 555}, "players": []},
    ))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/history/{collector.slug}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["seasons"]) == 1
    assert body["seasons"][0]["total_points"] == 555


@pytest.mark.asyncio
async def test_history_detail_unknown_season_returns_404(db_session):
    from models import ChestCollector
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=1, slug="hist-public-2")
    db_session.add(collector)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/history/{collector.slug}/99999")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_history_detail_returns_full_summary(db_session):
    from datetime import datetime, timedelta
    from models import ChestCollector, ChestSeasonHistory
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=1, slug="hist-public-3")
    db_session.add(collector)
    await db_session.flush()
    row = ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow(),
        target_points_snapshot=100,
        summary_json={"totals": {"total_points": 555}, "players": [], "chest_types": []},
    )
    db_session.add(row)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/history/{collector.slug}/{row.id}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["targets"]["points"] == 100
    assert body["totals"]["total_points"] == 555
```

- [ ] **Step 2: Run to verify failure**

Run: `cd server && python -m pytest tests/test_chests.py -k history -v`
Expected: FAIL with 404s from no matching route (currently returns 404 for unknown route shape, but `test_history_list_returns_archived_seasons` will fail because the slug DOES exist yet there's no `/history/` route registered — confirms the route is missing)

- [ ] **Step 3: Add the public routes to `server/chests.py`**

Add the import near the top of `chests.py` (next to `from chest_summary import ...`):

```python
from chest_history import build_history_list, build_history_detail
```

Append at the end of `server/chests.py`:

```python
@router.get("/history/{slug}")
async def list_chest_history(slug: str, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    return {"seasons": await build_history_list(db, collector.id)}


@router.get("/history/{slug}/{season_id}")
async def get_chest_history_detail(slug: str, season_id: int, db: AsyncSession = Depends(get_db)):
    collector = (await db.execute(
        select(ChestCollector).where(ChestCollector.slug == slug)
    )).scalar_one_or_none()
    if not collector:
        raise HTTPException(status_code=404, detail="Collector not found")
    detail = await build_history_detail(db, collector.id, season_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Season not found")
    return detail
```

- [ ] **Step 4: Run to verify the public tests pass**

Run: `cd server && python -m pytest tests/test_chests.py -k history -v`
Expected: all PASS

- [ ] **Step 5: Write the failing dashboard-endpoint tests**

Append to `server/tests/test_chest_dashboard.py` (check the top of that file first for its existing `_create_user`/auth-header helper and reuse it — follow the same pattern as the file's other authenticated tests):

```python
@pytest.mark.asyncio
async def test_dashboard_history_list_requires_ownership(db_session):
    from datetime import datetime, timedelta
    from models import ChestCollector, ChestSeasonHistory

    owner = await _create_user(db_session, "histownerusr0a")
    other = await _create_user(db_session, "histotherusr0a")
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=owner.id, slug="hist-dash-1")
    db_session.add(collector)
    await db_session.flush()
    db_session.add(ChestSeasonHistory(
        collector_id=collector.id,
        period_start=datetime.utcnow() - timedelta(days=14),
        period_end=datetime.utcnow(),
        summary_json={"totals": {"total_points": 42}, "players": []},
    ))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/web/dashboard/chests/{collector.slug}/history",
            headers=_auth_header(other),
        )
    assert resp.status_code == 403

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/web/dashboard/chests/{collector.slug}/history",
            headers=_auth_header(owner),
        )
    assert resp.status_code == 200
    assert resp.json()["seasons"][0]["total_points"] == 42


@pytest.mark.asyncio
async def test_dashboard_history_detail_unknown_season_returns_404(db_session):
    from models import ChestCollector

    owner = await _create_user(db_session, "histownerusr1a")
    collector = ChestCollector(kingdom="K1", clan="ClanA", user_id=owner.id, slug="hist-dash-2")
    db_session.add(collector)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            f"/web/dashboard/chests/{collector.slug}/history/99999",
            headers=_auth_header(owner),
        )
    assert resp.status_code == 404
```

**Note for the implementer:** `test_chest_dashboard.py` already defines `_create_user` and an auth-header helper for its other authenticated tests (e.g. used by the `/season` PATCH tests) — open the file, find the exact helper name (it may be called `_auth_header`, `_token_header`, or similar) and use that exact name instead of guessing; the two test functions above assume it's called `_auth_header(user)` and returns a dict suitable for `headers=`.

- [ ] **Step 6: Run to verify failure**

Run: `cd server && python -m pytest tests/test_chest_dashboard.py -k history -v`
Expected: FAIL — no `/history` route registered under `/web/dashboard/chests`

- [ ] **Step 7: Add the dashboard routes to `server/chest_dashboard.py`**

Add the import near the top (next to the existing `from models import (...)` block):

```python
from chest_history import build_history_list, build_history_detail
```

Append at the end of `server/chest_dashboard.py`:

```python
@router.get("/{slug}/history")
async def get_dashboard_history(slug: str, user: User = Depends(get_web_user),
                                db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    return {"seasons": await build_history_list(db, collector.id)}


@router.get("/{slug}/history/{season_id}")
async def get_dashboard_history_detail(slug: str, season_id: int,
                                       user: User = Depends(get_web_user),
                                       db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    detail = await build_history_detail(db, collector.id, season_id)
    if detail is None:
        raise HTTPException(status_code=404, detail="Season not found")
    return detail
```

- [ ] **Step 8: Run to verify the dashboard tests pass**

Run: `cd server && python -m pytest tests/test_chest_dashboard.py -k history -v`
Expected: all PASS

- [ ] **Step 9: Run the full backend test suite**

Run: `cd server && python -m pytest -v`
Expected: all PASS

- [ ] **Step 10: Commit**

```bash
git add server/chests.py server/chest_dashboard.py server/tests/test_chests.py server/tests/test_chest_dashboard.py
git commit -m "feat(chests): public and authenticated history list/detail endpoints"
```

---

## Task 6: Deploy backend (migration + GCP)

**Files:** none (operational task)

- [ ] **Step 1: Confirm full suite is green**

Run: `cd server && python -m pytest -v`
Expected: all PASS

- [ ] **Step 2: Commit and push to main** (if not already pushed by prior task commits)

```bash
git push origin main
```

- [ ] **Step 3: Deploy to GCP per the project's standard backend deploy procedure**

```bash
gcloud compute ssh totalhunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && cd server && sudo /opt/totalhunter/venv/bin/alembic upgrade head && sudo systemctl restart totalhunter"
```

(Exact venv path / service name — verify against `project_gcp_ssh.md` / `project_build_release.md` memory notes before running; this plan assumes the standard path documented there.)

- [ ] **Step 4: Verify the migration applied and the service is healthy**

```bash
gcloud compute ssh totalhunter-backend --zone=us-central1-f --command="sudo systemctl status totalhunter --no-pager | head -20"
curl -s https://api.total-hunter.com/api/v1/chests/history/does-not-exist
```

Expected: service `active (running)`, curl returns `{"detail":"Collector not found"}` with HTTP 404 (confirms the new route is live).

---

## Task 7: Frontend — extract `ChestSummaryTable` component

**Files:**
- Create: `web/src/components/ChestSummaryTable.jsx`
- Modify: `web/src/pages/ChestSummaryPage.jsx` (remove the extracted JSX/helpers, import and use the new component instead)

**Interfaces:**
- Produces: `<ChestSummaryTable chestTypes={string[]} players={Player[]} targets={{points, chests}} />` — a self-contained table with its own sticky-scroll-sync state. `Player` shape: `{ name, counts: Record<string,number>, points: number, quota_chests: number }`.

- [ ] **Step 1: Create `web/src/components/ChestSummaryTable.jsx`**

```jsx
import { useEffect, useRef, useState } from 'react'

function rowColorClass(player, targets) {
  const ratios = []
  if (targets.points) ratios.push(player.points / targets.points)
  if (targets.chests) ratios.push(player.quota_chests / targets.chests)
  if (ratios.length === 0) return ''
  const ratio = Math.min(...ratios)
  if (ratio >= 1) return 'row-success'
  if (ratio >= 0.5) return ''
  if (ratio > 0) return 'row-lagging'
  return 'row-danger'
}

const POINT_TIERS = [
  { key: '500k', threshold: 500000 },
  { key: '400k', threshold: 400000 },
  { key: '300k', threshold: 300000 },
  { key: '200k', threshold: 200000 },
  { key: '100k', threshold: 100000 },
  { key: '50k', threshold: 50000 },
]

function pointTier(player, targets) {
  if (rowColorClass(player, targets) !== 'row-success') return null
  const tier = POINT_TIERS.find(t => player.points >= t.threshold)
  return tier ? tier.key : null
}

function pointsHitTarget(player, targets) {
  return targets.points != null && player.points >= targets.points
}
function questHitTarget(player, targets) {
  return targets.chests != null && player.quota_chests >= targets.chests
}
function isEpicColumn(typeName) {
  return typeName.includes('Epic')
}

export default function ChestSummaryTable({ chestTypes, players, targets }) {
  const tableWrapRef = useRef(null)
  const topScrollRef = useRef(null)
  const [tableScrollWidth, setTableScrollWidth] = useState(0)

  useEffect(() => {
    if (tableWrapRef.current) setTableScrollWidth(tableWrapRef.current.scrollWidth)
  }, [chestTypes, players])

  function syncTableFromTopScroll() {
    if (tableWrapRef.current && topScrollRef.current) {
      tableWrapRef.current.scrollLeft = topScrollRef.current.scrollLeft
    }
  }
  function syncTopScrollFromTable() {
    if (tableWrapRef.current && topScrollRef.current) {
      topScrollRef.current.scrollLeft = tableWrapRef.current.scrollLeft
    }
  }

  return (
    <>
      <div
        className="public-table-top-scroll"
        ref={topScrollRef}
        onScroll={syncTableFromTopScroll}
      >
        <div style={{ width: tableScrollWidth, height: 1 }} />
      </div>

      <div className="public-table-wrap" ref={tableWrapRef} onScroll={syncTopScrollFromTable}>
        <table className="public-table">
          <thead>
            <tr>
              <th>#</th>
              <th>Player</th>
              <th>Points</th>
              <th className="public-epic-cell">Epic Crypts</th>
              {chestTypes.map(t => (
                <th key={t} className={isEpicColumn(t) ? 'public-epic-cell' : ''}>{t}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {players.map((p, i) => {
              const tier = pointTier(p, targets)
              return (
                <tr key={p.name} className={rowColorClass(p, targets)}>
                  <td>{i + 1}</td>
                  <td title={p.name}>
                    {tier
                      ? <span className={`public-tier-name public-tier-${tier}`}>{p.name}</span>
                      : p.name}
                  </td>
                  <td className={`public-points-cell ${pointsHitTarget(p, targets) ? 'public-cell-hit-target' : ''}`}>
                    {p.points}
                  </td>
                  <td className={[
                    'public-epic-cell',
                    questHitTarget(p, targets) && 'public-cell-hit-target',
                    p.quota_chests === 0 && 'public-cell-zero',
                  ].filter(Boolean).join(' ')}>
                    {p.quota_chests}
                  </td>
                  {chestTypes.map(t => {
                    const value = p.counts[t] || 0
                    return (
                      <td key={t} className={[
                        isEpicColumn(t) && 'public-epic-cell',
                        value === 0 && 'public-cell-zero',
                      ].filter(Boolean).join(' ')}>
                        {value}
                      </td>
                    )
                  })}
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </>
  )
}
```

- [ ] **Step 2: Rewrite `web/src/pages/ChestSummaryPage.jsx` to use the component**

Replace the entire file with:

```jsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchChestSummary } from '../api.js'
import ChestSummaryTable from '../components/ChestSummaryTable.jsx'

function formatRemaining(periodEndIso, offsetMinutes) {
  const [datePart, timePart] = periodEndIso.split('T')
  const [y, mo, d] = datePart.split('-').map(Number)
  const [h, mi, s] = (timePart || '00:00:00').split(':').map(Number)
  const periodEndMillis = Date.UTC(y, mo - 1, d, h, mi, s || 0)
  const clanNowMillis = Date.now() + offsetMinutes * 60000
  const remaining = periodEndMillis - clanNowMillis
  if (remaining <= 0) return 'Сбор завершён'
  const totalMinutes = Math.floor(remaining / 60000)
  const days = Math.floor(totalMinutes / (24 * 60))
  const hours = Math.floor((totalMinutes % (24 * 60)) / 60)
  const minutes = totalMinutes % 60
  return `Осталось: ${days} дн. ${hours} ч. ${minutes} мин.`
}

function CountdownTimer({ periodEnd, offsetMinutes }) {
  const [label, setLabel] = useState(() => formatRemaining(periodEnd, offsetMinutes))

  useEffect(() => {
    setLabel(formatRemaining(periodEnd, offsetMinutes))
    const id = setInterval(() => {
      setLabel(formatRemaining(periodEnd, offsetMinutes))
    }, 60000)
    return () => clearInterval(id)
  }, [periodEnd, offsetMinutes])

  return <span className="public-season-badge public-season-timer">{label}</span>
}

function formatOffsetLabel(offsetMinutes) {
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const abs = Math.abs(offsetMinutes)
  const h = String(Math.floor(abs / 60)).padStart(2, '0')
  const m = String(abs % 60).padStart(2, '0')
  return `${sign}${h}:${m}`
}

function formatUpdatedAt(isoString) {
  const [datePart, timePart] = isoString.split('T')
  const [y, mo, d] = datePart.split('-').map(Number)
  const [h, mi] = (timePart || '00:00:00').split(':').map(Number)
  return `${String(d).padStart(2, '0')}.${String(mo).padStart(2, '0')}.${y} ${String(h).padStart(2, '0')}:${String(mi).padStart(2, '0')}`
}

function formatPeriodPoint(isoString) {
  const [datePart, timePart] = isoString.split('T')
  const [, mo, d] = datePart.split('-').map(Number)
  const [h, mi] = (timePart || '00:00:00').split(':').map(Number)
  return `${String(d).padStart(2, '0')}.${String(mo).padStart(2, '0')} ${String(h).padStart(2, '0')}:${String(mi).padStart(2, '0')}`
}

export default function ChestSummaryPage() {
  const { slug } = useParams()
  const [data, setData] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    fetchChestSummary(slug).then(setData).catch(e => setError(e.message || 'not found'))
  }, [slug])

  if (error) return <div className="page-content">{error}</div>
  if (!data) return <div className="page-content text-muted">...</div>

  const updatedLabel = data.updated_at
    ? formatUpdatedAt(data.updated_at)
    : '—'

  const targets = data.targets || { points: null, chests: null }
  const hasSeasonTargets = targets.points != null || targets.chests != null

  return (
    <div className="page-content">
      <h1 className="public-summary-title">
        <span className="public-kingdom-label">{data.kingdom}/</span>
        <span className="public-clan-label">{data.clan}</span>
      </h1>

      {hasSeasonTargets && (
        <div className="public-season-info">
          <span className="public-season-badge">
            Цель сезона: {targets.points ?? '—'} очков / {targets.chests ?? '—'} Epic-склепов
          </span>
          {data.timezone_offset_minutes != null && (
            <span className="public-season-badge">
              Часовой пояс: UTC{formatOffsetLabel(data.timezone_offset_minutes)}
            </span>
          )}
          {data.period_start && data.period_end && (
            <span className="public-season-badge">
              {formatPeriodPoint(data.period_start)} – {formatPeriodPoint(data.period_end)}
            </span>
          )}
          {data.period_end && (
            <CountdownTimer periodEnd={data.period_end} offsetMinutes={data.timezone_offset_minutes ?? 0} />
          )}
        </div>
      )}

      <div className="public-summary-updated">Последнее обновление: {updatedLabel}</div>
      <div className="public-summary-divider" />

      <ChestSummaryTable chestTypes={data.chest_types} players={data.players} targets={targets} />
    </div>
  )
}
```

- [ ] **Step 3: Build and visually verify no regression**

Run: `cd web && npm run build`
Expected: build succeeds with no errors.

Then manually load a real clan's public page (`https://total-hunter.com/chests/<slug>`, or run `npm run dev` against a clan that exists in the DB) and confirm: sticky header still pins to viewport, left columns still pin, tier shimmer colors still render for 50k+ players, layout is pixel-identical to before this refactor (it is the exact same JSX, just relocated — there is no logic change, only a regression check).

- [ ] **Step 4: Commit**

```bash
git add web/src/components/ChestSummaryTable.jsx web/src/pages/ChestSummaryPage.jsx
git commit -m "refactor(chests): extract ChestSummaryTable component so the public page and the upcoming history view can share one table renderer"
```

---

## Task 8: Frontend — public page "История" tab

**Files:**
- Modify: `web/src/api.js` (add two fetcher functions)
- Modify: `web/src/pages/ChestSummaryPage.jsx` (add tab state + history list/detail rendering)
- Modify: `web/src/styles/theme.css` (add minimal tab styling, reusing existing `chest-tab`/`chest-tabs` class names already defined for the dashboard's tabs — check `ChestsPage.jsx`'s CSS classes first and reuse them verbatim rather than inventing new ones)

**Interfaces:**
- Produces: `fetchChestHistory(slug)` → `Promise<{ seasons: Array<{id, period_start, period_end, total_points}> }>`, `fetchChestHistorySeason(slug, seasonId)` → `Promise<SummaryShape>` in `api.js`.

- [ ] **Step 1: Add fetchers to `web/src/api.js`**

Append after the existing `fetchChestSummary` function:

```js
export async function fetchChestHistory(slug) {
  const res = await fetch(`${BASE}/api/v1/chests/history/${slug}`)
  if (!res.ok) throw new Error('Not found')
  return res.json()
}

export async function fetchChestHistorySeason(slug, seasonId) {
  const res = await fetch(`${BASE}/api/v1/chests/history/${slug}/${seasonId}`)
  if (!res.ok) throw new Error('Not found')
  return res.json()
}
```

- [ ] **Step 2: Add tab state and history rendering to `ChestSummaryPage.jsx`**

In `web/src/pages/ChestSummaryPage.jsx`, update the import line to also pull in the new fetchers:

```jsx
import { fetchChestSummary, fetchChestHistory, fetchChestHistorySeason } from '../api.js'
```

Inside the `ChestSummaryPage` function, add state right after the existing `error` state:

```jsx
const [tab, setTab] = useState('current')
const [history, setHistory] = useState(null)
const [historyError, setHistoryError] = useState('')
const [selectedSeasonId, setSelectedSeasonId] = useState(null)
const [seasonDetail, setSeasonDetail] = useState(null)

useEffect(() => {
  if (tab !== 'history' || history) return
  fetchChestHistory(slug).then(setHistory).catch(e => setHistoryError(e.message || 'error'))
}, [tab, slug, history])

useEffect(() => {
  if (selectedSeasonId == null) return
  setSeasonDetail(null)
  fetchChestHistorySeason(slug, selectedSeasonId).then(setSeasonDetail)
}, [selectedSeasonId, slug])
```

Add the tab bar right after the `<div className="public-summary-divider" />` line and before `<ChestSummaryTable ...>`:

```jsx
<div className="chest-tabs">
  <button
    className={`chest-tab ${tab === 'current' ? 'chest-tab--active' : ''}`}
    onClick={() => setTab('current')}
  >
    Текущий сезон
  </button>
  <button
    className={`chest-tab ${tab === 'history' ? 'chest-tab--active' : ''}`}
    onClick={() => setTab('history')}
  >
    История
  </button>
</div>
```

Replace the final `<ChestSummaryTable ... />` line with conditional rendering based on `tab`:

```jsx
{tab === 'current' && (
  <ChestSummaryTable chestTypes={data.chest_types} players={data.players} targets={targets} />
)}

{tab === 'history' && !selectedSeasonId && (
  <div className="chest-history-list">
    {historyError && <div className="text-muted">{historyError}</div>}
    {!historyError && !history && <div className="text-muted">...</div>}
    {history && history.seasons.length === 0 && (
      <div className="text-muted">Архив пока пуст — сезоны появятся здесь после первого автозакрытия.</div>
    )}
    {history && history.seasons.map(s => (
      <button
        key={s.id}
        className="public-season-badge"
        onClick={() => setSelectedSeasonId(s.id)}
        style={{ display: 'block', marginBottom: 8, cursor: 'pointer' }}
      >
        {formatPeriodPoint(s.period_start)} – {formatPeriodPoint(s.period_end)} · {s.total_points} очков
      </button>
    ))}
  </div>
)}

{tab === 'history' && selectedSeasonId && (
  <div>
    <button className="public-season-badge" onClick={() => { setSelectedSeasonId(null); setSeasonDetail(null) }} style={{ marginBottom: 12, cursor: 'pointer' }}>
      ← Назад к списку сезонов
    </button>
    {!seasonDetail && <div className="text-muted">...</div>}
    {seasonDetail && (
      <ChestSummaryTable
        chestTypes={seasonDetail.chest_types}
        players={seasonDetail.players}
        targets={seasonDetail.targets || { points: null, chests: null }}
      />
    )}
  </div>
)}
```

- [ ] **Step 3: Verify `chest-tab`/`chest-tabs` CSS classes already exist and render acceptably**

Run: `grep -n "chest-tab" web/src/styles/theme.css`
Expected: the rule already exists (added for `ChestsPage.jsx`'s existing tabs) — if it does, no CSS change needed for Step 4. If grep finds nothing, add a minimal rule to `web/src/styles/theme.css` matching the visual style of `public-season-badge` buttons already on the page (border, padding, accent color on `--active`), reusing existing CSS variables (`--elevated`, `--outline`, `--accent`) rather than introducing new colors.

- [ ] **Step 4: Build and manually verify**

Run: `cd web && npm run build`
Expected: build succeeds.

Manually verify on a real or local clan slug: "Текущий сезон" tab shows the live table (identical to before), "История" tab shows an empty-state message (no seasons archived yet, since Task 6 was just deployed and no season has rolled over) — this is expected and correct, not a bug; the real history list will populate once a clan's season actually auto-closes.

- [ ] **Step 5: Commit**

```bash
git add web/src/api.js web/src/pages/ChestSummaryPage.jsx web/src/styles/theme.css
git commit -m "feat(chests): season history tab on the public chest summary page"
```

---

## Task 9: Frontend — dashboard "История" tab

**Files:**
- Modify: `web/src/api.js` (two more fetchers using the authenticated `request` helper)
- Modify: `web/src/pages/ChestsPage.jsx` (add a third per-collector tab alongside the existing `chests`/`players` tabs)

**Interfaces:**
- Produces: `api.dashboardChestsHistory(slug)`, `api.dashboardChestsHistoryDetail(slug, seasonId)` in `api.js`.

- [ ] **Step 1: Add authenticated fetchers to `web/src/api.js`**

Add to the `api` object, after the existing `dashboardChestsPresets` line:

```js
dashboardChestsHistory: (slug) => request('GET', `/web/dashboard/chests/${slug}/history`),
dashboardChestsHistoryDetail: (slug, seasonId) => request('GET', `/web/dashboard/chests/${slug}/history/${seasonId}`),
```

- [ ] **Step 2: Read the existing tab implementation in `ChestsPage.jsx` before editing**

Open `web/src/pages/ChestsPage.jsx` and inspect lines 1-70 and 260-420 (the `setTab`/`activeTab` helpers and the `chest-tabs` JSX block found during planning) to confirm the exact per-collector state shape (`activeTabByCollector`) before adding a third tab — do not guess the field names, copy them exactly from the existing two tabs (`'chests'` and `'players'`).

- [ ] **Step 3: Add a third tab value `'history'` following the exact same pattern as the existing two**

In the `chest-tabs` JSX block (around line 268), add a third button identical in structure to the existing two, with `'history'` as its tab key and `История` as its label.

Add per-collector history state near the other `useState` declarations at the top of the component:

```jsx
const [historyByCollector, setHistoryByCollector] = useState({})
const [seasonDetailByCollector, setSeasonDetailByCollector] = useState({})

async function loadHistory(slug) {
  if (historyByCollector[slug]) return
  const data = await api.dashboardChestsHistory(slug)
  setHistoryByCollector(prev => ({ ...prev, [slug]: data.seasons }))
}

async function loadSeasonDetail(slug, seasonId) {
  const data = await api.dashboardChestsHistoryDetail(slug, seasonId)
  setSeasonDetailByCollector(prev => ({ ...prev, [slug]: { seasonId, data } }))
}
```

Wherever the component currently renders the `chests`/`players` tab bodies conditionally on `activeTab(collector.slug)`, add a third branch:

```jsx
{activeTab(collector.slug) === 'history' && (
  <div>
    {!historyByCollector[collector.slug] && (
      <button onClick={() => loadHistory(collector.slug)}>Загрузить историю</button>
    )}
    {historyByCollector[collector.slug]?.length === 0 && (
      <div className="text-muted">Архив пока пуст.</div>
    )}
    {historyByCollector[collector.slug]?.map(s => (
      <button key={s.id} onClick={() => loadSeasonDetail(collector.slug, s.id)}>
        {s.period_start} – {s.period_end} · {s.total_points} очков
      </button>
    ))}
    {seasonDetailByCollector[collector.slug] && (
      <ChestSummaryTable
        chestTypes={seasonDetailByCollector[collector.slug].data.chest_types}
        players={seasonDetailByCollector[collector.slug].data.players}
        targets={seasonDetailByCollector[collector.slug].data.targets || { points: null, chests: null }}
      />
    )}
  </div>
)}
```

Add the import at the top of `ChestsPage.jsx`:

```jsx
import ChestSummaryTable from '../components/ChestSummaryTable.jsx'
```

- [ ] **Step 4: Build and manually verify**

Run: `cd web && npm run build`
Expected: build succeeds.

Manually log into the dashboard at `/dashboard/chests` with an account that owns a chest collector, click the new "История" tab, click "Загрузить историю", confirm it shows the empty-state message (no real history exists yet until a season auto-closes).

- [ ] **Step 5: Commit**

```bash
git add web/src/api.js web/src/pages/ChestsPage.jsx
git commit -m "feat(chests): season history tab in the chest dashboard cabinet"
```

---

## Task 10: Deploy frontend

**Files:** none (operational task)

- [ ] **Step 1: Push to main** (if not already pushed)

```bash
git push origin main
```

- [ ] **Step 2: Trigger the Vercel deploy hook**

```bash
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
```

- [ ] **Step 3: Wait for READY and re-attach the production alias** (token from `.claude/settings.local.json` → `env.VERCEL_TOKEN`)

```bash
TOKEN="<VERCEL_TOKEN from settings.local.json>"
TEAM="team_CkkRPXdwtRtsL9YCk8n4Fzla"
PROJECT="prj_mWtcb6hJCkl40YLWheeIlxD5NmXj"
until STATE=$(curl -s "https://api.vercel.com/v6/deployments?projectId=$PROJECT&teamId=$TEAM&limit=1" \
  -H "Authorization: Bearer $TOKEN" | grep -o '"state":"[^"]*"' | head -1 | cut -d'"' -f4) \
  && [ "$STATE" = "READY" ]; do echo "State: $STATE"; sleep 10; done
DEP_ID=$(curl -s "https://api.vercel.com/v6/deployments?projectId=$PROJECT&teamId=$TEAM&limit=1" \
  -H "Authorization: Bearer $TOKEN" | grep -o '"uid":"[^"]*"' | head -1 | cut -d'"' -f4)
curl -s -X POST "https://api.vercel.com/v2/deployments/$DEP_ID/aliases?teamId=$TEAM" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"alias":"total-hunter.com"}'
```

- [ ] **Step 4: Manually verify on production**

Visit `https://total-hunter.com/chests/<a real clan slug>` and confirm the "История" tab appears and loads without error (empty list expected, since no real season has auto-closed yet).

---

## Spec coverage check

- Table schema with snapshot + summary_json: Task 1. ✅
- Avoiding circular import / reuse of pivot logic: Task 2. ✅
- Auto-close/archive/rollover per-collector, literal datetime comparison: Task 3. ✅
- Retention 90 days from `closed_at`: Task 3 (`run_retention_tick`). ✅
- Background loops started reliably (not lazy-on-request): Task 4. ✅
- Public + dashboard read endpoints: Task 5. ✅
- Manual "Запустить сезон" button non-interference invariant: already true of existing `update_season_settings` code (verified during planning, no code change needed) — covered implicitly, no new task required since nothing about it changes.
- Frontend reuse of one table renderer for live + history: Task 7. ✅
- History UI on public page and dashboard: Tasks 8, 9. ✅
- Deploys: Tasks 6, 10. ✅
