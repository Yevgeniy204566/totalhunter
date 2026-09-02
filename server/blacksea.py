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

from decimal import Decimal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import AppSetting, BlackSeaSale, Transaction, User
from payments import PACKAGES, _apply_referral_cascade
from tg_channel import send_manual_review_alert, send_purchase_alert
from vault import notify_balance_changed

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


async def _verify_sale(db: AsyncSession, sale_id: str) -> dict:
    """Запись продажи из BlackSea API либо BlackSeaApiError.

    Единственная реальная защита от поддельного POST: у вебхука BlackSea нет
    подписи, поэтому «в теле пришёл sale_id» само по себе не доказывает ничего.
    """
    access_token = await _read_setting(db, KEY_ACCESS_TOKEN)
    if not access_token:
        raise BlackSeaApiError(f"app_settings['{KEY_ACCESS_TOKEN}'] is missing")

    status, body = await fetch_blacksea_sale(sale_id, access_token)

    if status != 200:
        raise BlackSeaApiError(f"sales API returned HTTP {status}")
    sale = body.get("sale")
    if not isinstance(sale, dict):
        raise BlackSeaApiError("sales API response has no sale object")
    return sale


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

    quantity_raw = form.get("quantity")
    if quantity_raw is None:
        logger.warning("[BLACKSEA] sale %s came without quantity — treating as '1'", sale_id)
        quantity = "1"
    else:
        quantity = quantity_raw if isinstance(quantity_raw, str) else ""

    existing = (await db.execute(
        select(BlackSeaSale.id).where(BlackSeaSale.sale_id == sale_id)
    )).scalar_one_or_none()
    if existing is not None:
        logger.info("[BLACKSEA] sale %s already credited — no-op", sale_id)
        return JSONResponse({"status": "ok"})

    if product_id != PRODUCT_ID:
        logger.info("[BLACKSEA] webhook for foreign product %s — ignored", product_id)
        return JSONResponse({"status": "ok"})

    try:
        sale = await _verify_sale(db, sale_id)
    except (BlackSeaApiError, httpx.HTTPError) as exc:
        logger.error("[BLACKSEA] verification failed for sale %s: %s", sale_id, exc)
        return JSONResponse({"status": "ok"})

    reason = sale_matches_webhook(
        sale, sale_id=sale_id, email=email,
        price_kopecks=price_kopecks, product_id=product_id,
    )
    if reason is not None:
        logger.error("[BLACKSEA] sale %s rejected (%s) — webhook body does not match "
                     "the verified sale, possible forgery", sale_id, reason)
        return JSONResponse({"status": "ok"})

    uah_amount = Decimal(price_kopecks) / 100

    if quantity != "1":
        logger.warning("[BLACKSEA] sale %s has quantity=%r — manual review", sale_id, quantity)
        background_tasks.add_task(
            send_manual_review_alert, reason=f"quantity={quantity}",
            sale_id=sale_id, email=sale["email"], uah_amount=str(uah_amount),
        )
        return JSONResponse({"status": "ok"})

    # email берётся из ВЕРИФИЦИРОВАННОГО ответа API, не из тела вебхука.
    # with_for_update() держит строку покупателя до commit: user.credits += ...
    # это read-modify-write, две одновременные продажи одного покупателя без
    # лока могли бы прочитать один стартовый баланс и потерять одно начисление.
    user = (await db.execute(
        select(User).where(User.email == sale["email"]).with_for_update()
    )).scalar_one_or_none()
    if user is None:
        logger.warning("[BLACKSEA] no user with email %s for sale %s — manual review",
                       sale["email"], sale_id)
        background_tasks.add_task(
            send_manual_review_alert, reason="email_not_found",
            sale_id=sale_id, email=sale["email"], uah_amount=str(uah_amount),
        )
        return JSONResponse({"status": "ok"})

    credits = PACKAGES["ultra"]["credits"]

    # Атомарная точка идемпотентности. db.begin() здесь НЕЛЬЗЯ: SELECT'ы выше уже
    # открыли транзакцию через autobegin (ANTI-PATTERNS.md:842-847). Savepoint
    # откатывается сам, внешняя транзакция остаётся валидной, поэтому except —
    # СНАРУЖИ блока (паттерн roy.py:264-287): после неудачного flush внутри блока
    # обычный commit() рвался бы PendingRollbackError.
    try:
        async with db.begin_nested():
            db.add(BlackSeaSale(
                sale_id=sale_id, user_id=user.id, credits_total=credits,
                uah_amount=uah_amount,
            ))
            await db.flush()
    except IntegrityError:
        logger.info("[BLACKSEA] concurrent webhook already credited sale %s", sale_id)
        return JSONResponse({"status": "ok"})

    user.credits += credits
    db.add(Transaction(
        user_id=user.id,
        type="purchase",
        amount=credits,
        usd_amount=str(PACKAGES["ultra"]["usd"]),
        package="ultra",
        meta={"blacksea_sale_id": sale_id},
    ))
    await _apply_referral_cascade(db, user, credits)

    # снять до commit — после закрытия сессии ORM-атрибуты недоступны
    user_hwid   = user.hwid
    user_name   = user.username or user.email or f"user#{user.id}"
    user_ip     = user.ip_address
    bot_version = user.bot_version

    await db.commit()

    notify_balance_changed(user_hwid)   # разбудить long-poll бота, только после commit
    background_tasks.add_task(
        send_purchase_alert,
        name=user_name, hwid=user_hwid, package="ultra",
        usd_amount=str(PACKAGES["ultra"]["usd"]), credits=credits,
        ip=user_ip, bot_version=bot_version,
    )
    logger.info("[BLACKSEA] sale %s credited %s to user %s", sale_id, credits, user.id)
    return JSONResponse({"status": "ok"})
