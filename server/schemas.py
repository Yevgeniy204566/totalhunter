"""
schemas.py — Pydantic request/response models.

Определяет контракт API: что бот присылает и что сервер возвращает.
Совместимо с существующим auth.py в боте.
"""

from pydantic import BaseModel, Field
from typing import Optional


# ── Входящие запросы ──────────────────────────────────────────────────────────

class HwidRequest(BaseModel):
    """Базовый запрос — только HWID. Используется в большинстве эндпоинтов."""
    hwid: str
    bot_version: Optional[str] = None


class UseCreditsRequest(BaseModel):
    """Списание кредитов. amount зависит от типа находки."""
    hwid: str
    amount: int = 1          # exchange=5, crypt=1; дефолт 1 для обратной совместимости
    hunt_type: str = "crypt" # exchange / crypt — пишется в таблицу hunts


class ReferralRequest(BaseModel):
    """Активация реферального кода."""
    hwid: str
    ref_code: str


class LogErrorRequest(BaseModel):
    """Телеметрия ошибок от бота."""
    hwid: str
    error: str


# ── Исходящие ответы ──────────────────────────────────────────────────────────

class CheckAuthResponse(BaseModel):
    """
    Ответ /check_auth — полная сводка по пользователю.
    Совместим с текущим auth.py бота.
    """
    authorized: bool
    credits: int
    ref_credits: int
    message: str
    email: Optional[str] = None
    username: Optional[str] = None
    ref_id: Optional[str] = None      # ref_code пользователя
    broadcast: Optional[str] = None   # последнее активное сообщение
    banned: bool = False
    force_update: bool = False
    current_version: Optional[str] = None
    referrals: Optional[dict] = None  # {"l1": int, "l2": int, "l3": int}
    is_referred: bool = False         # invited_by_id уже установлен


class BasicResponse(BaseModel):
    """Простой ответ success/message для большинства операций."""
    success: bool
    message: str = ""
    credits: Optional[int] = None     # новый баланс после операции


# ── Web Platform Schemas ──────────────────────────────────────────────────────

class GoogleAuthRequest(BaseModel):
    """Frontend sends Google ID token; backend verifies and returns JWT."""
    id_token: str
    ref_code: str | None = None


class WebAuthResponse(BaseModel):
    jwt: str
    email: str
    username: Optional[str] = None


class WebMeResponse(BaseModel):
    id: int
    email: str
    username: Optional[str] = None
    credits: int
    ref_credits: int
    ref_code: str
    hwid: Optional[str] = None
    hwid_reset_at: Optional[str] = None
    trial_used: bool
    created_at: str
    referrals: dict = {"l1": 0, "l2": 0, "l3": 0}
    invited_by_id: Optional[int] = None


class LinkGenerateRequest(BaseModel):
    """Bot calls this to create a 6-digit code for HWID linking."""
    hwid: str


class LinkGenerateResponse(BaseModel):
    code: str
    expires_in_seconds: int


class LinkVerifyRequest(BaseModel):
    """Web user submits the 6-digit code shown in the bot."""
    code: str


class HwidResetResponse(BaseModel):
    success: bool
    message: str
    next_reset_available: Optional[str] = None


class HuntEntry(BaseModel):
    hunt_type: str
    created_at: str


class HuntsResponse(BaseModel):
    today: int
    week: int
    total: int
    items: list[HuntEntry]


class TransactionEntry(BaseModel):
    type: str
    amount: int
    created_at: str


class TransactionsResponse(BaseModel):
    items: list[TransactionEntry]


class GlobalStatsResponse(BaseModel):
    exchanges_today: int
    crypts_today: int
    active_hunters: int
    total_exchanges: int
    total_crypts: int


class FeedbackRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)


# ── Payments ──────────────────────────────────────────────────────────────────

class PaymentCreateRequest(BaseModel):
    package: str   # "lite" | "pro" | "ultra"

class PaymentCreateResponse(BaseModel):
    redirect_url: str

# ── Leaderboard ───────────────────────────────────────────────────────────────

class LeaderboardEntry(BaseModel):
    rank: int
    username: Optional[str] = None
    hwid: Optional[str] = None
    hunts_total: int
    exchanges: int
    crypts: int
    last_seen: Optional[str] = None

class LeaderboardResponse(BaseModel):
    items: list[LeaderboardEntry]


class CrashReportRequest(BaseModel):
    hwid: Optional[str] = None
    version: Optional[str] = None
    os_info: Optional[str] = None
    traceback: str
