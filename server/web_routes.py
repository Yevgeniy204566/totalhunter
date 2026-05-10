"""
web_routes.py — Web Platform API (Module 2).

All /web/* endpoints. JWT auth for protected routes.
Bot calls /web/link/generate (no JWT). Frontend calls everything else.
"""

import os
import random
import string

_REF_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"
from datetime import datetime, timedelta, timezone
from typing import Optional

import urllib.parse

import httpx
import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from sqlalchemy import select, update, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import CrashReport, Feedback, Hunt, HwidHistory, LinkCode, Transaction, User
from schemas import (
    BasicResponse,
    CrashReportRequest,
    FeedbackRequest,
    GlobalStatsResponse,
    GoogleAuthRequest,
    HuntsResponse,
    HuntEntry,
    HwidResetResponse,
    LinkGenerateRequest,
    LinkGenerateResponse,
    LinkVerifyRequest,
    TransactionEntry,
    TransactionsResponse,
    WebAuthResponse,
    WebMeResponse,
)

router = APIRouter(prefix="/web", tags=["web"])

JWT_SECRET    = os.environ.get("JWT_SECRET_KEY", "change-me-before-deploy")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_DAYS = 30
GOOGLE_CLIENT_ID     = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI  = os.environ.get("GOOGLE_REDIRECT_URI", "https://api.total-hunter.com/web/auth/google/callback")
FRONTEND_URL         = os.environ.get("FRONTEND_URL", "https://total-hunter.com")

# state → ref_code; consumed on use; safe for single-process deployment
_oauth_states: dict[str, str] = {}

_bearer = HTTPBearer()


# ─────────────────────────────────────────────────────────────────────────────
# JWT helpers
# ─────────────────────────────────────────────────────────────────────────────

def create_jwt(user_id: int, email: str) -> str:
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(days=JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_jwt(token: str) -> dict:
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])


async def get_web_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = decode_jwt(credentials.credentials)
        user_id = int(payload["sub"])
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or user.is_banned:
        raise HTTPException(status_code=401, detail="User not found or banned")
    return user


def _generate_link_code() -> str:
    return "".join(random.choices(string.digits, k=6))


def _verify_google_token(token: str) -> dict:
    """Verify Google ID token. Returns claims dict with 'email', 'name', 'sub'."""
    return google_id_token.verify_oauth2_token(
        token, google_requests.Request(), GOOGLE_CLIENT_ID
    )


import secrets as _secrets


# ─────────────────────────────────────────────────────────────────────────────
# POST /web/auth/google
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/auth/google", response_model=WebAuthResponse)
async def auth_google(req: GoogleAuthRequest, db: AsyncSession = Depends(get_db)):
    try:
        claims = _verify_google_token(req.id_token)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid Google token")

    email    = claims["email"]
    username = claims.get("name")

    async with db.begin():
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            new_ref_code = "".join(_secrets.choice(_REF_ALPHABET) for _ in range(8))
            invited_by_id = None
            if req.ref_code:
                ref_row = await db.execute(
                    select(User).where(User.ref_code == req.ref_code)
                )
                referrer = ref_row.scalar_one_or_none()
                if referrer:
                    invited_by_id = referrer.id
            user = User(
                email=email,
                username=username,
                ref_code=new_ref_code,
                invited_by_id=invited_by_id,
            )
            db.add(user)
            await db.flush()

            # Бонусы НЕ начисляем здесь — только после подтверждения HWID в /link/verify
            # invited_by_id сохранён, ref_bonus_claimed=False (default)

        elif username and user.username != username:
            user.username = username

    return WebAuthResponse(
        jwt=create_jwt(user.id, email),
        email=email,
        username=user.username,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /web/auth/google/start  — мобильный OAuth redirect flow
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/auth/google/start")
async def auth_google_start(ref_code: str = ""):
    state = _secrets.token_urlsafe(16)
    _oauth_states[state] = ref_code
    params = urllib.parse.urlencode({
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": "openid email profile",
        "state": state,
        "access_type": "online",
    })
    return RedirectResponse(f"https://accounts.google.com/o/oauth2/v2/auth?{params}")


# ─────────────────────────────────────────────────────────────────────────────
# GET /web/auth/google/callback  — Google возвращает code сюда
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/auth/google/callback")
async def auth_google_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    db: AsyncSession = Depends(get_db),
):
    if error or not code or not state:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=cancelled")

    ref_code = _oauth_states.pop(state, None)
    if ref_code is None:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=invalid_state")

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )

    if resp.status_code != 200:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=token_exchange")

    id_token_str = resp.json().get("id_token", "")
    try:
        claims = _verify_google_token(id_token_str)
    except Exception:
        return RedirectResponse(f"{FRONTEND_URL}/login?error=invalid_token")

    email    = claims["email"]
    username = claims.get("name")

    async with db.begin():
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()
        if user is None:
            new_ref = "".join(_secrets.choice(_REF_ALPHABET) for _ in range(8))
            invited_by_id = None
            if ref_code:
                ref_row = await db.execute(select(User).where(User.ref_code == ref_code))
                referrer = ref_row.scalar_one_or_none()
                if referrer:
                    invited_by_id = referrer.id
            user = User(
                email=email,
                username=username,
                ref_code=new_ref,
                invited_by_id=invited_by_id,
            )
            db.add(user)
            await db.flush()
        elif username and user.username != username:
            user.username = username

    return RedirectResponse(f"{FRONTEND_URL}/login?token={create_jwt(user.id, email)}")


