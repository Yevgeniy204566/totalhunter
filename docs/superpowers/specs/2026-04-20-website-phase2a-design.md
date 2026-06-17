# Design Spec — Website Phase 2A
**Date:** 2026-04-20  
**Status:** Approved by user

---

## Scope

Polish the existing personal dashboard (totalhunter.vercel.app). No new pages. No new backend tables. Pure UI improvements + 3 targeted feature additions.

Out of scope: referral tree, daily bonus, Free-Kassa, support tickets, bot changes, translations.

---

## 1. Design System — Deep Night theme upgrades

**Palette** — keep existing Deep Night, fix low-contrast areas:
- `--primary`: `#1B3A82` → buttons, active nav
- `--primary-dim`: `#2A4A9E` → hover
- `--green-btn`: `#0F5A3A` → Transfer / positive action buttons
- `--green-hover`: `#0A4A2E`
- `--on-surface`: `#C8D8F0` — primary text
- `--on-surface2`: `#8090B8` — secondary text

**Button sizes** — upgrade from current (14px/10px-padding) to:
- `.btn-primary`: `font-size: 16px`, `padding: 14px 28px`, `border-radius: 8px`, `font-weight: 600`
- `.btn-secondary`: same size + `border: 2px solid var(--primary-dim)`
- `.btn-danger`: inherits `.btn-secondary` size + `border-color: var(--error)`, `color: var(--error-text)`
- `.btn-green`: `background: var(--green-btn)` + same size as `.btn-primary`

**Nav sidebar** — active item: `background: var(--primary)`, inactive: `color: var(--on-surface2)`, font-size 14px, padding 10px, border-radius 6px.

**Files changed:** `web/src/styles/theme.css`

---

## 2. Global Stats Widget

Show platform-wide hunt counts on the dashboard (social proof — new users see the tool is actively used).

**UI:** A stats bar at the top of the dashboard (above profile card), 3 stat tiles side by side:
- "Exchanges found today" — count from backend
- "Crypts found today" — count from backend  
- "Active hunters" — unique users who hunted today

**Backend:** New endpoint `GET /web/stats/global` (no auth required).  
Returns: `{ exchanges_today: int, crypts_today: int, active_hunters: int }`  
Query: `SELECT hunt_type, COUNT(*) FROM hunt WHERE created_at >= today GROUP BY hunt_type` + distinct user count.

**Files changed:** `server/web_routes.py`, `web/src/api.js` (add `globalStats()`), `web/src/pages/DashboardPage.jsx`

---

## 3. Referral Transfer Button

Add "Transfer to Balance" button on ReferralsPage. The API method `api.referralTransfer()` already exists in `api.js` and the backend endpoint `POST /web/referral/transfer` is already implemented.

**UI:** On `ReferralsPage.jsx`, below the referral code block, add:
- Row: "Referral balance: **N credits**" + green `.btn-green` button "Transfer to Balance"
- Button disabled when `ref_credits === 0`
- On success: show confirmation message + re-fetch user data
- On error: show error message

**Files changed:** `web/src/pages/ReferralsPage.jsx`

---

## 4. Referral Link (replace code display)

The referral code still exists in the DB — just change how it's presented.

**UI change only** (no backend change):
- Replace plain `<code>AB12CD</code>` display with the full link: `https://totalhunter.vercel.app/ref/AB12CD`
- "Copy" button copies the full link, not just the code
- Show short code below link as secondary info: "Code: AB12CD"

**Note:** The `/ref/:code` route on the frontend doesn't need to do anything yet (Phase 2B will implement cookie tracking). For now just display the link correctly.

**Files changed:** `web/src/pages/ReferralsPage.jsx`

---

## 5. Layout polish — consistent card spacing

Minor pass across all pages for consistency:
- All page titles: `font-size: 22px`, `font-weight: 700`, `margin-bottom: 24px`
- All cards: `padding: 24px` (currently some are 20px)
- Table row height: `padding: 10px 0` (currently 8px — too tight for 35+ audience)
- Input fields: `font-size: 16px`, `padding: 14px` to match button size

**Files changed:** `web/src/styles/theme.css` (global rules), individual page files where inline styles override

---

## 6. Ad Slots (empty containers, ready for Coinzilla)

