# Phase 2B — Economy Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add paid credit packages (Free-Kassa), 3-level referral earnings on purchase, and Leaderboard TOP-50 to Total Hunter SaaS.

**Architecture:** `payments.py` owns all payment logic (PACKAGES, HMAC helpers, referral cascade, two new routes). Admin leaderboard goes directly into `main.py` following the existing admin pattern. All credits + referral cascade commit in one atomic DB transaction. Webhook is idempotent via `orders.status`.

**Tech Stack:** FastAPI, SQLAlchemy 2.0 async, SQLite (tests) / PostgreSQL (prod), Alembic, Alpine.js (admin), React/Vite (web frontend), Free-Kassa payment gateway.

---

## File Map

| Action | File | Responsibility |
|--------|------|----------------|
| Modify | `server/models.py` | Add `Order` ORM model |
| Modify | `server/schemas.py` | Add `PaymentCreateRequest`, `PaymentCreateResponse`, `LeaderboardEntry`, `LeaderboardResponse` |
| **Create** | `server/payments.py` | PACKAGES, FK helpers, referral cascade, `/payment/create`, `/payment/webhook` router |
| Modify | `server/main.py` | Include payments router; add `GET /admin/leaderboard` |
| Create | `server/alembic/versions/<hash>_add_orders.py` | Migration: create `orders` table |
| **Create** | `server/tests/test_payments.py` | All payment + referral + leaderboard tests |
| Modify | `server/admin/index.html` | Leaderboard nav + page (Alpine.js) |
| Modify | `web/src/pages/BalancePage.jsx` | Real package cards calling `/payment/create` |

---

## Task 1 — Order model + schema additions

**Files:**
- Modify: `server/models.py`
- Modify: `server/schemas.py`

- [ ] **Step 1.1 — Add Order to models.py**

Open `server/models.py`. After the `Feedback` class at the end, add:

```python
# ─────────────────────────────────────────────
# Orders — payment records
# ─────────────────────────────────────────────

class Order(Base):
    """
    One row per payment attempt.
    status: pending → paid (or failed).
    freekassa_order_id = str(order.id) — our PK sent to FK as merchant order id.
    Idempotency: webhook checks status == 'paid' before crediting.
    """
    __tablename__ = "orders"

    id                  = Column(Integer, primary_key=True)
    user_id             = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    package             = Column(String(10), nullable=False)
    usd_amount          = Column(Numeric(10, 2), nullable=False)
    credits_total       = Column(Integer, nullable=False)
    freekassa_order_id  = Column(String(50), unique=True, nullable=True)
    status              = Column(String(10), nullable=False, server_default=text("'pending'"))
    idempotency_key     = Column(String(36), unique=True, nullable=False)
    created_at          = Column(TIMESTAMP(timezone=True), nullable=False,
                                 server_default=func.now())

    user = relationship("User", backref="orders")
```

Also add `UUID` import — at the top of `models.py` the existing imports already cover `String`, `Integer`, `Numeric` etc. No new import needed.

- [ ] **Step 1.2 — Add schemas to schemas.py**

Open `server/schemas.py`. Append at the end:

```python
# ── Payments ──────────────────────────────────────────────────────────────────

class PaymentCreateRequest(BaseModel):
    package: str   # "lite" | "pro" | "ultra"

class PaymentCreateResponse(BaseModel):
    redirect_url: str

# ── Leaderboard ───────────────────────────────────────────────────────────────

class LeaderboardEntry(BaseModel):
    rank: int
    username: Optional[str]
    hwid: Optional[str]
    hunts_total: int
    exchanges: int
    crypts: int
    last_seen: Optional[str]

class LeaderboardResponse(BaseModel):
    items: list[LeaderboardEntry]
```

- [ ] **Step 1.3 — Generate Alembic migration**

```bash
cd server
alembic revision --autogenerate -m "add_orders"
```

Expected: creates `server/alembic/versions/XXXX_add_orders.py`.

Open the generated file and verify the `upgrade()` function contains `op.create_table('orders', ...)` with all columns. If autogenerate missed anything, the manual equivalent is:

```python
def upgrade() -> None:
    op.create_table(
        'orders',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('package', sa.String(10), nullable=False),
        sa.Column('usd_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('credits_total', sa.Integer(), nullable=False),
        sa.Column('freekassa_order_id', sa.String(50), nullable=True),
        sa.Column('status', sa.String(10), server_default="'pending'", nullable=False),
        sa.Column('idempotency_key', sa.String(36), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name='fk_orders_user_id_users'),
        sa.PrimaryKeyConstraint('id', name='pk_orders'),
        sa.UniqueConstraint('freekassa_order_id', name='uq_orders_freekassa_order_id'),
        sa.UniqueConstraint('idempotency_key', name='uq_orders_idempotency_key'),
    )
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])

def downgrade() -> None:
    op.drop_index('ix_orders_user_id', table_name='orders')
    op.drop_table('orders')
```

