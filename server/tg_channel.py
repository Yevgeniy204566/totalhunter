"""
tg_channel.py — Тизер-уведомления в публичный Telegram-канал @Total_Hunter.

Переменные окружения (GCP override.conf):
    TG_CHANNEL_TOKEN   — токен бота-постера (default: TELEGRAM_DEBUG_TOKEN)
    TG_CHANNEL_CHAT_ID — @username или -100... канала (default: @Total_Hunter)
    TG_CHANNEL_IMAGE   — путь к картинке (default: <server_dir>/tg_teaser.jpg)

Fallback: если картинки нет — шлёт только текст с эмодзи.
"""
import asyncio
import logging
import os

import requests as _requests

logger = logging.getLogger(__name__)

_TOKEN = os.getenv("TG_CHANNEL_TOKEN") or os.getenv("TELEGRAM_DEBUG_TOKEN", "")
_CHAT_ID = os.getenv("TG_CHANNEL_CHAT_ID", "@Total_Hunter")
_IMG_PATH = os.getenv(
    "TG_CHANNEL_IMAGE",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "tg_teaser.jpg"),
)


def _send_sync(percent: int) -> None:
    caption = f"🔥 🆕\n🏛️ ➕ 🐝\n📊 {percent}%"
    try:
        if os.path.exists(_IMG_PATH):
            with open(_IMG_PATH, "rb") as f:
                resp = _requests.post(
                    f"https://api.telegram.org/bot{_TOKEN}/sendPhoto",
                    data={"chat_id": _CHAT_ID, "caption": caption},
                    files={"photo": ("teaser.jpg", f, "image/jpeg")},
                    timeout=15,
                )
        else:
            resp = _requests.post(
                f"https://api.telegram.org/bot{_TOKEN}/sendMessage",
                data={"chat_id": _CHAT_ID, "text": caption},
                timeout=10,
            )
        if resp.status_code != 200:
            logger.warning("tg_channel: HTTP %s — %s", resp.status_code, resp.text[:120])
    except Exception as exc:
        logger.warning("tg_channel send failed: %s", exc)


async def send_telegram_alert(percent: int) -> None:
    """Fire-and-forget: отправить тизер в канал. Не бросает исключений."""
    if not _TOKEN:
        return
    await asyncio.to_thread(_send_sync, percent)
