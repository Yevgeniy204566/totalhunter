"""
web_routes.py — Web Platform API (Module 2).

All /web/* endpoints. JWT auth for protected routes.
Bot calls /web/link/generate (no JWT). Frontend calls everything else.
"""

import os
import random
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from google.oauth2 import id_token as google_id_token
from google.auth.transport import requests as google_requests
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import Hunt, HwidHistory, LinkCode, Transaction, User
from schemas import (
    BasicResponse,
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
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")

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
