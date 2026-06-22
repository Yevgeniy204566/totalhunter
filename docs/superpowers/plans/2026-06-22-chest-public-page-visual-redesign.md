# Chest Public Page Visual Redesign + Cabinet Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the broken sticky table header on the public clan chest page, split row-level coloring into independent per-cell signals, add a neon "Epic" visual treatment, polish column layout/clan title, and apply small cabinet UX fixes (button placement/labels) plus an English-only catalog dropdown in the cabinet.

**Architecture:** All frontend work is CSS + JSX changes to two existing files (`ChestSummaryPage.jsx`, `ChestsPage.jsx`) plus their shared stylesheet (`theme.css`) — no new components, no backend changes except one isolated function (`_load_catalog_options`) losing its language parameter. Each task is independently shippable and touches a distinct concern (bugfix+layout, coloring/Epic logic, cabinet buttons/text, backend catalog labels).

**Tech Stack:** FastAPI + SQLAlchemy async (backend, Task 4 only), React + plain CSS (frontend, Tasks 1-3), pytest + httpx (backend test).

## Global Constraints

- Spec source of truth: `docs/superpowers/specs/2026-06-22-chest-public-page-visual-redesign-design.md`
- No DB schema changes / no migration anywhere in this plan.
- `#50C878` is the existing "success green" used by `.row-top3` — reuse it, do not introduce a second green.
- `--epic-purple: #B24BF3`, `--epic-glow: rgba(178, 75, 243, 0.55)`, `--epic-shadow: #5A1B82` are the exact new color values — do not substitute different hex values.
- The cabinet's catalog `<select>` must show ONLY the English `catalog_id` as the option label — no `ChestLocalization` lookup in `_load_catalog_options` anymore. The public summary page's own localization (`server/chests.py`) is untouched — it's a different audience/file, explicitly out of scope.
- `.btn-green` already exists in `theme.css` (lines 112-124) — reuse it for the season button, do not write new CSS for it.

---

### Task 1: Backend — English-only catalog dropdown labels

**Files:**
- Modify: `server/chest_dashboard.py:36-47` (`_load_catalog_options`), its call site in `get_dashboard_chests` (~line 129)
- Test: `server/tests/test_chest_dashboard.py` (update `test_get_chests_combines_alias_config_and_unmapped_raw`)

**Interfaces:**
- Produces: `_load_catalog_options(db)` (signature changes — drops the `language` parameter) returns `[{"catalog_id": str, "label": str}]` where `label == catalog_id` always.

- [ ] **Step 1: Update the test to expect English labels**

In `server/tests/test_chest_dashboard.py`, find `test_get_chests_combines_alias_config_and_unmapped_raw`
(currently asserts `options["Epic Arachna"] == "Эпическая Арахна"` — note the test's existing typo
"Arachna" vs the real catalog id "Epic Arachne" used elsewhere in the same test; keep using whatever
string the test already inserts via `ChestTypeAlias`/`ChestConfiguration.catalog_id` — just change the
assertion). Replace the final two lines of that test:

```python
    options = {o["catalog_id"]: o["label"] for o in collector_data["catalog_options"]}
    assert options["Epic Arachna"] == "Эпическая Арахна"
```

with:

```python
    options = {o["catalog_id"]: o["label"] for o in collector_data["catalog_options"]}
    assert options["Epic Arachna"] == "Epic Arachna"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd server && JWT_SECRET_KEY=test_secret_key python -m pytest tests/test_chest_dashboard.py::test_get_chests_combines_alias_config_and_unmapped_raw -v`
Expected: FAIL — current code still returns the Russian localized label, not `"Epic Arachna"`

- [ ] **Step 3: Simplify `_load_catalog_options`**

In `server/chest_dashboard.py`, replace the current function (lines 36-47):

