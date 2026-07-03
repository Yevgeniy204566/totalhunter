# Древний: raw_ocr_name + физическое слияние + кнопка «Очистить» — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn off silent name auto-guessing at tournament import, always preserve the raw OCR name, and physically merge a raw OCR roster row into its confirmed canonical (Chests) row so quota/points/shortfall compute on one row instead of two — plus a leader-facing "Очистить" button to wipe stale tournament-import data without destroying curated troop/rank data.

**Architecture:** One new nullable `AncientRoster.raw_ocr_name` column. `tournaments.py` stops guessing names via `PlayerAlias` fuzzy-match and instead resolves only through already-confirmed `AncientNameMapping` rows. `ancients_dashboard.py` gets two new shared helpers (`_coalesce_roster_fields`, `_merge_roster_on_mapping_confirm`) used by both the existing `populate_roster_from_chests` (refactored) and the mapping-confirmation endpoint (new merge trigger) and a new `DELETE .../roster/ocr-import` endpoint. Frontend surfaces `raw_ocr_name`, fixes the "Разблокировать" button's now-wrong argument, hides it for already-merged rows, and adds the "Очистить" button.

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, Alembic, pytest + pytest-asyncio (SQLite in-memory via `tests/conftest.py`), React (plain JSX, no test framework for `.jsx` files — matches existing project convention, verified via `npm run build`).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-03-ancient-raw-name-clear-button-design.md` — this plan implements it in full (Parts 1–3).
- Test auth pattern for `server/tests/test_ancients_dashboard.py`: `_create_user_with_token(db, email)` + `create_jwt` from `web_routes` (already in the file, do not re-invent).
- Test command prefix (JWT secret required, matches sibling plans in this repo):
  `JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2`
- Mutation endpoints under `/web/dashboard/ancients/{slug}/...` that edit roster content use `_get_own_or_editor_collector` (NOT `_get_own_collector`, which is reserved for owner-only settings like `quota-thresholds`/`ancient-visibility`) — the new `clear_ocr_import` endpoint follows the editor-permitted group, consistent with `troop-level`, `rank`, `roster/{player_name}`, `name-mappings`.
- FastAPI route ordering matters: `DELETE /{slug}/roster/ocr-import` (static path) MUST be registered in the file *before* `DELETE /{slug}/roster/{player_name}` (dynamic path), otherwise Starlette matches the dynamic route first and treats `"ocr-import"` as a `player_name`.
- No new pip/npm dependencies.
- Migration `down_revision` must be `s1h2o3r4t5f6` (current sole alembic head — verified via `python -m alembic heads`).

---

## File Map

| File | Change |
|---|---|
| `server/models.py` | Add `AncientRoster.raw_ocr_name` column |
| `server/alembic/versions/r2a3w4o5c6r7_add_ancient_roster_raw_ocr_name.py` | New migration |
| `server/ancients_dashboard.py` | `_coalesce_roster_fields`, `_merge_roster_on_mapping_confirm`, wire into `patch_name_mappings`, refactor `populate_roster_from_chests`, update `_roster_rows`, new `DELETE /{slug}/roster/ocr-import` |
| `server/tests/test_ancients_dashboard.py` | New tests for merge-on-confirm, `raw_ocr_name` in GET response, clear-ocr endpoint |
| `server/tournaments.py` | Remove `PlayerAlias`/fuzzy resolve; resolve only via confirmed `AncientNameMapping`; always set `raw_ocr_name` |
| `server/tests/test_tournaments.py` | Replace 2 fuzzy-import tests; add `raw_ocr_name`-storage and confirmed-mapping-resolve tests |
| `web/src/api.js` | `dashboardAncientsClearOcrImport(slug)` |
| `web/src/pages/AncientsPage.jsx` | OCR column reads `raw_ocr_name`; fix "Разблокировать" argument; hide it for merged rows; add "Очистить" button |

---

### Task 1: DB — `raw_ocr_name` column + migration

**Files:**
- Modify: `server/models.py` (inside `AncientRoster`, currently lines 581–601)
- Create: `server/alembic/versions/r2a3w4o5c6r7_add_ancient_roster_raw_ocr_name.py`

**Interfaces:**
- Produces: `AncientRoster.raw_ocr_name: Optional[str]` importable from `models`, column present in DB after migration.

- [ ] **Step 1: Add the column to `server/models.py`**

Find this block (the `AncientRoster` class):

```python
    id                 = Column(Integer, primary_key=True)
    collector_id       = Column(Integer, ForeignKey("chest_collectors.id"),
                                nullable=False, index=True)
    player_name        = Column(String(100), nullable=False)
    place              = Column(Integer, nullable=True)
    points             = Column(BigInteger, nullable=True)
    troop_level        = Column(String(20), nullable=True)
    source             = Column(String(8), nullable=False, server_default=text("'ocr'"))
    manual_expires_at  = Column(TIMESTAMP(timezone=True), nullable=True)
    rank               = Column(String(20), nullable=True)
    updated_at        = Column(TIMESTAMP(timezone=True), nullable=False,
                               server_default=func.now())
```

Replace with (adds `raw_ocr_name` after `player_name`):

```python
    id                 = Column(Integer, primary_key=True)
    collector_id       = Column(Integer, ForeignKey("chest_collectors.id"),
                                nullable=False, index=True)
    player_name        = Column(String(100), nullable=False)
    raw_ocr_name       = Column(String(200), nullable=True)
    place              = Column(Integer, nullable=True)
    points             = Column(BigInteger, nullable=True)
    troop_level        = Column(String(20), nullable=True)
    source             = Column(String(8), nullable=False, server_default=text("'ocr'"))
    manual_expires_at  = Column(TIMESTAMP(timezone=True), nullable=True)
    rank               = Column(String(20), nullable=True)
    updated_at        = Column(TIMESTAMP(timezone=True), nullable=False,
                               server_default=func.now())