- [ ] **Step 1.4 — Commit**

```bash
git add server/models.py server/schemas.py server/alembic/versions/
git commit -m "feat: Order model + payment/leaderboard schemas"
```

---

## Task 2 — payments.py: PACKAGES, FK helpers, referral cascade

**Files:**
- Create: `server/payments.py`

- [ ] **Step 2.1 — Write failing tests for referral cascade first (TDD)**

Create `server/tests/test_payments.py`:

```python
"""Tests for payments.py — referral cascade logic."""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app
from models import User, Transaction
from database import get_db

# ── Helpers ───────────────────────────────────────────────────────────────────

async def _create_user(db, email, ref_code, invited_by_id=None, is_banned=False):
    import secrets
    u = User(
        email=email,
        username=email.split("@")[0],
        ref_code=ref_code or secrets.token_urlsafe(6),
        invited_by_id=invited_by_id,
        is_banned=is_banned,
    )
    db.add(u)
    await db.flush()
    return u


# ── Referral cascade tests ────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_referral_cascade_l1_l2_l3():
    """L1 gets 10%, L2 gets 5%, L3 gets 1% of credits_total."""
    from payments import _apply_referral_cascade

    async for db in app.dependency_overrides[get_db]():
        l3 = await _create_user(db, "l3@test.com", "L3CODE")
        l2 = await _create_user(db, "l2@test.com", "L2CODE", invited_by_id=l3.id)
        l1 = await _create_user(db, "l1@test.com", "L1CODE", invited_by_id=l2.id)
        buyer = await _create_user(db, "buyer@test.com", "BCODE", invited_by_id=l1.id)
        await db.flush()

        await _apply_referral_cascade(db, buyer, 2000)
        await db.flush()

        await db.refresh(l1)
        await db.refresh(l2)
        await db.refresh(l3)

        assert l1.ref_credits == 200   # 10% of 2000
        assert l2.ref_credits == 100   # 5% of 2000
        assert l3.ref_credits == 20    # 1% of 2000

        txns = (await db.execute(
            select(Transaction).where(Transaction.type == "ref_earning")
        )).scalars().all()
        assert len(txns) == 3
        levels = {t.meta["level"]: t.amount for t in txns}
        assert levels == {1: 200, 2: 100, 3: 20}


@pytest.mark.asyncio
async def test_referral_cascade_uses_credits_total_not_base():
    """Cascade base = credits_total (5000 ultra), not base credits."""
    from payments import _apply_referral_cascade

    async for db in app.dependency_overrides[get_db]():
        l1 = await _create_user(db, "ref_a@test.com", "REFA")
        buyer = await _create_user(db, "buyer_a@test.com", "BUYERA", invited_by_id=l1.id)
        await db.flush()

        await _apply_referral_cascade(db, buyer, 5000)
        await db.flush()
        await db.refresh(l1)

        assert l1.ref_credits == 500   # 10% of 5000 (not 10% of 4000 base)


@pytest.mark.asyncio
async def test_referral_cascade_banned_l1_skipped_l2_still_receives():
    """Banned L1 is skipped; cascade continues to L2."""
    from payments import _apply_referral_cascade

    async for db in app.dependency_overrides[get_db]():
        l2 = await _create_user(db, "l2b@test.com", "L2B")
        l1_banned = await _create_user(db, "l1b@test.com", "L1B",
                                        invited_by_id=l2.id, is_banned=True)
        buyer = await _create_user(db, "buyerb@test.com", "BUYERB",
                                    invited_by_id=l1_banned.id)
        await db.flush()

        await _apply_referral_cascade(db, buyer, 2000)
        await db.flush()
        await db.refresh(l1_banned)
        await db.refresh(l2)

        assert l1_banned.ref_credits == 0   # banned — no payout
        assert l2.ref_credits == 100        # L2 gets 5% regardless


@pytest.mark.asyncio
async def test_referral_cascade_no_referrer():
    """No invited_by — cascade is a no-op."""
    from payments import _apply_referral_cascade

    async for db in app.dependency_overrides[get_db]():
        buyer = await _create_user(db, "solo@test.com", "SOLO")
        await db.flush()

        await _apply_referral_cascade(db, buyer, 300)
        await db.flush()

        txns = (await db.execute(
            select(Transaction).where(Transaction.type == "ref_earning")
        )).scalars().all()
        assert len(txns) == 0
```

- [ ] **Step 2.2 — Run tests to confirm they fail (payments.py missing)**

```bash
cd server
python -m pytest tests/test_payments.py -v 2>&1 | head -20
```

Expected: `ImportError: cannot import name '_apply_referral_cascade' from 'payments'` or `ModuleNotFoundError: No module named 'payments'`.

- [ ] **Step 2.3 — Create server/payments.py**

