# Сундуки — редизайн кабинета + словарь игроков — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a self-service "Player Aliases" tab to `/dashboard/chests` and restyle the whole page with the site's existing dark theme (toggle switches, styled tables/inputs) instead of unstyled HTML.

**Architecture:** Backend gets one new full-replace endpoint (`POST /web/dashboard/chests/player-aliases`) mirroring the existing `/rows` endpoint, plus the GET handler grows one more field (`player_alias_rows`) per collector, built the same way unmapped chest rows already are. Frontend keeps the existing component structure (collector cards, one `fetch`-and-edit-in-state flow) but adds a tab switcher inside each card and new dark-themed CSS classes consumed by both tables.

**Tech Stack:** FastAPI + SQLAlchemy async (server/chest_dashboard.py), React + plain CSS (web/src/pages/ChestsPage.jsx, web/src/styles/theme.css), pytest + httpx for backend tests.

## Global Constraints

- Auth on all dashboard routes is the site session (`get_web_user`), never `ADMIN_TOKEN` — this is the self-service Phase 4 dashboard, not the admin Sheets flow.
- Every write endpoint must verify `collector.user_id == user.id` (403 otherwise) — use the existing `_get_own_collector` helper, don't duplicate the check.
- Full-replace semantics for both `/rows` and the new `/player-aliases`: omitted rows are deleted, not left stale.
- No new color palette — reuse `--bg`/`--card`/`--accent`/`--outline`/`--elevated`/`--separator`/`--on-surface`/`--on-surface2`/`--accent-glow`/`--accent-faint` from `web/src/styles/theme.css`.
- The "паттерн T9/T7 selector with separate Load/Save" idea from the Gemini prompt is explicitly out of scope — do not add it.
- No frontend automated test runner exists in this repo — frontend verification is manual in a browser (dev server), not unit tests.

---

### Task 1: Backend — GET dashboard includes player alias rows

**Files:**
- Modify: `server/chest_dashboard.py:20-23` (imports), `:49-89` (add new function after `_collector_rows`), `:92-108` (`get_dashboard_chests` — add field to result dict)
- Test: `server/tests/test_chest_dashboard.py` (append at end, after line 292)

**Interfaces:**
- Produces: `_player_alias_rows(db: AsyncSession, collector: ChestCollector) -> list[dict]` — each dict is `{"raw_name": str, "canonical_name": str | None}`. Later tasks (frontend) consume this as `collector.player_alias_rows` in the JSON response.

- [ ] **Step 1: Write the failing tests**

Append to `server/tests/test_chest_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_get_chests_includes_unmapped_sender_as_player_alias_row(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="player-rows-slug")
    db_session.add(Chest(collector_id=collector.id, sender_raw="Araiina",
                         sender_canonical="Araiina", chest_type_raw="X",
                         chest_type_canonical="X",
                         collected_at=datetime.fromisoformat("2026-06-20T10:00:00")))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    collector_data = resp.json()["collectors"][0]
    assert collector_data["player_alias_rows"] == [
        {"raw_name": "Araiina", "canonical_name": None}
    ]


@pytest.mark.asyncio
async def test_get_chests_includes_existing_player_alias_with_canonical_name(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="player-alias-slug")
    db_session.add(Chest(collector_id=collector.id, sender_raw="Araiina",
                         sender_canonical="Arahna", chest_type_raw="X",
                         chest_type_canonical="X",
                         collected_at=datetime.fromisoformat("2026-06-20T10:00:00")))
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="Araiina",
                               canonical_name="Arahna"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/web/dashboard/chests",
                                headers={"Authorization": f"Bearer {token}"})
    assert resp.status_code == 200
    collector_data = resp.json()["collectors"][0]
    assert collector_data["player_alias_rows"] == [
        {"raw_name": "Araiina", "canonical_name": "Arahna"}
    ]
```

Add `PlayerAlias` to the existing `from models import (...)` test import block (alphabetical, after `ChestTypeCatalog`):

