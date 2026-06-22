# Chest Dashboard Polish + Global Presets — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Polish the `/dashboard/chests` cabinet and the public `/chests/:slug` page with four small UX fixes, and add a global preset mechanism ("T9" etc.) that pre-fills the cabinet's points/in-preset table.

**Architecture:** Backend changes are additive to the existing `server/chest_dashboard.py` router (one new computed field on the rows response, one new read-only `/presets` endpoint backed by a static Python dict — no schema/migration). Frontend changes are confined to `web/src/pages/ChestsPage.jsx`, `web/src/pages/ChestSummaryPage.jsx`, `web/src/dashboard_content.js`/`.en.js`, `web/src/api.js`, and `web/src/styles/theme.css`. Preset "loading" is a pure client-side merge into the existing unsaved row state — the existing `POST /rows` save flow is reused unchanged.

**Tech Stack:** FastAPI + SQLAlchemy async (backend), React + plain CSS (frontend), pytest + httpx (backend tests).

## Global Constraints

- Spec source of truth: `docs/superpowers/specs/2026-06-22-chest-dashboard-polish-and-presets-design.md`
- No DB schema changes / no Alembic migration in this plan — everything is additive at the read layer or purely static data.
- T9 preset values are exact, taken live from clan 229/BERS's current `ChestConfiguration` rows (verified via `psql` on prod, 2026-06-22) — see Task 2.
- T8 and other levels are explicitly out of scope — only the `CHEST_PRESETS` dict gets a new key later, no code changes needed then.
- RU/EN translation keys must both be updated together — this codebase has no fallback language key resolution.
- "В паттерне" label becomes "В пресете" (RU) / "In Pattern" becomes "In Preset" (EN) — text only, the underlying field stays `is_in_pattern`.

---

### Task 1: Backend — `total_ever` column data (всего собрано за всё время)

**Files:**
- Modify: `server/chest_dashboard.py:1-92` (imports, `_collector_rows`)
- Test: `server/tests/test_chest_dashboard.py`

**Interfaces:**
- Produces: each dict in `_collector_rows()`'s return list gains a `total_ever: int` key. `GET /web/dashboard/chests` response rows therefore include `"total_ever"` alongside the existing fields.

- [ ] **Step 1: Write the failing test**

Append to `server/tests/test_chest_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_get_chests_total_ever_sums_across_raw_aliases_sharing_catalog_id(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="total-ever-slug")
    # Two different raw OCR strings, both mapped to the same official chest
    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="Exan",
                                  catalog_id="Yogwai"))
    db_session.add(ChestTypeAlias(collector_id=collector.id, raw_type="Yokai",
                                  catalog_id="Yogwai"))
    db_session.add(ChestConfiguration(collector_id=collector.id, catalog_id="Yogwai",
                                      points=40, is_in_pattern=False,
                                      counts_toward_quota=False))
    for i in range(3):
        db_session.add(Chest(collector_id=collector.id, sender_raw="P1", sender_canonical="P1",
                             chest_type_raw="Exan", chest_type_canonical="Exan",
                             collected_at=datetime.fromisoformat(f"2026-06-2{i}T10:00:00")))
    for i in range(2):
        db_session.add(Chest(collector_id=collector.id, sender_raw="P1", sender_canonical="P1",
                             chest_type_raw="Yokai", chest_type_canonical="Yokai",
                             collected_at=datetime.fromisoformat(f"2026-06-1{i}T10:00:00")))
    # An unrelated unmapped raw type, never aliased
    db_session.add(Chest(collector_id=collector.id, sender_raw="P2", sender_canonical="P2",
                         chest_type_raw="Mystery Box", chest_type_canonical="Mystery Box",
                         collected_at=datetime.fromisoformat("2026-06-01T10:00:00")))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    rows = resp.json()["collectors"][0]["rows"]

    by_raw = {r["raw_type"]: r for r in rows}
    # Both aliases pointing at "Yogwai" report the combined total (3 + 2 = 5),
    # regardless of is_in_pattern/counts_toward_quota being False.
    assert by_raw["Exan"]["total_ever"] == 5
    assert by_raw["Yokai"]["total_ever"] == 5
    # Unmapped raw type reports just its own count
    assert by_raw["Mystery Box"]["total_ever"] == 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_chest_dashboard.py::test_get_chests_total_ever_sums_across_raw_aliases_sharing_catalog_id -v`