```python
"""
payments.py — Free-Kassa integration + referral cascade.

Routes: POST /web/payment/create, POST /web/payment/webhook
Helpers: build_fk_url, verify_fk_webhook_signature, _apply_referral_cascade
"""

import hashlib
import os
import uuid
from urllib.parse import urlencode

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Order, Transaction, User
from schemas import PaymentCreateRequest, PaymentCreateResponse
from web_routes import get_web_user

router = APIRouter(prefix="/web", tags=["payments"])

FK_MERCHANT_ID  = os.environ.get("FK_MERCHANT_ID", "")
FK_SECRET_WORD  = os.environ.get("FK_SECRET_WORD", "")   # signs payment links
FK_SECRET_WORD2 = os.environ.get("FK_SECRET_WORD2", "")  # verifies webhooks

PACKAGES: dict[str, dict] = {
    "lite":  {"usd": "1.00",  "credits": 300},
    "pro":   {"usd": "5.00",  "credits": 2000},
    "ultra": {"usd": "10.00", "credits": 5000},
}


# ── FK helpers ────────────────────────────────────────────────────────────────

def build_fk_url(order_id: str, amount: str) -> str:
    """Build Free-Kassa payment redirect URL with MD5 signature."""
    sign_str = f"{FK_MERCHANT_ID}:{amount}:{FK_SECRET_WORD}:USD:{order_id}"
    sign = hashlib.md5(sign_str.encode()).hexdigest()
    params = {
        "m":        FK_MERCHANT_ID,
        "oa":       amount,
        "currency": "USD",
        "o":        order_id,
        "s":        sign,
        "lang":     "en",
    }
    return "https://pay.freekassa.com/?" + urlencode(params)


def verify_fk_webhook_signature(amount: str, order_id: str, received_sign: str) -> bool:
    """Verify HMAC from Free-Kassa webhook notification."""
    sign_str = f"{FK_MERCHANT_ID}:{amount}:{FK_SECRET_WORD2}:{order_id}"
    expected = hashlib.md5(sign_str.encode()).hexdigest()
    return expected == received_sign


# ── Referral cascade ──────────────────────────────────────────────────────────

async def _apply_referral_cascade(
    db: AsyncSession, buyer: User, credits_total: int
) -> None:
    """
    Walk up to 3 levels of invited_by_id chain.
    Base for % calculation = credits_total (includes bonus credits).
    Banned referrers are skipped; chain traversal continues.
    All writes happen inside the caller's transaction.
    """
    LEVELS = [(1, 0.10), (2, 0.05), (3, 0.01)]
    current_id = buyer.invited_by_id

    for level, rate in LEVELS:
        if not current_id:
            break

        result = await db.execute(select(User).where(User.id == current_id))
        referrer = result.scalar_one_or_none()

        if referrer is None:
            break

        if not referrer.is_banned:
            amount = int(credits_total * rate)
            if amount > 0:
                referrer.ref_credits += amount
                db.add(Transaction(
                    user_id=referrer.id,
                    type="ref_earning",
                    amount=amount,
                    meta={
                        "level": level,
                        "ref_from_user_id": buyer.id,
                        "credits_total": credits_total,
                    },
                ))

        current_id = referrer.invited_by_id


# ── POST /web/payment/create ──────────────────────────────────────────────────

@router.post("/payment/create", response_model=PaymentCreateResponse)
async def payment_create(
    req: PaymentCreateRequest,
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    pkg = PACKAGES.get(req.package)
    if not pkg:
        raise HTTPException(status_code=400, detail="Invalid package")

    idem_key = str(uuid.uuid4())

    async with db.begin():
        order = Order(
            user_id=web_user.id,
            package=req.package,
            usd_amount=pkg["usd"],
            credits_total=pkg["credits"],
            idempotency_key=idem_key,
            status="pending",
        )
        db.add(order)
        await db.flush()
        order.freekassa_order_id = str(order.id)

    redirect_url = build_fk_url(order_id=str(order.id), amount=pkg["usd"])
    return PaymentCreateResponse(redirect_url=redirect_url)


# ── POST /web/payment/webhook ─────────────────────────────────────────────────

@router.post("/payment/webhook")
async def payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    amount           = str(form.get("AMOUNT", ""))
    merchant_order_id = str(form.get("MERCHANT_ORDER_ID", ""))
    sign             = str(form.get("SIGN", ""))

    if not verify_fk_webhook_signature(amount, merchant_order_id, sign):
        raise HTTPException(status_code=400, detail="Invalid signature")

    async with db.begin():
        order_result = await db.execute(
            select(Order).where(Order.freekassa_order_id == merchant_order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=400, detail="Order not found")

        # Idempotency: Free-Kassa may send the webhook more than once
        if order.status == "paid":
            return PlainTextResponse("YES")

        user_result = await db.execute(select(User).where(User.id == order.user_id))
        user = user_result.scalar_one_or_none()
        if not user or user.is_banned:
            raise HTTPException(status_code=400, detail="User not found or banned")

        user.credits += order.credits_total
        db.add(Transaction(
            user_id=user.id,
            type="purchase",
            amount=order.credits_total,
            usd_amount=order.usd_amount,
            package=order.package,
            meta={"freekassa_order_id": merchant_order_id},
        ))

        await _apply_referral_cascade(db, user, order.credits_total)

        order.status = "paid"

    return PlainTextResponse("YES")
```

