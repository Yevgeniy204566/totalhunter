"""
tg_channel.py — Уведомления в публичный Telegram-канал @Total_Hunter
и в приватный чат владельца (debug-бот).

Переменные окружения (GCP override.conf):
    TELEGRAM_DEBUG_TOKEN   — токен бота-постера (общий для канала и debug-чата)
    TG_CHANNEL_CHAT_ID     — @username или -100... канала (default: -1003983747219)
    TELEGRAM_DEBUG_CHAT_ID — chat_id владельца (тот же, куда падают краш-скрины)
"""
import asyncio
import logging
import os

import requests as _requests

logger = logging.getLogger(__name__)

_TOKEN   = os.getenv("TG_CHANNEL_TOKEN") or os.getenv("TELEGRAM_DEBUG_TOKEN", "")
_CHAT_ID = os.getenv("TG_CHANNEL_CHAT_ID", "-1003983747219")
_TEXT    = "🟢 ➕1️⃣"

_DEBUG_TOKEN   = os.getenv("TELEGRAM_DEBUG_TOKEN", "")
_DEBUG_CHAT_ID = os.getenv("TELEGRAM_DEBUG_CHAT_ID", "")


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


def _send_debug_sync(text: str) -> None:
    try:
        resp = _requests.post(
            f"https://api.telegram.org/bot{_DEBUG_TOKEN}/sendMessage",
            data={"chat_id": _DEBUG_CHAT_ID, "text": text},
            timeout=10,
        )
        if resp.status_code != 200:
            logger.warning("purchase alert: HTTP %s — %s", resp.status_code, resp.text[:120])
    except Exception as exc:
        logger.warning("purchase alert send failed: %s", exc)


async def send_purchase_alert(
    *, name: str, hwid: str | None, package: str, usd_amount: str,
    credits: int, ip: str | None, bot_version: str | None,
) -> None:
    """Fire-and-forget: уведомить владельца о новой покупке в debug-чате. Не бросает исключений."""
    if not _DEBUG_TOKEN or not _DEBUG_CHAT_ID:
        return
    text = (
        "💰 Новая покупка!\n"
        f"👤 {name}\n"
        f"🖥 HWID: {hwid or '—'}\n"
        f"📦 Пакет: {package} — ${usd_amount}\n"
        f"💎 Кредиты: +{credits}\n"
        f"🌐 IP: {ip or '—'}\n"
        f"🤖 Версия бота: {bot_version or '—'}"
    )
    await asyncio.to_thread(_send_debug_sync, text)