Expected: FAIL with `KeyError: 'total_ever'`

- [ ] **Step 3: Implement `total_ever` in `_collector_rows`**

In `server/chest_dashboard.py`, add `func` to the sqlalchemy import (line 17):

```python
from sqlalchemy import delete, func, select
```

Add a new helper right before `_collector_rows` (after `_load_catalog_options`, i.e. after line 47):

```python
async def _raw_type_counts(db: AsyncSession, collector_id: int) -> dict:
    rows = (await db.execute(
        select(Chest.chest_type_raw, func.count())
        .where(Chest.collector_id == collector_id)
        .group_by(Chest.chest_type_raw)
    )).all()
    return {raw: count for raw, count in rows}


def _total_ever_for_catalog(catalog_id: Optional[str], aliases: list, raw_counts: dict) -> int:
    if catalog_id is None:
        return 0
    return sum(raw_counts.get(a.raw_type, 0) for a in aliases if a.catalog_id == catalog_id)
```

Now modify `_collector_rows` (currently lines 50-92) to compute `raw_counts` once and attach
`total_ever` to every row it builds:

```python
async def _collector_rows(db: AsyncSession, collector: ChestCollector) -> list:
    aliases = (await db.execute(
        select(ChestTypeAlias).where(ChestTypeAlias.collector_id == collector.id)
    )).scalars().all()
    configs = (await db.execute(
        select(ChestConfiguration).where(ChestConfiguration.collector_id == collector.id)
    )).scalars().all()
    config_by_catalog_id = {c.catalog_id: c for c in configs}
    raw_counts = await _raw_type_counts(db, collector.id)

    rows = []
    seen_catalog_ids = set()
    for alias in aliases:
        config = config_by_catalog_id.get(alias.catalog_id)
        seen_catalog_ids.add(alias.catalog_id)
        rows.append({
            "raw_type": alias.raw_type, "catalog_id": alias.catalog_id,
            "custom_name": config.custom_name if config else None,
            "points": config.points if config else 0,
            "is_in_pattern": config.is_in_pattern if config else False,
            "counts_toward_quota": config.counts_toward_quota if config else False,
            "total_ever": _total_ever_for_catalog(alias.catalog_id, aliases, raw_counts),
        })
    for config in configs:
        if config.catalog_id in seen_catalog_ids:
            continue
        rows.append({
            "raw_type": None, "catalog_id": config.catalog_id,
            "custom_name": config.custom_name, "points": config.points,
            "is_in_pattern": config.is_in_pattern,
            "counts_toward_quota": config.counts_toward_quota,
            "total_ever": _total_ever_for_catalog(config.catalog_id, aliases, raw_counts),
        })

    mapped_raw_types = {a.raw_type for a in aliases}
    unmapped = (await db.execute(
        select(Chest.chest_type_raw).distinct()
        .where(Chest.collector_id == collector.id)
    )).scalars().all()
    for raw_type in unmapped:
        if raw_type in mapped_raw_types:
            continue
        rows.append({"raw_type": raw_type, "catalog_id": None, "custom_name": None,
                     "points": 0, "is_in_pattern": False, "counts_toward_quota": False,
                     "total_ever": raw_counts.get(raw_type, 0)})

    return rows
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd server && python -m pytest tests/test_chest_dashboard.py::test_get_chests_total_ever_sums_across_raw_aliases_sharing_catalog_id -v`
Expected: PASS

- [ ] **Step 5: Run the full chest dashboard test file to check no regressions**