- [ ] **Step 2.4 — Run referral cascade tests**

```bash
cd server
python -m pytest tests/test_payments.py -k "cascade" -v
```

Expected: all 4 cascade tests PASS.

- [ ] **Step 2.5 — Commit**

```bash
git add server/payments.py server/tests/test_payments.py
git commit -m "feat: payments.py — PACKAGES, FK helpers, referral cascade (TDD)"
```

---

## Task 3 — Connect payments router + webhook tests

**Files:**
- Modify: `server/main.py`
- Modify: `server/tests/test_payments.py` (append)

- [ ] **Step 3.1 — Include payments router in main.py**

In `server/main.py`, find the existing import line:

```python
from web_routes import router as web_router
```

Add below it:

```python
from payments import router as payments_router
```

Find the existing line:

```python
app.include_router(web_router)
```

Add below it:

```python
app.include_router(payments_router)
```

- [ ] **Step 3.2 — Write webhook tests (append to test_payments.py)**

Add these tests to `server/tests/test_payments.py`:

```python
# ── Webhook tests ─────────────────────────────────────────────────────────────

import hashlib

FK_TEST_MERCHANT  = "12345"
FK_TEST_SECRET    = "secret1"
FK_TEST_SECRET2   = "secret2"


def _make_sign(amount: str, order_id: str) -> str:
    """Compute valid webhook signature using test credentials."""
    data = f"{FK_TEST_MERCHANT}:{amount}:{FK_TEST_SECRET2}:{order_id}"
    return hashlib.md5(data.encode()).hexdigest()


@pytest.fixture(autouse=False)
def fk_env(monkeypatch):
    monkeypatch.setenv("FK_MERCHANT_ID",  FK_TEST_MERCHANT)
    monkeypatch.setenv("FK_SECRET_WORD",  FK_TEST_SECRET)
    monkeypatch.setenv("FK_SECRET_WORD2", FK_TEST_SECRET2)
    # Reload module-level constants
    import payments
    payments.FK_MERCHANT_ID  = FK_TEST_MERCHANT
    payments.FK_SECRET_WORD  = FK_TEST_SECRET
    payments.FK_SECRET_WORD2 = FK_TEST_SECRET2


@pytest.mark.asyncio
async def test_webhook_happy_path_credits_buyer(fk_env):
    """Valid webhook credits buyer and marks order paid."""
    async for db in app.dependency_overrides[get_db]():
        from models import Order
        import secrets as _s
        user = User(email="buyer_w@test.com", username="buyer_w",
                    ref_code=_s.token_urlsafe(6))
        db.add(user)
        await db.flush()
        order = Order(user_id=user.id, package="pro", usd_amount="5.00",
                      credits_total=2000, freekassa_order_id="ORDER-1",
                      status="pending", idempotency_key=str(uuid.uuid4()))
        db.add(order)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/web/payment/webhook", data={
            "MERCHANT_ID":       FK_TEST_MERCHANT,
            "AMOUNT":            "5.00",
            "MERCHANT_ORDER_ID": "ORDER-1",
            "SIGN":              _make_sign("5.00", "ORDER-1"),
        })

    assert resp.status_code == 200
    assert resp.text == "YES"

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import select as _sel
        u = (await db.execute(_sel(User).where(User.email == "buyer_w@test.com"))).scalar_one()
        assert u.credits == 2000
        o = (await db.execute(_sel(Order).where(Order.freekassa_order_id == "ORDER-1"))).scalar_one()
        assert o.status == "paid"


@pytest.mark.asyncio
async def test_webhook_duplicate_is_idempotent(fk_env):
    """Second webhook call with same order_id does NOT double-credit."""
    async for db in app.dependency_overrides[get_db]():
        from models import Order
        import secrets as _s
        user = User(email="idem@test.com", username="idem",
                    ref_code=_s.token_urlsafe(6))
        db.add(user)
        await db.flush()
        order = Order(user_id=user.id, package="lite", usd_amount="1.00",
                      credits_total=300, freekassa_order_id="ORDER-IDEM",
                      status="pending", idempotency_key=str(uuid.uuid4()))
        db.add(order)
        await db.commit()

    payload = {
        "MERCHANT_ID":       FK_TEST_MERCHANT,
        "AMOUNT":            "1.00",
        "MERCHANT_ORDER_ID": "ORDER-IDEM",
        "SIGN":              _make_sign("1.00", "ORDER-IDEM"),
    }
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/web/payment/webhook", data=payload)
        resp2 = await client.post("/web/payment/webhook", data=payload)

    assert resp2.status_code == 200
    assert resp2.text == "YES"

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import select as _sel
        u = (await db.execute(_sel(User).where(User.email == "idem@test.com"))).scalar_one()
        assert u.credits == 300  # credited exactly once


@pytest.mark.asyncio
async def test_webhook_invalid_signature_returns_400(fk_env):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/web/payment/webhook", data={
            "MERCHANT_ID":       FK_TEST_MERCHANT,
            "AMOUNT":            "5.00",
            "MERCHANT_ORDER_ID": "ORDER-BAD",
            "SIGN":              "badsignature000",
        })
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_triggers_referral_l1(fk_env):
    """Webhook credits L1 referrer with 10% of credits_total."""
    async for db in app.dependency_overrides[get_db]():
        from models import Order
        import secrets as _s
        referrer = User(email="ref_wh@test.com", username="ref_wh",
                        ref_code=_s.token_urlsafe(6))
        db.add(referrer)
        await db.flush()
        buyer = User(email="buyer_wh@test.com", username="buyer_wh",
                     ref_code=_s.token_urlsafe(6), invited_by_id=referrer.id)
        db.add(buyer)
        await db.flush()
        order = Order(user_id=buyer.id, package="ultra", usd_amount="10.00",
                      credits_total=5000, freekassa_order_id="ORDER-REF",
                      status="pending", idempotency_key=str(uuid.uuid4()))
        db.add(order)
        await db.commit()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/web/payment/webhook", data={
            "MERCHANT_ID":       FK_TEST_MERCHANT,
            "AMOUNT":            "10.00",
            "MERCHANT_ORDER_ID": "ORDER-REF",
            "SIGN":              _make_sign("10.00", "ORDER-REF"),
        })

    async for db in app.dependency_overrides[get_db]():
        from sqlalchemy import select as _sel
        ref = (await db.execute(_sel(User).where(User.email == "ref_wh@test.com"))).scalar_one()
        assert ref.ref_credits == 500  # 10% of 5000
```

