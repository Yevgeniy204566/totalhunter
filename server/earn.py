"""
earn.py — Rewarded ads: watch ad → +5 diamonds (max 5/day per user).

GET  /web/earn/status  — today's count
POST /web/earn/reward  — credit 5 diamonds after watching
"""

from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Transaction, User
from web_routes import get_web_user
from vault import notify_balance_changed

router = APIRouter(prefix="/web/earn", tags=["earn"])

REWARD_PER_VIEW  = 5
MAX_VIEWS_PER_DAY = 5


async def _today_count(db: AsyncSession, user_id: int) -> int:
    now = datetime.now(timezone.utc)
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    result = await db.execute(
        select(func.count(Transaction.id)).where(
            Transaction.user_id == user_id,
            Transaction.type == "ad_reward",
            Transaction.created_at >= day_start,
        )
    )
    return result.scalar() or 0


@router.get("/status")
async def earn_status(
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    today = await _today_count(db, web_user.id)
    return {"today": today, "max": MAX_VIEWS_PER_DAY, "remaining": max(0, MAX_VIEWS_PER_DAY - today)}


@router.post("/reward")
async def earn_reward(
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    today = await _today_count(db, web_user.id)
    if today >= MAX_VIEWS_PER_DAY:
        return {"success": False, "message": "Daily limit reached", "credits": web_user.credits}

    web_user.credits += REWARD_PER_VIEW
    db.add(Transaction(
        user_id=web_user.id,
        type="ad_reward",
        amount=REWARD_PER_VIEW,
        meta={"source": "rewarded_ad"},
    ))
    await db.commit()

    notify_balance_changed(web_user.hwid)
    return {"success": True, "credits": web_user.credits, "earned": REWARD_PER_VIEW}
