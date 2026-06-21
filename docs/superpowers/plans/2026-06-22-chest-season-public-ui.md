# Сундуки — UI публичной страницы: сезон, таймер, ранг, подсветка (3/3) — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the public, no-login `/chests/:slug` page's table and header to show season targets, a clan-timezone countdown timer, a rank column, an Epic-crypt-only quota column instead of the all-pattern total, and target-completion-based row coloring — using only data the backend already provides (Specs 1-2, already deployed).

**Architecture:** Pure frontend change confined to `web/src/pages/ChestSummaryPage.jsx` (rewrite) and `web/src/styles/theme.css` (new CSS appended). No backend, no migration, no new API calls — `fetchChestSummary` already returns everything needed.

**Tech Stack:** React + plain CSS. No frontend test runner exists in this repo — verification is `npm run build` + manual code trace + a deferred real-browser check (consistent with every prior frontend task in this project).

## Global Constraints

- "Achieved the norm" (for the top-3 premium row color) means **both** configured targets met simultaneously — points AND Epic-crypt quota — not either one alone.
- Progress ratio for the color bands is `min(points/target_points, quota_chests/target_chests)`, computed only over targets that are actually configured (non-null, non-zero); if neither target is configured, no row coloring and no season UI block at all (full backward compatibility with clans that haven't set up a season).
- Color bands: `ratio >= 1 && rank < 3` (rank is 0-based, so this covers places 1-3) → `row-top3`; `ratio >= 0.5` → no special class (default styling); `0 < ratio < 0.5` → `row-lagging`; `ratio <= 0` → `row-danger`.
- The countdown timer compares against the *clan's own timezone wall-clock*, computed as `Date.now() + offsetMinutes * 60000`, never the visitor's browser timezone. `period_end` is parsed manually from its date/time components (never passed to `new Date(string)` directly) to avoid the browser reinterpreting a naive ISO string in its own local zone.
- Final table column order, left to right: `#` (rank), `Player`, `Очки` (points), `Epic склепов` (`quota_chests`), then the dynamic `chest_types` columns (already sorted by total count descending by the backend — do not re-sort them on the frontend). The old all-pattern `total` field is no longer rendered anywhere on this page.
- The `#` and `Player` columns (the first two) are sticky on horizontal scroll, with opaque backgrounds that account for zebra striping, hover, and the `row-top3`/`row-lagging`/`row-danger` states — no see-through artifacts during scroll.
- No new color palette — reuse existing `theme.css` variables (`--card`, `--elevated`, `--outline`, `--on-surface2`, `--accent`, `--accent-glow`) plus the three named hex colors the spec specifies for row states (`#50C878`, `#FFB347`, `#FF6961`).

---

### Task 1: CSS — season badges, custom scrollbar, row-color classes, two-column sticky

**Files:**
- Modify: `web/src/styles/theme.css` (append new section at end of file)

**Interfaces:**
- Produces CSS classes consumed by Task 2: `.public-season-info`, `.public-season-badge`, `.public-season-timer`, `.row-top3`, `.row-lagging`, `.row-danger`, plus updated `:nth-child(1)`/`:nth-child(2)` sticky rules on `.public-table th`/`.public-table td` (replacing the existing single-column `:first-child` sticky rule from the prior plan).

- [ ] **Step 1: Remove the old single-column sticky rule**

The end of `web/src/styles/theme.css` currently has this block (from the prior `2026-06-20-chest-summary-redesign` plan):

```css
.public-table th:first-child, .public-table td:first-child {
  position: sticky; left: 0; z-index: 2;
  background: var(--card);
}
.public-table tbody tr:nth-child(even) td:first-child { background: #0D1326; }
.public-table tbody tr:hover td:first-child { background: var(--accent-glow); }
```

Delete this block — it's being replaced by the two-column version in Step 2 (the old single-sticky-column behavior is superseded now that `#` is a new first column and `Player` becomes the second).

- [ ] **Step 2: Append the new CSS**

Add to the end of `web/src/styles/theme.css`:

```css

/* ── Public chest summary — season info, timer, row coloring, two-col sticky ─ */
.public-season-info { display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 12px; }
.public-season-badge {
  background: var(--elevated); border: 1px solid var(--outline); border-radius: 8px;
  padding: 6px 12px; font-size: 13px; color: var(--on-surface2);
}
.public-season-timer { color: var(--accent); font-weight: 600; }

.public-table-wrap::-webkit-scrollbar { height: 10px; }
.public-table-wrap::-webkit-scrollbar-track { background: var(--elevated); border-radius: 4px; }
.public-table-wrap::-webkit-scrollbar-thumb { background: var(--accent); border-radius: 4px; }
.public-table-wrap::-webkit-scrollbar-thumb:hover { background: var(--accent-glow); }

.row-top3 td { color: #50C878; font-weight: 600; }
.row-lagging td { color: #FFB347; }
.row-danger td { color: #FF6961; }

.public-table th:nth-child(1), .public-table td:nth-child(1) {
  position: sticky; left: 0; z-index: 2; width: 40px; background: var(--card);
}
.public-table th:nth-child(2), .public-table td:nth-child(2) {
  position: sticky; left: 40px; z-index: 2; background: var(--card);
}
.public-table tbody tr:nth-child(even) td:nth-child(1),
.public-table tbody tr:nth-child(even) td:nth-child(2) { background: #0D1326; }
.public-table tbody tr:hover td:nth-child(1),
.public-table tbody tr:hover td:nth-child(2) { background: var(--accent-glow); }
.public-table tbody tr.row-top3 td:nth-child(1),
.public-table tbody tr.row-top3 td:nth-child(2) { background: var(--card); }
.public-table tbody tr.row-top3:nth-child(even) td:nth-child(1),
.public-table tbody tr.row-top3:nth-child(even) td:nth-child(2) { background: #0D1326; }
```

- [ ] **Step 3: Build check**

Run: `cd C:\BattleBot\web && npm run build`
Expected: exit code 0, no CSS/build errors (CSS has no compile step beyond bundling, so this mainly confirms no syntax breakage in the surrounding pipeline).

- [ ] **Step 4: Commit**

```bash
git add web/src/styles/theme.css
git commit -m "feat(web): add season badge, scrollbar, row-color, and two-column sticky CSS for public chest summary"
```

---

### Task 2: Rewrite ChestSummaryPage.jsx — timer, targets, rank, quota column, row coloring

**Files:**
- Modify: `web/src/pages/ChestSummaryPage.jsx` (full rewrite)

**Interfaces:**
- Consumes: `fetchChestSummary(slug)` (existing, unchanged signature) returning `{kingdom, clan, chest_types, players: [{name, counts, total, points, quota_chests}], totals, updated_at, period_start, period_end, timezone_offset_minutes, targets: {points, chests}}` (all fields already live in production as of Specs 1-2). CSS classes from Task 1.
- Produces: no new exports consumed elsewhere — this is a leaf page component.

- [ ] **Step 1: Rewrite the component**

Replace the entire contents of `web/src/pages/ChestSummaryPage.jsx` with:

```jsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { fetchChestSummary } from '../api.js'

function formatRemaining(periodEndIso, offsetMinutes) {
  const [datePart, timePart] = periodEndIso.split('T')
  const [y, mo, d] = datePart.split('-').map(Number)
  const [h, mi, s] = timePart.split(':').map(Number)
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

function rowColorClass(player, rank, targets) {
  const ratios = []
  if (targets.points) ratios.push(player.points / targets.points)
  if (targets.chests) ratios.push(player.quota_chests / targets.chests)
  if (ratios.length === 0) return ''
  const ratio = Math.min(...ratios)
  if (ratio >= 1 && rank < 3) return 'row-top3'
  if (ratio >= 0.5) return ''
  if (ratio > 0) return 'row-lagging'
  return 'row-danger'
}

function formatOffsetLabel(offsetMinutes) {
  const sign = offsetMinutes >= 0 ? '+' : '-'
  const abs = Math.abs(offsetMinutes)
  const h = String(Math.floor(abs / 60)).padStart(2, '0')
  const m = String(abs % 60).padStart(2, '0')
  return `${sign}${h}:${m}`
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
    ? new Date(data.updated_at).toLocaleString()
    : '—'

  const targets = data.targets || { points: null, chests: null }
  const hasSeasonTargets = targets.points != null || targets.chests != null

  return (
    <div className="page-content">
      <h1 className="gradient-text public-summary-title">{data.kingdom} / {data.clan}</h1>

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
          {data.period_end && (
            <CountdownTimer periodEnd={data.period_end} offsetMinutes={data.timezone_offset_minutes ?? 0} />
          )}
        </div>
      )}

      <div className="public-summary-updated">Последнее обновление: {updatedLabel}</div>
      <div className="public-summary-divider" />

      <div className="public-table-wrap">
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
    </div>
  )
}
```

- [ ] **Step 2: Build check**

Run: `cd C:\BattleBot\web && npm run build`
Expected: exit code 0, no JSX/import errors.

- [ ] **Step 3: Manual code trace (substitute for browser verification — no browser tool in this environment)**

Re-read the final file and confirm by inspection:
- `hasSeasonTargets` is `false` when both `targets.points` and `targets.chests` are `null` (the real 229/BERS clan's current state in production) — confirm the `public-season-info` block and everything inside it (badges, timer) does not render in that case, matching the Global Constraint of zero season-UI for unconfigured clans.
- Column order in both `<thead>` and each `<tbody>` row is exactly `#, Player, Очки, Epic склепов, ...chest_types` — no `total` field referenced anywhere in the JSX.
- `rowColorClass` is called with `(p, i, targets)` where `i` is the same zero-based index used for the rank cell (`{i + 1}`) — confirms rank-based top-3 logic uses the same ordinal as what's displayed to the user.
- `formatRemaining` never calls `new Date(periodEndIso)` directly — it manually splits the string and uses `Date.UTC(...)` as a pure arithmetic constructor, never relying on the runtime's local-timezone parsing of a naive ISO string.
- `CountdownTimer`'s `useEffect` cleans up its `setInterval` via the returned `clearInterval` callback — no leaked timers across slug navigation.

Report DONE_WITH_CONCERNS noting that real-browser checks (actually seeing the four row colors with real numbers, sticky-column scroll behavior with two columns now, the visible custom scrollbar, and the timer counting down in real time) are deferred to after deploy — expected, not a gap caused by this task.

- [ ] **Step 4: Commit**

```bash
git add web/src/pages/ChestSummaryPage.jsx
git commit -m "feat(web): add season targets, countdown timer, rank column, and target-completion row coloring to public chest summary"
```

---

### Task 3: Deploy and verify

**Files:** none (deployment only)

- [ ] **Step 1: Push to main**

Run: `git push origin main`

- [ ] **Step 2: Deploy frontend to Vercel**

Run:
```bash
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
```
Then poll deployment state and attach the `total-hunter.com` alias per the 3-step Vercel deploy procedure in `CLAUDE.md` section 6.5. No backend deploy is needed — this plan touches no server code.

- [ ] **Step 3: Live verification on production (unconfigured clan)**

Open `https://total-hunter.com/chests/m00bqgjcl1xqUHRDvEa8bQ` (real 229/BERS clan, currently has no season configured). Confirm:
- No season info block, no timer, no target badges appear (matches `targets.points`/`targets.chests` both being `null` in production right now).
- Table shows `#`, `Player`, `Очки`, `Epic склепов`, then the dynamic chest-type columns, in that order.
- `Epic склепов` column shows `0` for every player (dimmed, via `public-cell-zero`) since this clan hasn't marked any chest type as `counts_toward_quota` yet.
- Horizontal scroll on a narrow window keeps both `#` and `Player` visibly pinned.

- [ ] **Step 4: Live verification with a real season configured (owner-assisted)**

Through `/dashboard/chests` (already shipped), set a season for 229/BERS with small, easy-to-eyeball target numbers (e.g. low enough that at least one real player exceeds them) and mark a couple of chest types as "Считать в квоту." Reload the public page and confirm:
- The season info badges and a live, counting-down timer appear.
- At least one row shows each of the non-default colors achievable with the real data (top-3 green if some player's points and quota both clear the targets, amber/red for players below half/zero).
- Removing/clearing the season afterward (or simply noting it was a one-off test) is the owner's call — not part of this plan's required steps.