- [ ] **Step 3.3 — Run all payment tests**

```bash
cd server
python -m pytest tests/test_payments.py -v
```

Expected: all tests PASS.

- [ ] **Step 3.4 — Run full test suite to check no regressions**

```bash
cd server
python -m pytest tests/ -v
```

Expected: all tests PASS.

- [ ] **Step 3.5 — Commit**

```bash
git add server/main.py server/tests/test_payments.py
git commit -m "feat: wire payments router + webhook tests (idempotency, referral, invalid sig)"
```

---

## Task 4 — Admin leaderboard endpoint

**Files:**
- Modify: `server/main.py`
- Modify: `server/tests/test_payments.py` (append leaderboard test)

- [ ] **Step 4.1 — Write failing leaderboard test (append to test_payments.py)**

```python
# ── Leaderboard tests ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_leaderboard_returns_ranked_list():
    """GET /admin/leaderboard returns users ranked by total hunts."""
    import secrets as _s
    from models import Hunt

    async for db in app.dependency_overrides[get_db]():
        u1 = User(email="top@lb.com", username="top", ref_code=_s.token_urlsafe(6))
        u2 = User(email="mid@lb.com", username="mid", ref_code=_s.token_urlsafe(6))
        db.add(u1); db.add(u2)
        await db.flush()
        for _ in range(5):
            db.add(Hunt(user_id=u1.id, hunt_type="exchange"))
        for _ in range(2):
            db.add(Hunt(user_id=u2.id, hunt_type="crypt"))
        await db.commit()

    ADMIN_TOKEN = os.environ.get("ADMIN_TOKEN", "dev-admin-token")
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get(
            "/admin/leaderboard",
            headers={"Authorization": f"Bearer {ADMIN_TOKEN}"},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["items"][0]["hunts_total"] == 5
    assert data["items"][0]["rank"] == 1
    assert data["items"][1]["hunts_total"] == 2
    assert data["items"][1]["rank"] == 2
```

- [ ] **Step 4.2 — Run to confirm it fails**

```bash
cd server
python -m pytest tests/test_payments.py::test_leaderboard_returns_ranked_list -v
```

Expected: FAIL — `404` or route not found.

- [ ] **Step 4.3 — Add leaderboard endpoint to main.py**

In `server/main.py`, add these imports at the top (after existing ones):

```python
from datetime import timedelta  # already imported — skip if present
from schemas import LeaderboardEntry, LeaderboardResponse
```

Find the block after `feedback_list` endpoint (around line 600). Add the leaderboard endpoint:

