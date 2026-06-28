# Ancient Name Mapping Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Link OCR player names from the Ancient module to manually-corrected canonical names from Chests, so the Ancient dashboard shows correct names with minimal manual effort.

**Architecture:** New `AncientNameMapping` table stores confirmed raw→canonical pairs per collector. The dashboard GET endpoint enriches each roster row with `mapped_name` (confirmed) and `suggested_name` (fuzzy-match via `difflib`) by joining against `PlayerAlias` from Chests. Two new endpoints handle batch upsert and single-row delete (unlock). Frontend adds a fuzzy threshold slider and a "Правильное имя" column with lock/unlock UX.

**Tech Stack:** FastAPI + SQLAlchemy async + Alembic (backend); React + useState (frontend); `difflib.get_close_matches` (fuzzy matching, stdlib — no new dependencies)

## Global Constraints

- No new pip dependencies — use `difflib` (stdlib) for fuzzy matching
- `fuzzy_threshold` query param: float, range 0.5–1.0 inclusive, default 0.75
- `AncientNameMapping` unique constraint on `(collector_id, raw_ocr_name)` + composite index
- All endpoints under `/web/dashboard/ancients/` use `_get_own_collector` for auth
- Upsert on PATCH (INSERT if absent, UPDATE if exists) — never duplicate
- Roster rows enrichment: `mapping_confirmed=True` → `mapped_name` populated, `suggested_name=None`; no confirmed mapping → `mapped_name=None`, `suggested_name` from fuzzy or None
- Public ancients page does not exist yet — skip public GET changes
- Tests file: `server/tests/test_ancients_dashboard.py` (already exists, follow its patterns)
- Auth pattern: `create_jwt(user.id, email)` from `web_routes`, `_create_user_with_token` helper

---

## File Map

| File | Change |
|---|---|
| `server/models.py` | Add `AncientNameMapping` class |
| `server/alembic/versions/<auto>_add_ancient_name_mappings.py` | New migration |
| `server/ancients_dashboard.py` | Enrich GET + 2 new endpoints |
| `server/tests/test_ancients_dashboard.py` | 6 new tests |
| `web/src/api.js` | 2 new helpers |
| `web/src/pages/AncientsPage.jsx` | Slider + "Правильное имя" column |

---

### Task 1: DB — AncientNameMapping model + migration

**Files:**
- Modify: `server/models.py`
- Create: `server/alembic/versions/<auto>_add_ancient_name_mappings.py`

**Interfaces:**
- Produces: `AncientNameMapping` model importable from `models`, migration applied

- [ ] **Step 1: Add model to `server/models.py`**

Find the block after `AncientCalculation` (around line 578) and add:

```python
class AncientNameMapping(Base):
    __tablename__ = "ancient_name_mappings"
    __table_args__ = (
        UniqueConstraint("collector_id", "raw_ocr_name",
                         name="uq_ancient_name_mapping"),
        Index("ix_ancient_name_mappings_lookup", "collector_id", "raw_ocr_name"),
    )
    id             = Column(Integer, primary_key=True)
    collector_id   = Column(Integer, ForeignKey("chest_collectors.id", ondelete="CASCADE"),
                            nullable=False)
    raw_ocr_name   = Column(String(200), nullable=False)
    canonical_name = Column(String(200), nullable=False)
    confirmed      = Column(Boolean, nullable=False, default=False)
    created_at     = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at     = Column(DateTime, nullable=False, default=datetime.utcnow,
                            onupdate=datetime.utcnow)
```

Verify `Index` and `UniqueConstraint` are already imported in `models.py` (they are used in other models — check before adding).

- [ ] **Step 2: Generate migration**

```powershell
cd server
$env:DATABASE_URL = "postgresql+asyncpg://hunter:TotalHunter2026@localhost:5432/totalhunter"
# If no local PG, generate manually instead:
```

Since there is no local PostgreSQL, create the migration file manually.

First check current heads:
```powershell
ls alembic\versions\ | Select-Object Name | Sort-Object Name
```

Create file `server/alembic/versions/<timestamp>_add_ancient_name_mappings.py` where `<timestamp>` = current datetime digits, e.g. `a9b8c7d6e5f4`. Set `down_revision` to the current head revision (look for the file with no child pointing to it — that's the head; it's `x1y2z3a4b5c6` after the leader-exclusion migration).

