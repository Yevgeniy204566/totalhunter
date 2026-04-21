"""Tests for payments.py — referral cascade logic."""
import pytest
import hashlib
import uuid
import os
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select

import sys
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


# ── Webhook constants + helper ────────────────────────────────────────────────

FK_TEST_MERCHANT  = "12345"
FK_TEST_SECRET    = "secret1"
FK_TEST_SECRET2   = "secret2"


def _make_sign(amount: str, order_id: str) -> str:
    data = f"{FK_TEST_MERCHANT}:{amount}:{FK_TEST_SECRET2}:{order_id}"
    return hashlib.md5(data.encode()).hexdigest()


@pytest.fixture(autouse=False)
def fk_env(monkeypatch):
    monkeypatch.setenv("FK_MERCHANT_ID",  FK_TEST_MERCHANT)
    monkeypatch.setenv("FK_SECRET_WORD",  FK_TEST_SECRET)
    monkeypatch.setenv("FK_SECRET_WORD2", FK_TEST_SECRET2)
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
    """Second webhook with same order_id does NOT double-credit."""
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