```python
# ── GET /admin/leaderboard ────────────────────────────────────────────────────

@app.get("/admin/leaderboard", response_model=LeaderboardResponse,
         dependencies=[Depends(require_admin)])
async def admin_leaderboard(
    period: str = "alltime",
    db: AsyncSession = Depends(get_db),
):
    now = datetime.now(timezone.utc)
    if period == "week":
        period_start = now - timedelta(days=7)
    elif period == "month":
        period_start = now - timedelta(days=30)
    else:
        period_start = None

    hunt_q = (
        select(
            Hunt.user_id,
            func.count(Hunt.id).label("hunts_total"),
            func.sum(
                func.cast(Hunt.hunt_type == "exchange", Integer)
            ).label("exchanges"),
            func.sum(
                func.cast(Hunt.hunt_type == "crypt", Integer)
            ).label("crypts"),
        )
        .group_by(Hunt.user_id)
        .order_by(func.count(Hunt.id).desc())
        .limit(50)
    )
    if period_start:
        hunt_q = hunt_q.where(Hunt.created_at >= period_start)

    rows = (await db.execute(hunt_q)).all()

    items = []
    for rank, row in enumerate(rows, start=1):
        user_result = await db.execute(select(User).where(User.id == row.user_id))
        user = user_result.scalar_one_or_none()
        items.append(LeaderboardEntry(
            rank=rank,
            username=user.username if user else None,
            hwid=user.hwid if user else None,
            hunts_total=row.hunts_total,
            exchanges=row.exchanges or 0,
            crypts=row.crypts or 0,
            last_seen=user.last_seen.isoformat() if user and user.last_seen else None,
        ))

    return LeaderboardResponse(items=items)
```

Also ensure `Integer` is imported from sqlalchemy — it already is via `models.py` imports but `main.py` needs it. Check top of `main.py` for `from sqlalchemy import ...` and add `Integer` if missing.

- [ ] **Step 4.4 — Run leaderboard test**

```bash
cd server
python -m pytest tests/test_payments.py::test_leaderboard_returns_ranked_list -v
```

Expected: PASS.

- [ ] **Step 4.5 — Run full suite**

```bash
cd server
python -m pytest tests/ -v
```

Expected: all PASS.

- [ ] **Step 4.6 — Commit**

```bash
git add server/main.py
git commit -m "feat: GET /admin/leaderboard?period=alltime|month|week (TOP-50)"
```

---

## Task 5 — Admin UI: Leaderboard page

**Files:**
- Modify: `server/admin/index.html`

- [ ] **Step 5.1 — Add nav item**

In `server/admin/index.html`, find the existing nav block that ends with the Feedback nav-item:

```html
    <div class="nav-item" :class="{active: page==='feedback'}" @click="page='feedback'; loadFeedback()">
      <span class="material-symbols-rounded">feedback</span> Feedback
      <span id="feedback-badge" ...></span>
    </div>
```

Add immediately after:

```html
    <div class="nav-item" :class="{active: page==='leaderboard'}" @click="page='leaderboard'; loadLeaderboard()">
      <span class="material-symbols-rounded">leaderboard</span> Leaderboard
    </div>
```

- [ ] **Step 5.2 — Add leaderboard page template**

Find the closing `</main>` tag. Add the leaderboard template before it:

```html
    <!-- LEADERBOARD -->
    <template x-if="page==='leaderboard'">
      <div>
        <div class="page-title">Leaderboard TOP-50</div>

        <div style="display:flex;gap:8px;margin-bottom:20px">
          <button class="btn btn-sm"
                  :class="lbPeriod==='alltime' ? 'btn-primary' : 'btn-ghost'"
                  @click="lbPeriod='alltime'; loadLeaderboard()">All time</button>
          <button class="btn btn-sm"
                  :class="lbPeriod==='month' ? 'btn-primary' : 'btn-ghost'"
                  @click="lbPeriod='month'; loadLeaderboard()">Month</button>
          <button class="btn btn-sm"
                  :class="lbPeriod==='week' ? 'btn-primary' : 'btn-ghost'"
                  @click="lbPeriod='week'; loadLeaderboard()">Week</button>
          <button class="btn btn-ghost btn-sm" @click="loadLeaderboard()">
            <span class="material-symbols-rounded" style="font-size:16px">refresh</span>
          </button>
        </div>

        <div class="section">
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>#</th>
                  <th>Username / HWID</th>
                  <th>Exchanges</th>
                  <th>Crypts</th>
                  <th>Total</th>
                  <th>Last seen</th>
                </tr>
              </thead>
              <tbody>
                <template x-for="row in leaderboard" :key="row.rank">
                  <tr>
                    <td style="color:var(--md-on-surface-dim);font-weight:600" x-text="row.rank"></td>
                    <td>
                      <div style="font-weight:500" x-text="row.username || '—'"></div>
                      <div style="font-size:11px;color:var(--md-on-surface-dim);font-family:monospace"
                           x-text="row.hwid || '—'"></div>
                    </td>
                    <td style="color:var(--md-primary)" x-text="row.exchanges"></td>
                    <td style="color:var(--md-secondary)" x-text="row.crypts"></td>
                    <td style="font-weight:600" x-text="row.hunts_total"></td>
                    <td style="font-size:12px;color:var(--md-on-surface-dim)"
                        x-text="row.last_seen ? formatDate(row.last_seen) : '—'"></td>
                  </tr>
                </template>
                <tr x-show="leaderboard.length === 0">
                  <td colspan="6" style="text-align:center;color:var(--md-on-surface-dim);padding:24px">
                    Нет данных
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>
```