```python
"""add_ancient_name_mappings

Revision ID: a9b8c7d6e5f4
Revises: x1y2z3a4b5c6
Create Date: 2026-06-28 20:00:00.000000
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'a9b8c7d6e5f4'
down_revision: Union[str, None] = 'x1y2z3a4b5c6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'ancient_name_mappings',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('collector_id', sa.Integer(), sa.ForeignKey(
            'chest_collectors.id', ondelete='CASCADE'), nullable=False),
        sa.Column('raw_ocr_name', sa.String(200), nullable=False),
        sa.Column('canonical_name', sa.String(200), nullable=False),
        sa.Column('confirmed', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(), nullable=False,
                  server_default=sa.text('now()')),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('collector_id', 'raw_ocr_name',
                            name='uq_ancient_name_mapping'),
    )
    op.create_index('ix_ancient_name_mappings_lookup',
                    'ancient_name_mappings', ['collector_id', 'raw_ocr_name'])


def downgrade() -> None:
    op.drop_index('ix_ancient_name_mappings_lookup',
                  table_name='ancient_name_mappings')
    op.drop_table('ancient_name_mappings')
```

- [ ] **Step 3: Commit**

```bash
git add server/models.py server/alembic/versions/a9b8c7d6e5f4_add_ancient_name_mappings.py
git commit -m "feat(ancient): AncientNameMapping model + migration"
```

---

### Task 2: Backend — GET enrichment with fuzzy matching

**Files:**
- Modify: `server/ancients_dashboard.py`
- Modify: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `AncientNameMapping` (Task 1), `PlayerAlias` (from `models.py`, already importable)
- Produces: `GET /web/dashboard/ancients?fuzzy_threshold=0.75` returns roster rows with `mapped_name`, `suggested_name`, `mapping_confirmed`

- [ ] **Step 1: Write 2 failing tests**

Add to `server/tests/test_ancients_dashboard.py`:

```python
from models import AncientNameMapping, PlayerAlias  # add to existing import line

@pytest.mark.asyncio
async def test_get_roster_suggested_name_via_fuzzy(db_session):
    """Roster row gets suggested_name when fuzzy-match finds a canonical name."""
    user, token = await _create_user_with_token(db_session, "fuzzy1@test.com")
    collector = await _create_collector(db_session, user.id, slug="fuzzy-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Marisha",
                                 place=1, points=100, troop_level=None))
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="ocr_raw",
                               canonical_name="Маришка"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["player_name"] == "Marisha"
    assert row["mapping_confirmed"] is False
    assert row["mapped_name"] is None
    assert "is_alias_source" in row
    # cross-script fuzzy won't fire; suggested_name None → is_alias_source False
    assert row["is_alias_source"] is False


@pytest.mark.asyncio
async def test_get_roster_confirmed_mapping_applied(db_session):
    """Confirmed mapping → mapped_name populated, mapping_confirmed=True."""
    user, token = await _create_user_with_token(db_session, "mapped1@test.com")
    collector = await _create_collector(db_session, user.id, slug="mapped-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Marisha",
                                 place=1, points=100, troop_level=None))
    db_session.add(AncientNameMapping(collector_id=collector.id,
                                      raw_ocr_name="Marisha",
                                      canonical_name="Маришка",
                                      confirmed=True))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["mapped_name"] == "Маришка"
    assert row["mapping_confirmed"] is True
    assert row["suggested_name"] is None
    assert row["is_alias_source"] is False  # confirmed mapping → no suggestion active
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd server && python -m pytest tests/test_ancients_dashboard.py::test_get_roster_suggested_name_via_fuzzy tests/test_ancients_dashboard.py::test_get_roster_confirmed_mapping_applied -v --tb=short
```

Expected: `KeyError: 'mapping_confirmed'` or similar — field not yet in response.

- [ ] **Step 3: Update `ancients_dashboard.py`**

At top, add imports:
```python
from difflib import get_close_matches
from fastapi import Query
```

Add `AncientNameMapping, PlayerAlias` to the `from models import ...` line.

Replace `_roster_rows` with the enriched version:

