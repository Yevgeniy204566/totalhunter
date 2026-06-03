"""
tg_channel.py — Уведомления в публичный Telegram-канал @Total_Hunter.

Переменные окружения (GCP override.conf):
    TELEGRAM_DEBUG_TOKEN — токен бота-постера
    TG_CHANNEL_CHAT_ID   — @username или -100... канала (default: -1003983747219)
"""
import asyncio
import logging
import os

import requests as _requests

logger = logging.getLogger(__name__)

_TOKEN   = os.getenv("TG_CHANNEL_TOKEN") or os.getenv("TELEGRAM_DEBUG_TOKEN", "")
_CHAT_ID = os.getenv("TG_CHANNEL_CHAT_ID", "-1003983747219")
_TEXT    = "🟢 ➕1️⃣"


def _send_sync() -> None:
    try:
        resp = _requests.post(
            f"https://api.telegram.org/bot{_TOKEN}/sendMessage",
            data={"chat_id": _CHAT_ID, "text": _TEXT},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("tg_channel: HTTP %s — %s", resp.status_code, resp.text[:120])
    except Exception as exc:
        logger.warning("tg_channel send failed: %s", exc)


async def send_telegram_alert(percent: int) -> None:
    """Fire-and-forget: отправить уведомление в канал. Не бросает исключений."""
    if not _TOKEN:
        return
    await asyncio.to_thread(_send_sync)
