"""
payments.py — NOWPayments (crypto) integration + referral cascade.

Routes: POST /web/payment/create, POST /web/payment/webhook
"""

import hashlib
import hmac
import json
import logging
import os
import uuid

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request

logger = logging.getLogger(__name__)
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Order, Transaction, User
from schemas import PaymentCreateRequest, PaymentCreateResponse
from web_routes import get_web_user
from vault import notify_balance_changed

router = APIRouter(prefix="/web", tags=["payments"])

NP_API_KEY    = os.environ.get("NOWPAYMENTS_API_KEY", "")
NP_IPN_SECRET = os.environ.get("NOWPAYMENTS_IPN_SECRET", "")
NP_API_BASE   = "https://api.nowpayments.io/v1"
NP_IPN_URL    = "https://api.total-hunter.com/web/payment/webhook"
NP_SUCCESS_URL = "https://total-hunter.com/dashboard"
NP_CANCEL_URL  = "https://total-hunter.com/dashboard"

PACKAGES: dict[str, dict] = {
    "ultra": {"usd": 10.00, "credits": 5000, "description": "Total Hunter — 5000 diamonds"},
}


async def create_nowpayments_invoice(order_id: int, amount: float, description: str) -> tuple[str, str]:
    """Call NOWPayments API. Returns (invoice_url, nowpayments_id)."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                f"{NP_API_BASE}/invoice",
                headers={"x-api-key": NP_API_KEY, "Content-Type": "application/json"},
                json={
                    "price_amount": amount,
                    "price_currency": "usd",
                    "order_id": str(order_id),
                    "order_description": description,
                    "ipn_callback_url": NP_IPN_URL,
                    "success_url": NP_SUCCESS_URL,
                    "cancel_url": NP_CANCEL_URL,
                    "is_fixed_rate": True,
                    "is_fee_paid_by_user": False,
                },
            )
    except Exception as exc:
        logger.error("[PAYMENT] NP API network error: %s", exc)
        raise HTTPException(status_code=503, detail="Payment gateway unavailable")

    if resp.status_code != 200:
        logger.error("[PAYMENT] NP API error %s: %s", resp.status_code, resp.text[:300])
        raise HTTPException(status_code=503, detail="Payment gateway unavailable")

    data = resp.json()
    invoice_url = data.get("invoice_url")
    np_id = data.get("id")
    if not invoice_url or not np_id:
        logger.error("[PAYMENT] NP API unexpected response: %s", data)
        raise HTTPException(status_code=503, detail="Payment gateway unavailable")

    return invoice_url, str(np_id)


def verify_nowpayments_sig(body_bytes: bytes, received_sig: str) -> bool:
    """HMAC-SHA512 of raw body bytes — NP sends pre-sorted compact JSON and signs as-is."""
    try:
        expected = hmac.new(
            NP_IPN_SECRET.encode(), body_bytes, hashlib.sha512
        ).hexdigest()
        return hmac.compare_digest(expected, received_sig)
    except Exception as exc:
        logger.error("[SIG] exception: %s", exc)
        return False


async def _apply_referral_cascade(
    db: AsyncSession, buyer: User, credits_total: int
) -> None:
    """Walk up to 3 referral levels. Banned referrers skipped; chain continues."""
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

    # flush() даёт нам order.id без коммита — транзакция остаётся открытой
    order = Order(
        user_id=web_user.id,
        package=req.package,
        usd_amount=str(pkg["usd"]),
        credits_total=pkg["credits"],
        idempotency_key=str(uuid.uuid4()),
        status="pending",
    )
    db.add(order)
    await db.flush()

    # NP API вне любого явного begin() — сессия уже в autobegin
    invoice_url, np_id = await create_nowpayments_invoice(
        order_id=order.id,
        amount=pkg["usd"],
        description=pkg["description"],
    )

    # Если NP API упал — HTTPException выше, flush откатится при закрытии сессии
    order.nowpayments_payment_id = np_id
    await db.commit()

    return PaymentCreateResponse(redirect_url=invoice_url)


@router.post("/payment/webhook")
async def payment_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()
    sig  = request.headers.get("x-nowpayments-sig", "")

    if not verify_nowpayments_sig(body, sig):
        raise HTTPException(status_code=400, detail="Invalid signature")

    data     = json.loads(body)
    status   = data.get("payment_status", "")
    order_id_raw = data.get("order_id", "?")

    logger.info("[PAYMENT] Received NP webhook for order %s, status: %s", order_id_raw, status)

    # Only "finished" triggers crediting; accept everything else silently
    if status != "finished":
        return JSONResponse({"status": "ok"})

    order_id = int(order_id_raw)

    async with db.begin():
        order_result = await db.execute(select(Order).where(Order.id == order_id))
        order = order_result.scalar_one_or_none()
        if not order:
            raise HTTPException(status_code=400, detail="Order not found")

        if order.status == "paid":
            return JSONResponse({"status": "ok"})

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
            meta={"nowpayments_payment_id": data.get("payment_id")},
        ))

        await _apply_referral_cascade(db, user, order.credits_total)
        order.status = "paid"
        user_hwid = user.hwid  # capture before session closes

    notify_balance_changed(user_hwid)  # wake bot's long-poll after commit
    return JSONResponse({"status": "ok"})