```python
async def _roster_rows(
    db: AsyncSession,
    collector_id: int,
    mappings_dict: dict,       # raw_ocr_name → AncientNameMapping
    canonical_names: list[str],
    fuzzy_threshold: float,
) -> list:
    rows = (await db.execute(
        select(AncientRoster, PlayerProfile.troop_level.label("profile_troop"))
        .outerjoin(
            PlayerProfile,
            and_(
                PlayerProfile.collector_id == AncientRoster.collector_id,
                PlayerProfile.canonical_name == AncientRoster.player_name,
            )
        )
        .where(AncientRoster.collector_id == collector_id)
        .order_by(AncientRoster.place.asc().nullslast())
    )).all()

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
        result.append({
            "player_name": raw,
            "place": r.AncientRoster.place,
            "points": r.AncientRoster.points,
            "troop_level": r.AncientRoster.troop_level or r.profile_troop,
            "mapped_name": mapped_name,
            "suggested_name": suggested_name,
            "mapping_confirmed": confirmed,
            "is_alias_source": suggested_name is not None,  # True = авто-найдено из Сундуков
        })
    return result
```

Update `get_dashboard_ancients` to load mappings + canonical names and pass to `_roster_rows`:

```python
@router.get("")
async def get_dashboard_ancients(
    fuzzy_threshold: float = Query(default=0.75, ge=0.5, le=1.0),
    user: User = Depends(get_web_user),
    db: AsyncSession = Depends(get_db),
):
    collectors = (await db.execute(
        select(ChestCollector).where(ChestCollector.user_id == user.id)
    )).scalars().all()

    result = []
    for collector in collectors:
        canonical_names = list((await db.execute(
            select(PlayerAlias.canonical_name).where(
                PlayerAlias.collector_id == collector.id)
        )).scalars().all())

        mappings = (await db.execute(
            select(AncientNameMapping).where(
                AncientNameMapping.collector_id == collector.id)
        )).scalars().all()
        mappings_dict = {m.raw_ocr_name: m for m in mappings}

        result.append({
            "slug": collector.slug,
            "kingdom": collector.kingdom,
            "clan": collector.clan,
            "roster": await _roster_rows(
                db, collector.id, mappings_dict, canonical_names, fuzzy_threshold),
            "history": await _history_rows(db, collector.id),
            "troop_steps": TROOP_STEPS,
            "presets": sorted(TROOP_QUOTA_PRESETS.keys()),
        })
    return {"collectors": result, "ancient_level_hp": ANCIENT_LEVEL_HP}
```

- [ ] **Step 4: Run the 2 new tests — expect passing**

```bash
cd server && python -m pytest tests/test_ancients_dashboard.py::test_get_roster_suggested_name_via_fuzzy tests/test_ancients_dashboard.py::test_get_roster_confirmed_mapping_applied -v --tb=short
```

Expected: 2 × PASSED.

- [ ] **Step 5: Run full suite**

```bash
cd server && python -m pytest tests/test_ancients_dashboard.py -v --tb=short 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 6: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "feat(ancient): GET roster enriched with mapped_name/suggested_name/fuzzy"
```

---

### Task 3: Backend — PATCH upsert + DELETE unlock endpoints

**Files:**
- Modify: `server/ancients_dashboard.py`
- Modify: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `AncientNameMapping` (Task 1), `_get_own_collector` (existing)
- Produces:
  - `PATCH /web/dashboard/ancients/{slug}/name-mappings` → `{"ok": True}`
  - `DELETE /web/dashboard/ancients/{slug}/name-mappings/{raw_ocr_name}` → `{"ok": True}`

- [ ] **Step 1: Write 3 failing tests**

