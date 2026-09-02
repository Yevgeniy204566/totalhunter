"""
blacksea.py — BlackSea (blacksea.in.ua) fiat payments.

Route: POST /web/payment/blacksea/webhook

В отличие от NOWPayments у вебхука BlackSea НЕТ подписи (подтверждено двумя
живыми тестами). Единственная граница безопасности — серверная проверка
sale_id через BlackSea API, а не тело запроса.
"""

import httpx
import logging
import os
import urllib.parse

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AppSetting, BlackSeaSale

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


def _client() -> httpx.AsyncClient:
    """Единственное место сборки HTTP-клиента — тесты подменяют его целиком."""
    return httpx.AsyncClient(timeout=HTTP_TIMEOUT)


async def fetch_blacksea_sale(sale_id: str, access_token: str) -> tuple[int, dict]:
    """GET /api/v2/sales/{sale_id} → (HTTP-код, тело-словарь).

    Тело, которое не разбирается как JSON-объект, отдаётся пустым словарём —
    решение «верить или нет» принимает sale_matches_webhook, здесь только
    транспорт. Сетевые ошибки НЕ глотаются: httpx.HTTPError уходит наверх.
    """
    quoted = urllib.parse.quote(sale_id, safe="")
    async with _client() as client:
        resp = await client.get(
            f"{BLACKSEA_API_BASE}/api/v2/sales/{quoted}",
            params={"access_token": access_token},
        )
    try:
        body = resp.json()
    except ValueError:
        return resp.status_code, {}
    return resp.status_code, body if isinstance(body, dict) else {}


async def refresh_blacksea_token(refresh_token: str) -> tuple[str, str]:
    """POST /oauth/token (grant_type=refresh_token) → (access_token, refresh_token).

    BlackSea ротирует refresh_token при обмене, поэтому возвращаются оба
    значения — записывать в app_settings обязательно оба или ни одного.
    """
    async with _client() as client:
        resp = await client.post(
            f"{BLACKSEA_API_BASE}/oauth/token",
            data={
                "client_id":     CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type":    "refresh_token",
            },
        )
    if resp.status_code != 200:
        raise BlackSeaApiError(f"token refresh failed with HTTP {resp.status_code}")
    try:
        body = resp.json()
    except ValueError:
        raise BlackSeaApiError("token refresh returned a non-JSON body")

    new_access  = body.get("access_token")
    new_refresh = body.get("refresh_token")
    if not isinstance(new_access, str) or not new_access \
            or not isinstance(new_refresh, str) or not new_refresh:
        raise BlackSeaApiError("token refresh response has no usable token pair")
    return new_access, new_refresh


async def _read_setting(db: AsyncSession, key: str) -> str | None:
    row = (await db.execute(
        select(AppSetting).where(AppSetting.key == key)
    )).scalar_one_or_none()
    return row.value if row is not None else None


def sale_matches_webhook(sale: dict, *, sale_id: str, email: str,
                         price_kopecks: int, product_id: str) -> str | None:
    """None — продажа верифицирована и совпадает с телом вебхука; иначе причина.

    Тело вебхука BlackSea не подписано, поэтому источник истины — ответ API, а
    тело только сверяется с ним. Fail-closed: любое отсутствующее поле или поле
    не того типа — отказ, а не попытка угадать смысл нестандартного ответа.
    """
    paid        = sale.get("paid")
    chargedback = sale.get("chargedback")
    refunded    = sale.get("refunded")
    if not isinstance(paid, bool) or not isinstance(chargedback, bool) \
            or not isinstance(refunded, bool):
        return "malformed_status_fields"

    api_email = sale.get("email")
    if not isinstance(api_email, str) or not api_email:
        return "malformed_email"

    api_price = sale.get("price")
    # bool — подкласс int: price=true не должен пролезть как число
    if not isinstance(api_price, int) or isinstance(api_price, bool):
        return "malformed_price"

    api_product = sale.get("product_id")
    if not isinstance(api_product, str) or not api_product:
        return "malformed_product_id"

    api_id = sale.get("id")
    if api_id is not None and api_id != sale_id:
        return "sale_id_mismatch"

    if paid is not True:
        return "not_paid"
    if chargedback:
        return "chargedback"
    if refunded:
        return "refunded"

    if api_email != email:
        return "email_mismatch"
    if api_price != price_kopecks:
        return "price_mismatch"
    if api_product != product_id:
        return "product_id_mismatch"
    return None


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