Add two banner containers to `Layout.jsx` — visually consistent with Deep Night, no ad code yet:
- **Top banner:** above the main content area, full width, height 90px, `background: var(--elevated)`, border-bottom `1px solid var(--outline)`, centered text "Ad" in `var(--on-surface2)` as placeholder
- **Footer banner:** below main content, same style, height 90px

When Coinzilla is integrated (Phase 2B), just replace the placeholder div content with their script tag.

**Files changed:** `web/src/components/Layout.jsx`, `web/src/styles/theme.css` (`.ad-slot` class)

---

## 7. Referral Link Cookie Tracking

Flow:
1. User clicks `https://totalhunter.vercel.app/ref/AB12CD`
2. New React route `/ref/:code` saves `ref_code` to cookie (30-day expiry), redirects to `/login`
3. `LoginPage.jsx` reads cookie on mount, passes `ref_code` to `api.authGoogle(id_token, ref_code)`
4. Backend `POST /web/auth/google` accepts optional `ref_code` — sets `referred_by` on the new User row only if user is new AND `referred_by` is currently null

Cookie key: `th_ref`. Cookie expiry: 30 days. If no cookie → `ref_code` is `null` → backend ignores it.

**Files changed:** `web/src/App.jsx` (add `/ref/:code` route), `web/src/pages/LoginPage.jsx`, `web/src/api.js` (`authGoogle` gains optional param), `server/web_routes.py` (`GoogleAuthRequest` gains optional `ref_code: str | None`)

---

## 8. Feedback Module

New nav item "Feedback" (last in sidebar, before Sign out).

**UI:** `FeedbackPage.jsx` — single `<textarea>` (4 rows, max 1000 chars) + `.btn-primary` "Send Idea" button. On success: "Thank you! We read every suggestion." On error: show message. Textarea clears after send.

**Backend:** `POST /web/feedback` (auth required). Body: `{ text: str }`. Saves to new `Feedback` table.

**DB model:**
```python
class Feedback(Base):
    __tablename__ = "feedback"
    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    text       = Column(Text, nullable=False)
    created_at = Column(DateTime, default=func.now())
```

**Alembic migration:** new file `server/alembic/versions/xxxx_add_feedback.py`

**Files changed:** `server/models.py`, `server/web_routes.py`, `server/alembic/versions/`, `web/src/pages/FeedbackPage.jsx` (new), `web/src/components/Layout.jsx` (add nav item), `web/src/App.jsx` (add route)

---

## 9. Balance Page — UI Stubs

On `BalancePage.jsx` add two placeholder sections (no functionality, just UI):
- **Daily Bonus block:** card with "Daily Bonus" title, big button "Watch Ad → Get 3–7 Credits" (disabled, tooltip "Coming soon"), shows "0/3 claimed today"
- **Buy Credits block:** card with "Buy Credits" title, package options (50 / 100 / 500 credits), button "Buy via Free-Kassa" (disabled, tooltip "Coming soon")

**Files changed:** `web/src/pages/BalancePage.jsx`

---

## Data Flow

```
New user clicks /ref/AB12CD
  → /ref/:code route → saves cookie th_ref=AB12CD → redirect /login
  → LoginPage reads cookie → authGoogle(id_token, ref_code="AB12CD")
  → backend sets user.referred_by = "AB12CD" (new users only)

DashboardPage loads
  → api.me()          → GET /web/me           → user profile
  → api.globalStats() → GET /web/stats/global → platform counts (no auth)

ReferralsPage loads
  → api.me() → user.ref_credits, user.ref_code
  → displays full link: totalhunter.vercel.app/ref/{ref_code}

Transfer button clicked
  → api.referralTransfer() → POST /web/referral/transfer
  → on success → api.me() refresh

Feedback send clicked
  → api.sendFeedback(text) → POST /web/feedback
  → saved to Feedback table with user_id
```

---

## Error Handling

- Global stats fail silently (show `—` in tiles, don't break dashboard)
- Transfer: show inline error message, re-enable button
- All loading states: show "Loading..." text, not blank

---

## Testing

- `GET /web/stats/global` returns correct counts (manual test with seeded data)
- Transfer button disabled when `ref_credits === 0`
- Transfer button triggers success message and updates balance display
- Referral page shows full link, Copy copies full URL
- Buttons visually larger than before (visual regression check)
