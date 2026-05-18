"""
earn.py — Rewarded ads: watch ad → random diamond reward (max 5/day per user).

GET  /web/earn/status  — today's count
POST /web/earn/reward  — credit random diamonds after watching

Reward table (backend-only, anti-fraud):
  90% → 5 diamonds
   5% → 10 diamonds
   3% → 20 diamonds
   1% → 30 diamonds
   1% → 50 diamonds (jackpot)
"""

import random
from datetime import datetime, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Transaction, User
from web_routes import get_web_user
from vault import notify_balance_changed

router = APIRouter(prefix="/web/earn", tags=["earn"])

MAX_VIEWS_PER_DAY = 5
_NO_LIMIT_EMAILS = {"ievgeniy2011@gmail.com"}  # dev/owner accounts

_REWARDS = [5,  7, 15, 30, 50]
_WEIGHTS = [78, 12,  6,  3,  1]

# 20-sector wheel layout (indexes 0-19, each = 18°)
SECTORS = [5, 7, 5, 15, 5, 30, 5, 7, 5, 15, 5, 7, 5, 15, 5, 50, 5, 7, 5, 30]


def calculate_ad_reward() -> int:
    return random.choices(_REWARDS, weights=_WEIGHTS, k=1)[0]


def pick_sector(earned: int) -> int:
    candidates = [i for i, v in enumerate(SECTORS) if v == earned]
    return random.choice(candidates)


def sector_to_angle(sector_index: int) -> int:
    return sector_index * 18 + 9


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
    no_limit = web_user.email in _NO_LIMIT_EMAILS
    today = await _today_count(db, web_user.id)
    remaining = MAX_VIEWS_PER_DAY if no_limit else max(0, MAX_VIEWS_PER_DAY - today)
    return {"today": today, "max": MAX_VIEWS_PER_DAY, "remaining": remaining}


@router.post("/reward")
async def earn_reward(
    db: AsyncSession = Depends(get_db),
    web_user: User = Depends(get_web_user),
):
    no_limit = web_user.email in _NO_LIMIT_EMAILS
    today = await _today_count(db, web_user.id)
    if not no_limit and today >= MAX_VIEWS_PER_DAY:
        return {"success": False, "message": "Daily limit reached", "credits": web_user.credits}

    earned = calculate_ad_reward()
    sector_idx = pick_sector(earned)
    web_user.credits += earned
    db.add(Transaction(
        user_id=web_user.id,
        type="ad_reward",
        amount=earned,
        meta={"source": "rewarded_ad", "jackpot": earned >= 50},
    ))
    await db.commit()

    notify_balance_changed(web_user.hwid)
    return {
        "success": True,
        "credits": web_user.credits,
        "earned": earned,
        "jackpot": earned >= 50,
        "sector_index": sector_idx,
        "angle": sector_to_angle(sector_idx),
    }
