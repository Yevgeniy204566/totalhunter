# Phase 2B — Economy: Design Spec
**Date:** 2026-04-21  
**Status:** Approved  
**Scope:** Free-Kassa payments + 3-level referral cascade + Leaderboard TOP-50

---

## Context

Phase 2A complete: web platform, Google OAuth, HWID linking, referral UI, anti-fraud HWID bonuses.  
Phase 2B adds the revenue engine: paid credit packages, referral earnings on purchases, leaderboard.

Market: international (Ukraine, EU, China, USA). Currency: USD in UI. Free-Kassa converts to local currency automatically.

---

## 1. Credit Packages

| ID | USD | credits_total | Base | Bonus |
|----|-----|---------------|------|-------|
| `lite` | $1.00 | 300 | 300 | 0 |
| `pro` | $5.00 | 2000 | 1500 | 500 |
| `ultra` | $10.00 | 5000 | 4000 | 1000 |

`credits_total` is the canonical amount — used for crediting the buyer AND as the base for referral % calculation.

---

## 2. Payment Flow

### POST /web/payment/create (JWT required)
- Input: `{ "package": "lite" | "pro" | "ultra" }`
- Creates `Order` row: `status=pending`, `idempotency_key=uuid4()`
- Builds Free-Kassa redirect URL with HMAC signature (`FK_MERCHANT_ID`, `FK_SECRET_WORD`)
- Returns: `{ "redirect_url": "https://pay.freekassa.com/..." }`

### POST /web/payment/webhook (no auth — called by Free-Kassa)
- Input: Free-Kassa form-data notification
- Steps:
  1. Verify HMAC signature — reject 400 if invalid
  2. Find `Order` by `freekassa_order_id`
  3. **Idempotency check:** if `order.status == "paid"` → return 200 immediately (no double-credit)
  4. In single DB transaction:
     - `user.credits += credits_total`
     - Insert `Transaction(type="purchase", amount=credits_total, usd_amount=usd, package=pkg)`
     - Call `_apply_referral_cascade(db, buyer, credits_total)`
     - `order.status = "paid"`
  5. Return `"YES"` (Free-Kassa expects this string)

### New DB table: `orders`
```
id               INTEGER PK
user_id          FK → users.id
package          VARCHAR(10)         -- lite / pro / ultra
usd_amount       NUMERIC(10,2)
credits_total    INTEGER
freekassa_order_id VARCHAR(50) UNIQUE
status           VARCHAR(10)         -- pending / paid / failed
idempotency_key  UUID UNIQUE
created_at       TIMESTAMP TZ
```

---

## 3. Referral Cascade

### Trigger
Called inside webhook handler after crediting the buyer, within the same DB transaction.

### Function signature
```python
async def _apply_referral_cascade(db: AsyncSession, buyer: User, credits_total: int) -> None
```

### Algorithm
Traverse up to 3 levels of `invited_by_id` chain:

| Level | Relation | Rate | Amount (pro example: 2000 cr) |
|-------|----------|------|-------------------------------|
| L1 | `buyer.invited_by` | 10% | 200 ref_credits |
| L2 | `L1.invited_by` | 5% | 100 ref_credits |
| L3 | `L2.invited_by` | 1% | 20 ref_credits |

### Rules
- Base = `credits_total` (includes bonus credits — e.g. 2000, not 1500)
- Skip level if referrer is `None` or `is_banned=True`
- Each level: `referrer.ref_credits += amount`
- Each level: insert `Transaction(type="ref_earning", amount=amount, meta={"level": N, "ref_from_user_id": buyer.id, "credits_total": credits_total})`
- All inserts atomic with the purchase transaction
- Minimum payout: `floor(credits_total * rate)` — integer arithmetic only

### Example
Buyer purchases `ultra` (5000 credits):
- L1: +500 ref_credits
- L2: +250 ref_credits
- L3: +50 ref_credits

---

## 4. Leaderboard TOP-50

### Endpoint
```
GET /admin/leaderboard?period=alltime|month|week
```
Admin token required (same as other `/admin/*` routes).

### Response
```json
[
  { "rank": 1, "username": "...", "hwid": "...",
    "hunts_total": 420, "exchanges": 310, "crypts": 110,
    "last_seen": "2026-04-21T..." }
]
```

### Query logic
- Filter `hunts.created_at >= period_start` (or no filter for alltime)
- GROUP BY user, ORDER BY hunts_total DESC, LIMIT 50
- JOIN users for username/hwid/last_seen

### Admin UI
- New nav item "Leaderboard" (icon: `leaderboard`)
- Period toggle: All time / Month / Week
- Table: Rank | Username | HWID | Exchanges | Crypts | Total | Last seen
- Refresh button — Alpine.js pattern matching existing pages

---

## 5. New Files & Changes

| File | Change |
|------|--------|
| `server/payments.py` | NEW — package constants, FK signature helper, `_apply_referral_cascade` |
| `server/web_routes.py` | ADD `/payment/create`, `/payment/webhook` routes |
| `server/models.py` | ADD `Order` model |
| `server/main.py` | IMPORT payments router |
| `server/alembic/versions/` | NEW migration for `orders` table |
| `server/admin/index.html` | ADD leaderboard page |
| `server/tests/test_payments.py` | NEW — webhook happy path, duplicate idempotency, referral cascade |
| `web/src/pages/BalancePage.jsx` | UPDATE — real package cards with /payment/create call |

---

## 6. Environment Variables (new)

| Var | Purpose |
|-----|---------|
| `FK_MERCHANT_ID` | Free-Kassa merchant ID |
| `FK_SECRET_WORD` | Free-Kassa secret for HMAC signature |

---

## 7. Error Handling

| Scenario | Behaviour |
|----------|-----------|
| Invalid FK signature | 400, log attempt |
| Order not found | 400 |
| Order already paid | 200 "YES" (idempotent) |
| User not found | 400 |
| User banned | 400 |
| Referrer banned | Skip that level silently |
| DB error | 500, FK will retry webhook |

---

## 8. Testing Plan

- `test_webhook_happy_path` — lite/pro/ultra each credit correct amount
- `test_webhook_duplicate` — second call with same order_id does not double-credit
- `test_webhook_invalid_signature` — returns 400
- `test_referral_cascade_l1_l2_l3` — verifies ref_credits at each level use credits_total as base
- `test_referral_cascade_banned_referrer` — banned L1 skipped, L2 still receives
- `test_leaderboard_returns_top50` — returns ranked list
