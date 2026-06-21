# Публичная страница клана `/chests/:slug` — редизайн — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reorder and restyle the public, no-login `/chests/:slug` page (Player → Points → Total → chest-type columns sorted by count, premium dark table, "last updated" timestamp) without touching the scoring logic itself.

**Architecture:** Backend changes are confined to `_pivot_summary`'s chest-type ordering and one new field (`updated_at`) on the existing `GET /api/v1/chests/summary/{slug}` response — no new endpoints, no schema changes. Frontend is a full rewrite of the one-component page plus new CSS classes appended to the shared `theme.css`.

**Tech Stack:** FastAPI + SQLAlchemy async (`server/chests.py`), React + plain CSS (`web/src/pages/ChestSummaryPage.jsx`, `web/src/styles/theme.css`), pytest + httpx for backend tests.

## Global Constraints

- "Last updated" is the timestamp of the most recently collected chest in the data (`max(Chest.collected_at)`), not the time of the HTTP request.
- Chest-type columns are sorted by total count of that type across the clan, descending, tie-broken by display name ascending (same tie-break style already used for player sorting in `_pivot_summary`).
- No new color palette — reuse `--bg`/`--card`/`--elevated`/`--accent`/`--accent-glow`/`--outline`/`--on-surface`/`--on-surface2`/`--credits-gold`/`.gradient-text` from `web/src/styles/theme.css`.
- Header decoration stays minimal: gradient text + one thin divider line — no new SVG/CSS ornament shapes.
- Scoring/aggregation logic (`ChestConfiguration`, alias resolution, pattern filtering) is unchanged — this plan only reorders/restyles already-computed data.
- No frontend automated test runner exists in this repo — frontend verification is manual in a browser (dev server), not unit tests.

---

### Task 1: Backend — sort chest-type columns by total count descending

**Files:**
- Modify: `server/chests.py:230` (the `chest_types = [...]` line inside `_pivot_summary`)
- Test: `server/tests/test_chests.py` (append after line 405, inside/after `test_summary_aggregates_players_and_chest_types`)

**Interfaces:**
- No signature changes. `_pivot_summary(kingdom, clan, rows) -> dict` still returns the same keys; only the **order** of the `chest_types` list (and therefore the column order downstream) changes.

- [ ] **Step 1: Write the failing test**

Append to `server/tests/test_chests.py` (after the existing `test_summary_aggregates_players_and_chest_types` test, before `test_summary_empty_collector_returns_empty_lists`):

```python
@pytest.mark.asyncio
async def test_summary_chest_types_sorted_by_total_count_descending(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "sortbytotal0a")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K12", clan="SortClan",
            items=[
                {"chest_type": "Rare", "sender": "P1", "timestamp": "2026-06-18T13:00:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T13:01:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T13:02:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T13:03:00"},
                {"chest_type": "Epic", "sender": "P1", "timestamp": "2026-06-18T13:04:00"},
                {"chest_type": "Epic", "sender": "P1", "timestamp": "2026-06-18T13:05:00"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id
        for catalog_id in ("Rare", "Common", "Epic"):
            db_session.add(ChestConfiguration(collector_id=collector_id, catalog_id=catalog_id,
                                              points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    body = resp.json()
    # Common=3, Epic=2, Rare=1 -> descending order
    assert body["chest_types"] == ["Common", "Epic", "Rare"]
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chests.py -k sorted_by_total_count -v`
Expected: FAIL — `assert body["chest_types"] == ["Common", "Epic", "Rare"]` fails because the current order is insertion order (`["Rare", "Common", "Epic"]`, the order the items were imported in).

- [ ] **Step 3: Implement the sort**

In `server/chests.py`, inside `_pivot_summary`, replace this line:

```python
    chest_types = [display_names[t] for t in chest_type_order]
```

with:

