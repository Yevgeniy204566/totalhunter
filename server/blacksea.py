"""
blacksea.py — BlackSea (blacksea.in.ua) fiat payments.

Route: POST /web/payment/blacksea/webhook

В отличие от NOWPayments у вебхука BlackSea НЕТ подписи (подтверждено двумя
живыми тестами). Единственная граница безопасности — серверная проверка
sale_id через BlackSea API, а не тело запроса.
"""

import logging
import os

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import BlackSeaSale

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/web/payment/blacksea", tags=["blacksea"])

BLACKSEA_API_BASE = "https://blacksea.in.ua"
HTTP_TIMEOUT      = 15

KEY_ACCESS_TOKEN  = "blacksea_access_token"
KEY_REFRESH_TOKEN = "blacksea_refresh_token"

MAX_SALE_ID_LEN = 50   # == длина колонки BlackSeaSale.sale_id

CLIENT_ID     = os.environ.get("BLACKSEA_CLIENT_ID", "")
CLIENT_SECRET = os.environ.get("BLACKSEA_CLIENT_SECRET", "")
PRODUCT_ID    = os.environ.get("BLACKSEA_PRODUCT_ID", "")

for _name, _value in (
    ("BLACKSEA_CLIENT_ID",     CLIENT_ID),
    ("BLACKSEA_CLIENT_SECRET", CLIENT_SECRET),
    ("BLACKSEA_PRODUCT_ID",    PRODUCT_ID),
):
    if not _value:
        raise ValueError(
            f"{_name} is not set in environment variables — server refuses to start without it"
        )


class BlackSeaApiError(Exception):
    """Продажу не удалось верифицировать: сеть, не-200 от API или неудачный
    обмен токена. Никогда не означает «не оплачено» — fail-closed, без начисления."""


def _form_str(form, key: str) -> str:
    """Значения form-данных в Starlette — str; всё остальное (например файл в
    multipart) считаем отсутствующим, а не приводим к строке."""
    value = form.get(key)
    return value if isinstance(value, str) else ""


@router.post("/webhook")
async def blacksea_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    form = await request.form()

    sale_id    = _form_str(form, "sale_id")
    email      = _form_str(form, "email")
    price_raw  = _form_str(form, "price")
    product_id = _form_str(form, "product_id")

    if not sale_id or not email or not price_raw or not product_id:
        raise HTTPException(status_code=400, detail="Malformed webhook body")
    if len(sale_id) > MAX_SALE_ID_LEN:
        raise HTTPException(status_code=400, detail="Malformed webhook body")
    try:
        price_kopecks = int(price_raw)
    except ValueError:
        raise HTTPException(status_code=400, detail="Malformed webhook body")

    logger.info("[BLACKSEA] webhook sale=%s price_kopecks=%s", sale_id, price_kopecks)
    return JSONResponse({"status": "ok"})