```python
async def _load_catalog_options(db: AsyncSession, language: Optional[str]) -> list:
    known_ids = sorted(await _load_known_catalog_ids(db))
    labels = {}
    if language:
        rows = (await db.execute(
            select(ChestLocalization.canonical_type, ChestLocalization.display_text)
            .where(ChestLocalization.language == language)
        )).all()
        labels = dict(rows)
    options = [{"catalog_id": cid, "label": labels.get(cid, cid)} for cid in known_ids]
    options.sort(key=lambda o: o["label"])
    return options
```

with:

```python
async def _load_catalog_options(db: AsyncSession) -> list:
    known_ids = sorted(await _load_known_catalog_ids(db))
    return [{"catalog_id": cid, "label": cid} for cid in known_ids]
```

Then update the single call site inside `get_dashboard_chests` (currently around line 129):

```python
            "catalog_options": await _load_catalog_options(db, collector.language),
```

to:

```python
            "catalog_options": await _load_catalog_options(db),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd server && JWT_SECRET_KEY=test_secret_key python -m pytest tests/test_chest_dashboard.py::test_get_chests_combines_alias_config_and_unmapped_raw -v`
Expected: PASS

- [ ] **Step 5: Run the full backend test suite to check no regressions**

Run: `cd server && JWT_SECRET_KEY=test_secret_key python -m pytest tests/test_chest_dashboard.py tests/test_chests.py -v`
Expected: all PASS (note: `ChestLocalization` import in `chest_dashboard.py` is still used elsewhere by `_load_known_catalog_ids` — do not remove the import)

- [ ] **Step 6: Commit**

```bash
git add server/chest_dashboard.py server/tests/test_chest_dashboard.py
git commit -m "feat(chests): catalog dropdown shows English catalog_id only, drop per-clan localization in cabinet select"
```

---

### Task 2: Frontend — ChestSummaryPage.jsx sticky-header bugfix + layout polish (dividers, Player column, clan title)

**Files:**
- Modify: `web/src/pages/ChestSummaryPage.jsx`
- Modify: `web/src/styles/theme.css`

**Interfaces:**
- No new functions consumed by other tasks. Task 3 will edit the same file's `<td>`/`<th>` JSX further (different lines) — this task does not touch the coloring logic (`rowColorClass`, the `Points`/`Epic Crypts` cells' className expressions), only structural/cosmetic markup, so there's no overlap risk if Task 3 runs after this one lands.

- [ ] **Step 1: Fix the sticky-header bug in `theme.css`**

In `web/src/styles/theme.css`, replace line 369:

```css
.public-table-wrap { overflow-x: auto; }
```

with:

```css
.public-table-wrap { overflow-x: auto; overflow-y: auto; max-height: 70vh; }
```

- [ ] **Step 2: Add column dividers in `theme.css`**

Right after the `.public-table td` rule (currently lines 377-381), add:

```css
.public-table th, .public-table td { border-right: 1px solid rgba(255, 255, 255, 0.07); }
.public-table th:last-child, .public-table td:last-child { border-right: none; }
```

- [ ] **Step 3: Narrow the Player column in `theme.css`**

Right after the column-divider rules you just added, add:

```css
.public-table td:nth-child(2) {
  max-width: 110px; overflow: hidden; text-overflow: ellipsis;
}
```

- [ ] **Step 4: Add the clan-title shimmer styles in `theme.css`**

Replace line 362:

```css
.public-summary-title { font-size: 28px; margin-bottom: 4px; }
```

with:

```css
.public-summary-title { margin-bottom: 4px; }
.public-kingdom-label {
  font-size: 18px; font-weight: 500; color: var(--on-surface2); margin-right: 2px;
  vertical-align: middle;
}
.public-clan-label {
  font-size: 40px; font-weight: 900; letter-spacing: 0.5px;
  background: linear-gradient(90deg, var(--accent) 0%, #FFFFFF 50%, var(--accent) 100%);
  background-size: 200% auto;
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
  -webkit-text-stroke: 1px rgba(61, 127, 255, 0.45);
  text-shadow: 0 0 18px var(--accent-glow);
  animation: public-clan-shimmer 3s linear infinite;
}
@keyframes public-clan-shimmer {
  to { background-position: -200% center; }
}
```

