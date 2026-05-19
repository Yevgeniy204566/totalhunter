"""
debug_router.py — Принимает debug-скрины от ботов и пересылает в Telegram.
Файлы НЕ сохраняются на диск.
"""
import os
from datetime import datetime, timezone, timedelta

import requests as _requests
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

router = APIRouter(prefix="/api/debug", tags=["debug"])

_KYIV = timezone(timedelta(hours=3))

_TG_TOKEN   = os.getenv("TELEGRAM_DEBUG_TOKEN", "")
_TG_CHAT_ID = os.getenv("TELEGRAM_DEBUG_CHAT_ID", "")


@router.post("/upload-shot")
async def upload_shot(
    file:      UploadFile = File(...),
    hwid:      str        = Form(...),
    shot_type: str        = Form(...),   # "FIND" | "DIALOG"
):
    if not _TG_TOKEN or not _TG_CHAT_ID:
        # Telegram не настроен — молча принимаем и игнорируем
        return {"ok": True, "forwarded": False}

    img_bytes = await file.read()
    if not img_bytes:
        raise HTTPException(status_code=400, detail="empty file")

    now_kyiv = datetime.now(_KYIV).strftime("%d.%m.%Y %H:%M:%S")
    caption  = f"🔍 HWID: {hwid}\nТип: {shot_type}\nВремя: {now_kyiv} (Киев)"

    try:
        resp = _requests.post(
            f"https://api.telegram.org/bot{_TG_TOKEN}/sendPhoto",
            data={"chat_id": _TG_CHAT_ID, "caption": caption},
            files={"photo": ("shot.jpg", img_bytes, "image/jpeg")},
            timeout=15,
        )
        ok = resp.status_code == 200
    except Exception:
        ok = False

    return {"ok": True, "forwarded": ok}