```python
    chest_type_order_sorted = sorted(
        seen_types, key=lambda t: (-totals[t], display_names[t])
    )
    chest_types = [display_names[t] for t in chest_type_order_sorted]
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chests.py -v`
Expected: all tests in the file PASS, including the new one and the pre-existing `test_summary_aggregates_players_and_chest_types` (which only asserts `sorted(body["chest_types"]) == [...]`, so it's order-independent and unaffected).

- [ ] **Step 5: Commit**

```bash
git add server/chests.py server/tests/test_chests.py
git commit -m "feat(chests): sort public summary chest-type columns by total count descending"
```

---

### Task 2: Backend — add `updated_at` to the summary response

**Files:**
- Modify: `server/chests.py:255-297` (`get_chest_summary`)
- Test: `server/tests/test_chests.py` (append near the existing summary tests, after Task 1's new test)

**Interfaces:**
- Produces: `GET /api/v1/chests/summary/{slug}` response gains one new top-level key, `"updated_at"` — an ISO-8601 string (e.g. `"2026-06-18T11:15:00"`) when the collector has at least one chest, or `null` when it has none. Consumed by Task 3 (frontend).

- [ ] **Step 1: Write the failing tests**

Append to `server/tests/test_chests.py`:

```python
@pytest.mark.asyncio
async def test_summary_includes_updated_at_as_latest_chest_timestamp(db_session):
    from models import ChestConfiguration

    user = await _create_user(db_session, "updatedattest")
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        import_resp = await client.post("/api/v1/chests/import", json=_payload(
            user.hwid, kingdom="K13", clan="UpdatedAtClan",
            items=[
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T09:00:00"},
                {"chest_type": "Common", "sender": "P1", "timestamp": "2026-06-18T14:30:00"},
            ],
        ))
        assert import_resp.status_code == 200
        slug = import_resp.json()["collector_slug"]

        collector_id = (await db_session.execute(
            select(ChestCollector).where(ChestCollector.slug == slug)
        )).scalar_one().id
        db_session.add(ChestConfiguration(collector_id=collector_id, catalog_id="Common",
                                          points=0, is_in_pattern=True))
        await db_session.commit()

        resp = await client.get(f"/api/v1/chests/summary/{slug}")
    assert resp.status_code == 200
    assert resp.json()["updated_at"] == "2026-06-18T14:30:00"


@pytest.mark.asyncio
async def test_summary_updated_at_is_none_for_collector_with_zero_chests(db_session):
    import secrets as _secrets
    user = await _create_user(db_session, "noupdatedat0a")
    collector = ChestCollector(kingdom="K14", clan="NoChestsClan", user_id=user.id,
                               slug=_secrets.token_urlsafe(16))
    db_session.add(collector)
    await db_session.commit()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(f"/api/v1/chests/summary/{collector.slug}")
    assert resp.status_code == 200
    assert resp.json()["updated_at"] is None
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chests.py -k updated_at -v`
Expected: FAIL — `KeyError`-equivalent (`resp.json()["updated_at"]` is `None` via `.get` semantics in the test would not fail, but here we index directly so it raises `KeyError: 'updated_at'`) because the field doesn't exist yet.

- [ ] **Step 3: Implement**

In `server/chests.py`, find the end of `get_chest_summary` (currently):

```python
    return _pivot_summary(collector.kingdom, collector.clan, rows)
```

Replace with:

```python
    updated_at = (await db.execute(
        select(func.max(Chest.collected_at)).where(Chest.collector_id == collector.id)
    )).scalar_one_or_none()

    result = _pivot_summary(collector.kingdom, collector.clan, rows)
    result["updated_at"] = updated_at.isoformat() if updated_at else None
    return result
```

No new imports are needed — `func` and `Chest` are already imported and used earlier in this same file (`func.coalesce`, `func.count()`, and the `Chest` model are already referenced in `get_chest_summary` itself).

- [ ] **Step 4: Run the tests to verify they pass**

Run: `cd C:\BattleBot\server && JWT_SECRET_KEY=test_secret python -m pytest tests/test_chests.py -v`
Expected: all tests PASS, including the two new ones and every pre-existing test in the file (no regressions — `updated_at` is an additive field, no existing test asserts the response has exactly these keys and no more).

- [ ] **Step 5: Commit**

```bash
git add server/chests.py server/tests/test_chests.py
git commit -m "feat(chests): add updated_at (latest chest timestamp) to public summary response"
```

---

### Task 3: Frontend — rewrite ChestSummaryPage.jsx with premium dark table

**Files:**
- Modify: `web/src/pages/ChestSummaryPage.jsx` (full rewrite of the component body)
- Modify: `web/src/styles/theme.css` (append new CSS section at end of file)

**Interfaces:**
- Consumes: `fetchChestSummary(slug)` (existing, unchanged signature in `web/src/api.js`) returning `{kingdom, clan, chest_types, players, totals, updated_at}` — `chest_types` is now pre-sorted by total count descending (Task 1), `updated_at` is an ISO string or `null` (Task 2). `players[].points` and `players[].total` already exist in the pre-existing response shape (unchanged by Tasks 1-2).
- Produces CSS classes consumed only within this page's JSX: `.public-summary-title`, `.public-summary-updated`, `.public-summary-divider`, `.public-table-wrap`, `.public-table`, `.public-cell-zero`, `.public-points-cell`.

- [ ] **Step 1: Append the CSS block to theme.css**

Add to the end of `web/src/styles/theme.css`:

```css

/* ── Public chest summary page — premium dark table ───────────── */
.public-summary-title { font-size: 28px; margin-bottom: 4px; }
.public-summary-updated { color: var(--on-surface2); font-size: 13px; margin-bottom: 12px; }
.public-summary-divider {
  height: 1px; background: linear-gradient(90deg, var(--accent) 0%, transparent 80%);
  margin-bottom: 20px;
}

.public-table-wrap { overflow-x: auto; }
.public-table { width: 100%; border-collapse: collapse; white-space: nowrap; }
.public-table th {
  text-align: right; padding: 10px 14px; color: var(--on-surface2);
  font-size: 12px; text-transform: uppercase; letter-spacing: 0.4px;
  background: var(--elevated); border-bottom: 1px solid var(--outline);
}
.public-table th:first-child, .public-table td:first-child { text-align: left; }
.public-table td {
  padding: 8px 14px; text-align: right;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
  color: var(--on-surface);
}
.public-table tbody tr:nth-child(even) td { background: rgba(255, 255, 255, 0.02); }
.public-table tbody tr:hover td { background: var(--accent-glow); }
.public-cell-zero { color: var(--on-surface2); }
.public-points-cell { color: var(--credits-gold); font-weight: 700; }

.public-table th:first-child, .public-table td:first-child {
  position: sticky; left: 0; z-index: 2;
  background: var(--card);
}
.public-table tbody tr:nth-child(even) td:first-child { background: #0D1326; }
.public-table tbody tr:hover td:first-child { background: var(--accent-glow); }
```

- [ ] **Step 2: Rewrite the component**

Replace the entire contents of `web/src/pages/ChestSummaryPage.jsx` with:

```jsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchChestSummary } from '../api.js'

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
    ? new Date(data.updated_at).toLocaleString()
    : '—'

  return (
    <div className="page-content">
      <h1 className="gradient-text public-summary-title">{data.kingdom} / {data.clan}</h1>
      <div className="public-summary-updated">Последнее обновление: {updatedLabel}</div>
      <div className="public-summary-divider" />

      <div className="public-table-wrap">
        <table className="public-table">
          <thead>
            <tr>
              <th>Player</th>
              <th>Очки</th>
              <th>Всего сундуков</th>
              {data.chest_types.map(t => <th key={t}>{t}</th>)}
            </tr>
          </thead>
          <tbody>
            {data.players.map(p => (
              <tr key={p.name}>
                <td>{p.name}</td>
                <td className="public-points-cell">{p.points}</td>
                <td className={p.total === 0 ? 'public-cell-zero' : ''}>{p.total}</td>
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
    </div>
  )
}
```

- [ ] **Step 3: Build check**

Run: `cd C:\BattleBot\web && npm run build`
Expected: exit code 0, no JSX/import errors.

- [ ] **Step 4: Manual browser verification**

Run: `cd C:\BattleBot\web && npm run dev` (leave running), open `/chests/<a real slug, e.g. m00bqgjcl1xqUHRDvEa8bQ>` in a browser. Verify:
- Column order is Player, Очки (gold-colored numbers), Всего сундуков, then chest-type columns — and the chest-type columns appear ordered from the highest total count down to the lowest.
- "Последнее обновление: ..." line shows a real date/time, not "Invalid Date" or "—" (the test clan has real chest data).
- Resize the browser window narrow (or use mobile device emulation) — the table scrolls horizontally, and the leftmost "Player" column stays visibly pinned while the rest scrolls underneath it (no see-through/flicker).
- Hover over a data row — the whole row highlights, including the sticky first column (not just the non-sticky cells).
- Any all-zero row/column reads visibly dimmer than rows with real numbers.

If the zebra-stripe shade on the sticky first column (`#0D1326`) is indistinguishable from the surrounding `--card` background on your screen, adjust that one hex value to taste — this was flagged in the spec as a cosmetic value to tune live, not a logic bug.

- [ ] **Step 5: Commit**

```bash
git add web/src/pages/ChestSummaryPage.jsx web/src/styles/theme.css
git commit -m "feat(web): redesign public chest summary page with premium dark table"
```

---

### Task 4: Deploy and verify in production

**Files:** none (deployment only)

- [ ] **Step 1: Push to main**

Run: `git push origin main`

- [ ] **Step 2: Deploy backend to GCP**

Run:
```bash
gcloud compute ssh total-hunter-backend --zone=us-central1-f --command="cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && sudo systemctl restart totalhunter && sleep 2 && sudo systemctl is-active totalhunter"
```
Expected output ends with `active`.

- [ ] **Step 3: Deploy frontend to Vercel**

Run:
```bash
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
```
Then poll deployment state and attach the `total-hunter.com` alias per the 3-step Vercel deploy procedure in `CLAUDE.md` section 6.5.

- [ ] **Step 4: Live verification on production**

Open `https://total-hunter.com/chests/m00bqgjcl1xqUHRDvEa8bQ` (the real 229/BERS public page) and confirm:
- Real player data renders with the new column order and styling.
- "Последнее обновление" shows a recent, real timestamp matching the clan's actual latest chest submission.
- Horizontal scroll + sticky player column work on a narrow viewport with the real (wide, many-chest-type) dataset.