Run: `cd server && python -m pytest tests/test_chest_dashboard.py -v`
Expected: all PASS (existing tests don't assert on the full row dict shape with `==`, only check membership of `(raw_type, catalog_id)` tuples, so the new key is safe)

- [ ] **Step 6: Commit**

```bash
git add server/chest_dashboard.py server/tests/test_chest_dashboard.py
git commit -m "feat(chests): add total_ever lifetime count to dashboard rows"
```

---

### Task 2: Backend — global presets endpoint (T9)

**Files:**
- Modify: `server/chest_dashboard.py` (add `CHEST_PRESETS` constant + new route)
- Test: `server/tests/test_chest_dashboard.py`

**Interfaces:**
- Produces: `GET /web/dashboard/chests/presets` → `{"T9": [{"catalog_id": str, "points": int, "is_in_pattern": bool}, ...]}`. Requires the same Bearer session auth as the rest of the router.

- [ ] **Step 1: Write the failing test**

Append to `server/tests/test_chest_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_get_presets_requires_auth():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests/presets")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_get_presets_returns_t9_with_valid_entries(db_session):
    _, token = await _create_user_with_token(db_session)
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests/presets",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "T9" in data
    t9 = data["T9"]
    assert len(t9) > 0
    by_catalog = {item["catalog_id"]: item for item in t9}
    assert by_catalog["Epic Crypt 35"]["points"] == 135
    assert by_catalog["Epic Crypt 35"]["is_in_pattern"] is True
    for item in t9:
        assert set(item.keys()) == {"catalog_id", "points", "is_in_pattern"}
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && python -m pytest tests/test_chest_dashboard.py::test_get_presets_returns_t9_with_valid_entries -v`
Expected: FAIL with 404 (route doesn't exist yet)

- [ ] **Step 3: Implement `CHEST_PRESETS` and the route**

In `server/chest_dashboard.py`, add the constant right after the `router = APIRouter(...)` line (line 27):

```python
router = APIRouter(prefix="/web/dashboard/chests", tags=["chest-dashboard"])

# Global ready-made point/preset templates. Maintained by hand (Claude, on request) —
# not editable through the UI. T9 mirrors clan 229/BERS's live working configuration
# as of 2026-06-22, used as the reference template. New tiers (T8, ...) are added here
# as new dict keys, no API/schema changes required.
CHEST_PRESETS = {
    "T9": [
        {"catalog_id": "Epic Crypt 35", "points": 135, "is_in_pattern": True},
        {"catalog_id": "Epic Crypt 30", "points": 80, "is_in_pattern": True},
        {"catalog_id": "Rare Crypt 30", "points": 65, "is_in_pattern": True},
        {"catalog_id": "Epic Shadow City", "points": 55, "is_in_pattern": True},
        {"catalog_id": "Epic Crypt 25", "points": 45, "is_in_pattern": True},
        {"catalog_id": "Dark Omens Chest", "points": 45, "is_in_pattern": True},
        {"catalog_id": "Epic Briareus", "points": 45, "is_in_pattern": True},
        {"catalog_id": "Epic Arachne", "points": 40, "is_in_pattern": True},
        {"catalog_id": "Elven Citadel 30", "points": 40, "is_in_pattern": True},
        {"catalog_id": "Yogwai", "points": 40, "is_in_pattern": True},
        {"catalog_id": "Epic Fire Hydra", "points": 30, "is_in_pattern": True},
        {"catalog_id": "Epic Basilisk", "points": 30, "is_in_pattern": True},
        {"catalog_id": "Epic Undead", "points": 25, "is_in_pattern": True},
        {"catalog_id": "Epic Chimera", "points": 20, "is_in_pattern": True},
        {"catalog_id": "Rare Crypt 25", "points": 20, "is_in_pattern": True},
        {"catalog_id": "Epic Hellforge", "points": 20, "is_in_pattern": True},
        {"catalog_id": "Common Crypt 25", "points": 5, "is_in_pattern": True},
        {"catalog_id": "Epic Jormungander", "points": 5, "is_in_pattern": True},
        {"catalog_id": "Epic Fenrir", "points": 5, "is_in_pattern": True},
    ],
}
```

Add the route right after `_load_catalog_options` (after line 47), before `_collector_rows`:

```python
@router.get("/presets")
async def get_presets(user: User = Depends(get_web_user)):
    return CHEST_PRESETS
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && python -m pytest tests/test_chest_dashboard.py::test_get_presets_requires_auth tests/test_chest_dashboard.py::test_get_presets_returns_t9_with_valid_entries -v`
Expected: both PASS

- [ ] **Step 5: Run the full backend test suite**

Run: `cd server && python -m pytest tests/test_chest_dashboard.py tests/test_chests.py -v`
Expected: all PASS

- [ ] **Step 6: Commit**

```bash
git add server/chest_dashboard.py server/tests/test_chest_dashboard.py
git commit -m "feat(chests): add global chest-preset templates endpoint (T9)"
```

---

### Task 3: Frontend — ChestsPage.jsx (raw-name fallback, total-ever column, presets UI, label rename)

**Files:**
- Modify: `web/src/pages/ChestsPage.jsx`
- Modify: `web/src/api.js`
- Modify: `web/src/dashboard_content.js`
- Modify: `web/src/dashboard_content.en.js`

**Interfaces:**
- Consumes: `GET /web/dashboard/chests` rows now include `total_ever` (Task 1); `GET /web/dashboard/chests/presets` (Task 2) returns `{[presetName]: [{catalog_id, points, is_in_pattern}]}`.
- Produces: no new interfaces consumed elsewhere — this is the leaf UI.

There is no frontend test runner in this project (confirmed: no `*.test.jsx` files, no jest/vitest config) — this task is verified manually in the browser per Step 6, consistent with how every prior `ChestsPage.jsx` change in this project has shipped.

- [ ] **Step 1: Add the new API call**

In `web/src/api.js`, add this line right after line 49 (`dashboardChestsSeason`):

```js
  dashboardChestsPresets: ()            => request('GET',   '/web/dashboard/chests/presets'),
```

- [ ] **Step 2: Add translation keys (RU)**

In `web/src/dashboard_content.js`, inside the `chests:` object, change line 48 and add three new keys right after it:

```js
    inPatternCol: 'В пресете',
    totalEverCol: 'Итого собрано',
    loadPresetBtn: 'Загрузить пресет',
    presetLoaded: 'Пресет применён, не забудь сохранить',
```

- [ ] **Step 3: Add translation keys (EN)**

In `web/src/dashboard_content.en.js`, inside the `chests:` object, change line 48 and add three new keys right after it:

```js
    inPatternCol: 'In Preset',
    totalEverCol: 'Total Ever',
    loadPresetBtn: 'Load Preset',
    presetLoaded: 'Preset applied — remember to save',
```

- [ ] **Step 4: Add `displayName` helper and presets state to `ChestsPage.jsx`**

In `web/src/pages/ChestsPage.jsx`, add this pure function right after the imports (after line 6):

```js
function displayName(row, catalogOptions) {
  if (row.raw_type) return row.raw_type
  if (row.custom_name) return row.custom_name
  if (row.catalog_id) {
    const opt = catalogOptions.find(o => o.catalog_id === row.catalog_id)
    if (opt) return opt.label
  }
  return '—'
}
```

In the component body, add new state right after `const [claimCode, setClaimCode] = useState('')` (line 16):

```js
  const [presets, setPresets] = useState(null)
  const [presetChoiceByCollector, setPresetChoiceByCollector] = useState({})
```

Add a `useEffect` to load presets once, right after the existing `useEffect(() => { refresh() }, [])` (line 50):

```js
  useEffect(() => { api.dashboardChestsPresets().then(setPresets).catch(() => {}) }, [])
```

- [ ] **Step 5: Add the `loadPreset` function**

Add this function right after `addRow` (after line 71, before `async function save`):

```js
  function loadPreset(slug, presetName) {
    const preset = presets?.[presetName]
    if (!preset) return
    setRowsByCollector(prev => {
      const rows = [...(prev[slug] || [])]
      for (const item of preset) {
        const idx = rows.findIndex(r => r.catalog_id === item.catalog_id)
        if (idx >= 0) {
          rows[idx] = { ...rows[idx], points: item.points, is_in_pattern: item.is_in_pattern }
        } else {
          rows.push({ raw_type: null, catalog_id: item.catalog_id, custom_name: null,
                     points: item.points, is_in_pattern: item.is_in_pattern,
                     counts_toward_quota: false })
        }
      }
      return { ...prev, [slug]: rows }
    })
    setMsg(cx.presetLoaded)
  }
```

- [ ] **Step 6: Add the presets UI and total-ever column to the table, fix the raw-name fallback**

In the `chests` tab block, right before the `<table className="chest-table">` (line 252), add:

```jsx
              {presets && Object.keys(presets).length > 0 && (
                <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
                  <select
                    className="input-dark"
                    style={{ width: 'auto' }}
                    value={presetChoiceByCollector[collector.slug] || Object.keys(presets)[0]}
                    onChange={e => setPresetChoiceByCollector(prev => ({ ...prev, [collector.slug]: e.target.value }))}
                  >
                    {Object.keys(presets).map(name => <option key={name} value={name}>{name}</option>)}
                  </select>
                  <button
                    className="btn-secondary"
                    onClick={() => loadPreset(collector.slug, presetChoiceByCollector[collector.slug] || Object.keys(presets)[0])}
                  >
                    {cx.loadPresetBtn}
                  </button>
                </div>
              )}
```

In the table header (lines 253-261), add the new column at the end:

```jsx
                <thead>
                  <tr>
                    <th>{cx.rawCol}</th>
                    <th>{cx.catalogCol}</th>
                    <th>{cx.customNameCol}</th>
                    <th>{cx.pointsCol}</th>
                    <th>{cx.inPatternCol}</th>
                    <th>{cx.quotaCol}</th>
                    <th>{cx.totalEverCol}</th>
                  </tr>
                </thead>
```

Replace the raw-name cell (line 266) `<td>{row.raw_type || '—'}</td>` with:

```jsx
                      <td>{displayName(row, collector.catalog_options)}</td>
```

Add the new cell at the end of each `<tr>` body row, right after the `counts_toward_quota` toggle cell (after line 313, before the closing `</tr>` on line 314):

```jsx
                      <td style={{ textAlign: 'right', color: 'var(--on-surface2)' }}>
                        {row.total_ever ?? 0}
                      </td>
```

- [ ] **Step 7: Manual browser verification**

Run the dev server: `cd web && npm run dev`

Open `/dashboard/chests` logged in as the owner account, and confirm:
1. Rows that previously showed "—" in the first column now show a name (custom name or catalog label) when `raw_type` is empty but `catalog_id`/`custom_name` is set.
2. A new rightmost column "Итого собрано" shows a non-zero number for rows that have collected chests.
3. A "Загрузить пресет" dropdown + button appears above the table; selecting "T9" and clicking it fills in points and turns on the "В пресете" toggle for the 19 T9 catalog entries (adding new rows for any not already present), without making a network request (check Network tab — no POST until you click the real "Сохранить" button).
4. Column header that said "В паттерне" now says "В пресете".

- [ ] **Step 8: Commit**

```bash
git add web/src/pages/ChestsPage.jsx web/src/api.js web/src/dashboard_content.js web/src/dashboard_content.en.js
git commit -m "feat(chests): raw-name fallback, total-ever column, preset loader UI, rename pattern->preset label"
```

---

### Task 4: Frontend — ChestSummaryPage.jsx (sticky header, top scrollbar, period dates) + CSS

**Files:**
- Modify: `web/src/pages/ChestSummaryPage.jsx`
- Modify: `web/src/styles/theme.css`

**Interfaces:**
- Consumes: existing `data.period_start`, `data.period_end`, `data.timezone_offset_minutes` fields already returned by `GET /chests/summary/{slug}` (no backend change needed — these fields exist since Спека 2).

- [ ] **Step 1: Add the period-range formatter and badge**

In `web/src/pages/ChestSummaryPage.jsx`, add this function right after `formatOffsetLabel` (after line 52):

```js
function formatPeriodPoint(isoString) {
  const [datePart, timePart] = isoString.split('T')
  const [, mo, d] = datePart.split('-').map(Number)
  const [h, mi] = (timePart || '00:00:00').split(':').map(Number)
  return `${String(d).padStart(2, '0')}.${String(mo).padStart(2, '0')} ${String(h).padStart(2, '0')}:${String(mi).padStart(2, '0')}`
}
```

In the JSX, inside the `{hasSeasonTargets && (...)}` block, add a new badge right after the timezone badge (after line 86, before the `<CountdownTimer>` line):

```jsx
          {data.period_start && data.period_end && (
            <span className="public-season-badge">
              {formatPeriodPoint(data.period_start)} – {formatPeriodPoint(data.period_end)}
            </span>
          )}
```

- [ ] **Step 2: Add scroll-sync refs and state for the top scrollbar**

Add `useRef` to the React import (line 1):

```js
import { useEffect, useRef, useState } from 'react'
```

Inside the component, add right after `const [error, setError] = useState('')` (line 57):

```js
  const tableWrapRef = useRef(null)
  const topScrollRef = useRef(null)
  const [tableScrollWidth, setTableScrollWidth] = useState(0)

  useEffect(() => {
    if (tableWrapRef.current) setTableScrollWidth(tableWrapRef.current.scrollWidth)
  }, [data])

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
```

- [ ] **Step 3: Wire the refs into the JSX**

Replace the table-wrap block (lines 96-126):

```jsx
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
              <th>Очки</th>
              <th>Epic склепов</th>
              {data.chest_types.map(t => <th key={t}>{t}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.players.map((p, i) => (
              <tr key={p.name} className={rowColorClass(p, i, targets)}>
                <td>{i + 1}</td>
                <td>{p.name}</td>
                <td className="public-points-cell">{p.points}</td>
                <td className={p.quota_chests === 0 ? 'public-cell-zero' : ''}>{p.quota_chests}</td>
                {data.chest_types.map(t => {
                  const value = p.counts[t] || 0
                  return (
                    <td key={t} className={value === 0 ? 'public-cell-zero' : ''}>
                      {value}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
```

- [ ] **Step 4: Add CSS for the sticky header and the top scrollbar**

In `web/src/styles/theme.css`, append at the end of the "Public chest summary" section (after line 417):

```css
.public-table-top-scroll { overflow-x: auto; overflow-y: hidden; height: 14px; }
.public-table-top-scroll::-webkit-scrollbar { height: 10px; }
.public-table-top-scroll::-webkit-scrollbar-track { background: var(--elevated); border-radius: 4px; }
.public-table-top-scroll::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 4px; }
.public-table-top-scroll::-webkit-scrollbar-thumb:hover { background: var(--accent-glow); }

.public-table thead th {
  position: sticky; top: 0; z-index: 3; background: var(--elevated);
}
.public-table thead th:nth-child(1), .public-table thead th:nth-child(2) {
  z-index: 4; background: var(--card);
}
```

- [ ] **Step 5: Manual browser verification**

Run the dev server: `cd web && npm run dev`

Open `/chests/<a-real-slug-with-a-configured-season>` (e.g. the 229/BERS slug) and confirm:
1. A thin scrollbar appears above the table, in sync with the existing bottom one — dragging either one scrolls both and the table together.
2. Scrolling the page down so the table header would normally scroll out of view — it now stays pinned at the top of the viewport, including the frozen first two columns underneath it.
3. A new badge shows the literal period dates (e.g. "01.07 00:00 – 14.07 23:59") next to the countdown timer and timezone badge.
4. If the season isn't configured for this slug, none of the season badges (including the new one) render — same as before this change.

- [ ] **Step 6: Commit**

```bash
git add web/src/pages/ChestSummaryPage.jsx web/src/styles/theme.css
git commit -m "feat(chests): sticky table header, top scrollbar, explicit season period dates on public page"
```

---

## Deployment (after all 4 tasks pass review)

Per `CLAUDE.md` §6.5 — this is web-only (`server/` + `web/`), no client bot release needed:

```bash
git push origin main
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
```

Then wait for Vercel READY + alias `total-hunter.com` (see CLAUDE.md §6.5 for the exact polling commands), and deploy the backend change to GCP:

```bash
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && sudo systemctl restart totalhunter"
```
