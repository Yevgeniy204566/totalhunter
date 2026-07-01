# Ancient Quota Shortfall Formatting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Highlight roster rows in the "Древний" (Ancient) dashboard table when a
player's actual points fall short of their computed quota, using 3 leader-configurable
percentage thresholds (light/medium/critical), reusing the existing Chests color
palette.

**Architecture:** A new pure `shortfall_pct(quota, points)` function in
`server/ancient_quota.py` computes the percentage shortfall (guarding division-by-zero
and negative-shortfall-on-overshoot per the spec). Three new nullable `Float` columns
on `ChestCollector` store leader-configurable thresholds (defaulting to 10/30/60 when
unset), exposed via a new `PATCH /{slug}/quota-thresholds` endpoint and included in the
dashboard GET response. The frontend adds three number inputs and a
`rowShortfallClass()` helper that maps a row's `shortfall_pct` + the collector's
thresholds to one of four CSS classes (no highlight, `row-quota-light` (new),
`row-lagging`, `row-danger` — the latter two already exist).

**Tech Stack:** Python 3.13, FastAPI, SQLAlchemy async, Alembic, pytest +
pytest-asyncio, React (plain JSX, no test framework for this file — matches existing
project convention).

## Global Constraints

- Formula: `shortfall_pct = (quota - points) / quota * 100`.
- `quota is None` or `points is None` → `shortfall_pct` is `None` (no data, no highlight).
- `quota == 0` → `shortfall_pct` is `None` (explicit division-by-zero guard, owner-mandated).
- `points > quota` (overshoot) → `shortfall_pct` is negative, falls into the "no
  highlight" zone (`<= light_pct`) — not an error, not a separate color, tested
  explicitly (owner-mandated regression test, not just positive-shortfall cases).
- Threshold storage is per-`ChestCollector`, nullable, defaults 10/30/60 when `None`.
- `PATCH /{slug}/quota-thresholds` is owner-only (uses `_get_own_collector`, same as
  `/ancient-visibility` — NOT `_get_own_or_editor_collector`, which is used by
  `/troop-level` and `/rank`).
- No new frontend automated test layer — verification is `npm run build`.

---

### Task 1: `shortfall_pct` function + `ChestCollector` threshold columns + migration

**Files:**
- Modify: `server/models.py:413` (add 3 columns to `ChestCollector`)
- Modify: `server/ancient_quota.py` (add `shortfall_pct`)
- Create: `server/alembic/versions/s1h2o3r4t5f6_add_ancient_quota_thresholds.py`
- Test: `server/tests/test_ancient_quota.py`

**Interfaces:**
- Produces: `shortfall_pct(quota: float | None, points: int | None) -> float | None`
  (importable from `ancient_quota.py`); `ChestCollector.ancient_shortfall_light_pct`,
  `.ancient_shortfall_medium_pct`, `.ancient_shortfall_critical_pct` (all
  `Optional[float]`, default `None` at the DB level — the 10/30/60 fallback happens in
  application code, not a DB `server_default`, so Task 2 can apply it uniformly).

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_ancient_quota.py`:

```python
from ancient_quota import shortfall_pct


def test_shortfall_pct_basic_case():
    assert shortfall_pct(100, 50) == pytest.approx(50.0)


def test_shortfall_pct_zero_shortfall():
    assert shortfall_pct(100, 100) == pytest.approx(0.0)


def test_shortfall_pct_full_miss():
    assert shortfall_pct(100, 0) == pytest.approx(100.0)


def test_shortfall_pct_zero_quota_returns_none():
    # Division-by-zero guard — owner-mandated explicit test.
    assert shortfall_pct(0, 50) is None


def test_shortfall_pct_overshoot_is_negative_not_an_error():
    # Owner-mandated: exceeding quota must not raise, and must be negative
    # (falls into the "no highlight" zone at the call site, not a special case here).
    assert shortfall_pct(100, 150) == pytest.approx(-50.0)