- [ ] **Step 5.3 — Add Alpine.js data and loadLeaderboard()**

In the `adminApp()` function in the `<script>` block, find where app data is returned (the `return { ... }` object). Add to the data:

```js
leaderboard: [],
lbPeriod: 'alltime',
```

Find the `methods` section (or where functions like `loadUsers()` are defined). Add:

```js
async loadLeaderboard() {
  const data = await this.api(`/admin/leaderboard?period=${this.lbPeriod}`);
  if (data) this.leaderboard = data.items;
},
```

- [ ] **Step 5.4 — Manual test**

Open `http://34.68.86.57:8000/admin`, log in, click "Leaderboard". Verify:
- Table renders with rank/username/HWID/counts
- Period buttons switch All time / Month / Week and reload
- Refresh button works

- [ ] **Step 5.5 — Commit**

```bash
git add server/admin/index.html
git commit -m "feat: admin leaderboard page — TOP-50 with period filter"
```

---

## Task 6 — BalancePage.jsx: real payment flow

**Files:**
- Modify: `web/src/pages/BalancePage.jsx`

- [ ] **Step 6.1 — Check api.js for paymentCreate method**

Open `web/src/api.js`. If there is no `paymentCreate` method, add it alongside the existing methods:

```js
paymentCreate: (pkg) =>
  authFetch('/web/payment/create', {
    method: 'POST',
    body: JSON.stringify({ package: pkg }),
  }),
```

(`authFetch` is the existing helper that sends JWT in Authorization header — use the same pattern as `api.hunts()` etc.)

- [ ] **Step 6.2 — Replace BalancePage.jsx**

Replace the entire content of `web/src/pages/BalancePage.jsx` with:

```jsx
import { useEffect, useState } from 'react'
import { api } from '../api.js'

const PACKAGES = [
  { id: 'lite',  label: '300 credits',  price: '$1.00', bonus: null },
  { id: 'pro',   label: '2000 credits', price: '$5.00', bonus: '+500 bonus' },
  { id: 'ultra', label: '5000 credits', price: '$10.00', bonus: '+1000 bonus' },
]

export default function BalancePage() {
  const [user, setUser]       = useState(null)
  const [buying, setBuying]   = useState(null)
  const [error, setError]     = useState('')

  useEffect(() => { api.me().then(setUser) }, [])

  async function handleBuy(pkg) {
    setBuying(pkg)
    setError('')
    try {
      const data = await api.paymentCreate(pkg)
      window.location.href = data.redirect_url
    } catch (e) {
      setError(e.message || 'Payment error')
      setBuying(null)
    }
  }

  if (!user) return <div className="page-content text-muted">Loading...</div>

  return (
    <div className="page-content">
      <h2 style={{ marginBottom: 24, fontSize: 22, fontWeight: 700 }}>Balance</h2>

      <div style={{ display: 'flex', gap: 16, flexWrap: 'wrap', marginBottom: 24 }}>
        <StatCard title="Credits"          value={user.credits} />
        <StatCard title="Referral balance" value={user.ref_credits} />
      </div>

      {/* Buy Credits */}
      <div className="card" style={{ maxWidth: 520, marginBottom: 16 }}>
        <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 16 }}>Buy Credits</div>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', marginBottom: 16 }}>
          {PACKAGES.map(pkg => (
            <div key={pkg.id} className="card"
                 style={{ flex: 1, minWidth: 140, textAlign: 'center',
                          background: 'var(--elevated)', position: 'relative' }}>
              <div style={{ fontWeight: 600, marginBottom: 4 }}>{pkg.label}</div>
              {pkg.bonus && (
                <div style={{ fontSize: 11, color: 'var(--primary-dim)',
                              marginBottom: 6 }}>{pkg.bonus}</div>
              )}
              <div className="text-muted" style={{ marginBottom: 12 }}>{pkg.price}</div>
              <button
                className="btn-primary"
                style={{ width: '100%', padding: '8px 0' }}
                disabled={buying === pkg.id}
                onClick={() => handleBuy(pkg.id)}
              >
                {buying === pkg.id ? '...' : 'Buy'}
              </button>
            </div>
          ))}
        </div>
        {error && (
          <div style={{ color: 'var(--error-text)', fontSize: 13 }}>{error}</div>
        )}
        <div className="text-muted" style={{ fontSize: 12, marginTop: 8 }}>
          Secure payment via Free-Kassa. Credits appear instantly after payment.
        </div>
      </div>

      {/* Daily Bonus stub */}
      <div className="card" style={{ maxWidth: 520 }}>
        <div style={{ fontWeight: 600, fontSize: 16, marginBottom: 6 }}>Daily Bonus</div>
        <div className="text-muted" style={{ marginBottom: 16 }}>
          Watch a short ad and get 3–7 free credits. Up to 3 times per day.
        </div>
        <button className="btn-primary" disabled
                style={{ opacity: 0.5, cursor: 'not-allowed' }}>
          Watch Ad → Get Credits
        </button>
        <div className="text-muted" style={{ marginTop: 10, fontSize: 12 }}>Coming soon</div>
      </div>
    </div>
  )
}

function StatCard({ title, value }) {
  return (
    <div className="card" style={{ minWidth: 160 }}>
      <div className="text-muted" style={{ marginBottom: 8 }}>{title}</div>
      <div style={{ fontSize: 32, fontWeight: 700 }}>{value}</div>
    </div>
  )
}
```