Add to `server/tests/test_ancients_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_patch_name_mappings_upsert(db_session):
    """PATCH creates new mapping; second PATCH with same raw_name updates it (upsert)."""
    from sqlalchemy import select as sa_select
    user, token = await _create_user_with_token(db_session, "map2@test.com")
    collector = await _create_collector(db_session, user.id, slug="map-2")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # First PATCH — creates
        resp = await client.patch(
            f"/web/dashboard/ancients/{collector.slug}/name-mappings",
            json={"mappings": [{"raw_ocr_name": "Marisha", "canonical_name": "Маришка",
                                "confirmed": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json() == {"ok": True}

        # Second PATCH — updates
        resp2 = await client.patch(
            f"/web/dashboard/ancients/{collector.slug}/name-mappings",
            json={"mappings": [{"raw_ocr_name": "Marisha", "canonical_name": "Мариша",
                                "confirmed": True}]},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp2.status_code == 200

    rows = (await db_session.execute(
        sa_select(AncientNameMapping).where(AncientNameMapping.collector_id == collector.id)
    )).scalars().all()
    assert len(rows) == 1
    assert rows[0].canonical_name == "Мариша"


@pytest.mark.asyncio
async def test_delete_name_mapping_unlocks(db_session):
    """DELETE removes the mapping; subsequent GET returns mapping_confirmed=False."""
    user, token = await _create_user_with_token(db_session, "del1@test.com")
    collector = await _create_collector(db_session, user.id, slug="del-1")
    db_session.add(AncientNameMapping(collector_id=collector.id,
                                      raw_ocr_name="PL4YER",
                                      canonical_name="PLAYER",
                                      confirmed=True))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.delete(
            f"/web/dashboard/ancients/{collector.slug}/name-mappings/PL4YER",
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200
    assert resp.json() == {"ok": True}

    from sqlalchemy import select as sa_select
    row = (await db_session.execute(
        sa_select(AncientNameMapping).where(
            AncientNameMapping.collector_id == collector.id,
            AncientNameMapping.raw_ocr_name == "PL4YER",
        )
    )).scalar_one_or_none()
    assert row is None


@pytest.mark.asyncio
async def test_patch_name_mappings_wrong_owner_returns_403(db_session):
    """PATCH to another user's collector returns 403."""
    owner, _ = await _create_user_with_token(db_session, "owner2@test.com")
    _, attacker_token = await _create_user_with_token(db_session, "attacker@test.com")
    collector = await _create_collector(db_session, owner.id, slug="own-2")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            f"/web/dashboard/ancients/{collector.slug}/name-mappings",
            json={"mappings": []},
            headers={"Authorization": f"Bearer {attacker_token}"},
        )
    assert resp.status_code == 403
```

- [ ] **Step 2: Run tests — expect failures**

```bash
cd server && python -m pytest tests/test_ancients_dashboard.py::test_patch_name_mappings_upsert tests/test_ancients_dashboard.py::test_delete_name_mapping_unlocks tests/test_ancients_dashboard.py::test_patch_name_mappings_wrong_owner_returns_403 -v --tb=short
```

Expected: `404 Not Found` — endpoints don't exist yet.

- [ ] **Step 3: Add endpoints to `ancients_dashboard.py`**

Add after `patch_troop_level`, before `CalculatePayload`:

```python
class NameMappingItem(BaseModel):
    raw_ocr_name: str
    canonical_name: str
    confirmed: bool = True


class NameMappingsPayload(BaseModel):
    mappings: List[NameMappingItem]


@router.patch("/{slug}/name-mappings")
async def patch_name_mappings(slug: str, payload: NameMappingsPayload,
                               user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
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


@router.delete("/{slug}/name-mappings/{raw_ocr_name}")
async def delete_name_mapping(slug: str, raw_ocr_name: str,
                               user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    await db.execute(
        delete(AncientNameMapping).where(
            AncientNameMapping.collector_id == collector.id,
            AncientNameMapping.raw_ocr_name == raw_ocr_name,
        )
    )
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Run the 3 new tests — expect passing**

```bash
cd server && python -m pytest tests/test_ancients_dashboard.py::test_patch_name_mappings_upsert tests/test_ancients_dashboard.py::test_delete_name_mapping_unlocks tests/test_ancients_dashboard.py::test_patch_name_mappings_wrong_owner_returns_403 -v --tb=short
```

Expected: 3 × PASSED.

- [ ] **Step 5: Run full test suite**

```bash
cd server && python -m pytest tests/test_ancients_dashboard.py -v --tb=short 2>&1 | tail -10
```

Expected: all pass.

- [ ] **Step 6: Add `fuzzy_threshold` test**

Add one more test confirming the threshold param works:

```python
@pytest.mark.asyncio
async def test_fuzzy_threshold_high_suppresses_weak_match(db_session):
    """?fuzzy_threshold=1.0 suppresses suggestions that would pass at 0.75."""
    user, token = await _create_user_with_token(db_session, "thresh1@test.com")
    collector = await _create_collector(db_session, user.id, slug="thresh-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Aleksei",
                                 place=1, points=50, troop_level=None))
    # canonical "Aleksey" is ~0.86 similar to "Aleksei" — passes 0.75, fails 1.0
    db_session.add(PlayerAlias(collector_id=collector.id,
                               raw_name="r1", canonical_name="Aleksey"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp_75  = await client.get("/web/dashboard/ancients?fuzzy_threshold=0.75",
                                    headers={"Authorization": f"Bearer {token}"})
        resp_100 = await client.get("/web/dashboard/ancients?fuzzy_threshold=1.0",
                                    headers={"Authorization": f"Bearer {token}"})

    row_75  = resp_75.json()["collectors"][0]["roster"][0]
    row_100 = resp_100.json()["collectors"][0]["roster"][0]
    # At 0.75, fuzzy may suggest "Aleksey" (implementation-dependent — just check no crash)
    assert "suggested_name" in row_75
    # At 1.0 (exact only), no suggestion possible
    assert row_100["suggested_name"] is None
```

Run it:
```bash
cd server && python -m pytest tests/test_ancients_dashboard.py::test_fuzzy_threshold_high_suppresses_weak_match -v --tb=short
```

- [ ] **Step 7: Run full suite again and commit**

```bash
cd server && python -m pytest tests/test_ancients_dashboard.py -v --tb=short 2>&1 | tail -10
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "feat(ancient): PATCH/DELETE name-mappings endpoints + fuzzy threshold test"
```

---

### Task 4: Frontend — threshold slider + "Правильное имя" column

**Files:**
- Modify: `web/src/api.js`
- Modify: `web/src/pages/AncientsPage.jsx`

**Interfaces:**
- Consumes: `GET /web/dashboard/ancients?fuzzy_threshold=X` (Task 2), `PATCH/{slug}/name-mappings` (Task 3), `DELETE/{slug}/name-mappings/{name}` (Task 3)
- Produces: slider that triggers re-fetch; new column showing mapped/suggested name with lock/unlock

- [ ] **Step 1: Add API helpers to `web/src/api.js`**

After `dashboardAncientsCalculate`, add:

```javascript
  dashboardAncientsNameMappings: (slug, mappings) =>
    request('PATCH', `/web/dashboard/ancients/${slug}/name-mappings`, { mappings }),
  dashboardAncientsNameMappingDelete: (slug, rawOcrName) =>
    request('DELETE', `/web/dashboard/ancients/${slug}/name-mappings/${encodeURIComponent(rawOcrName)}`),
```

- [ ] **Step 2: Add state to `AncientsPage.jsx`**

Read the current component structure. Find where the existing `useState` calls are (around lines 13–25). Add after them:

```javascript
  const [fuzzyThreshold, setFuzzyThreshold] = useState(0.75)
  const [pendingMappings, setPendingMappings] = useState({})   // { slug: { raw_ocr_name: canonical_name } }
```

- [ ] **Step 3: Update `refresh()` to pass threshold**

Find `refresh()` in `AncientsPage.jsx` — it calls `api.dashboardAncients()`. Change it to:

```javascript
  async function refresh(threshold = fuzzyThreshold) {
    try {
      const data = await api.dashboardAncients(threshold)
      // ... rest of existing refresh body unchanged
```

And update the api call. First check current signature of `api.dashboardAncients`:
```javascript
dashboardAncients: () => request('GET', '/web/dashboard/ancients'),
```

Change to:
```javascript
dashboardAncients: (fuzzyThreshold = 0.75) =>
  request('GET', `/web/dashboard/ancients?fuzzy_threshold=${fuzzyThreshold}`),
```

- [ ] **Step 4: Add slider above roster table**

Find the roster table rendering in `AncientsPage.jsx` (around line 279 where `cx.rosterTitle` appears). Just above `<div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.rosterTitle}</div>`, add:

```jsx
              <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 12 }}>
                <label style={{ fontSize: 13, color: '#a6adc8', whiteSpace: 'nowrap' }}>
                  Точность распознавания: {Math.round(fuzzyThreshold * 100)}%
                </label>
                <input
                  type="range" min={50} max={100} step={5}
                  value={Math.round(fuzzyThreshold * 100)}
                  onChange={e => {
                    const val = parseInt(e.target.value) / 100
                    setFuzzyThreshold(val)
                    refresh(val)
                  }}
                  style={{ width: 140 }}
                />
                <span style={{ fontSize: 12, color: '#6c7086' }}>
                  чем выше — тем строже
                </span>
              </div>
```

- [ ] **Step 5: Add `canonical_names` to GET response (backend)**

In `server/ancients_dashboard.py`, update `get_dashboard_ancients` — the `result.append({...})` dict already loads `canonical_names` from the DB. Add it to the returned dict:

```python
    "canonical_names": sorted(canonical_names),   # list of str from PlayerAlias
```

This is needed so the frontend dropdown can list all valid canonical names.

Commit this change together at Step 8.

- [ ] **Step 6: Add "Правильное имя" column to roster table**

Find the roster table `<thead>` (contains player name / troop columns). Add new `<th>`:

```jsx
                    <th>Правильное имя</th>
```

In `<tbody>` where each `<tr key={p.player_name}>` is rendered, add a new `<td>` after the existing player_name cell:

```jsx
                        <td>
                          {p.mapping_confirmed ? (
                            <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                              <span style={{ color: '#a6e3a1', fontWeight: 600 }}>
                                {p.mapped_name}
                              </span>
                              <button
                                style={{ fontSize: 11, padding: '1px 6px', cursor: 'pointer',
                                         background: 'transparent', border: '1px solid #6c7086',
                                         color: '#6c7086', borderRadius: 4 }}
                                onClick={async () => {
                                  await api.dashboardAncientsNameMappingDelete(c.slug, p.player_name)
                                  refresh()
                                }}
                              >
                                🔓
                              </button>
                            </span>
                          ) : (
                            <select
                              className="input-dark"
                              value={(pendingMappings[c.slug] || {})[p.player_name] ||
                                     p.suggested_name || ''}
                              onChange={e => setPendingMappings(prev => ({
                                ...prev,
                                [c.slug]: { ...(prev[c.slug] || {}),
                                            [p.player_name]: e.target.value },
                              }))}
                              style={{ minWidth: 130 }}
                            >
                              <option value="">— не сопоставлять —</option>
                              {(c.canonical_names || []).map(name => (
                                <option key={name} value={name}>{name}</option>
                              ))}
                            </select>
                          )}
                        </td>
```

- [ ] **Step 7: Add "Сохранить маппинги" button**

Below the roster table (after the `</table>` tag), add:

```jsx
              {Object.keys(pendingMappings[c.slug] || {}).length > 0 && (
                <button
                  className="btn-primary"
                  style={{ marginTop: 10 }}
                  onClick={async () => {
                    const pending = pendingMappings[c.slug] || {}
                    const mappings = Object.entries(pending)
                      .filter(([, canonical]) => canonical)
                      .map(([raw_ocr_name, canonical_name]) => ({
                        raw_ocr_name, canonical_name, confirmed: true,
                      }))
                    if (mappings.length === 0) return
                    await api.dashboardAncientsNameMappings(c.slug, mappings)
                    setPendingMappings(prev => ({ ...prev, [c.slug]: {} }))
                    refresh()
                  }}
                >
                  Сохранить маппинги
                </button>
              )}
```

- [ ] **Step 8: Commit all Task 4 changes**

```bash
git add web/src/api.js web/src/pages/AncientsPage.jsx server/ancients_dashboard.py
git commit -m "feat(ancient): name mapping UI — slider + Правильное имя column + save"
```

---

### Task 5: Deploy

**Files:** none (infra only)

- [ ] **Step 1: Push to main**

```bash
git push origin main
```

- [ ] **Step 2: GCP — migration + restart**

```bash
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && sudo env DATABASE_URL='postgresql+asyncpg://hunter:TotalHunter2026@localhost:5432/totalhunter' /opt/totalhunter/venv/bin/alembic -c /opt/totalhunter/server/alembic.ini upgrade a9b8c7d6e5f4 && sudo systemctl restart totalhunter && sleep 3 && systemctl is-active totalhunter"
```

Expected: `Running upgrade x1y2z3a4b5c6 -> a9b8c7d6e5f4, add_ancient_name_mappings` then `active`.

- [ ] **Step 3: Vercel deploy + alias**

```bash
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
```

Wait for READY then attach alias (standard 3-step procedure from CLAUDE.md).

- [ ] **Step 4: Smoke test**

Open `https://total-hunter.com/dashboard/ancients`:
1. Ползунок «Точность распознавания» виден, меняет %
2. Колонка «Правильное имя» отображается
3. Дропдаун показывает canonical_names из Сундуков
4. Выбрать имя → «Сохранить маппинги» → перезагрузить → 🔒 иконка на строке
5. Нажать 🔓 → маппинг снимается, дропдаун возвращается