def test_shortfall_pct_none_quota_returns_none():
    assert shortfall_pct(None, 50) is None


def test_shortfall_pct_none_points_returns_none():
    assert shortfall_pct(100, None) is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancient_quota.py -k shortfall -v`
Expected: FAIL — `ImportError: cannot import name 'shortfall_pct' from 'ancient_quota'`.

- [ ] **Step 3: Implement `shortfall_pct`**

Append to the end of `server/ancient_quota.py`:

```python
def shortfall_pct(quota: float | None, points: int | None) -> float | None:
    if quota is None or points is None:
        return None
    if quota == 0:
        return None
    return (quota - points) / quota * 100.0
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancient_quota.py -v`
Expected: PASS — full file green.

- [ ] **Step 5: Add the 3 columns to `ChestCollector`**

Modify `server/models.py` — right after line 413 (`ancient_hidden_at = Column(...)`,
the last field before the class ends), add:

```python
    ancient_shortfall_light_pct    = Column(Float, nullable=True)
    ancient_shortfall_medium_pct   = Column(Float, nullable=True)
    ancient_shortfall_critical_pct = Column(Float, nullable=True)
```

(`Float` is already imported at the top of `models.py` — no import changes needed.)

- [ ] **Step 6: Write the Alembic migration**

Create `server/alembic/versions/s1h2o3r4t5f6_add_ancient_quota_thresholds.py`:

```python
"""add_ancient_quota_thresholds

Revision ID: s1h2o3r4t5f6
Revises: m1n2u3a4l5r6
Create Date: 2026-07-01

Three leader-configurable percentage thresholds (light/medium/critical) driving
roster-row conditional formatting for quota shortfall. NULL means "use the
application-level default" (10/30/60) — not stored as a DB server_default so the
distinction between "never configured" and "explicitly set to 10" stays visible.
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 's1h2o3r4t5f6'
down_revision: Union[str, None] = 'm1n2u3a4l5r6'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        'chest_collectors',
        sa.Column('ancient_shortfall_light_pct', sa.Float(), nullable=True),
    )
    op.add_column(
        'chest_collectors',
        sa.Column('ancient_shortfall_medium_pct', sa.Float(), nullable=True),
    )
    op.add_column(
        'chest_collectors',
        sa.Column('ancient_shortfall_critical_pct', sa.Float(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column('chest_collectors', 'ancient_shortfall_critical_pct')
    op.drop_column('chest_collectors', 'ancient_shortfall_medium_pct')
    op.drop_column('chest_collectors', 'ancient_shortfall_light_pct')
```

- [ ] **Step 7: Verify the migration is the sole head**

Run: `cd server && python -m alembic heads`
Expected: `s1h2o3r4t5f6 (head)` — exactly one head, confirming this migration chains
cleanly onto `m1n2u3a4l5r6` (the head before this change) without creating a branch.

- [ ] **Step 8: Commit**

```bash
git add server/models.py server/ancient_quota.py server/tests/test_ancient_quota.py server/alembic/versions/s1h2o3r4t5f6_add_ancient_quota_thresholds.py
git commit -m "$(cat <<'EOF'
feat(ancients): shortfall_pct formula + quota-threshold columns

Division-by-zero and overshoot (points > quota) are explicitly handled:
zero quota returns None (no highlight possible), overshoot returns a
negative percentage that falls into the no-highlight zone at the call site.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: Backend — thresholds endpoint + wiring into roster rows

**Files:**
- Modify: `server/ancients_dashboard.py:74-139` (`_roster_rows`), `:157-229`
  (`get_dashboard_ancients`), add new `PATCH /{slug}/quota-thresholds` route
- Test: `server/tests/test_ancients_dashboard.py`

**Interfaces:**
- Consumes: `shortfall_pct` from Task 1 (`server/ancient_quota.py`);
  `ChestCollector.ancient_shortfall_{light,medium,critical}_pct` columns from Task 1.
- Produces: each roster row dict now includes `"shortfall_pct"`; each collector entry
  in the `GET /dashboard/ancients` response now includes `"quota_thresholds":
  {"light_pct": float, "medium_pct": float, "critical_pct": float}` (always concrete
  floats — defaults substituted for `None` at this layer, per Global Constraints).

- [ ] **Step 1: Write the failing tests**

Add to `server/tests/test_ancients_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_get_dashboard_returns_default_thresholds(db_session):
    user, token = await _create_user_with_token(db_session, "thresh1@test.com")
    await _create_collector(db_session, user.id, slug="thresh-1")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    thresholds = resp.json()["collectors"][0]["quota_thresholds"]
    assert thresholds == {"light_pct": 10.0, "medium_pct": 30.0, "critical_pct": 60.0}


@pytest.mark.asyncio
async def test_patch_quota_thresholds_saves_and_reflects_in_get(db_session):
    user, token = await _create_user_with_token(db_session, "thresh2@test.com")
    await _create_collector(db_session, user.id, slug="thresh-2")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        patch_resp = await client.patch(
            "/web/dashboard/ancients/thresh-2/quota-thresholds",
            json={"light_pct": 15.0, "medium_pct": 40.0, "critical_pct": 70.0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert patch_resp.status_code == 200

        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    thresholds = resp.json()["collectors"][0]["quota_thresholds"]
    assert thresholds == {"light_pct": 15.0, "medium_pct": 40.0, "critical_pct": 70.0}


@pytest.mark.asyncio
async def test_patch_quota_thresholds_rejects_non_owner_editor(db_session):
    owner, _ = await _create_user_with_token(db_session, "thresh3owner@test.com")
    editor, editor_token = await _create_user_with_token(db_session, "thresh3editor@test.com")
    collector = await _create_collector(db_session, owner.id, slug="thresh-3")
    db_session.add(AncientEditor(collector_id=collector.id, user_id=editor.id,
                                 expires_at=datetime.now(timezone.utc) + timedelta(days=30)))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.patch(
            "/web/dashboard/ancients/thresh-3/quota-thresholds",
            json={"light_pct": 15.0, "medium_pct": 40.0, "critical_pct": 70.0},
            headers={"Authorization": f"Bearer {editor_token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_roster_shortfall_pct_present_when_quota_and_points_exist(db_session):
    user, token = await _create_user_with_token(db_session, "shortfallget1@test.com")
    collector = await _create_collector(db_session, user.id, slug="shortfallget-1")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Иванов",
                                 place=1, points=50, rank="Глава"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        calc_resp = await client.post(
            "/web/dashboard/ancients/shortfallget-1/calculate",
            json={"strategy": "A", "summon_levels": [81], "amplification_coef": 1.0,
                  "officer_count": 1, "veteran_count": 0},
            headers={"Authorization": f"Bearer {token}"},
        )
        assert calc_resp.status_code == 200
        officer_quota = calc_resp.json()["result"]["officer_quota"]

        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    expected = (officer_quota - 50) / officer_quota * 100.0
    assert row["shortfall_pct"] == pytest.approx(expected)


@pytest.mark.asyncio
async def test_roster_shortfall_pct_none_without_quota(db_session):
    user, token = await _create_user_with_token(db_session, "shortfallget2@test.com")
    collector = await _create_collector(db_session, user.id, slug="shortfallget-2")
    db_session.add(AncientRoster(collector_id=collector.id, player_name="Петров",
                                 place=1, points=50, rank=None))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/ancients",
                                headers={"Authorization": f"Bearer {token}"})
    row = resp.json()["collectors"][0]["roster"][0]
    assert row["shortfall_pct"] is None
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py -k "threshold or shortfall" -v`
Expected: FAIL — `PATCH /{slug}/quota-thresholds` doesn't exist (404), roster rows and
collector entries have no `"shortfall_pct"`/`"quota_thresholds"` keys (`KeyError`).

- [ ] **Step 3: Import `shortfall_pct`**

Modify the import at `server/ancients_dashboard.py:21-24` from:
```python
from ancient_quota import (
    ANCIENT_LEVEL_HP, OFFICER_RANKS, RANKS, VALID_PRESETS, parse_troop_level,
    split_strategy_a, split_strategy_b, total_quota_millions,
)
```
to:
```python
from ancient_quota import (
    ANCIENT_LEVEL_HP, OFFICER_RANKS, RANKS, VALID_PRESETS, parse_troop_level,
    shortfall_pct, split_strategy_a, split_strategy_b, total_quota_millions,
)
```

- [ ] **Step 4: Add `shortfall_pct` to `_roster_rows`**

Modify `server/ancients_dashboard.py:127-138` (the `result.append({...})` block inside
`_roster_rows`) from:
```python
        result.append({
            "player_name": raw,
            "place": r.AncientRoster.place,
            "points": r.AncientRoster.points,
            "troop_level": r.AncientRoster.troop_level or r.profile_troop,
            "rank": r.AncientRoster.rank,
            "quota": quota,
            "mapped_name": mapped_name,
            "suggested_name": suggested_name,
            "mapping_confirmed": confirmed,
            "is_alias_source": suggested_name is not None,  # True = авто-найдено из Сундуков
        })
```
to:
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

- [ ] **Step 5: Add `quota_thresholds` to the collector entry + the new PATCH endpoint**

Modify `server/ancients_dashboard.py:218-229` (the `result.append({...})` block inside
`get_dashboard_ancients`) from:
```python
        result.append({
            "slug": collector.slug,
            "kingdom": collector.kingdom,
            "clan": collector.clan,
            "is_owner": is_owner,
            "canonical_names": canonical_names,
            "roster": await _roster_rows(
                db, collector.id, mappings_dict, canonical_names, fuzzy_threshold,
                latest_calc),
            "history": await _history_rows(db, collector.id),
            "presets": sorted(VALID_PRESETS),
        })
```
to:
```python
        result.append({
            "slug": collector.slug,
            "kingdom": collector.kingdom,
            "clan": collector.clan,
            "is_owner": is_owner,
            "canonical_names": canonical_names,
            "roster": await _roster_rows(
                db, collector.id, mappings_dict, canonical_names, fuzzy_threshold,
                latest_calc),
            "history": await _history_rows(db, collector.id),
            "presets": sorted(VALID_PRESETS),
            "quota_thresholds": {
                "light_pct": collector.ancient_shortfall_light_pct if collector.ancient_shortfall_light_pct is not None else 10.0,
                "medium_pct": collector.ancient_shortfall_medium_pct if collector.ancient_shortfall_medium_pct is not None else 30.0,
                "critical_pct": collector.ancient_shortfall_critical_pct if collector.ancient_shortfall_critical_pct is not None else 60.0,
            },
        })
```

Add this new route immediately after `set_ancient_visibility` (which ends at
`server/ancients_dashboard.py:252` with `return {"ok": True}`):

```python
class QuotaThresholdsPayload(BaseModel):
    light_pct: float
    medium_pct: float
    critical_pct: float


@router.patch("/{slug}/quota-thresholds")
async def set_quota_thresholds(slug: str, payload: QuotaThresholdsPayload,
                               user: User = Depends(get_web_user),
                               db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, slug, user)
    collector.ancient_shortfall_light_pct = payload.light_pct
    collector.ancient_shortfall_medium_pct = payload.medium_pct
    collector.ancient_shortfall_critical_pct = payload.critical_pct
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=8f3a9b2e1d7c4f6a0e5b8d3c9a2f1e4b7d6c3a0f9e2b5d8c1a4f7e0b3d6c9a2 python -m pytest tests/test_ancients_dashboard.py tests/test_ancient_quota.py tests/test_ancient_retention.py -v`
Expected: PASS — every test green, including all 5 new tests and every pre-existing
test.

- [ ] **Step 7: Commit**

```bash
git add server/ancients_dashboard.py server/tests/test_ancients_dashboard.py
git commit -m "$(cat <<'EOF'
feat(ancients): PATCH /quota-thresholds endpoint + shortfall_pct in roster rows

Owner-only (mirrors /ancient-visibility). GET response now includes
quota_thresholds per collector (defaults 10/30/60 substituted for unset
NULL columns) and shortfall_pct per roster row.

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Frontend — threshold inputs + row highlight

**Files:**
- Modify: `web/src/styles/theme.css` (add `.row-quota-light`)
- Modify: `web/src/api.js` (add `dashboardAncientsQuotaThresholds`)
- Modify: `web/src/pages/AncientsPage.jsx` (add `rowShortfallClass`, 3 number inputs,
  apply the class to roster `<tr>`)
- Modify: `web/src/dashboard_content.js`, `web/src/dashboard_content.en.js` (add
  threshold-label i18n keys)

**Interfaces:**
- Consumes: `PATCH /{slug}/quota-thresholds`, `quota_thresholds` (per collector) and
  `shortfall_pct` (per roster row) from Task 2.
- Produces: nothing consumed by later tasks — final integration point for this plan.

- [ ] **Step 1: Add the CSS class**

In `web/src/styles/theme.css`, add this line immediately after line 429
(`.row-danger td { color: #FF6961; }`):
```css
.row-quota-light td { color: #F5D76E; }
```

- [ ] **Step 2: Add the API call**

In `web/src/api.js`, add this line immediately after `dashboardAncientsRank`:
```javascript
  dashboardAncientsQuotaThresholds: (slug, lightPct, mediumPct, criticalPct) =>
    request('PATCH', `/web/dashboard/ancients/${slug}/quota-thresholds`,
            { light_pct: lightPct, medium_pct: mediumPct, critical_pct: criticalPct }),
```

- [ ] **Step 3: Add i18n keys**

In `web/src/dashboard_content.js`, modify the line (currently line 92-93):
```javascript
    player: 'Игрок', place: 'Место', points: 'Очки', troopLevel: 'Состав',
    rank: 'Звание', quota: 'Квота',
    noTroopLevel: 'не указан',
```
to:
```javascript
    player: 'Игрок', place: 'Место', points: 'Очки', troopLevel: 'Состав',
    rank: 'Звание', quota: 'Квота',
    noTroopLevel: 'не указан',
    thresholdsTitle: 'Пороги недобора квоты (%)',
    thresholdLight: 'Лёгкий', thresholdMedium: 'Средний', thresholdCritical: 'Критический',
```

In `web/src/dashboard_content.en.js`, modify the corresponding line similarly:
```javascript
    player: 'Player', place: 'Place', points: 'Points', troopLevel: 'Composition',
    rank: 'Rank', quota: 'Quota',
    noTroopLevel: 'not set',
    thresholdsTitle: 'Quota shortfall thresholds (%)',
    thresholdLight: 'Light', thresholdMedium: 'Medium', thresholdCritical: 'Critical',
```

- [ ] **Step 4: Add `rowShortfallClass` helper**

In `web/src/pages/AncientsPage.jsx`, add this function immediately after
`clientFuzzyMatch` (currently ending at line 43):

```javascript
function rowShortfallClass(shortfallPct, thresholds) {
  if (shortfallPct == null || !thresholds) return ''
  if (shortfallPct <= thresholds.light_pct) return ''
  if (shortfallPct <= thresholds.medium_pct) return 'row-quota-light'
  if (shortfallPct <= thresholds.critical_pct) return 'row-lagging'
  return 'row-danger'
}
```

- [ ] **Step 5: Add threshold inputs and handler**

Add this handler function immediately after `handleRankChange`:

```javascript
  async function handleThresholdChange(slug, thresholds, field, value) {
    const next = { ...thresholds, [field]: parseFloat(value) || 0 }
    try {
      await api.dashboardAncientsQuotaThresholds(
        slug, next.light_pct, next.medium_pct, next.critical_pct)
      refresh()
    } catch (e) {
      alert(e.message || 'Ошибка сохранения')
    }
  }
```

Add the 3 inputs inside the per-collector card, immediately before the roster table's
enclosing `<div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.rosterTitle}</div>`
(currently line 509):

```javascript
              <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center', flexWrap: 'wrap' }}>
                <span style={{ fontSize: 12, color: 'var(--on-surface2)' }}>{cx.thresholdsTitle}:</span>
                <label style={{ fontSize: 12, display: 'flex', gap: 4, alignItems: 'center' }}>
                  {cx.thresholdLight}
                  <input type="number" className="input-dark" style={{ width: 60 }}
                    value={c.quota_thresholds.light_pct}
                    onChange={e => handleThresholdChange(c.slug, c.quota_thresholds, 'light_pct', e.target.value)} />
                </label>
                <label style={{ fontSize: 12, display: 'flex', gap: 4, alignItems: 'center' }}>
                  {cx.thresholdMedium}
                  <input type="number" className="input-dark" style={{ width: 60 }}
                    value={c.quota_thresholds.medium_pct}
                    onChange={e => handleThresholdChange(c.slug, c.quota_thresholds, 'medium_pct', e.target.value)} />
                </label>
                <label style={{ fontSize: 12, display: 'flex', gap: 4, alignItems: 'center' }}>
                  {cx.thresholdCritical}
                  <input type="number" className="input-dark" style={{ width: 60 }}
                    value={c.quota_thresholds.critical_pct}
                    onChange={e => handleThresholdChange(c.slug, c.quota_thresholds, 'critical_pct', e.target.value)} />
                </label>
              </div>

              <div style={{ marginBottom: 8, fontWeight: 600 }}>{cx.rosterTitle}</div>
```

- [ ] **Step 6: Apply the class to roster rows**

Modify the roster row's opening tag (currently `<tr key={p.player_name}>` at line 545)
to:
```javascript
                        <tr key={p.player_name}
                          className={rowShortfallClass(p.shortfall_pct, c.quota_thresholds)}>
```

- [ ] **Step 7: Manual verification**

Run: `cd web && npm run build`
Expected: build succeeds with no errors.

- [ ] **Step 8: Commit**

```bash
git add web/src/styles/theme.css web/src/api.js web/src/pages/AncientsPage.jsx web/src/dashboard_content.js web/src/dashboard_content.en.js
git commit -m "$(cat <<'EOF'
feat(ancients): quota shortfall row highlighting with leader-set thresholds

Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>
EOF
)"
```

## Self-Review Notes

- Spec coverage: `shortfall_pct` formula with zero-quota guard and overshoot handling
  (Task 1), threshold storage + migration (Task 1), `PATCH /quota-thresholds` owner-only
  endpoint (Task 2), `quota_thresholds` defaults in GET response (Task 2),
  `shortfall_pct` per roster row (Task 2), row highlighting reusing
  `row-lagging`/`row-danger` plus new `row-quota-light` (Task 3), leader-editable
  percentage inputs (Task 3) — all covered.
- Placeholder scan: none found — every step has literal code/commands.
- Type consistency: `shortfall_pct(quota, points)` defined in Task 1, imported and
  called identically in Task 2 (`shortfall_pct(quota, r.AncientRoster.points)`).
  `quota_thresholds` dict shape (`light_pct`/`medium_pct`/`critical_pct`) is identical
  between the Task 2 GET response, the Task 3 `dashboardAncientsQuotaThresholds` API
  call parameter order, and the Task 3 `rowShortfallClass`/`handleThresholdChange`
  consumers — no naming drift.
