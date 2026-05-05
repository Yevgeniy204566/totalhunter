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
FK_SECRET_WORD  = os.environ.get("FK_SECRET_WORD", "")
FK_SECRET_WORD2 = os.environ.get("FK_SECRET_WORD2", "")

PACKAGES: dict[str, dict] = {
    "lite":  {"usd": "1.00",  "credits": 300},
    "pro":   {"usd": "5.00",  "credits": 2000},
    "ultra": {"usd": "10.00", "credits": 5000},
}


def build_fk_url(order_id: str, amount: str) -> str:
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
    sign_str = f"{FK_MERCHANT_ID}:{amount}:{FK_SECRET_WORD2}:{order_id}"
    expected = hashlib.md5(sign_str.encode()).hexdigest()
    return expected == received_sign


async def _apply_referral_cascade(
    db: AsyncSession, buyer: User, credits_total: int
) -> None:
    """
    Walk up to 3 levels of invited_by_id chain.
    Base = credits_total (includes bonus). Banned referrers skipped; chain continues.
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
                        "related_user_id": buyer.id,
                        "ref_from_user_id": buyer.id,
                        "credits_total": credits_total,
                    },
                ))

        current_id = referrer.invited_by_id


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
        order_id_str = str(order.id)  # capture before commit expires the object

    redirect_url = build_fk_url(order_id=order_id_str, amount=pkg["usd"])
    return PaymentCreateResponse(redirect_url=redirect_url)


@router.post("/payment/webhook")
async def payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()
    amount            = str(form.get("AMOUNT", ""))
    merchant_order_id = str(form.get("MERCHANT_ORDER_ID", ""))
    sign              = str(form.get("SIGN", ""))

    if not verify_fk_webhook_signature(amount, merchant_order_id, sign):
        raise HTTPException(status_code=400, detail="Invalid signature")

    async with db.begin():
        order_result = await db.execute(
            select(Order).where(Order.freekassa_order_id == merchant_order_id)
        )
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=400, detail="Order not found")

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
