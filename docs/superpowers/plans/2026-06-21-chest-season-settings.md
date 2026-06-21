# Сундуки — Настройки сезона (1/3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a clan owner configure an optional "season" (timezone offset, period start/end, point/chest targets) and mark specific chest types as counting toward the chest-count quota — all through `/dashboard/chests`, with zero effect on clans that never configure it.

**Architecture:** Five new nullable columns on `ChestCollector` plus one new boolean column on `ChestConfiguration`, added via one Alembic migration. The existing dashboard GET/POST endpoints in `server/chest_dashboard.py` grow to read/write these fields; one new `PATCH .../season` endpoint handles partial updates with date-order validation. The frontend dashboard gains a "Настройки сезона" card and a second toggle-switch column in the existing chest-types table.

**Tech Stack:** FastAPI + SQLAlchemy async (`server/chest_dashboard.py`, `server/models.py`), Alembic migration, React + plain CSS (`web/src/pages/ChestsPage.jsx`), pytest + httpx.

## Global Constraints

- All 5 new `ChestCollector` columns are nullable, no backfill — `NULL` means "season not configured," and nothing else in the system (public page, scoring) reads these fields yet (that's Spec 2/3) — this plan only adds storage + admin CRUD.
- Timezone is stored as a fixed UTC offset in minutes (`timezone_offset_minutes`), never an IANA zone name — no DST handling anywhere in this codebase.
- `counts_toward_quota` on `ChestConfiguration` defaults to `false` (`server_default=text("false")`), consistent with the existing `is_in_pattern` column's style.
- `PATCH .../season` partial-update semantics: a field omitted from the request body (`None` in the Pydantic model) leaves the stored value untouched — there is no way to clear a field back to `NULL` in this version.
- Date validation: compute the *effective* `period_start`/`period_end` (request value if provided, else the value already in the database) and reject with `400` if both are non-null and `effective_end <= effective_start` — this catches both a same-request bad pair and a partial update that conflicts with an already-stored value.
- No new color palette on the frontend — reuse existing `theme.css` variables and the existing `.toggle-switch`/`.input-dark`/`.chest-table` classes.
- All datetime values in this codebase (see `Chest.collected_at` and its existing tests) are handled as naive ISO strings with no UTC offset suffix — follow that exact convention for `period_start`/`period_end` test data and any manual testing, even though the column type is `DateTime(timezone=True)`.

---

### Task 1: Schema — new columns + migration

**Files:**
- Modify: `server/models.py:379-399` (`ChestCollector` class — add 5 columns)
- Modify: `server/models.py:454-468` (`ChestConfiguration` class — add 1 column)
- Create: `server/alembic/versions/s1e2a3s4o5n6_add_chest_season_settings.py`
- Test: `server/tests/test_chest_dashboard.py` (append)

**Interfaces:**
- Produces: `ChestCollector.timezone_offset_minutes: int | None`, `.period_start: datetime | None`, `.period_end: datetime | None`, `.target_points: int | None`, `.target_chests: int | None`. `ChestConfiguration.counts_toward_quota: bool` (defaults `False`). Consumed by every later task in this plan.

- [ ] **Step 1: Write the failing test**

Append to `server/tests/test_chest_dashboard.py` (the `from models import (...)` block at the top already needs `ChestConfiguration` — it's already imported; no import changes needed for this test):

```python
@pytest.mark.asyncio
async def test_collector_and_configuration_persist_new_season_columns(db_session):
    from datetime import datetime
    from models import ChestConfiguration

    user, _ = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="season-columns-slug")
    collector.timezone_offset_minutes = 180
    collector.period_start = datetime.fromisoformat("2026-06-21T00:00:00")
    collector.period_end = datetime.fromisoformat("2026-07-05T00:00:00")
    collector.target_points = 5000
    collector.target_chests = 50
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Epic Crypt 30",
                                      points=80, is_in_pattern=True, counts_toward_quota=True))
    await db_session.commit()

    reloaded = (await db_session.execute(
        select(ChestCollector).where(ChestCollector.slug == "season-columns-slug")
    )).scalar_one()
    assert reloaded.timezone_offset_minutes == 180
    assert reloaded.period_start == datetime.fromisoformat("2026-06-21T00:00:00")
    assert reloaded.period_end == datetime.fromisoformat("2026-07-05T00:00:00")
    assert reloaded.target_points == 5000
    assert reloaded.target_chests == 50

    config = (await db_session.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalar_one()
    assert config.counts_toward_quota is True


@pytest.mark.asyncio
async def test_new_season_columns_default_to_none_and_quota_defaults_to_false(db_session):
    from models import ChestConfiguration

    user, _ = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="season-defaults-slug")
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Rare Crypt 25",
                                      points=20, is_in_pattern=True))
    await db_session.commit()

    reloaded = (await db_session.execute(
        select(ChestCollector).where(ChestCollector.slug == "season-defaults-slug")
    )).scalar_one()
    assert reloaded.timezone_offset_minutes is None
    assert reloaded.period_start is None
    assert reloaded.period_end is None
    assert reloaded.target_points is None
    assert reloaded.target_chests is None

    config = (await db_session.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalar_one()
    assert config.counts_toward_quota is False
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -k season_columns -v`
Expected: FAIL — `AttributeError: 'ChestCollector' object has no attribute 'timezone_offset_minutes'` (the columns don't exist on the model yet).

- [ ] **Step 3: Add the columns to the models**

In `server/models.py`, inside the `ChestCollector` class, right after the `created_at` column (the last line of that class body, currently ending the class at line 399):

```python
    timezone_offset_minutes = Column(Integer, nullable=True)
    period_start            = Column(TIMESTAMP(timezone=True), nullable=True)
    period_end              = Column(TIMESTAMP(timezone=True), nullable=True)
    target_points           = Column(Integer, nullable=True)
    target_chests           = Column(Integer, nullable=True)
```

In the `ChestConfiguration` class, right after the `is_in_pattern` column:

```python
    counts_toward_quota = Column(Boolean, nullable=False, server_default=text("false"))
```

- [ ] **Step 4: Write the Alembic migration**

Create `server/alembic/versions/s1e2a3s4o5n6_add_chest_season_settings.py`:

```python
"""add season settings to chest_collectors, counts_toward_quota to chest_configurations

Revision ID: s1e2a3s4o5n6
Revises: c4d5e6f7g8h9
Create Date: 2026-06-21

All 6 new columns are nullable or have a server_default — existing rows need no
backfill. NULL season fields mean "season not configured" for that collector.
"""
from alembic import op
import sqlalchemy as sa

revision      = 's1e2a3s4o5n6'
down_revision = 'c4d5e6f7g8h9'
branch_labels = None
depends_on    = None


def upgrade() -> None:
    op.add_column('chest_collectors', sa.Column('timezone_offset_minutes', sa.Integer(), nullable=True))
    op.add_column('chest_collectors', sa.Column('period_start', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('chest_collectors', sa.Column('period_end', sa.TIMESTAMP(timezone=True), nullable=True))
    op.add_column('chest_collectors', sa.Column('target_points', sa.Integer(), nullable=True))
    op.add_column('chest_collectors', sa.Column('target_chests', sa.Integer(), nullable=True))
    op.add_column('chest_configurations', sa.Column('counts_toward_quota', sa.Boolean(),
                                                     nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('chest_configurations', 'counts_toward_quota')
    op.drop_column('chest_collectors', 'target_chests')
    op.drop_column('chest_collectors', 'target_points')
    op.drop_column('chest_collectors', 'period_end')
    op.drop_column('chest_collectors', 'period_start')
    op.drop_column('chest_collectors', 'timezone_offset_minutes')
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -v`
Expected: all tests PASS, including the two new ones (tests use `Base.metadata.create_all`, not Alembic, so the model changes alone make these pass — the migration file is exercised separately at deploy time in Task 7, not by pytest).

- [ ] **Step 6: Commit**

```bash
git add server/models.py server/alembic/versions/s1e2a3s4o5n6_add_chest_season_settings.py server/tests/test_chest_dashboard.py
git commit -m "feat(chests): add season settings columns and counts_toward_quota flag"
```

---

### Task 2: Backend — GET dashboard includes season settings

**Files:**
- Modify: `server/chest_dashboard.py:118-128` (`get_dashboard_chests`)
- Test: `server/tests/test_chest_dashboard.py` (append)

**Interfaces:**
- Produces: each collector object in `GET /web/dashboard/chests`'s `"collectors"` array gains 5 keys: `timezone_offset_minutes`, `period_start`, `period_end`, `target_points`, `target_chests` (values mirror the Task 1 model fields; `datetime` values serialize to ISO strings via FastAPI's default JSON encoder, `None` serializes to `null`). Consumed by Task 5/6 (frontend).

- [ ] **Step 1: Write the failing test**

Append to `server/tests/test_chest_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_get_chests_includes_season_settings_fields(db_session):
    from datetime import datetime

    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="season-get-slug")
    collector.timezone_offset_minutes = 180
    collector.period_start = datetime.fromisoformat("2026-06-21T00:00:00")
    collector.period_end = datetime.fromisoformat("2026-07-05T00:00:00")
    collector.target_points = 5000
    collector.target_chests = 50
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    collector_data = resp.json()["collectors"][0]
    assert collector_data["timezone_offset_minutes"] == 180
    assert collector_data["period_start"] == "2026-06-21T00:00:00"
    assert collector_data["period_end"] == "2026-07-05T00:00:00"
    assert collector_data["target_points"] == 5000
    assert collector_data["target_chests"] == 50


@pytest.mark.asyncio
async def test_get_chests_season_settings_are_null_when_unconfigured(db_session):
    user, token = await _create_user_with_token(db_session)
    await _create_collector(db_session, user.id, slug="season-null-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    collector_data = resp.json()["collectors"][0]
    assert collector_data["timezone_offset_minutes"] is None
    assert collector_data["period_start"] is None
    assert collector_data["period_end"] is None
    assert collector_data["target_points"] is None
    assert collector_data["target_chests"] is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -k season_settings_fields -v`
Expected: FAIL — `KeyError: 'timezone_offset_minutes'` (the field isn't in the response dict yet).

- [ ] **Step 3: Add the fields to the response**

In `server/chest_dashboard.py`, inside `get_dashboard_chests`, change:

```python
        result.append({
            "slug": collector.slug, "kingdom": collector.kingdom, "clan": collector.clan,
            "language": collector.language,
            "public_url": f"https://total-hunter.com/chests/{collector.slug}",
            "rows": await _collector_rows(db, collector),
            "player_alias_rows": await _player_alias_rows(db, collector),
            "catalog_options": await _load_catalog_options(db, collector.language),
        })
```

to:

```python
        result.append({
            "slug": collector.slug, "kingdom": collector.kingdom, "clan": collector.clan,
            "language": collector.language,
            "public_url": f"https://total-hunter.com/chests/{collector.slug}",
            "rows": await _collector_rows(db, collector),
            "player_alias_rows": await _player_alias_rows(db, collector),
            "catalog_options": await _load_catalog_options(db, collector.language),
            "timezone_offset_minutes": collector.timezone_offset_minutes,
            "period_start": collector.period_start,
            "period_end": collector.period_end,
            "target_points": collector.target_points,
            "target_chests": collector.target_chests,
        })
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -v`
Expected: all tests PASS, no regressions.

- [ ] **Step 5: Commit**

```bash
git add server/chest_dashboard.py server/tests/test_chest_dashboard.py
git commit -m "feat(chests): include season settings fields in dashboard GET response"
```

---

### Task 3: Backend — PATCH /web/dashboard/chests/{slug}/season

**Files:**
- Modify: `server/chest_dashboard.py:11-12` (imports — add `datetime`), and append the new payload model + route after `update_language` (end of file)
- Test: `server/tests/test_chest_dashboard.py` (append)

**Interfaces:**
- Consumes: `_get_own_collector(db, slug, user)` (existing).
- Produces: `PATCH /web/dashboard/chests/{slug}/season` — body `{"timezone_offset_minutes"?: int, "period_start"?: str (ISO), "period_end"?: str (ISO), "target_points"?: int, "target_chests"?: int}` (all optional), response `{"ok": true}` on success, `400` on bad date ordering, `403` on foreign collector. Consumed by Task 5/6 (frontend, via `api.dashboardChestsSeason`).

- [ ] **Step 1: Write the failing tests**

Append to `server/tests/test_chest_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_patch_season_updates_own_collector(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="season-patch-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/chests/season-patch-slug/season",
            json={"timezone_offset_minutes": 180,
                 "period_start": "2026-06-21T00:00:00",
                 "period_end": "2026-07-05T00:00:00",
                 "target_points": 5000, "target_chests": 50},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    await db_session.refresh(collector)
    assert collector.timezone_offset_minutes == 180
    assert collector.target_points == 5000
    assert collector.target_chests == 50


@pytest.mark.asyncio
async def test_patch_season_partial_update_leaves_other_fields_untouched(db_session):
    from datetime import datetime

    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="season-partial-slug")
    collector.timezone_offset_minutes = 180
    collector.target_points = 5000
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/chests/season-partial-slug/season",
            json={"target_chests": 50},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    await db_session.refresh(collector)
    assert collector.timezone_offset_minutes == 180
    assert collector.target_points == 5000
    assert collector.target_chests == 50


@pytest.mark.asyncio
async def test_patch_season_rejects_end_before_start_same_request(db_session):
    user, token = await _create_user_with_token(db_session)
    await _create_collector(db_session, user.id, slug="season-badorder-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/chests/season-badorder-slug/season",
            json={"period_start": "2026-07-05T00:00:00",
                 "period_end": "2026-06-21T00:00:00"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_patch_season_rejects_new_end_conflicting_with_stored_start(db_session):
    from datetime import datetime

    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="season-conflict-slug")
    collector.period_start = datetime.fromisoformat("2026-06-21T00:00:00")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/chests/season-conflict-slug/season",
            json={"period_end": "2026-06-01T00:00:00"},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_patch_season_rejects_other_users_collector(db_session):
    owner, _ = await _create_user_with_token(db_session, email="seasonowner@example.com")
    intruder, intruder_token = await _create_user_with_token(db_session, email="seasonintruder@example.com")
    await _create_collector(db_session, owner.id, slug="season-protected-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/chests/season-protected-slug/season",
            json={"target_points": 100},
            headers={"Authorization": f"Bearer {intruder_token}"},
        )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -k patch_season -v`
Expected: FAIL — `404 Not Found` (the route doesn't exist yet).

- [ ] **Step 3: Implement the route**

In `server/chest_dashboard.py`, change the import line:

```python
import secrets
from typing import List, Optional
```

to:

```python
import secrets
from datetime import datetime
from typing import List, Optional
```

Then append this block at the end of the file (after `update_language`):

```python
class SeasonSettingsPayload(BaseModel):
    timezone_offset_minutes: Optional[int] = None
    period_start: Optional[datetime] = None
    period_end: Optional[datetime] = None
    target_points: Optional[int] = None
    target_chests: Optional[int] = None


@router.patch("/{slug}/season")
async def update_season_settings(slug: str, payload: SeasonSettingsPayload,
                                  user: User = Depends(get_web_user),
                                  db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)

    effective_start = (payload.period_start if payload.period_start is not None
                       else collector.period_start)
    effective_end = (payload.period_end if payload.period_end is not None
                     else collector.period_end)
    if (effective_start is not None and effective_end is not None
            and effective_end <= effective_start):
        raise HTTPException(status_code=400, detail="period_end must be after period_start")

    if payload.timezone_offset_minutes is not None:
        collector.timezone_offset_minutes = payload.timezone_offset_minutes
    if payload.period_start is not None:
        collector.period_start = payload.period_start
    if payload.period_end is not None:
        collector.period_end = payload.period_end
    if payload.target_points is not None:
        collector.target_points = payload.target_points
    if payload.target_chests is not None:
        collector.target_chests = payload.target_chests

    await db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -v`
Expected: all tests PASS, no regressions.

- [ ] **Step 5: Commit**

```bash
git add server/chest_dashboard.py server/tests/test_chest_dashboard.py
git commit -m "feat(chests): add PATCH /web/dashboard/chests/{slug}/season with date validation"
```

---

### Task 4: Backend — counts_toward_quota toggle on the chest-types table

**Files:**
- Modify: `server/chest_dashboard.py:49-89` (`_collector_rows`), `:131-181` (`RowIn`, `post_dashboard_rows`)
- Test: `server/tests/test_chest_dashboard.py` (append)

**Interfaces:**
- Produces: each row object returned by `_collector_rows` (and therefore each row in `GET /web/dashboard/chests`'s `rows` array) gains a `counts_toward_quota: bool` key. `RowIn` (used by `POST /web/dashboard/chests/rows`) gains `counts_toward_quota: bool = False`, persisted onto the corresponding `ChestConfiguration` row. Consumed by Task 5/6 (frontend toggle column).

- [ ] **Step 1: Write the failing tests**

Append to `server/tests/test_chest_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_get_chests_rows_include_counts_toward_quota(db_session):
    from models import ChestConfiguration, ChestTypeAlias

    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="quota-get-slug")
    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="RawEpic",
                                  catalog_id="Epic Crypt 30"))
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Epic Crypt 30",
                                      points=80, is_in_pattern=True, counts_toward_quota=True))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    rows = resp.json()["collectors"][0]["rows"]
    row = next(r for r in rows if r["catalog_id"] == "Epic Crypt 30")
    assert row["counts_toward_quota"] is True


@pytest.mark.asyncio
async def test_post_rows_persists_counts_toward_quota(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="quota-post-slug")
    db_session.add(ChestTypeCatalog(canonical_type="Epic Crypt 30", pattern="T9", points=80))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/rows",
            json={"collector_slug": "quota-post-slug",
                 "rows": [{"raw_type": "RawEpic", "catalog_id": "Epic Crypt 30",
                           "custom_name": None, "points": 80, "is_in_pattern": True,
                           "counts_toward_quota": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    config = (await db_session.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalar_one()
    assert config.counts_toward_quota is True
```

Add `ChestTypeCatalog` to the test file's imports if not already present at module scope (check the existing `from models import (...)` block at the top of `test_chest_dashboard.py` — it already imports `ChestTypeCatalog`, so no import change is needed here).

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -k counts_toward_quota -v`
Expected: FAIL — `KeyError: 'counts_toward_quota'` on the GET test, and a Pydantic validation pass-through but missing persistence (assertion failure, `config.counts_toward_quota is False` instead of `True`) on the POST test.

- [ ] **Step 3: Implement**

In `server/chest_dashboard.py`, update `_collector_rows`'s two `rows.append(...)` calls (the aliased+configured branch and the config-only branch) to include the new field. Change:

```python
        rows.append({
            "raw_type": alias.raw_type, "catalog_id": alias.catalog_id,
            "custom_name": config.custom_name if config else None,
            "points": config.points if config else 0,
            "is_in_pattern": config.is_in_pattern if config else False,
        })
```

to:

```python
        rows.append({
            "raw_type": alias.raw_type, "catalog_id": alias.catalog_id,
            "custom_name": config.custom_name if config else None,
            "points": config.points if config else 0,
            "is_in_pattern": config.is_in_pattern if config else False,
            "counts_toward_quota": config.counts_toward_quota if config else False,
        })
```

and:

```python
        rows.append({
            "raw_type": None, "catalog_id": config.catalog_id,
            "custom_name": config.custom_name, "points": config.points,
            "is_in_pattern": config.is_in_pattern,
        })
```

to:

```python
        rows.append({
            "raw_type": None, "catalog_id": config.catalog_id,
            "custom_name": config.custom_name, "points": config.points,
            "is_in_pattern": config.is_in_pattern,
            "counts_toward_quota": config.counts_toward_quota,
        })
```

The third `rows.append` (the fully-unmapped raw-type branch) gets the field too — change:

```python
        rows.append({"raw_type": raw_type, "catalog_id": None, "custom_name": None,
                     "points": 0, "is_in_pattern": False})
```

to:

```python
        rows.append({"raw_type": raw_type, "catalog_id": None, "custom_name": None,
                     "points": 0, "is_in_pattern": False, "counts_toward_quota": False})
```

Update `RowIn`:

```python
class RowIn(BaseModel):
    raw_type: Optional[str] = None
    catalog_id: Optional[str] = None
    custom_name: Optional[str] = None
    points: int = 0
    is_in_pattern: bool = False
```

to:

```python
class RowIn(BaseModel):
    raw_type: Optional[str] = None
    catalog_id: Optional[str] = None
    custom_name: Optional[str] = None
    points: int = 0
    is_in_pattern: bool = False
    counts_toward_quota: bool = False
```

Update `post_dashboard_rows`'s `ChestConfiguration` construction:

```python
        if row.catalog_id is not None:
            db.add(ChestConfiguration(collector_id=collector.id, catalog_id=row.catalog_id,
                                      custom_name=row.custom_name, points=row.points,
                                      is_in_pattern=row.is_in_pattern))
```

to:

```python
        if row.catalog_id is not None:
            db.add(ChestConfiguration(collector_id=collector.id, catalog_id=row.catalog_id,
                                      custom_name=row.custom_name, points=row.points,
                                      is_in_pattern=row.is_in_pattern,
                                      counts_toward_quota=row.counts_toward_quota))
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -v`
Expected: all tests PASS, no regressions. Also run `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chests.py -v` to confirm the unrelated public-summary test file is unaffected (it constructs `ChestConfiguration` directly in several tests without `counts_toward_quota`, which must still work since the column defaults to `False`).

- [ ] **Step 5: Commit**

```bash
git add server/chest_dashboard.py server/tests/test_chest_dashboard.py
git commit -m "feat(chests): add counts_toward_quota toggle to dashboard rows GET/POST"
```

---

### Task 5: Frontend — API client + i18n strings

**Files:**
- Modify: `web/src/api.js` (add one function)
- Modify: `web/src/dashboard_content.js` (add keys to the `chests` block)
- Modify: `web/src/dashboard_content.en.js` (add keys to the `chests` block)

**Interfaces:**
- Produces: `api.dashboardChestsSeason(slug, payload)` — `PATCH /web/dashboard/chests/{slug}/season` with `payload` as the request body. Consumed by Task 6.
- Produces new `cx.*` keys: `seasonTitle`, `timezoneLabel`, `periodStartLabel`, `periodEndLabel`, `targetPointsLabel`, `targetChestsLabel`, `saveSeason`, `quotaCol`. Consumed by Task 6.

- [ ] **Step 1: Add the API function**

In `web/src/api.js`, add this line right after `dashboardChestsLang`:

```js
  dashboardChestsSeason: (slug, payload) => request('PATCH', `/web/dashboard/chests/${slug}/season`, payload),
```

- [ ] **Step 2: Add Russian strings**

In `web/src/dashboard_content.js`, inside the `chests: { ... }` block, add after `savePlayerAliases: 'Сохранить имена',`:

```js
    seasonTitle: 'Настройки сезона',
    timezoneLabel: 'Часовой пояс',
    periodStartLabel: 'Начало периода',
    periodEndLabel: 'Конец периода',
    targetPointsLabel: 'Цель (очки)',
    targetChestsLabel: 'Цель (сундуки)',
    saveSeason: 'Сохранить сезон',
    quotaCol: 'Считать в квоту',
```

- [ ] **Step 3: Add English strings**

In `web/src/dashboard_content.en.js`, inside the `chests: { ... }` block, add after `savePlayerAliases: 'Save names',`:

```js
    seasonTitle: 'Season Settings',
    timezoneLabel: 'Timezone',
    periodStartLabel: 'Period Start',
    periodEndLabel: 'Period End',
    targetPointsLabel: 'Target (Points)',
    targetChestsLabel: 'Target (Chests)',
    saveSeason: 'Save Season',
    quotaCol: 'Counts Toward Quota',
```

- [ ] **Step 4: Commit**

```bash
git add web/src/api.js web/src/dashboard_content.js web/src/dashboard_content.en.js
git commit -m "feat(web): add season settings API call and i18n strings"
```

---

### Task 6: Frontend — season settings card + quota toggle column

**Files:**
- Modify: `web/src/pages/ChestsPage.jsx`

**Interfaces:**
- Consumes: `api.dashboardChestsSeason(slug, payload)` (Task 5), `cx.seasonTitle`/`timezoneLabel`/`periodStartLabel`/`periodEndLabel`/`targetPointsLabel`/`targetChestsLabel`/`saveSeason`/`quotaCol` (Task 5), `collector.timezone_offset_minutes`/`period_start`/`period_end`/`target_points`/`target_chests` (Task 2 response fields), `row.counts_toward_quota` (Task 4 response field).

- [ ] **Step 1: Add season-settings local state and helpers**

In `web/src/pages/ChestsPage.jsx`, add a new state hook right after `const [activeTabByCollector, setActiveTabByCollector] = useState({})`:

```jsx
  const [seasonByCollector, setSeasonByCollector] = useState({})
```

In `refresh()`, change:

```jsx
      const nextRows = {}
      const nextPlayerRows = {}
      for (const c of data.collectors) {
        nextRows[c.slug] = c.rows
        nextPlayerRows[c.slug] = c.player_alias_rows
      }
      setRowsByCollector(nextRows)
      setPlayerRowsByCollector(nextPlayerRows)
```

to:

```jsx
      const nextRows = {}
      const nextPlayerRows = {}
      const nextSeason = {}
      for (const c of data.collectors) {
        nextRows[c.slug] = c.rows
        nextPlayerRows[c.slug] = c.player_alias_rows
        nextSeason[c.slug] = {
          timezone_offset_minutes: c.timezone_offset_minutes,
          period_start: c.period_start ? c.period_start.slice(0, 16) : '',
          period_end: c.period_end ? c.period_end.slice(0, 16) : '',
          target_points: c.target_points,
          target_chests: c.target_chests,
        }
      }
      setRowsByCollector(nextRows)
      setPlayerRowsByCollector(nextPlayerRows)
      setSeasonByCollector(nextSeason)
```

(`.slice(0, 16)` truncates an ISO string like `"2026-06-21T00:00:00"` to `"2026-06-21T00:00"`, the exact format `<input type="datetime-local">` expects.)

Add these handler functions right after `addPlayerRow`:

```jsx
  function updateSeasonField(slug, field, value) {
    setSeasonByCollector(prev => ({
      ...prev,
      [slug]: { ...prev[slug], [field]: value },
    }))
  }

  async function saveSeason(slug) {
    const s = seasonByCollector[slug]
    const payload = {
      timezone_offset_minutes: s.timezone_offset_minutes === '' || s.timezone_offset_minutes == null
        ? null : Number(s.timezone_offset_minutes),
      period_start: s.period_start ? s.period_start + ':00' : null,
      period_end: s.period_end ? s.period_end + ':00' : null,
      target_points: s.target_points === '' || s.target_points == null ? null : Number(s.target_points),
      target_chests: s.target_chests === '' || s.target_chests == null ? null : Number(s.target_chests),
    }
    await api.dashboardChestsSeason(slug, payload)
    setMsg(cx.saved)
    await refresh()
  }
```

(`+ ':00'` turns the `datetime-local` value `"2026-06-21T00:00"` back into `"2026-06-21T00:00:00"`, matching the naive-ISO-string convention the backend expects, per the Global Constraints.)

- [ ] **Step 2: Add the season settings card to the JSX**

In the collector card's JSX, insert this block right after the language `<div>` (after the closing `</div>` of the block that contains `{cx.language}: ...` and before `<div className="chest-tabs">`):

```jsx
          <div className="card" style={{ marginBottom: 16 }}>
            <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.seasonTitle}</div>
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 8 }}>
              <select
                className="input-dark"
                style={{ width: 'auto' }}
                value={seasonByCollector[collector.slug]?.timezone_offset_minutes ?? ''}
                onChange={e => updateSeasonField(collector.slug, 'timezone_offset_minutes', e.target.value)}
              >
                <option value="">{cx.timezoneLabel}</option>
                {[-720, -660, -600, -540, -480, -420, -360, -300, -240, -210, -180, -120, -60, 0,
                  60, 120, 180, 210, 240, 270, 300, 330, 345, 360, 390, 420, 480, 540, 570, 600,
                  630, 660, 720, 765, 780, 840].map(m => (
                  <option key={m} value={m}>
                    UTC{m >= 0 ? '+' : '-'}{String(Math.floor(Math.abs(m) / 60)).padStart(2, '0')}:{String(Math.abs(m) % 60).padStart(2, '0')}
                  </option>
                ))}
              </select>
              <input
                className="input-dark" style={{ width: 'auto' }} type="datetime-local"
                value={seasonByCollector[collector.slug]?.period_start || ''}
                onChange={e => updateSeasonField(collector.slug, 'period_start', e.target.value)}
              />
              <input
                className="input-dark" style={{ width: 'auto' }} type="datetime-local"
                value={seasonByCollector[collector.slug]?.period_end || ''}
                onChange={e => updateSeasonField(collector.slug, 'period_end', e.target.value)}
              />
              <input
                className="input-dark" style={{ width: 120 }} type="number"
                placeholder={cx.targetPointsLabel}
                value={seasonByCollector[collector.slug]?.target_points ?? ''}
                onChange={e => updateSeasonField(collector.slug, 'target_points', e.target.value)}
              />
              <input
                className="input-dark" style={{ width: 120 }} type="number"
                placeholder={cx.targetChestsLabel}
                value={seasonByCollector[collector.slug]?.target_chests ?? ''}
                onChange={e => updateSeasonField(collector.slug, 'target_chests', e.target.value)}
              />
            </div>
            <button className="btn-primary" onClick={() => saveSeason(collector.slug)}>
              {cx.saveSeason}
            </button>
          </div>
```

- [ ] **Step 3: Add the quota toggle column to the chest-types table**

In the "Сундуки" tab's `<table className="chest-table">`, change the header row:

```jsx
                  <tr>
                    <th>{cx.rawCol}</th>
                    <th>{cx.catalogCol}</th>
                    <th>{cx.customNameCol}</th>
                    <th>{cx.pointsCol}</th>
                    <th>{cx.inPatternCol}</th>
                  </tr>
```

to:

```jsx
                  <tr>
                    <th>{cx.rawCol}</th>
                    <th>{cx.catalogCol}</th>
                    <th>{cx.customNameCol}</th>
                    <th>{cx.pointsCol}</th>
                    <th>{cx.inPatternCol}</th>
                    <th>{cx.quotaCol}</th>
                  </tr>
```

And add a new `<td>` right after the existing `is_in_pattern` toggle `<td>` (after its closing `</td>`, before the row's closing `</tr>`):

```jsx
                      <td>
                        <label className="toggle-switch">
                          <input
                            type="checkbox"
                            checked={row.counts_toward_quota}
                            onChange={e => updateRow(collector.slug, i, 'counts_toward_quota', e.target.checked)}
                          />
                          <span className="slider"></span>
                        </label>
                      </td>
```

- [ ] **Step 4: Build check**

Run: `cd C:\BattleBot\web && npm run build`
Expected: exit code 0, no JSX/import errors.

- [ ] **Step 5: Manual browser verification**

Run: `cd C:\BattleBot\web && npm run dev`, open `/dashboard/chests`, log in. Verify:
- "Настройки сезона" card renders with timezone dropdown, two datetime pickers, two number inputs.
- Pick a timezone, dates, and targets, click "Сохранить сезон" — reload the page (F5) — values persist exactly as entered.
- In the "Сундуки" tab, the new "Считать в квоту" toggle column renders, can be flipped, and "Сохранить" persists it after F5 alongside the existing fields (no regression to the existing save flow).

- [ ] **Step 6: Commit**

```bash
git add web/src/pages/ChestsPage.jsx
git commit -m "feat(web): add season settings card and quota toggle column to chests dashboard"
```

---

### Task 7: Deploy and verify

**Files:** none (deployment + migration only)

- [ ] **Step 1: Push to main**

Run: `git push origin main`

- [ ] **Step 2: Deploy backend to GCP and run the migration**

Run:
```bash
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && sudo systemctl restart totalhunter && sleep 2 && sudo systemctl is-active totalhunter"
```

Then apply the migration (the service restart alone does not run Alembic):
```bash
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && DATABASE_URL=\$(sudo systemctl show totalhunter -p Environment | tr ' ' '\n' | grep ^DATABASE_URL | cut -d= -f2-) sudo -E env PATH=\$PATH /opt/totalhunter/venv/bin/alembic upgrade head"
```

If the venv path or the exact env-extraction command differs from what's on the box, inspect `sudo systemctl cat totalhunter` and `ls /opt/totalhunter` first to find the right virtualenv and env-loading convention already used for this service — do not guess blindly, this is a production database.

Expected: `is_active` returns `active`, and the alembic command reports the new revision `s1e2a3s4o5n6` applied with no errors.

- [ ] **Step 3: Deploy frontend to Vercel**

Run:
```bash
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
```
Then poll deployment state and attach the `total-hunter.com` alias per the 3-step Vercel deploy procedure in `CLAUDE.md` section 6.5.

- [ ] **Step 4: Live verification on production**

Open `https://total-hunter.com/dashboard/chests`, log in as the owner, confirm:
- "Настройки сезона" card appears for the real "229/BERS" collector, currently empty (unconfigured) since this clan has never set season fields.
- Set a timezone, period dates, and targets, save, reload — values persist.
- The "Считать в квоту" toggle appears in the chest-types table and can be set on a couple of real Epic-crypt rows without disturbing the existing points/pattern data.