# ─────────────────────────────────────────────────────────────────────────────
# GET /web/me
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/me", response_model=WebMeResponse)
async def web_me(user: User = Depends(get_web_user), db: AsyncSession = Depends(get_db)):
    l1_ids = (await db.execute(
        select(User.id).where(User.invited_by_id == user.id)
    )).scalars().all()
    l1 = len(l1_ids)
    l2_ids = (await db.execute(
        select(User.id).where(User.invited_by_id.in_(l1_ids))
    )).scalars().all() if l1_ids else []
    l2 = len(l2_ids)
    l3 = (await db.execute(
        select(func.count(User.id)).where(User.invited_by_id.in_(l2_ids))
    )).scalar() or 0 if l2_ids else 0

    return WebMeResponse(
        id=user.id,
        email=user.email or "",
        username=user.username,
        credits=user.credits,
        ref_credits=user.ref_credits,
        ref_code=user.ref_code,
        hwid=user.hwid,
        hwid_reset_at=user.hwid_reset_at.isoformat() if user.hwid_reset_at else None,
        trial_used=user.trial_used,
        created_at=user.created_at.isoformat() if user.created_at else "",
        referrals={"l1": l1, "l2": l2, "l3": l3},
        invited_by_id=user.invited_by_id,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /web/stats/global  (no auth required)
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/stats/global", response_model=GlobalStatsResponse)
async def global_stats(db: AsyncSession = Depends(get_db)):
    today_start = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    rows = await db.execute(
        select(Hunt.hunt_type, func.count().label("cnt"))
        .where(Hunt.created_at >= today_start)
        .group_by(Hunt.hunt_type)
    )
    counts = {row.hunt_type: row.cnt for row in rows}

    active_row = await db.execute(
        select(func.count(func.distinct(Hunt.user_id)))
        .where(Hunt.created_at >= today_start)
    )
    active_hunters = active_row.scalar() or 0

    total_rows = await db.execute(
        select(Hunt.hunt_type, func.count().label("cnt"))
        .group_by(Hunt.hunt_type)
    )
    totals = {row.hunt_type: row.cnt for row in total_rows}

    return GlobalStatsResponse(
        exchanges_today=counts.get("exchange", 0),
        crypts_today=counts.get("crypt", 0),
        active_hunters=active_hunters,
        total_exchanges=totals.get("exchange", 0),
        total_crypts=totals.get("crypt", 0),
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /web/feedback
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/feedback", response_model=BasicResponse)
async def send_feedback(
    req: FeedbackRequest,
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    async with db.begin_nested():
        db.add(Feedback(user_id=web_user.id, text=req.text.strip()))
    await db.commit()
    return BasicResponse(success=True, message="Thank you for your feedback!")


# ─────────────────────────────────────────────────────────────────────────────
# POST /web/link/generate + /web/link/verify
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/link/generate", response_model=LinkGenerateResponse)
async def link_generate(req: LinkGenerateRequest, db: AsyncSession = Depends(get_db)):
    code = _generate_link_code()
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=10)

    async with db.begin():
        existing = await db.execute(select(LinkCode).where(LinkCode.hwid == req.hwid))
        for row in existing.scalars().all():
            await db.delete(row)
        db.add(LinkCode(hwid=req.hwid, code=code, expires_at=expires_at))

    return LinkGenerateResponse(code=code, expires_in_seconds=600)


TRIAL_CREDITS    = 100
REFERRAL_REWARD  = 50

@router.post("/link/verify", response_model=BasicResponse)
async def link_verify(
    req: LinkVerifyRequest,
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    now = datetime.now(timezone.utc)

    result = await db.execute(
        select(LinkCode).where(
            LinkCode.code == req.code,
            LinkCode.expires_at > now,
        )
    )
    link = result.scalar_one_or_none()
    if not link:
        raise HTTPException(status_code=404, detail="Code not found or expired")

    hwid = link.hwid

    # Check if this HWID has ever been used for bonuses
    history_result = await db.execute(
        select(HwidHistory).where(HwidHistory.hwid == hwid).limit(1)
    )
    hwid_is_new = history_result.scalar_one_or_none() is None

    bot_result = await db.execute(select(User).where(User.hwid == hwid))
    bot_user = bot_result.scalar_one_or_none()

    async with db.begin_nested():
        await db.delete(link)

        # Capture before merge: if web_user already had inviter (set via web signup bonus)
        # → referrer was already paid +100, skip the +50 HWID reward to avoid double-pay
        had_inviter_before_merge = web_user.invited_by_id is not None

        skip_ref_welcome = False
        if bot_user and bot_user.id != web_user.id:
            web_user.credits     += bot_user.credits
            web_user.ref_credits += bot_user.ref_credits
            if bot_user.trial_used:
                web_user.trial_used = True
            # Transfer referral chain — referrer already paid via /activate_referral
            if bot_user.invited_by_id and not web_user.invited_by_id:
                web_user.invited_by_id = bot_user.invited_by_id
                skip_ref_welcome = True
            await db.execute(update(Hunt).where(Hunt.user_id == bot_user.id).values(user_id=web_user.id))
            await db.execute(update(Transaction).where(Transaction.user_id == bot_user.id).values(user_id=web_user.id))
            await db.delete(bot_user)
            await db.flush()  # DELETE bot_user до UPDATE web_user.hwid — иначе unique constraint падает

        web_user.hwid = hwid
        db.add(HwidHistory(hwid=hwid, user_id=web_user.id))

        if hwid_is_new and not web_user.trial_used:
            # First time this hardware links — grant trial bonus
            web_user.credits    += TRIAL_CREDITS
            web_user.trial_used  = True
            db.add(Transaction(
                user_id=web_user.id,
                type="trial",
                amount=TRIAL_CREDITS,
                meta={"hwid": hwid, "reason": "first_hwid_link"},
            ))

            # Pay ref bonus only if HWID is new and bonus not yet claimed
            if web_user.invited_by_id and not web_user.ref_bonus_claimed and not skip_ref_welcome:
                referrer_result = await db.execute(
                    select(User).where(User.id == web_user.invited_by_id)
                )
                referrer = referrer_result.scalar_one_or_none()
                if referrer and not referrer.is_banned:
                    web_user.ref_credits += 50
                    db.add(Transaction(
                        user_id=web_user.id, type="ref_welcome", amount=50,
                        meta={"role": "invited", "hwid": hwid},
                    ))
                    referrer.ref_credits += 100
                    db.add(Transaction(
                        user_id=referrer.id, type="ref_welcome", amount=100,
                        meta={"role": "inviter", "ref_from_user_id": web_user.id, "hwid": hwid},
                    ))
            web_user.ref_bonus_claimed = True
        elif not hwid_is_new:
            # Duplicate HWID — link without bonuses, log the attempt
            db.add(Transaction(
                user_id=web_user.id,
                type="hwid_duplicate_blocked",
                amount=0,
                meta={"hwid": hwid, "reason": "duplicate_hwid_bonus_blocked"},
            ))

    await db.commit()
    return BasicResponse(success=True, message="HWID linked successfully")


# ─────────────────────────────────────────────────────────────────────────────
# POST /web/hwid/reset
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/hwid/reset", response_model=HwidResetResponse)
async def hwid_reset(
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    if not web_user.hwid:
        raise HTTPException(status_code=400, detail="No HWID linked to this account")

    now = datetime.now(timezone.utc)
    if web_user.hwid_reset_at:
        next_allowed = web_user.hwid_reset_at + timedelta(days=7)
        if now < next_allowed:
            raise HTTPException(
                status_code=429,
                detail={
                    "message": "HWID reset available once per 7 days",
                    "next_reset_available": next_allowed.isoformat(),
                },
            )

    async with db.begin_nested():
        web_user.hwid          = None
        web_user.hwid_reset_at = now

    await db.commit()
    return HwidResetResponse(success=True, message="HWID unlinked. Link new device with a code from the bot.")


# ─────────────────────────────────────────────────────────────────────────────
# GET /web/hunts
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/hunts", response_model=HuntsResponse)
async def web_hunts(
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start  = now - timedelta(days=7)

    today = (await db.execute(
        select(func.count(Hunt.id)).where(Hunt.user_id == web_user.id, Hunt.created_at >= today_start)
    )).scalar()
    week = (await db.execute(
        select(func.count(Hunt.id)).where(Hunt.user_id == web_user.id, Hunt.created_at >= week_start)
    )).scalar()
    total = (await db.execute(
        select(func.count(Hunt.id)).where(Hunt.user_id == web_user.id)
    )).scalar()

    rows = (await db.execute(
        select(Hunt).where(Hunt.user_id == web_user.id).order_by(Hunt.created_at.desc()).limit(100)
    )).scalars().all()

    return HuntsResponse(
        today=today, week=week, total=total,
        items=[HuntEntry(hunt_type=h.hunt_type, created_at=h.created_at.isoformat()) for h in rows],
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET /web/transactions
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/transactions", response_model=TransactionsResponse)
async def web_transactions(
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    rows = (await db.execute(
        select(Transaction)
        .where(Transaction.user_id == web_user.id)
        .order_by(Transaction.created_at.desc())
        .limit(100)
    )).scalars().all()
    return TransactionsResponse(
        items=[TransactionEntry(type=t.type, amount=t.amount, created_at=t.created_at.isoformat()) for t in rows]
    )


# ─────────────────────────────────────────────────────────────────────────────
# POST /web/referral/transfer
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/referral/transfer", response_model=BasicResponse)
async def web_referral_transfer(
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    if web_user.ref_credits <= 0:
        return BasicResponse(success=False, message="Referral balance is empty", credits=web_user.credits)
    amount = web_user.ref_credits
    async with db.begin_nested():
        web_user.credits    += amount
        web_user.ref_credits = 0
        db.add(Transaction(user_id=web_user.id, type="ref_transfer", amount=amount, meta={"from": "ref_credits"}))
    await db.commit()
    return BasicResponse(success=True, message=f"Transferred {amount} credits", credits=web_user.credits)


# POST /web/referral/activate
# ─────────────────────────────────────────────────────────────────────────────

@router.post("/referral/activate", response_model=BasicResponse)
async def web_referral_activate(
    ref_code: str,
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    """Активация кода пригласителя из личного кабинета на сайте."""
    if web_user.invited_by_id is not None:
        return BasicResponse(success=False, message="Referral code already activated.")

    async with db.begin():
        ref_result = await db.execute(select(User).where(User.ref_code == ref_code.upper()))
        inviter = ref_result.scalar_one_or_none()

        if not inviter:
            return BasicResponse(success=False, message="Code not found.")
        if inviter.id == web_user.id:
            return BasicResponse(success=False, message="Cannot use your own code.")

        web_user.invited_by_id = inviter.id

        # Pay bonus immediately only if HWID already verified (user linked bot before entering code)
        # Otherwise bonus will be paid at /link/verify when bot is linked
        if web_user.hwid and not web_user.ref_bonus_claimed:
            web_user.ref_credits += 50
            db.add(Transaction(user_id=web_user.id, type="ref_welcome", amount=50,
                               meta={"role": "invited", "via": "web_profile", "related_user_id": inviter.id}))
            if not inviter.is_banned:
                inviter.ref_credits += 100
                db.add(Transaction(user_id=inviter.id, type="ref_welcome", amount=100,
                                   meta={"role": "inviter", "related_user_id": web_user.id}))
            web_user.ref_bonus_claimed = True
            msg = "Code activated! +50 added to referral balance."
        else:
            msg = "Code saved! Bonus will be credited after your first device link."

    return BasicResponse(success=True, message=msg)


# ── POST /web/crash_report ────────────────────────────────────────────────────

@router.post("/crash_report")
async def crash_report(payload: CrashReportRequest, db: AsyncSession = Depends(get_db)):
    """Принимает отчёт о падении бота. Публичный, без JWT. Rate limit: 3/HWID/час."""
    async with db.begin():
        if payload.hwid:
            since = datetime.now(timezone.utc) - timedelta(hours=1)
            result = await db.execute(
                select(CrashReport.id).where(
                    CrashReport.hwid == payload.hwid,
                    CrashReport.created_at >= since,
                ).limit(3)
            )
            if len(result.scalars().all()) >= 3:
                raise HTTPException(status_code=429, detail="Rate limit: max 3 crash reports per hour")

        db.add(CrashReport(
            hwid=payload.hwid,
            version=payload.version,
            os_info=payload.os_info,
            traceback=(payload.traceback or "")[:8000],
        ))
    return {"ok": True}