```

- [ ] **Step 2: Verify current alembic head**

Run: `cd server && python -m alembic heads`
Expected: `s1h2o3r4t5f6 (head)` — exactly one head.

- [ ] **Step 3: Create the migration**

Create `server/alembic/versions/r2a3w4o5c6r7_add_ancient_roster_raw_ocr_name.py`:

```python
"""add_ancient_roster_raw_ocr_name

Revision ID: r2a3w4o5c6r7
Revises: s1h2o3r4t5f6
Create Date: 2026-07-03

Stores the last raw OCR text seen for a roster row, separate from
player_name (which becomes the row's stable canonical/display identity
once a name mapping is confirmed and physically merged).
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'r2a3w4o5c6r7'
down_revision: Union[str, None] = 's1h2o3r4t5f6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'ancient_roster',
        sa.Column('raw_ocr_name', sa.String(200), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('ancient_roster', 'raw_ocr_name')
```

- [ ] **Step 4: Verify it's the sole head**

Run: `cd server && python -m alembic heads`
Expected: `r2a3w4o5c6r7 (head)` — exactly one head.

- [ ] **Step 5: Commit**

```bash
git add server/models.py server/alembic/versions/r2a3w4o5c6r7_add_ancient_roster_raw_ocr_name.py
git commit -m "$(cat <<'EOF'
feat(ancients): add AncientRoster.raw_ocr_name column

Stores the last raw OCR text separately from player_name, which becomes
a stable canonical identity once a confirmed name mapping physically
merges a row (see following commits).

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Backend — `_coalesce_roster_fields` helper + refactor `populate_roster_from_chests`

**Files:**
- Modify: `server/ancients_dashboard.py` (add helper near top; refactor `populate_roster_from_chests`, currently lines 550–614)
- Modify: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `AncientRoster.raw_ocr_name` (Task 1)
- Produces: `_coalesce_roster_fields(base: dict, row: AncientRoster) -> dict` — importable within `ancients_dashboard.py` (module-level function, used by Task 3 too)

- [ ] **Step 1: Write the failing test**

Add to `server/tests/test_ancients_dashboard.py` (near the other `populate_from_chests` tests, after `test_populate_from_chests_merges_confirmed_mapping_into_canonical_name`):

```python
@pytest.mark.asyncio
async def test_populate_from_chests_preserves_raw_ocr_name(db_session):
    """The synced canonical row keeps the raw OCR text that was on the
    source row, so the dashboard can still show 'what the bot actually read'
    after populate-from-chests renames the row."""
    user, token = await _create_user_with_token(db_session, "populate7@test.com")
    collector = await _create_collector(db_session, user.id, slug="populate-7")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="r1", canonical_name="Кузнецов"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Кузнецов",
                                 place=3, points=500, raw_ocr_name="Кузнецoв_VIP",
                                 source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/ancients/populate-7/roster/populate-from-chests",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.raw_ocr_name == "Кузнецoв_VIP"
```

- [ ] **Step 2: Run the test — verify it fails**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py::test_populate_from_chests_preserves_raw_ocr_name -v`
Expected: FAIL — `row.raw_ocr_name` is `None` (the current `preserved` dict logic doesn't carry it over).

- [ ] **Step 3: Add `_coalesce_roster_fields` and refactor `populate_roster_from_chests`**

In `server/ancients_dashboard.py`, add this function immediately after `_get_own_or_editor_collector` (before `_roster_rows`):

```python
def _coalesce_roster_fields(base: dict, row: AncientRoster) -> dict:
    """Merges row's non-NULL fields into base, keeping base's existing
    value wherever row's is NULL. Used to combine two physical
    AncientRoster rows (e.g. a Chests-seeded row and an OCR-imported row)
    into one set of fields before writing a single merged row."""
    return {
        "place": row.place if row.place is not None else base.get("place"),
        "points": row.points if row.points is not None else base.get("points"),
        "troop_level": row.troop_level if row.troop_level is not None else base.get("troop_level"),
        "rank": row.rank if row.rank is not None else base.get("rank"),
        "raw_ocr_name": row.raw_ocr_name if row.raw_ocr_name is not None else base.get("raw_ocr_name"),
        "source": "ocr" if row.source == "ocr" else base.get("source", row.source),
    }
```

Then find this block inside `populate_roster_from_chests`:

```python
        current = preserved.get(target, {})
        preserved[target] = {
            "place": row.place if row.place is not None else current.get("place"),
            "points": row.points if row.points is not None else current.get("points"),
            "troop_level": row.troop_level if row.troop_level is not None else current.get("troop_level"),
            "rank": row.rank if row.rank is not None else current.get("rank"),
            "source": "ocr" if row.source == "ocr" else current.get("source", row.source),
        }
        await db.delete(row)
```

Replace with:

```python
        preserved[target] = _coalesce_roster_fields(preserved.get(target, {}), row)
        await db.delete(row)
```

Then find:

```python
    for name in canonical_names:
        data = preserved.get(name, {})
        db.add(AncientRoster(
            collector_id=collector.id, player_name=name,
            place=data.get("place"), points=data.get("points"),
            troop_level=data.get("troop_level"), rank=data.get("rank"),
            source=data.get("source", "chests"), manual_expires_at=None,
        ))
```

Replace with (adds `raw_ocr_name`):

```python
    for name in canonical_names:
        data = preserved.get(name, {})
        db.add(AncientRoster(
            collector_id=collector.id, player_name=name,
            place=data.get("place"), points=data.get("points"),
            troop_level=data.get("troop_level"), rank=data.get("rank"),
            raw_ocr_name=data.get("raw_ocr_name"),
            source=data.get("source", "chests"), manual_expires_at=None,
        ))
```

- [ ] **Step 4: Run the new test — verify it passes**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py::test_populate_from_chests_preserves_raw_ocr_name -v`
Expected: PASS

- [ ] **Step 5: Run the full existing populate-from-chests test group — verify no regression**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k populate_from_chests -v`
Expected: all PASS (5 pre-existing + 1 new = 6).

- [ ] **Step 6: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "$(cat <<'EOF'
refactor(ancients): extract _coalesce_roster_fields, carry raw_ocr_name in populate-from-chests

Generalizes the inline preserved-dict logic in populate_roster_from_chests
into a shared helper (reused by the merge-on-confirm logic added next) and
adds raw_ocr_name to the set of fields that survive a sync.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Backend — `_merge_roster_on_mapping_confirm` + wire into `patch_name_mappings`

**Files:**
- Modify: `server/ancients_dashboard.py` (add helper; modify `patch_name_mappings`, currently lines 348–371)
- Modify: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `_coalesce_roster_fields` (Task 2)
- Produces: `_merge_roster_on_mapping_confirm(db, collector_id, raw_ocr_name, canonical_name) -> None` (module-level async function in `ancients_dashboard.py`)

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_ancients_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_patch_name_mappings_merges_into_existing_canonical_row(db_session):
    """Confirming a mapping when a canonical row already exists (e.g. from
    populate-from-chests) physically merges the two rows into one — no
    duplicate, quota (troop_level) and points end up on the same row."""
    user, token = await _create_user_with_token(db_session, "merge1@test.com")
    collector = await _create_collector(db_session, user.id, slug="merge-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 troop_level="G8 S8 M8", rank="Офицер", source="chests"))
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Пeтрoв*VIP",
                                 place=5, points=80000, raw_ocr_name="Пeтрoв*VIP",
                                 source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/merge-1/name-mappings",
            json={"mappings": [{"raw_ocr_name": "Пeтрoв*VIP", "canonical_name": "Петров",
                                "confirmed": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
    merged = rows[0]
    assert merged.player_name == "Петров"
    assert merged.troop_level == "G8 S8 M8"
    assert merged.rank == "Офицер"
    assert merged.points == 80000
    assert merged.place == 5
    assert merged.raw_ocr_name == "Пeтрoв*VIP"


@pytest.mark.asyncio
async def test_patch_name_mappings_renames_when_no_canonical_row_exists(db_session):
    """Confirming a mapping when no canonical-named row exists yet just
    renames the raw row in place (nothing to merge with)."""
    user, token = await _create_user_with_token(db_session, "merge2@test.com")
    collector = await _create_collector(db_session, user.id, slug="merge-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Marisha",
                                 place=1, points=100, raw_ocr_name="Marisha", source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/merge-2/name-mappings",
            json={"mappings": [{"raw_ocr_name": "Marisha", "canonical_name": "Маришка",
                                "confirmed": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].player_name == "Маришка"
    assert rows[0].raw_ocr_name == "Marisha"
    assert rows[0].points == 100


@pytest.mark.asyncio
async def test_patch_name_mappings_unconfirmed_does_not_merge(db_session):
    """confirmed=False must not trigger a physical merge — only a confirmed
    mapping is trusted enough to rewrite roster data."""
    user, token = await _create_user_with_token(db_session, "merge3@test.com")
    collector = await _create_collector(db_session, user.id, slug="merge-3")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Сидоров*99",
                                 place=2, points=200, raw_ocr_name="Сидоров*99", source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/merge-3/name-mappings",
            json={"mappings": [{"raw_ocr_name": "Сидоров*99", "canonical_name": "Сидоров",
                                "confirmed": False}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].player_name == "Сидоров*99"  # unchanged — not merged
```

- [ ] **Step 2: Run the tests — verify they fail**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k "merges_into_existing or renames_when_no_canonical or unconfirmed_does_not_merge" -v`
Expected: FAIL — `test_patch_name_mappings_merges_into_existing_canonical_row` and `test_patch_name_mappings_renames_when_no_canonical_row_exists` fail (`len(rows) == 2`, no merge happens yet). The unconfirmed test passes already (nothing to break) — that's fine, it'll stay green through this task as a guard-rail.

- [ ] **Step 3: Add `_merge_roster_on_mapping_confirm` and wire it in**

In `server/ancients_dashboard.py`, add this function immediately after `_coalesce_roster_fields` (added in Task 2):

```python
async def _merge_roster_on_mapping_confirm(
    db: AsyncSession, collector_id: int, raw_ocr_name: str, canonical_name: str,
) -> None:
    """Physically merges the roster row sitting under raw_ocr_name into the
    row sitting under canonical_name (creating the canonical row if it
    didn't exist), so quota-bearing fields (troop_level/rank) and
    points-bearing fields (place/points) end up on one row instead of two.
    No-op if no row exists under raw_ocr_name yet — future tournament
    imports will resolve straight to the canonical name instead (see
    tournaments.py)."""
    if raw_ocr_name == canonical_name:
        return
    raw_row = (await db.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector_id,
            AncientRoster.player_name == raw_ocr_name,
        )
    )).scalar_one_or_none()
    if raw_row is None:
        return

    canonical_row = (await db.execute(
        select(AncientRoster).where(
            AncientRoster.collector_id == collector_id,
            AncientRoster.player_name == canonical_name,
        )
    )).scalar_one_or_none()

    merged: dict = {}
    if canonical_row is not None:
        merged = _coalesce_roster_fields(merged, canonical_row)
        await db.delete(canonical_row)
    merged = _coalesce_roster_fields(merged, raw_row)
    merged["raw_ocr_name"] = merged.get("raw_ocr_name") or raw_row.player_name
    await db.delete(raw_row)
    await db.flush()

    db.add(AncientRoster(
        collector_id=collector_id, player_name=canonical_name,
        place=merged.get("place"), points=merged.get("points"),
        troop_level=merged.get("troop_level"), rank=merged.get("rank"),
        raw_ocr_name=merged.get("raw_ocr_name"),
        source=merged.get("source", "ocr"), manual_expires_at=None,
    ))
```

Then find `patch_name_mappings`:

```python
@router.patch("/{slug}/name-mappings")
async def patch_name_mappings(slug: str, payload: NameMappingsPayload,
                               user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collector, _ = await _get_own_or_editor_collector(db, slug, user)
    for item in payload.mappings:
        existing = (await db.execute(
            select(AncientNameMapping).where(
                AncientNameMapping.collector_id == collector.id,
                AncientNameMapping.raw_ocr_name == item.raw_ocr_name,
            )
        )).scalar_one_or_none()
        if existing:
            existing.canonical_name = item.canonical_name
            existing.confirmed = item.confirmed
        else:
            db.add(AncientNameMapping(
                collector_id=collector.id,
                raw_ocr_name=item.raw_ocr_name,
                canonical_name=item.canonical_name,
                confirmed=item.confirmed,
            ))
    await db.commit()
    return {"ok": True}
```

Replace with:

```python
@router.patch("/{slug}/name-mappings")
async def patch_name_mappings(slug: str, payload: NameMappingsPayload,
                               user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collector, _ = await _get_own_or_editor_collector(db, slug, user)
    for item in payload.mappings:
        existing = (await db.execute(
            select(AncientNameMapping).where(
                AncientNameMapping.collector_id == collector.id,
                AncientNameMapping.raw_ocr_name == item.raw_ocr_name,
            )
        )).scalar_one_or_none()
        if existing:
            existing.canonical_name = item.canonical_name
            existing.confirmed = item.confirmed
        else:
            db.add(AncientNameMapping(
                collector_id=collector.id,
                raw_ocr_name=item.raw_ocr_name,
                canonical_name=item.canonical_name,
                confirmed=item.confirmed,
            ))
        if item.confirmed:
            await _merge_roster_on_mapping_confirm(
                db, collector.id, item.raw_ocr_name, item.canonical_name)
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Run the 3 tests — verify they pass**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k "merges_into_existing or renames_when_no_canonical or unconfirmed_does_not_merge" -v`
Expected: 3 × PASS

- [ ] **Step 5: Run the full name-mappings test group — verify no regression**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k "name_mapping" -v`
Expected: all PASS (includes `test_patch_name_mappings_upsert`, `test_delete_name_mapping_unlocks`, `test_patch_name_mappings_wrong_owner_returns_403` from before — none of these attach an `AncientRoster` row under the raw name, so `_merge_roster_on_mapping_confirm` no-ops for them via the `raw_row is None` early return).

- [ ] **Step 6: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "$(cat <<'EOF'
feat(ancients): physically merge roster rows on confirmed name mapping

Confirming a raw->canonical name mapping on the dashboard now merges the
two AncientRoster rows immediately (troop_level/rank from the canonical
row, place/points from the raw OCR row) instead of only cosmetically
labeling the raw row — otherwise quota and points stay split across two
rows and shortfall_pct can never compute. unconfirmed mappings never merge.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Backend — `_roster_rows` recognizes already-merged rows + exposes `raw_ocr_name`

**Files:**
- Modify: `server/ancients_dashboard.py` (`_roster_rows`, currently lines 74–140)
- Modify: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `AncientRoster.raw_ocr_name` (Task 1)
- Produces: `GET /web/dashboard/ancients` roster rows now include `"raw_ocr_name"`; rows where `raw_ocr_name != player_name` report `mapping_confirmed=True`/`mapped_name=player_name` without needing a live `AncientNameMapping` row.

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_ancients_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_get_roster_already_merged_row_reports_confirmed_without_mapping_row(db_session):
    """A row that was already physically merged (raw_ocr_name differs from
    player_name) must show as confirmed even if the AncientNameMapping
    record was later deleted (unlock doesn't un-merge — see spec)."""
    user, token = await _create_user_with_token(db_session, "mergedget1@test.com")
    collector = await _create_collector(db_session, user.id, slug="mergedget-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=5, points=80000, raw_ocr_name="Пeтрoв*VIP",
                                 troop_level="G8 S8 M8", source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["player_name"] == "Петров"
    assert row["raw_ocr_name"] == "Пeтрoв*VIP"
    assert row["mapped_name"] == "Петров"
    assert row["mapping_confirmed"] is True
    assert row["suggested_name"] is None


@pytest.mark.asyncio
async def test_get_roster_raw_ocr_name_none_for_pure_chests_row(db_session):
    """A row seeded purely by populate-from-chests, never touched by a
    tournament import, has no raw_ocr_name."""
    user, token = await _create_user_with_token(db_session, "mergedget2@test.com")
    collector = await _create_collector(db_session, user.id, slug="mergedget-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Сидоров",
                                 troop_level="G7 S7 M7", source="chests"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["raw_ocr_name"] is None
    assert row["mapping_confirmed"] is False
```

- [ ] **Step 2: Run the tests — verify they fail**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k "already_merged_row or raw_ocr_name_none_for_pure" -v`
Expected: FAIL — `KeyError: 'raw_ocr_name'` (field not yet in the response).

- [ ] **Step 3: Update `_roster_rows`**

Find:

```python
    result = []
    for r in rows:
        raw = r.AncientRoster.player_name
        mapping = mappings_dict.get(raw)
        if mapping and mapping.confirmed:
            mapped_name = mapping.canonical_name
            suggested_name = None
            confirmed = True
        else:
            mapped_name = None
            matches = get_close_matches(raw, canonical_names, n=1, cutoff=fuzzy_threshold)
            suggested_name = matches[0] if matches else None
            confirmed = False
```

Replace with:

```python
    result = []
    for r in rows:
        raw = r.AncientRoster.player_name
        raw_ocr_name = r.AncientRoster.raw_ocr_name
        already_merged = raw_ocr_name is not None and raw_ocr_name != raw
        if already_merged:
            mapped_name = raw
            suggested_name = None
            confirmed = True
        else:
            mapping = mappings_dict.get(raw)
            if mapping and mapping.confirmed:
                mapped_name = mapping.canonical_name
                suggested_name = None
                confirmed = True
            else:
                mapped_name = None
                matches = get_close_matches(raw, canonical_names, n=1, cutoff=fuzzy_threshold)
                suggested_name = matches[0] if matches else None
                confirmed = False
```

Then find the `result.append({...})` block at the end of the loop:

```python
        result.append({
            "player_name": raw,
            "place": r.AncientRoster.place,
            "points": r.AncientRoster.points,
            "troop_level": r.AncientRoster.troop_level or r.profile_troop,
            "rank": r.AncientRoster.rank,
            "quota": quota,
            "shortfall_pct": shortfall_pct(quota, r.AncientRoster.points),
            "mapped_name": mapped_name,
            "suggested_name": suggested_name,
            "mapping_confirmed": confirmed,
            "is_alias_source": suggested_name is not None,  # True = авто-найдено из Сундуков
        })
```

Replace with (adds `raw_ocr_name`):

```python
        result.append({
            "player_name": raw,
            "raw_ocr_name": raw_ocr_name,
            "place": r.AncientRoster.place,
            "points": r.AncientRoster.points,
            "troop_level": r.AncientRoster.troop_level or r.profile_troop,
            "rank": r.AncientRoster.rank,
            "quota": quota,
            "shortfall_pct": shortfall_pct(quota, r.AncientRoster.points),
            "mapped_name": mapped_name,
            "suggested_name": suggested_name,
            "mapping_confirmed": confirmed,
            "is_alias_source": suggested_name is not None,  # True = авто-найдено из Сундуков
        })
```

- [ ] **Step 4: Run the 2 new tests — verify they pass**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k "already_merged_row or raw_ocr_name_none_for_pure" -v`
Expected: 2 × PASS

- [ ] **Step 5: Run the full test file — verify no regression**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -v --tb=short 2>&1 | tail -20`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "$(cat <<'EOF'
feat(ancients): expose raw_ocr_name in roster GET, recognize already-merged rows

A row is treated as confirmed/merged whenever raw_ocr_name differs from
player_name, independent of whether the AncientNameMapping record still
exists — matches the "unlock doesn't un-merge" behavior from the spec.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Backend — `tournaments.py` stops guessing, resolves only via confirmed mapping, always stores `raw_ocr_name`

**Files:**
- Modify: `server/tournaments.py` (full rewrite of the resolution logic)
- Modify: `server/tests/test_tournaments.py`

**Interfaces:**
- Consumes: `AncientNameMapping` (existing model), `AncientRoster.raw_ocr_name` (Task 1)
- Produces: `POST /api/v1/tournaments/import` no longer performs fuzzy `PlayerAlias` matching; resolves a raw name to canonical only via an existing confirmed `AncientNameMapping`; always sets `raw_ocr_name` on the upserted row.

- [ ] **Step 1: Write the failing tests**

In `server/tests/test_tournaments.py`, replace the two fuzzy-matching tests:

```python
@pytest.mark.asyncio
async def test_fuzzy_match_uses_close_alias_canonical_name(db_session):
    ...
```

and

```python
@pytest.mark.asyncio
async def test_fuzzy_match_does_not_match_dissimilar_name(db_session):
    ...
```

(the two full test functions, from `@pytest.mark.asyncio` through their closing assertion) with:

```python
@pytest.mark.asyncio
async def test_import_stores_raw_ocr_name(db_session):
    """Every imported row always carries the exact raw OCR text in
    raw_ocr_name, regardless of whether it resolved to a canonical name."""
    user = await _create_user(db_session, "hwid5000000000a")
    await db_session.commit()

    payload = _payload(
        user.hwid, clan="BERS5",
        items=[{"name": "Бандеролька __", "place": 5, "points": 1264203992}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS5")
    )).scalar_one()
    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.player_name == "Бандеролька __"
    assert row.raw_ocr_name == "Бандеролька __"


@pytest.mark.asyncio
async def test_import_ignores_unconfirmed_playeralias_similarity(db_session):
    """PlayerAlias (Chests) no longer drives any resolution on import —
    even an exact PlayerAlias.raw_name key hit must NOT auto-resolve.
    Only a confirmed AncientNameMapping does (see next test)."""
    user = await _create_user(db_session, "hwid6000000000a")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERS6",
        items=[{"name": "Иванов", "place": 1, "points": 100}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS6")
    )).scalar_one()
    db_session.add(PlayerAlias(collector_id=collector.id,
                               raw_name="ivanov_raw_ocr", canonical_name="Иванов"))
    await db_session.commit()

    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Marisha?", "place": 12, "points": 1155240852}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert {r.player_name for r in rows} == {"Marisha?"}


@pytest.mark.asyncio
async def test_import_resolves_via_confirmed_ancient_name_mapping(db_session):
    """A confirmed AncientNameMapping (set via the dashboard) DOES resolve
    the raw import name to the canonical one, writing straight into the
    canonical row instead of creating a duplicate raw row."""
    user = await _create_user(db_session, "hwid7000000000b")
    await db_session.commit()

    base_payload = _payload(
        user.hwid, clan="BERS7B",
        items=[{"name": "Кузнецов", "place": 1, "points": 10}],
    )
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=base_payload)

    collector = (await db_session.execute(
        select(ChestCollector).where(
            ChestCollector.kingdom == "K229", ChestCollector.clan == "BERS7B")
    )).scalar_one()
    from models import AncientNameMapping
    db_session.add(AncientNameMapping(collector_id=collector.id,
                                      raw_ocr_name="Кузнецoв_VIP",
                                      canonical_name="Кузнецов", confirmed=True))
    await db_session.commit()

    reimport_payload = dict(base_payload, timestamp="2026-06-23T11:00:00",
                            items=[{"name": "Кузнецoв_VIP", "place": 2, "points": 999}])
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/v1/tournaments/import", json=reimport_payload)

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].player_name == "Кузнецов"
    assert rows[0].raw_ocr_name == "Кузнецoв_VIP"
    assert rows[0].points == 999
```

- [ ] **Step 2: Run the tests — verify they fail**

Run: `cd server && python -m pytest tests/test_tournaments.py -k "raw_ocr_name or ignores_unconfirmed or resolves_via_confirmed" -v`
Expected: FAIL — `test_import_stores_raw_ocr_name` fails on `AttributeError`/`assert None == "..."` (column doesn't exist yet in the import path); `test_import_resolves_via_confirmed_ancient_name_mapping` fails with 2 rows instead of 1 (no `AncientNameMapping` resolution yet).

- [ ] **Step 3: Rewrite `server/tournaments.py`**

Replace the entire file content with:

```python
"""
tournaments.py — Tournament roster import endpoint.

POST /api/v1/tournaments/import — принимает турнирный ростер от бота (tournament_reader.py),
изолирует по тенанту [kingdom, clan, user_id] (тот же ChestCollector, что у Сундуков),
полностью заменяет ancient_roster для этого collector_id: upsert по player_name (place/
points обновляются, troop_level не трогается), удаление строк для игроков, отсутствующих
в новом импорте.

Резолвинг сырого OCR-имени в каноническое происходит ТОЛЬКО через уже подтверждённый на
дашборде AncientNameMapping (raw_ocr_name -> canonical_name, confirmed=True) — никакого
fuzzy-угадывания на импорте больше нет. Не подтверждённое лидером сырое имя сохраняется
как есть (в player_name и в raw_ocr_name) и ждёт ручного сопоставления на дашборде
(ancients_dashboard.py), которое сливает физические строки при подтверждении.

Auth: hwid в payload → User (как /api/v1/chests/import). Бесплатно — не списывает кредиты,
весь функционал «Древний» бесплатен по требованию.
"""
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from chests import _get_or_create_collector
from database import get_db
from models import AncientNameMapping, AncientRoster, Log, User

router = APIRouter(prefix="/api/v1/tournaments", tags=["tournaments"])


class TournamentItemIn(BaseModel):
    name: str
    place: Optional[int] = None
    points: Optional[int] = None


class TournamentImportPayload(BaseModel):
    hwid: str
    kingdom: str
    clan: str
    timestamp: str
    items: List[TournamentItemIn]


@router.post("/import")
async def import_tournament(payload: TournamentImportPayload,
                            db: AsyncSession = Depends(get_db)):
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
    if collector.ancient_hidden:
        collector.ancient_hidden_at = datetime.now(timezone.utc)

    confirmed_mappings = {
        m.raw_ocr_name: m.canonical_name
        for m in (await db.execute(
            select(AncientNameMapping).where(
                AncientNameMapping.collector_id == collector.id,
                AncientNameMapping.confirmed == True,
            )
        )).scalars().all()
    }

    incoming_names = set()
    for item in payload.items:
        target_name = confirmed_mappings.get(item.name, item.name)
        incoming_names.add(target_name)

        existing = (await db.execute(
            select(AncientRoster).where(
                AncientRoster.collector_id == collector.id,
                AncientRoster.player_name == target_name,
            )
        )).scalar_one_or_none()
        if existing:
            existing.place = item.place
            existing.points = item.points
            existing.source = "ocr"
            existing.manual_expires_at = None
            existing.raw_ocr_name = item.name
        else:
            db.add(AncientRoster(
                collector_id=collector.id, player_name=target_name,
                place=item.place, points=item.points, troop_level=None,
                source="ocr", raw_ocr_name=item.name,
            ))

    await db.flush()
    await db.execute(
        delete(AncientRoster).where(
            AncientRoster.collector_id == collector.id,
            AncientRoster.player_name.not_in(incoming_names),
            AncientRoster.source == "ocr",
        )
    )

    db.add(Log(hwid=user.hwid, event_type="ancient_ocr_import"))

    await db.commit()
    return {"ok": True, "count": len(payload.items), "collector_slug": collector.slug}
```

- [ ] **Step 4: Run the 3 new tests — verify they pass**

Run: `cd server && python -m pytest tests/test_tournaments.py -k "raw_ocr_name or ignores_unconfirmed or resolves_via_confirmed" -v`
Expected: 3 × PASS

- [ ] **Step 5: Run the full file — verify no regression**

Run: `cd server && python -m pytest tests/test_tournaments.py -v --tb=short 2>&1 | tail -30`
Expected: all PASS (9 pre-existing minus 2 replaced, plus 3 new = 10 total).

- [ ] **Step 6: Commit**

```bash
git add server/tournaments.py server/tests/test_tournaments.py
git commit -m "$(cat <<'EOF'
refactor(ancients): tournament import resolves only via confirmed mapping

Removes the silent PlayerAlias-based fuzzy auto-resolve at import time —
raw OCR text is always preserved (raw_ocr_name), and the only thing that
resolves a raw name to canonical is an explicit, leader-confirmed
AncientNameMapping (dashboard). Restores full transparency: what the bot
read is never silently rewritten.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 6: Backend — `DELETE /{slug}/roster/ocr-import` (Очистить)

**Files:**
- Modify: `server/ancients_dashboard.py` (insert new route before `delete_roster_entry`, currently line 397)
- Modify: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Produces: `DELETE /web/dashboard/ancients/{slug}/roster/ocr-import` → `{"deleted": int, "cleared": int}`

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_ancients_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_clear_ocr_deletes_pure_ocr_rows(db_session):
    """A row with no troop_level/rank — pure tournament-import junk — is
    deleted entirely."""
    user, token = await _create_user_with_token(db_session, "clear1@test.com")
    collector = await _create_collector(db_session, user.id, slug="clear-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Случайный*VIP",
                                 place=9, points=10, raw_ocr_name="Случайный*VIP",
                                 source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            "/web/dashboard/ancients/clear-1/roster/ocr-import",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 1, "cleared": 0}

    rows = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()
    assert rows == []


@pytest.mark.asyncio
async def test_clear_ocr_only_clears_points_on_curated_row(db_session):
    """A row that carries troop_level/rank (curated by the leader, possibly
    merged from a tournament import) survives — only place/points reset."""
    user, token = await _create_user_with_token(db_session, "clear2@test.com")
    collector = await _create_collector(db_session, user.id, slug="clear-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=5, points=80000, raw_ocr_name="Пeтрoв*VIP",
                                 troop_level="G8 S8 M8", rank="Офицер", source="ocr"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            "/web/dashboard/ancients/clear-2/roster/ocr-import",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 0, "cleared": 1}

    row = (await db_session.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalar_one()
    assert row.place is None
    assert row.points is None
    assert row.troop_level == "G8 S8 M8"
    assert row.rank == "Офицер"
    assert row.player_name == "Петров"


@pytest.mark.asyncio
async def test_clear_ocr_wrong_owner_returns_403(db_session):
    owner, _ = await _create_user_with_token(db_session, "clear3owner@test.com")
    _, attacker_token = await _create_user_with_token(db_session, "clear3attacker@test.com")
    collector = await _create_collector(db_session, owner.id, slug="clear-3")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            "/web/dashboard/ancients/clear-3/roster/ocr-import",
            headers={"Authorization": f"Bearer {attacker_token}"},
        )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run the tests — verify they fail**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k clear_ocr -v`
Expected: FAIL — `404 Not Found` (endpoint doesn't exist yet).

- [ ] **Step 3: Add the endpoint**

In `server/ancients_dashboard.py`, find `delete_roster_entry`:

```python
@router.delete("/{slug}/roster/{player_name}")
async def delete_roster_entry(slug: str, player_name: str,
```

Insert this new route **immediately before** that line (route ordering matters — see Global Constraints):

```python
@router.delete("/{slug}/roster/ocr-import")
async def clear_ocr_import(slug: str,
                           user: User = Depends(get_web_user),
                           db: AsyncSession = Depends(get_db)):
    """«Очистить» — стирает результаты последнего турнирного импорта.
    Строка без войск/звания (чистый OCR-мусор) удаляется целиком. Строка,
    несущая войска/звание (слитая с Сундуками или ручная), только теряет
    место/очки — иначе кнопка стирала бы кураторские данные лидера."""
    collector, _ = await _get_own_or_editor_collector(db, slug, user)
    rows = (await db.execute(
        select(AncientRoster).where(AncientRoster.collector_id == collector.id)
    )).scalars().all()

    deleted = 0
    cleared = 0
    for row in rows:
        if row.place is None and row.points is None:
            continue
        if row.source == "ocr" and row.troop_level is None and row.rank is None:
            await db.delete(row)
            deleted += 1
        else:
            row.place = None
            row.points = None
            cleared += 1

    await db.commit()
    return {"deleted": deleted, "cleared": cleared}


```

- [ ] **Step 4: Run the 3 new tests — verify they pass**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k clear_ocr -v`
Expected: 3 × PASS

- [ ] **Step 5: Run the full backend test suite for this module — verify no regression**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py tests/test_ancient_quota.py tests/test_ancient_retention.py -v --tb=short 2>&1 | tail -20`
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "$(cat <<'EOF'
feat(ancients): DELETE /roster/ocr-import — Очистить button backend

Pure tournament-junk rows (no troop_level/rank) are deleted outright;
rows carrying curated troop_level/rank only lose place/points, so the
leader's manually-entered composition/rank data survives a clear.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 7: Frontend — raw OCR column, fix unlock argument, hide unlock for merged rows

**Files:**
- Modify: `web/src/pages/AncientsPage.jsx`

**Interfaces:**
- Consumes: `raw_ocr_name` field on each roster row (Task 4)

- [ ] **Step 1: Fix the OCR column to read `raw_ocr_name`**

Find (in the roster `<tbody>` map, currently line 592):

```jsx
                          <td>{p.player_name}</td>
```

Replace with:

```jsx
                          <td>{p.raw_ocr_name || p.player_name}</td>
```

- [ ] **Step 2: Fix the "Разблокировать" argument and hide it for already-merged rows**

Find (currently lines 593–626):

```jsx
                          <td>
                            {p.mapping_confirmed ? (
                              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <span style={{ color: '#a6e3a1', fontWeight: 600 }}>{p.mapped_name}</span>
                                <button
                                  style={{
                                    fontSize: 11, padding: '1px 6px', cursor: 'pointer',
                                    background: 'transparent', border: '1px solid #6c7086',
                                    color: '#6c7086', borderRadius: 4,
                                  }}
                                  onClick={async () => {
                                    await api.dashboardAncientsNameMappingDelete(c.slug, p.player_name)
                                    refresh()
                                  }}
                                >
                                  Разблокировать
                                </button>
                              </span>
                            ) : (
```

Replace with (button only shown when the row is NOT yet physically merged; a merged row shows a static lock icon instead, and the unlock call now passes `p.raw_ocr_name`, the actual `AncientNameMapping` key):

```jsx
                          <td>
                            {p.mapping_confirmed ? (
                              <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                                <span style={{ color: '#a6e3a1', fontWeight: 600 }}>{p.mapped_name}</span>
                                {p.raw_ocr_name && p.raw_ocr_name !== p.player_name ? (
                                  <span title="Слияние необратимо" style={{ fontSize: 12 }}>🔒</span>
                                ) : (
                                  <button
                                    style={{
                                      fontSize: 11, padding: '1px 6px', cursor: 'pointer',
                                      background: 'transparent', border: '1px solid #6c7086',
                                      color: '#6c7086', borderRadius: 4,
                                    }}
                                    onClick={async () => {
                                      await api.dashboardAncientsNameMappingDelete(c.slug, p.raw_ocr_name || p.player_name)
                                      refresh()
                                    }}
                                  >
                                    Разблокировать
                                  </button>
                                )}
                              </span>
                            ) : (
```

- [ ] **Step 3: Manual verification**

Run: `cd web && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/AncientsPage.jsx
git commit -m "$(cat <<'EOF'
fix(ancients): OCR column reads raw_ocr_name; fix unlock arg for merged rows

Разблокировать was passing player_name (now the canonical name after a
physical merge) instead of the actual AncientNameMapping key. Hidden
entirely for already-merged rows since the merge is not reversible.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 8: Frontend — «Очистить» button

**Files:**
- Modify: `web/src/api.js`
- Modify: `web/src/pages/AncientsPage.jsx`

**Interfaces:**
- Consumes: `DELETE /{slug}/roster/ocr-import` (Task 6)

- [ ] **Step 1: Add the API helper**

In `web/src/api.js`, find:

```javascript
  dashboardAncientsDeleteRosterEntry: (slug, playerName) =>
    request('DELETE', `/web/dashboard/ancients/${slug}/roster/${encodeURIComponent(playerName)}`),
```

Add immediately after it:

```javascript
  dashboardAncientsClearOcrImport: (slug) =>
    request('DELETE', `/web/dashboard/ancients/${slug}/roster/ocr-import`),
```

- [ ] **Step 2: Add confirm-state and handler in `AncientsPage.jsx`**

Find:

```javascript
  const [confirmDeleteRoster, setConfirmDeleteRoster] = useState({})
```

Add immediately after it:

```javascript
  const [confirmClearOcr, setConfirmClearOcr] = useState({})
  const [clearOcrMsg, setClearOcrMsg] = useState({})
```

Find `handleDeleteRosterEntry`:

```javascript
  async function handleDeleteRosterEntry(slug, playerName) {
    const key = `${slug}:${playerName}`
    await api.dashboardAncientsDeleteRosterEntry(slug, playerName)
    setConfirmDeleteRoster(prev => ({ ...prev, [key]: false }))
    refresh()
  }
```

Add immediately after it:

```javascript
  async function handleClearOcrImport(slug) {
    const { deleted, cleared } = await api.dashboardAncientsClearOcrImport(slug)
    setConfirmClearOcr(prev => ({ ...prev, [slug]: false }))
    setClearOcrMsg(prev => ({ ...prev, [slug]: `Удалено: ${deleted}, очищено: ${cleared}` }))
    setTimeout(() => setClearOcrMsg(prev => ({ ...prev, [slug]: '' })), 5000)
    refresh()
  }
```

- [ ] **Step 3: Add the button above the roster table**

Find:

```jsx
              <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.rosterTitle}</div>
```

Replace with:

```jsx
              <div style={{ marginBottom: 8, display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ fontWeight: 600 }}>{cx.rosterTitle}</span>
                {confirmClearOcr[c.slug] ? (
                  <span style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
                    <span style={{ fontSize: 12, color: '#f9a825' }}>Стереть турнирные очки?</span>
                    <button
                      style={{ fontSize: 11, padding: '2px 6px', background: '#DC2626', border: 'none', color: '#fff', borderRadius: 4 }}
                      onClick={() => handleClearOcrImport(c.slug)}
                    >{cx.deleteRosterYes}</button>
                    <button
                      style={{ fontSize: 11, padding: '2px 6px', background: 'transparent', border: '1px solid #6c7086', color: '#6c7086', borderRadius: 4 }}
                      onClick={() => setConfirmClearOcr(prev => ({ ...prev, [c.slug]: false }))}
                    >{cx.closeSeasonNo}</button>
                  </span>
                ) : (
                  <button
                    style={{ fontSize: 11, padding: '2px 8px', cursor: 'pointer', background: 'transparent', border: '1px solid #6c7086', color: '#6c7086', borderRadius: 4 }}
                    onClick={() => setConfirmClearOcr(prev => ({ ...prev, [c.slug]: true }))}
                  >
                    Очистить
                  </button>
                )}
                {clearOcrMsg[c.slug] && (
                  <span style={{ fontSize: 12, color: '#a6e3a1' }}>{clearOcrMsg[c.slug]}</span>
                )}
              </div>
```

- [ ] **Step 4: Manual verification**

Run: `cd web && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 5: Commit**

```bash
git add web/src/api.js web/src/pages/AncientsPage.jsx
git commit -m "$(cat <<'EOF'
feat(ancients): Очистить button — wipe stale tournament-import data

Two-step confirm above the roster table, mirrors the existing per-row
delete confirm pattern. Reports how many rows were deleted vs cleared.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 9: Deploy

**Files:** none (infra only)

- [ ] **Step 1: Push to main**

```bash
git push origin main
```

- [ ] **Step 2: GCP — migration + restart**

```bash
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && sudo env DATABASE_URL='postgresql+asyncpg://hunter:TotalHunter2026@localhost:5432/totalhunter' /opt/totalhunter/venv/bin/alembic -c /opt/totalhunter/server/alembic.ini upgrade r2a3w4o5c6r7 && sudo systemctl restart totalhunter && sleep 3 && systemctl is-active totalhunter"
```

Expected: `Running upgrade s1h2o3r4t5f6 -> r2a3w4o5c6r7, add_ancient_roster_raw_ocr_name` then `active`.

- [ ] **Step 3: Vercel deploy + alias**

```bash
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
```

Wait for `READY`, then attach alias — standard 3-step procedure from `CLAUDE.md` §6.5.

- [ ] **Step 4: Smoke test**

Open `https://total-hunter.com/dashboard/ancients`:
1. Импортировать (или проверить существующий) турнир — колонка «Игрок (OCR)» показывает ровно то, что прислал бот.
2. Выбрать «Правильное имя» для нескольких строк из дропдауна, «Сохранить маппинги» → строки схлопываются в одну, войска/звание сохранились, очки подтянулись.
3. На уже слитой строке иконка 🔒 вместо кнопки «Разблокировать».
4. Кнопка «Очистить» → двухшаговое подтверждение → сообщение «Удалено: N, очищено: M» → чисто-мусорные строки исчезли, слитые остались без места/очков, войска/звание не пропали.

---

## Self-Review Notes

- **Spec coverage:** Часть 1 (raw_ocr_name всегда сохраняется, резолвинг только через подтверждённый маппинг) — Tasks 1, 5. Часть 2 (Очистить: удаление чистого мусора vs очистка курированных строк) — Task 6, 8. Часть 3 (физическое слияние: `_coalesce_roster_fields`, `_merge_roster_on_mapping_confirm`, вызов из `patch_name_mappings`, рефакторинг `populate_roster_from_chests`, обновление `_roster_rows`) — Tasks 2, 3, 4. Фронтенд (колонка OCR, фикс/скрытие «Разблокировать», кнопка «Очистить») — Tasks 7, 8. Все пункты спеки покрыты.
- **Placeholder scan:** none — каждый шаг содержит финальный код или точную команду.
- **Type consistency:** `_coalesce_roster_fields(base: dict, row: AncientRoster) -> dict` определена в Task 2, используется без изменения сигнатуры в Task 3 (`_merge_roster_on_mapping_confirm`). `raw_ocr_name` как имя поля идентично во всех слоях: модель (Task 1) → бэкенд-ответ `_roster_rows`/`tournaments.py` (Tasks 4–5) → фронтенд `p.raw_ocr_name` (Tasks 7–8) — без расхождений в написании.
- **Route-ordering risk (Global Constraints)** явно отражена в Task 6 Step 3 — новый статический путь вставляется до динамического `{player_name}`.