- [ ] **Step 5: Update the JSX title markup in `ChestSummaryPage.jsx`**

Replace line 101:

```jsx
      <h1 className="gradient-text public-summary-title">{data.kingdom} / {data.clan}</h1>
```

with:

```jsx
      <h1 className="public-summary-title">
        <span className="public-kingdom-label">{data.kingdom}/</span>
        <span className="public-clan-label">{data.clan}</span>
      </h1>
```

- [ ] **Step 6: Add `title` tooltip to the Player cell in `ChestSummaryPage.jsx`**

Replace line 150:

```jsx
                <td>{p.name}</td>
```

with:

```jsx
                <td title={p.name}>{p.name}</td>
```

- [ ] **Step 7: Build check**

Run: `cd web && npx vite build`
Expected: build succeeds with no errors

- [ ] **Step 8: Commit**

```bash
git add web/src/pages/ChestSummaryPage.jsx web/src/styles/theme.css
git commit -m "fix(chests): sticky table header actually sticks (max-height+overflow-y); add column dividers, narrower Player column, shimmering clan-name title"
```

---

### Task 3: Frontend — ChestSummaryPage.jsx independent cell coloring + neon Epic styling

**Files:**
- Modify: `web/src/pages/ChestSummaryPage.jsx`
- Modify: `web/src/styles/theme.css`

**Interfaces:**
- Consumes: `targets.points`, `targets.chests` (already destructured from `data.targets` earlier in the component, unchanged), `p.points`, `p.quota_chests`, `data.chest_types` (all already in scope from existing code).
- Produces: `pointsHitTarget(player, targets)`, `questHitTarget(player, targets)`, `isEpicColumn(typeName)` — pure functions local to this file, not consumed elsewhere.

This task must land after Task 2 (same file) to avoid a merge conflict on the title/Player-cell lines — apply Task 2's diff first.

- [ ] **Step 1: Add the new CSS variables in `theme.css`**

In the `:root` block (after line 34, the `--credits-glow` line), add:

```css

  /* Epic chest/monster neon accent */
  --epic-purple: #B24BF3;
  --epic-glow:   rgba(178, 75, 243, 0.55);
  --epic-shadow: #5A1B82;
```

- [ ] **Step 2: Add the new coloring classes in `theme.css`**

Right after `.public-points-cell { color: var(--credits-gold); font-weight: 700; }` (currently line 385), add:

```css
.public-cell-hit-target { color: #50C878 !important; font-weight: 700; }
.public-epic-cell {
  color: var(--epic-purple); font-weight: 700;
  text-shadow: 0 1px 0 var(--epic-shadow), 0 0 8px var(--epic-glow), 0 0 16px var(--epic-glow);
}
```

- [ ] **Step 3: Add the helper functions in `ChestSummaryPage.jsx`**

Right after `formatPeriodPoint` (after line 59), add:

```js
function pointsHitTarget(player, targets) {
  return targets.points != null && player.points >= targets.points
}
function questHitTarget(player, targets) {
  return targets.chests != null && player.quota_chests >= targets.chests
}
function isEpicColumn(typeName) {
  return typeName.includes('Epic')
}
```

- [ ] **Step 4: Apply the classes to the table header**

Replace the `<thead>` block:

```jsx
          <thead>
            <tr>
              <th>#</th>
              <th>Player</th>
              <th>Очки</th>
              <th>Epic склепов</th>
              {data.chest_types.map(t => <th key={t}>{t}</th>)}
            </tr>
          </thead>
```

with:

```jsx
          <thead>
            <tr>
              <th>#</th>
              <th>Player</th>
              <th>Points</th>
              <th className="public-epic-cell">Epic Crypts</th>
              {data.chest_types.map(t => (
                <th key={t} className={isEpicColumn(t) ? 'public-epic-cell' : ''}>{t}</th>
              ))}
            </tr>
          </thead>
```

- [ ] **Step 5: Apply the classes to the table body cells**

Replace the `<tbody>` row-rendering block:

```jsx
          <tbody>
            {data.players.map((p, i) => (
              <tr key={p.name} className={rowColorClass(p, i, targets)}>
                <td>{i + 1}</td>
                <td title={p.name}>{p.name}</td>
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
```

with:

```jsx
          <tbody>
            {data.players.map((p, i) => (
              <tr key={p.name} className={rowColorClass(p, i, targets)}>
                <td>{i + 1}</td>
                <td title={p.name}>{p.name}</td>
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
                {data.chest_types.map(t => {
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
            ))}
          </tbody>
```

- [ ] **Step 6: Build check**

Run: `cd web && npx vite build`
Expected: build succeeds with no errors

- [ ] **Step 7: Commit**

```bash
git add web/src/pages/ChestSummaryPage.jsx web/src/styles/theme.css
git commit -m "feat(chests): independent per-cell target coloring for Points/Epic Crypts, neon purple styling for all Epic-named columns"
```

---

### Task 4: Frontend — ChestsPage.jsx cabinet polish (rename, duplicate Save button, green season button)

**Files:**
- Modify: `web/src/pages/ChestsPage.jsx`
- Modify: `web/src/dashboard_content.js`
- Modify: `web/src/dashboard_content.en.js`

**Interfaces:**
- No new functions — reuses the existing `save(slug)` function (defined at `ChestsPage.jsx:106-112`, unchanged) for the new duplicate button's `onClick`.

- [ ] **Step 1: Update RU translation keys**

In `web/src/dashboard_content.js`, inside the `chests:` object:

Replace line 62:
```js
    totalEverCol: 'Итого собрано',
```
with:
```js
    totalEverCol: 'Итого',
```

Replace line 61:
```js
    saveSeason: 'Сохранить сезон',
```
with:
```js
    saveSeason: 'Запустить сезон',
```

- [ ] **Step 2: Update EN translation keys**

In `web/src/dashboard_content.en.js`, inside the `chests:` object:

Replace line 62:
```js
    totalEverCol: 'Total Ever',
```
with:
```js
    totalEverCol: 'Total',
```

Replace line 61:
```js
    saveSeason: 'Save Season',
```
with:
```js
    saveSeason: 'Start Season',
```

- [ ] **Step 3: Make the season button green**

In `web/src/pages/ChestsPage.jsx`, replace lines 263-265:

```jsx
            <button className="btn-primary" onClick={() => saveSeason(collector.slug)}>
              {cx.saveSeason}
            </button>
```

with:

```jsx
            <button className="btn-green" onClick={() => saveSeason(collector.slug)}>
              {cx.saveSeason}
            </button>
```

- [ ] **Step 4: Add a duplicate Save button above the chests table**

In `web/src/pages/ChestsPage.jsx`, find the presets UI block (lines 285-302, the `{presets && Object.keys(presets).length > 0 && (...)}` block) immediately followed by `<table className="chest-table">` on line 303. Insert a new button right after that block's closing `)}` and right before `<table className="chest-table">`:

```jsx
              <button className="btn-primary" onClick={() => save(collector.slug)} style={{ marginBottom: 12 }}>
                {cx.save}
              </button>
              <table className="chest-table">
```

(The existing bottom Save button at lines 377-379 stays unchanged — this just adds a second, identical-behavior button above the table.)

- [ ] **Step 5: Build check**

Run: `cd web && npx vite build`
Expected: build succeeds with no errors

- [ ] **Step 6: Commit**

```bash
git add web/src/pages/ChestsPage.jsx web/src/dashboard_content.js web/src/dashboard_content.en.js
git commit -m "feat(chests): rename Итого/Запустить сезон labels, green season button, duplicate Save button above the chests table"
```

---

## Deployment (after all 4 tasks pass review)

Per `CLAUDE.md` §6.5 — web-only, no client bot release needed:

```bash
git push origin main
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
```

Wait for Vercel READY + alias `total-hunter.com`, then deploy the backend change (Task 1) to GCP:

```bash
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && sudo systemctl restart totalhunter"
```