- [ ] **Step 6.3 — Build and verify**

```bash
cd web
npm run build
```

Expected: build succeeds, no TypeScript / import errors.

- [ ] **Step 6.4 — Manual test (dev server)**

```bash
npm run dev
```

Open `http://localhost:5173/dashboard/balance`. Verify:
- Three package cards render with correct labels, bonus tags, prices
- Clicking "Buy" calls `/web/payment/create` and redirects to Free-Kassa URL
- Disabled state shows `...` during request

- [ ] **Step 6.5 — Commit**

```bash
git add web/src/pages/BalancePage.jsx web/src/api.js
git commit -m "feat: BalancePage — real credit packages with Free-Kassa redirect"
```

---

## Task 7 — Deploy + environment variables

**Files:** GCP server environment

- [ ] **Step 7.1 — Run migration on GCP**

```bash
ssh user@34.68.86.57
cd /path/to/battlebot/server
alembic upgrade head
```

Expected: `Running upgrade ... -> <hash>, add_orders` — no errors.

- [ ] **Step 7.2 — Set env vars in systemd service**

Edit the systemd unit file (e.g. `/etc/systemd/system/battlebot.service`). Add to `[Service]`:

```
Environment=FK_MERCHANT_ID=<your_merchant_id>
Environment=FK_SECRET_WORD=<your_secret_word_1>
Environment=FK_SECRET_WORD2=<your_secret_word_2>
```

Then:

```bash
sudo systemctl daemon-reload
sudo systemctl restart battlebot
sudo systemctl status battlebot
```

Expected: `Active: active (running)`.

- [ ] **Step 7.3 — Deploy Vercel frontend**

```bash
cd web
npm run build
# Push to git — Vercel auto-deploys from main branch
git add -A
git commit -m "build: BalancePage production build"
git push origin master
```

Expected: Vercel build completes, `/dashboard/balance` shows real package cards.

- [ ] **Step 7.4 — Final smoke test**

In browser, log in to web platform → Balance page → click "Buy" on lite package.  
Expected: redirect to `pay.freekassa.com` with correct merchant ID and amount.

- [ ] **Step 7.5 — Final commit**

```bash
git add .
git commit -m "feat: Phase 2B Economy complete — payments, referral cascade, leaderboard"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Credit packages ($1/$5/$10 → 300/2000/5000 credits) — Task 1 + 6
- ✅ Free-Kassa HMAC signature (outgoing + incoming) — Task 2
- ✅ Idempotent webhook — Task 3 (duplicate test)
- ✅ Referral cascade L1/L2/L3 using credits_total as base — Task 2 + 3
- ✅ Banned referrer skipped, chain continues — Task 2 + 3
- ✅ All credits + referral in one atomic transaction — `async with db.begin()` in webhook
- ✅ Leaderboard TOP-50 with alltime/month/week filter — Task 4
- ✅ Admin UI leaderboard page — Task 5
- ✅ BalancePage real cards — Task 6
- ✅ Migration for orders table — Task 1
- ✅ FK env vars — Task 7

**Placeholder scan:** No TBD, no "implement later", no vague steps — all steps have code.

**Type consistency:**
- `_apply_referral_cascade(db, buyer, credits_total)` — same signature in payments.py (Task 2) and all test calls (Task 2, 3)
- `PaymentCreateResponse.redirect_url` — matches `data.redirect_url` in BalancePage.jsx (Task 6)
- `LeaderboardEntry` fields — match what the endpoint returns (Task 4) and what the admin UI reads (Task 5)
