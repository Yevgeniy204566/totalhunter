"""
schemas.py — Pydantic request/response models.

Определяет контракт API: что бот присылает и что сервер возвращает.
Совместимо с существующим auth.py в боте.
"""

from pydantic import BaseModel
from typing import Optional


# ── Входящие запросы ──────────────────────────────────────────────────────────

class HwidRequest(BaseModel):
    """Базовый запрос — только HWID. Используется в большинстве эндпоинтов."""
    hwid: str


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


class BasicResponse(BaseModel):
    """Простой ответ success/message для большинства операций."""
    success: bool
    message: str = ""
    credits: Optional[int] = None     # новый баланс после операции
