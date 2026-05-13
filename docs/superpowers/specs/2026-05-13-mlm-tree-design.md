# MLM Referral Tree — Design Spec
**Date:** 2026-05-13  
**Status:** Approved

---

## Summary

Add a visual MLM referral tree to `ReferralsPage` on total-hunter.com. Users see their referral network as an interactive org-chart (desktop) or accordion (mobile), with per-node data: masked username, join date, credits balance.

---

## Decisions

| Question | Decision |
|---|---|
| Desktop layout | Org-chart — top-down (root → L1 → L2 → L3) |
| Mobile layout | Vertical accordion (L1 rows, expand to show L2/L3) |
| Node data — diamonds | `credits` (main balance) |
| Large L1 list | Show first 5, `+ ещё N` button reveals all |
| Click behavior | Click node = expand/collapse children; all data visible on card |
| Email masking | First 3 chars + `***` (no domain — all users are Google/Gmail) |
| Implementation | Pure CSS tree, no new dependencies |

---

## Backend

### New endpoint: `GET /web/referral/tree`

**File:** `server/web_routes.py`  
**Auth:** `get_web_user` (JWT bearer, same as all `/web/*` routes)

**Logic — 3 async queries:**
1. `SELECT id, email, credits, created_at FROM users WHERE invited_by_id = {me.id}`
2. `SELECT id, email, credits, created_at FROM users WHERE invited_by_id IN {l1_ids}`
3. `SELECT id, email, credits, created_at FROM users WHERE invited_by_id IN {l2_ids}`

Queries 2 and 3 are skipped (return `[]`) if the preceding list is empty.

**Email masking:** `email[:3] + "***"` — applied server-side before returning.

**Response schema:**
```json
{
  "l1": [
    {
      "id": 1,
      "email_masked": "yev***",
      "credits": 50,
      "created_at": "2026-02-15",
      "l2": [
        {
          "id": 5,
          "email_masked": "ser***",
          "credits": 12,
          "created_at": "2026-03-20",
          "l3": [
            {
              "id": 11,
              "email_masked": "pet***",
              "credits": 4,
              "created_at": "2026-04-01"
            }
          ]
        }
      ]
    }
  ]
}
```

L3 nodes have no `l3` field (depth = 3 max).

**Performance:** Max 3 DB round-trips. No recursive CTE needed — depth is fixed at 3.

**Index:** `users.invited_by_id` currently has no index in `models.py`. This endpoint requires an Alembic migration to add `Index('ix_users_invited_by_id', 'invited_by_id')` — otherwise L2/L3 queries do full table scans.

---

## Frontend

### New file: `web/src/components/ReferralTree.jsx`

**State:**
- `treeData` — API response, null while loading
- `expandedIds` — `Set<number>` of node IDs whose children are visible
- `showAllL1` — `boolean`, false = show first 5 L1 nodes only

**Component tree:**
```
ReferralTree
  ├── loading state → spinner
  ├── empty state → "У вас пока нет рефералов"
  ├── DesktopTree  [hidden on mobile via CSS media query ≤640px]
  │     ├── RootNode  (current user — "ВЫ" badge, email masked, credits)
  │     ├── L1Row
  │     │     ├── NodeCard × min(5, l1.length)
  │     │     │     ├── badge, email_masked, created_at, credits
  │     │     │     └── expand button (only if node.l2.length > 0)
  │     │     │           └── L2Row (rendered below node when expanded)
  │     │     │                 ├── NodeCard × l2 items
  │     │     │                 │     └── expand button (only if node.l3.length > 0)
  │     │     │                 │           └── L3Row
  │     │     └── ShowMoreBtn  (only if l1.length > 5)
  └── MobileAccordion  [hidden on desktop via CSS media query >640px]
        └── AccordionItem × l1 (header: badge + email + credits + arrow)
              └── AccordionBody (L2 list as flat rows)
                    └── AccordionSubItem × l2 (badge + email + credits)
                          └── AccordionSubBody (L3 list, shown on sub-expand)
```

**CSS connector lines (pure CSS, no SVG):**
- Vertical line from parent to children row: `::before` on children container
- Horizontal bar across children: `::before` on children inner flex row
- Per-node vertical drop: `::before` on `.node-col`
- Colors: L1 = `#3D7FFF`, L2 = `#B060FF`, L3 = `#FFD166`
- Children row uses `align-items: flex-start` so cards of varying height don't misalign connector lines

**Expand/collapse:** Toggle `expandedIds.has(node.id)` on card click. `▶` icon when collapsed, `▲` when expanded.

**Show more:** `showAllL1` state. Button label: `+ ещё {l1.length - 5}`. Clicking sets `showAllL1 = true`. When expanded, a `Свернуть` button appears to collapse back to 5 (prevents 100+ node sprawl).

**L2/L3 pagination:** None. All L2 children of an expanded L1 node are shown in full, same for L3. In practice these numbers are small (a user rarely has 10+ L2 under one L1).

### Changes to existing files

**`web/src/pages/ReferralsPage.jsx`:**
- Import `ReferralTree` at top
- Add `<ReferralTree />` section after the "Cascade info" card (bottom of page)
- Add section header: `r.treeTitle` (i18n key)

**`web/src/api.js`:**
- Add: `referralTree: () => request('GET', '/web/referral/tree')`

**`web/src/dashboard_content.js` + `dashboard_content.en.js`:**
- Add `referrals.treeTitle` — RU: `"Ваша сеть"`, EN: `"Your Network"`
- Add `referrals.treeEmpty` — RU: `"У вас пока нет рефералов"`, EN: `"No referrals yet"`

---

## Mobile accordion

Breakpoint: `max-width: 640px` (matches existing mobile breakpoints in the project).

Each L1 row:
- Header: `[L1 badge] [email***] [credits ◆] [▶/▲]`
- Body (visible when expanded): flat list of L2 rows
  - Each L2 row: `[L2 badge] [email***] [credits ◆] [▶/▲ if has L3]`
  - L3 sub-body: flat list of L3 rows (same format, no expand)
- `+ ещё N` button at bottom if l1.length > 5

---

## Out of scope

- Pagination beyond "show more" button
- Earnings-per-node breakdown (separate feature)
- Admin view of other users' trees
- Real-time updates (page reload sufficient)

---

## Loading state

Show a skeleton (3 placeholder NodeCard outlines) while `treeData === null`. Prevents blank flash during the 3 sequential DB queries. Skeleton matches the shape of NodeCard: same width/height, `background: rgba(255,255,255,0.05)`, animated pulse via CSS `@keyframes`.

---

## Files changed

| File | Change |
|---|---|
| `server/alembic/versions/<hash>_add_index_invited_by_id.py` | New migration — index on `users.invited_by_id` |
| `server/models.py` | Add `index=True` to `invited_by_id` column |
| `server/web_routes.py` | Add `GET /web/referral/tree` endpoint |
| `web/src/components/ReferralTree.jsx` | New file |
| `web/src/pages/ReferralsPage.jsx` | Import + render `<ReferralTree />` |
| `web/src/api.js` | Add `referralTree` method |
| `web/src/dashboard_content.js` | Add `treeTitle`, `treeEmpty` keys |
| `web/src/dashboard_content.en.js` | Add `treeTitle`, `treeEmpty` keys |
