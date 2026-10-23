"""Необработанные исключения сервера → закрытый Telegram debug-канал (владелец 2026-10-23: ошибка привязки бота
неделями жила только в journalctl, админка о ней не знала). Секреты вычищаются, повторы гасятся."""
import asyncio
import logging
import re
import time
import traceback
from datetime import datetime, timezone

from tg_channel import _send_debug_sync

logger = logging.getLogger(__name__)

COOLDOWN_SEC = 600
_last_sent: dict[str, float] = {}
_suppressed: dict[str, int] = {}

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
_BEARER = re.compile(r"(?i)bearer\s+[\w.~+/=-]+")
_LONG_TOKEN = re.compile(r"\b[A-Za-z0-9_\-+/=]{32,}\b")
_SECRET_KV = re.compile(r"(?i)\b(password|passwd|token|secret|api[_-]?key|authorization|access_token|id_token)\b(\s*[=:]\s*)\S+")


def scrub(text: str) -> str:
    text = _BEARER.sub("Bearer ***", text)
    text = _SECRET_KV.sub(r"\1\2***", text)
    text = _EMAIL.sub("***@***", text)
    return _LONG_TOKEN.sub("***", text)


def _key(method: str, path: str, exc: BaseException) -> str:
    tb = traceback.extract_tb(exc.__traceback__)
    last = f"{tb[-1].filename}:{tb[-1].lineno}" if tb else ""
    return f"{method} {path} {type(exc).__name__} {last}"


def should_send(key: str, now: float | None = None) -> bool:
    """Одинаковая ошибка (маршрут + тип + место) — не чаще раза в COOLDOWN_SEC; остальные считаются."""
    now = time.monotonic() if now is None else now
    prev = _last_sent.get(key)
    if prev is not None and now - prev < COOLDOWN_SEC:
        _suppressed[key] = _suppressed.get(key, 0) + 1
        return False
    _last_sent[key] = now
    return True


def build_text(method: str, path: str, exc: BaseException, repeats: int = 0) -> str:
    tb = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
    tb = scrub(tb)[-1800:]  # путь без query-строки: в ней бывают коды/токены
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    head = f"🔥 Ошибка сервера 500\n🕐 {stamp}\n🔗 {method} {path}\n"
    if repeats:
        head += f"🔁 ещё {repeats} раз с прошлого уведомления\n"
    return head + tb


async def notify_server_error(method: str, path: str, exc: BaseException) -> None:
    """Не бросает исключений: сбой уведомления не должен ломать ответ клиенту."""
    try:
        key = _key(method, path, exc)
        if not should_send(key):
            return
        repeats = _suppressed.pop(key, 0)
        await asyncio.to_thread(_send_debug_sync, build_text(method, path, exc, repeats))
    except Exception as err:  # noqa: BLE001
        logger.warning("error alert failed: %s", err)