```python
from models import (
    Chest, ChestCollector, ChestConfiguration, ChestLocalization, ChestTypeAlias,
    ChestTypeCatalog, PlayerAlias, User,
)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -k player_alias_row -v`
Expected: FAIL — `KeyError: 'player_alias_rows'` (the field doesn't exist in the response yet).

- [ ] **Step 3: Implement `_player_alias_rows` and wire it into the GET handler**

In `server/chest_dashboard.py`, change the import block (around line 20-23) to add `PlayerAlias`:

```python
from models import (
    Chest, ChestCollector, ChestConfiguration, ChestLocalization, ChestTypeAlias,
    ChestTypeCatalog, PlayerAlias, User,
)
```

Add this new function right after `_collector_rows` (after line 89, before `@router.get("")`):

```python
async def _player_alias_rows(db: AsyncSession, collector: ChestCollector) -> list:
    aliases = (await db.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()
    rows = [{"raw_name": a.raw_name, "canonical_name": a.canonical_name} for a in aliases]

    mapped_raw_names = {a.raw_name for a in aliases}
    unmapped = (await db.execute(
        select(Chest.sender_raw).distinct()
        .where(Chest.collector_id == collector.id)
    )).scalars().all()
    for raw_name in unmapped:
        if raw_name in mapped_raw_names:
            continue
        rows.append({"raw_name": raw_name, "canonical_name": None})

    return rows
```

In `get_dashboard_chests` (the loop building `result`), add the new field next to `"rows"`:

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

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -v`
Expected: all tests PASS (including the two new ones and all pre-existing ones in this file).

- [ ] **Step 5: Commit**

```bash
git add server/chest_dashboard.py server/tests/test_chest_dashboard.py
git commit -m "feat(chests): include player alias rows in dashboard GET response"
```

---

### Task 2: Backend — full-replace POST for player aliases

**Files:**
- Modify: `server/chest_dashboard.py` (add Pydantic models + route after the existing `/rows` route, i.e. after line 161 in the pre-Task-1 file — after the `post_dashboard_rows` function)
- Test: `server/tests/test_chest_dashboard.py` (append at end)

**Interfaces:**
- Consumes: `_get_own_collector(db, slug, user)` (existing, from Task before this plan — already in `chest_dashboard.py`), `PlayerAlias` model (imported in Task 1).
- Produces: `POST /web/dashboard/chests/player-aliases` — request body `{"collector_slug": str, "rows": [{"raw_name": str, "canonical_name": str | None}]}`, response `{"ok": true}`. Frontend (Task 5) calls this via `api.dashboardChestsPlayerAliases(slug, rows)` (added in Task 3).

- [ ] **Step 1: Write the failing tests**

Append to `server/tests/test_chest_dashboard.py`:

```python
@pytest.mark.asyncio
async def test_post_player_aliases_rejects_other_users_collector(db_session):
    user, token = await _create_user_with_token(db_session)
    other_user, _ = await _create_user_with_token(db_session, email="other3@example.com")
    await _create_collector(db_session, other_user.id, slug="not-mine-pa-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/player-aliases",
            json={"collector_slug": "not-mine-pa-slug", "rows": []},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_post_player_aliases_creates_and_skips_empty_canonical(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="pa-create-slug")
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/player-aliases",
            json={"collector_slug": "pa-create-slug",
                 "rows": [{"raw_name": "Araiina", "canonical_name": "Arahna"},
                          {"raw_name": "Unfixed", "canonical_name": None},
                          {"raw_name": "AlsoUnfixed", "canonical_name": "  "}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    aliases = (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()
    assert len(aliases) == 1
    assert aliases[0].raw_name == "Araiina" and aliases[0].canonical_name == "Arahna"


@pytest.mark.asyncio
async def test_post_player_aliases_full_replace_removes_omitted_rows(db_session):
    user, token = await _create_user_with_token(db_session)
    collector = await _create_collector(db_session, user.id, slug="pa-replace-slug")
    db_session.add(PlayerAlias(collector_id=collector.id, raw_name="OldRaw",
                               canonical_name="OldCanon"))
    await db_session.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/web/dashboard/chests/player-aliases",
            json={"collector_slug": "pa-replace-slug",
                 "rows": [{"raw_name": "NewRaw", "canonical_name": "NewCanon"}]},
            headers={"Authorization": f"Bearer {token}"},
        )
    assert resp.status_code == 200

    aliases = (await db_session.execute(
        select(PlayerAlias).where(PlayerAlias.collector_id == collector.id)
    )).scalars().all()
    assert len(aliases) == 1
    assert aliases[0].raw_name == "NewRaw"
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -k player_aliases -v`
Expected: FAIL with `404 Not Found` (route doesn't exist yet).

- [ ] **Step 3: Implement the route**

In `server/chest_dashboard.py`, add this block right after the `post_dashboard_rows` function (after the closing of that function, before `class CollectorSlugPayload`):

```python
class PlayerAliasRowIn(BaseModel):
    raw_name: str
    canonical_name: Optional[str] = None


class PlayerAliasesPayload(BaseModel):
    collector_slug: str
    rows: List[PlayerAliasRowIn] = []


@router.post("/player-aliases")
async def post_player_aliases(payload: PlayerAliasesPayload, user: User = Depends(get_web_user),
                              db: AsyncSession = Depends(get_db)):
    collector = await _get_own_collector(db, payload.collector_slug, user)

    await db.execute(delete(PlayerAlias).where(PlayerAlias.collector_id == collector.id))

    for row in payload.rows:
        canonical = (row.canonical_name or "").strip()
        if not canonical:
            continue
        db.add(PlayerAlias(collector_id=collector.id, raw_name=row.raw_name,
                           canonical_name=canonical))

    await db.commit()
    return {"ok": True}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chest_dashboard.py -v`
Expected: all tests PASS.

- [ ] **Step 5: Commit**

```bash
git add server/chest_dashboard.py server/tests/test_chest_dashboard.py
git commit -m "feat(chests): add full-replace POST /web/dashboard/chests/player-aliases"
```

---

### Task 3: Frontend — API client function + i18n strings

**Files:**
- Modify: `web/src/api.js:43-47` (add new function next to `dashboardChestsSave`)
- Modify: `web/src/dashboard_content.js:42-59` (`chests` block)
- Modify: `web/src/dashboard_content.en.js:42-59` (`chests` block)

**Interfaces:**
- Produces: `api.dashboardChestsPlayerAliases(slug, rows)` — POSTs to `/web/dashboard/chests/player-aliases`. Consumed by Task 5 (`ChestsPage.jsx`).
- Produces: new keys on `D.chests` (`D` = `dashboard_content.js`/`.en.js` exports): `chestsTab`, `playersTab`, `playerRawCol`, `playerCanonicalCol`, `addPlayerRow`, `savePlayerAliases`. Consumed by Task 5.

- [ ] **Step 1: Add the API function**

In `web/src/api.js`, right after the line `dashboardChestsSave:  (slug, rows)    => request('POST',  '/web/dashboard/chests/rows', { collector_slug: slug, rows }),`, add:

```js
  dashboardChestsPlayerAliases: (slug, rows) => request('POST', '/web/dashboard/chests/player-aliases', { collector_slug: slug, rows }),
```

- [ ] **Step 2: Add Russian strings**

In `web/src/dashboard_content.js`, inside the `chests: { ... }` block, add these keys right after `inPatternCol: 'В паттерне',`:

```js
    chestsTab: 'Сундуки',
    playersTab: 'Игроки',
    playerRawCol: 'Сырое имя (OCR)',
    playerCanonicalCol: 'Правильное имя',
    addPlayerRow: 'Добавить игрока вручную',
    savePlayerAliases: 'Сохранить имена',
```

- [ ] **Step 3: Add English strings**

In `web/src/dashboard_content.en.js`, inside the `chests: { ... }` block, add these keys right after `inPatternCol: 'In Pattern',`:

```js
    chestsTab: 'Chests',
    playersTab: 'Players',
    playerRawCol: 'Raw Name (OCR)',
    playerCanonicalCol: 'Correct Name',
    addPlayerRow: 'Add player manually',
    savePlayerAliases: 'Save names',
```

- [ ] **Step 4: Verify no syntax errors**

Run: `cd web && node -e "require('./src/dashboard_content.js')" 2>&1 | head -5`

This will fail with an ESM error (`require` of an ES module) — that's expected and fine, it's not a real test. Instead, verify by reading the file back and confirming valid JS object syntax (matching commas, quotes). Skip a strict run here; Task 5's dev-server check is the real verification.

- [ ] **Step 5: Commit**

```bash
git add web/src/api.js web/src/dashboard_content.js web/src/dashboard_content.en.js
git commit -m "feat(web): add player-aliases API call and i18n strings for chests dashboard"
```

---

### Task 4: Frontend — dark theme CSS for tabs, table, inputs, toggle

**Files:**
- Modify: `web/src/styles/theme.css` (append new section at end of file, after line 313)

**Interfaces:**
- Produces CSS classes consumed by Task 5: `.chest-tabs`, `.chest-tab`, `.chest-tab--active`, `.chest-table`, `.input-dark`, `.toggle-switch` (with nested `input` + `.slider`).

- [ ] **Step 1: Append the new CSS block**

Add to the end of `web/src/styles/theme.css`:

```css

/* ── Chests dashboard — tabs, table, dark inputs, toggle ─────── */
.chest-tabs {
  display: flex; gap: 4px; margin-bottom: 16px;
  border-bottom: 1px solid var(--outline);
}
.chest-tab {
  background: transparent; border: none; padding: 10px 18px;
  color: var(--on-surface2); font-size: 14px; font-weight: 600;
  font-family: inherit; cursor: pointer; border-bottom: 2px solid transparent;
  transition: color 0.15s, border-color 0.15s;
}
.chest-tab:hover { color: var(--on-surface); }
.chest-tab--active { color: var(--on-surface); border-bottom-color: var(--accent); }

.chest-table { width: 100%; border-collapse: collapse; }
.chest-table th {
  text-align: left; padding: 10px 12px; color: var(--on-surface2);
  font-size: 12px; text-transform: uppercase; letter-spacing: 0.4px;
  border-bottom: 1px solid var(--outline);
}
.chest-table td { padding: 8px 12px; border-bottom: 1px solid var(--separator); }
.chest-table tr:hover td { background: var(--accent-faint); }

.input-dark {
  background: var(--elevated); color: var(--on-surface);
  border: 1px solid var(--outline); border-radius: 6px;
  padding: 8px 10px; font-size: 14px; font-family: inherit; width: 100%;
}
.input-dark:focus {
  outline: none; border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-glow);
}

.toggle-switch { position: relative; display: inline-block; width: 40px; height: 22px; }
.toggle-switch input { opacity: 0; width: 0; height: 0; }
.toggle-switch .slider {
  position: absolute; inset: 0; background: var(--outline);
  border-radius: 22px; cursor: pointer; transition: background 0.15s;
}
.toggle-switch .slider::before {
  content: ''; position: absolute; width: 16px; height: 16px;
  left: 3px; top: 3px; background: var(--on-surface);
  border-radius: 50%; transition: transform 0.15s;
}
.toggle-switch input:checked + .slider { background: var(--accent); }
.toggle-switch input:checked + .slider::before { transform: translateX(18px); }
```

- [ ] **Step 2: Commit**

```bash
git add web/src/styles/theme.css
git commit -m "feat(web): add dark-themed tab/table/toggle CSS for chests dashboard"
```

---

### Task 5: Frontend — rewrite ChestsPage.jsx with tabs and dark styling

**Files:**
- Modify: `web/src/pages/ChestsPage.jsx` (full rewrite of the component body)

**Interfaces:**
- Consumes: `api.dashboardChests()`, `api.dashboardChestsSave(slug, rows)`, `api.dashboardChestsPlayerAliases(slug, rows)`, `api.dashboardChestsToken(slug)`, `api.dashboardChestsClaim(code)`, `api.dashboardChestsLang(slug, language)` (all from Task 3 / pre-existing `api.js`). `cx.chestsTab`, `cx.playersTab`, `cx.playerRawCol`, `cx.playerCanonicalCol`, `cx.addPlayerRow`, `cx.savePlayerAliases` (from Task 3). CSS classes `.chest-tabs`, `.chest-tab`, `.chest-tab--active`, `.chest-table`, `.input-dark`, `.toggle-switch` (from Task 4).
- Response shape consumed: `data.collectors[].player_alias_rows` (from Task 1), `data.collectors[].rows` / `.catalog_options` (pre-existing).

- [ ] **Step 1: Rewrite the component**

Replace the entire contents of `web/src/pages/ChestsPage.jsx` with:

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useLang } from '../lang.js'
import { DASHBOARD as D_RU } from '../dashboard_content.js'
import { DASHBOARD as D_EN } from '../dashboard_content.en.js'
import { useMeta } from '../hooks/useMeta.js'

export default function ChestsPage() {
  const [collectors, setCollectors] = useState(null)
  const [rowsByCollector, setRowsByCollector] = useState({})
  const [playerRowsByCollector, setPlayerRowsByCollector] = useState({})
  const [activeTabByCollector, setActiveTabByCollector] = useState({})
  const [msg, setMsg] = useState('')
  const [loadError, setLoadError] = useState('')
  const [claimCode, setClaimCode] = useState('')
  const { lang } = useLang()
  const D = lang === 'ru' ? D_RU : D_EN
  const cx = D.chests
  useMeta({
    title: lang === 'ru' ? 'Total Hunter — Сундуки' : 'Total Hunter — Chests',
    description: lang === 'ru' ? 'Настройка сундуков клана.' : 'Configure your clan chests.',
  })

  async function refresh() {
    try {
      const data = await api.dashboardChests()
      setCollectors(data.collectors)
      const nextRows = {}
      const nextPlayerRows = {}
      for (const c of data.collectors) {
        nextRows[c.slug] = c.rows
        nextPlayerRows[c.slug] = c.player_alias_rows
      }
      setRowsByCollector(nextRows)
      setPlayerRowsByCollector(nextPlayerRows)
    } catch (e) {
      setLoadError(e.message || 'failed to load')
    }
  }
  useEffect(() => { refresh() }, [])

  function activeTab(slug) { return activeTabByCollector[slug] || 'chests' }
  function setTab(slug, tab) {
    setActiveTabByCollector(prev => ({ ...prev, [slug]: tab }))
  }

  function updateRow(slug, index, field, value) {
    setRowsByCollector(prev => {
      const rows = [...prev[slug]]
      rows[index] = { ...rows[index], [field]: value }
      return { ...prev, [slug]: rows }
    })
  }

  function addRow(slug) {
    setRowsByCollector(prev => ({
      ...prev,
      [slug]: [...prev[slug], { raw_type: null, catalog_id: null, custom_name: null,
                                points: 0, is_in_pattern: false }],
    }))
  }

  async function save(slug) {
    await api.dashboardChestsSave(slug, rowsByCollector[slug])
    setMsg(cx.saved)
    await refresh()
  }

  function updatePlayerRow(slug, index, field, value) {
    setPlayerRowsByCollector(prev => {
      const rows = [...prev[slug]]
      rows[index] = { ...rows[index], [field]: value }
      return { ...prev, [slug]: rows }
    })
  }

  function addPlayerRow(slug) {
    setPlayerRowsByCollector(prev => ({
      ...prev,
      [slug]: [...prev[slug], { raw_name: '', canonical_name: '' }],
    }))
  }

  async function savePlayerAliases(slug) {
    await api.dashboardChestsPlayerAliases(slug, playerRowsByCollector[slug])
    setMsg(cx.saved)
    await refresh()
  }

  async function genToken(slug) {
    const res = await api.dashboardChestsToken(slug)
    setMsg(res.code)
  }

  async function claim() {
    try {
      await api.dashboardChestsClaim(claimCode)
      setClaimCode('')
      await refresh()
    } catch (e) { setMsg(e.message) }
  }

  async function changeLanguage(slug, language) {
    await api.dashboardChestsLang(slug, language)
    await refresh()
  }

  if (loadError) return <div className="page-content text-muted">{loadError}</div>
  if (!collectors) return <div className="page-content text-muted">...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24 }}>{cx.title}</h2>

      <div className="card" style={{ marginBottom: 16, maxWidth: 480 }}>
        <input
          className="input-dark"
          value={claimCode}
          onChange={e => setClaimCode(e.target.value)}
          placeholder={cx.claimPlaceholder}
          style={{ marginBottom: 8 }}
        />
        <button className="btn-secondary" onClick={claim}>{cx.claimBtn}</button>
      </div>

      {collectors.length === 0 && <div className="text-muted" style={{ marginTop: 12 }}>{cx.noCollectors}</div>}

      {collectors.map(collector => (
        <div className="card" key={collector.slug} style={{ marginBottom: 24 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 12 }}>
            <div>{collector.kingdom} / {collector.clan}</div>
            <a href={collector.public_url} target="_blank" rel="noreferrer">{cx.publicLink}</a>
          </div>

          <div style={{ marginBottom: 16, display: 'flex', gap: 8, alignItems: 'center' }}>
            {cx.language}:
            <select
              className="input-dark"
              style={{ width: 'auto' }}
              value={collector.language || ''}
              onChange={e => changeLanguage(collector.slug, e.target.value)}
            >
              <option value="ru">ru</option>
              <option value="en">en</option>
            </select>
            <button className="btn-secondary" onClick={() => genToken(collector.slug)}>
              {cx.generateToken}
            </button>
          </div>

          <div className="chest-tabs">
            <button
              className={`chest-tab ${activeTab(collector.slug) === 'chests' ? 'chest-tab--active' : ''}`}
              onClick={() => setTab(collector.slug, 'chests')}
            >
              {cx.chestsTab}
            </button>
            <button
              className={`chest-tab ${activeTab(collector.slug) === 'players' ? 'chest-tab--active' : ''}`}
              onClick={() => setTab(collector.slug, 'players')}
            >
              {cx.playersTab}
            </button>
          </div>

          {activeTab(collector.slug) === 'chests' && (
            <>
              <table className="chest-table">
                <thead>
                  <tr>
                    <th>{cx.rawCol}</th>
                    <th>{cx.catalogCol}</th>
                    <th>{cx.customNameCol}</th>
                    <th>{cx.pointsCol}</th>
                    <th>{cx.inPatternCol}</th>
                  </tr>
                </thead>
                <tbody>
                  {rowsByCollector[collector.slug]?.map((row, i) => (
                    <tr key={i}>
                      <td>{row.raw_type || '—'}</td>
                      <td>
                        <select
                          className="input-dark"
                          value={row.catalog_id || ''}
                          onChange={e => updateRow(collector.slug, i, 'catalog_id', e.target.value || null)}
                        >
                          <option value="">{cx.noCatalog}</option>
                          {collector.catalog_options.map(o => (
                            <option key={o.catalog_id} value={o.catalog_id}>{o.label}</option>
                          ))}
                        </select>
                      </td>
                      <td>
                        <input
                          className="input-dark"
                          value={row.custom_name || ''}
                          onChange={e => updateRow(collector.slug, i, 'custom_name', e.target.value || null)}
                        />
                      </td>
                      <td>
                        <input
                          className="input-dark"
                          type="number"
                          value={row.points === 0 ? '' : row.points}
                          onChange={e => updateRow(collector.slug, i, 'points', parseInt(e.target.value, 10) || 0)}
                        />
                      </td>
                      <td>
                        <label className="toggle-switch">
                          <input
                            type="checkbox"
                            checked={row.is_in_pattern}
                            onChange={e => updateRow(collector.slug, i, 'is_in_pattern', e.target.checked)}
                          />
                          <span className="slider"></span>
                        </label>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <button className="btn-secondary" onClick={() => addRow(collector.slug)} style={{ marginTop: 12 }}>
                {cx.addRow}
              </button>
              <button className="btn-primary" onClick={() => save(collector.slug)} style={{ marginTop: 12, marginLeft: 8 }}>
                {cx.save}
              </button>
            </>
          )}

          {activeTab(collector.slug) === 'players' && (
            <>
              <table className="chest-table">
                <thead>
                  <tr>
                    <th>{cx.playerRawCol}</th>
                    <th>{cx.playerCanonicalCol}</th>
                  </tr>
                </thead>
                <tbody>
                  {playerRowsByCollector[collector.slug]?.map((row, i) => (
                    <tr key={i}>
                      <td>{row.raw_name || '—'}</td>
                      <td>
                        <input
                          className="input-dark"
                          value={row.canonical_name || ''}
                          onChange={e => updatePlayerRow(collector.slug, i, 'canonical_name', e.target.value)}
                        />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>

              <button className="btn-secondary" onClick={() => addPlayerRow(collector.slug)} style={{ marginTop: 12 }}>
                {cx.addPlayerRow}
              </button>
              <button className="btn-primary" onClick={() => savePlayerAliases(collector.slug)} style={{ marginTop: 12, marginLeft: 8 }}>
                {cx.savePlayerAliases}
              </button>
            </>
          )}
        </div>
      ))}

      {msg && <div className="text-muted" style={{ marginTop: 12 }}>{msg}</div>}
    </div>
  )
}
```

- [ ] **Step 2: Start the dev server and verify visually**

Run: `cd web && npm run dev` (leave running)

Open the dashboard in a browser, log in, navigate to `/dashboard/chests`. Verify:
- Page background, card, inputs, and table rows use the dark theme (no white inputs).
- Both tabs ("Сундуки"/"Игроки" or "Chests"/"Players" depending on language) switch the visible table without page reload.
- Toggle switch renders as a pill, not a checkbox, and visually flips on click.
- Type a points value starting from a row where it was previously `0` — confirm no stray leading zero is displayed (e.g. typing "4" then "0" shows "40", not "040").
- Edit a name in the "Игроки"/"Players" tab, click Save, refresh the page (F5) — the edit must persist.
- Edit a chest row, click "Сохранить"/"Save" — confirm the existing chests-table save flow still works exactly as before (no regression).

If the leading-zero behavior is NOT reproducible (browsers usually already strip it for `type="number"`), no further action is needed — the `row.points === 0 ? '' : row.points` change already shipped in Step 1 is a safe no-op in that case.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/ChestsPage.jsx
git commit -m "feat(web): redesign chests dashboard with tabs, dark theme, toggle switches"
```

---

### Task 6: Deploy and verify in production

**Files:** none (deployment only)

- [ ] **Step 1: Deploy backend to GCP**

Run:
```bash
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && sudo systemctl restart totalhunter && sleep 2 && sudo systemctl is-active totalhunter"
```
Expected output ends with `active`.

- [ ] **Step 2: Deploy frontend to Vercel**

Run (already pushed to `main` via the commits in Tasks 3-5):
```bash
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
```
Then poll deployment state and attach the `total-hunter.com` alias per the 3-step Vercel deploy procedure in `CLAUDE.md` section 6.5.

- [ ] **Step 3: Live verification on production**

Open `https://total-hunter.com/dashboard/chests`, log in as the owner, confirm:
- The single "229 / BERS" card (post-merge from the earlier collector-dedup fix) renders with the new dark styling.
- The "Игроки" tab shows real unmapped sender names pulled from the 6833 merged chest rows.
- Editing and saving a player alias persists after reload.
