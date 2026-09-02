"""Тесты контура BlackSea — вебхук, верификация продажи через API, начисление.

Граница тестовой среды: SQLite вырезает FOR UPDATE (dialects/sqlite/base.py,
for_update_clause → пустая строка), поэтому здесь доказывается АЛГОРИТМ
(идемпотентность через UNIQUE, перечитывание токена, бюджет повторов), а не
блокировочная семантика PostgreSQL. Реальная сериализация проверяется ручным
прогоном против Postgres перед боевым включением (Задача 8).
"""
import asyncio
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from decimal import Decimal
from httpx import AsyncClient, ASGITransport
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

import blacksea
from main import app
from database import get_db
from models import AppSetting, BlackSeaSale, Transaction, User


async def _create_user(db, email, credits=0, invited_by_id=None):
    u = User(email=email, username=email.split("@")[0],
             ref_code=secrets.token_urlsafe(6), hwid=secrets.token_hex(8),
             credits=credits, invited_by_id=invited_by_id,
             ip_address="1.2.3.4", bot_version="1.8.18")
    db.add(u)
    await db.flush()
    return u


@pytest.mark.asyncio
async def test_blacksea_sale_row_stores_sale(db_session):
    """Строка продажи пишется со всеми полями, uah_amount — Numeric(10,2)."""
    user = await _create_user(db_session, "sale_owner@test.com")
    db_session.add(BlackSeaSale(sale_id="sale-1", user_id=user.id,
                                credits_total=5000, uah_amount=Decimal("410.00")))
    await db_session.commit()

    row = (await db_session.execute(
        select(BlackSeaSale).where(BlackSeaSale.sale_id == "sale-1")
    )).scalar_one()
    assert row.user_id == user.id
    assert row.credits_total == 5000
    assert float(row.uah_amount) == 410.00
    assert row.created_at is not None


@pytest.mark.asyncio
async def test_blacksea_sale_sale_id_is_unique(db_session):
    """UNIQUE(sale_id) — фундамент идемпотентности: второй INSERT падает."""
    user = await _create_user(db_session, "dupe_owner@test.com")
    db_session.add(BlackSeaSale(sale_id="sale-dup", user_id=user.id,
                                credits_total=5000, uah_amount=Decimal("410.00")))
    await db_session.commit()

    db_session.add(BlackSeaSale(sale_id="sale-dup", user_id=user.id,
                                credits_total=5000, uah_amount=Decimal("410.00")))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


SALE_ID     = "v1N13bcVloNleQc9iKMeTg=="
BUYER_EMAIL = "blacksea_buyer@test.com"
PRICE_KOP   = 41000            # 410.00 UAH ≈ $10 по курсу конвертации BlackSea


def _form(**overrides):
    """Тело вебхука BlackSea. Поля — из реального payload, зафиксированного живой
    покупкой (MEMORY/project_blacksea_payment_gateway.md), не выдуманы."""
    body = {
        "seller_id":         "seller-1",
        "product_id":        blacksea.PRODUCT_ID,
        "product_name":      "Total Hunter — 5000 diamonds",
        "permalink":         "abc123",
        "product_permalink": "https://shop.blacksea.in.ua/l/abc123",
        "short_product_id":  "abc123",
        "email":             BUYER_EMAIL,
        "price":             str(PRICE_KOP),
        "fee":               "4100",
        "currency":          "uah",
        "quantity":          "1",
        "order_number":      "568433115",
        "sale_id":           SALE_ID,
        "sale_timestamp":    "2026-09-01T15:04:05Z",
        "purchaser_id":      "purchaser-1",
        "test":              "true",
        "refunded":          "false",
        "resource_name":     "sale",
        "disputed":          "false",
        "dispute_won":       "false",
    }
    body.update(overrides)
    return {k: v for k, v in body.items() if v is not None}


async def _post_webhook(form: dict):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        return await client.post("/web/payment/blacksea/webhook", data=form)


@pytest.mark.parametrize("missing", ["sale_id", "email", "price", "product_id"])
@pytest.mark.asyncio
async def test_webhook_missing_required_field_returns_400(missing):
    """Синтаксически невалидное тело — единственная ветка, отвечающая не 200."""
    resp = await _post_webhook(_form(**{missing: None}))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_non_numeric_price_returns_400():
    resp = await _post_webhook(_form(price="сто гривен"))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_oversized_sale_id_returns_400():
    """sale_id длиннее колонки String(50) — отбрасывать до БД, не ловить обрезкой."""
    resp = await _post_webhook(_form(sale_id="x" * 51))
    assert resp.status_code == 400


@pytest.mark.asyncio
async def test_webhook_wellformed_body_returns_200_without_side_effects(db_session):
    resp = await _post_webhook(_form())
    assert resp.status_code == 200

    async for db in app.dependency_overrides[get_db]():
        assert (await db.execute(select(BlackSeaSale))).scalars().all() == []


@pytest.mark.asyncio
async def test_module_refuses_to_import_without_env_var(monkeypatch):
    """Отсутствие BLACKSEA_* роняет приложение на старте, а не тихо принимает
    вебхуки, которые нечем обработать."""
    import importlib

    original = sys.modules["blacksea"]
    monkeypatch.delenv("BLACKSEA_CLIENT_ID", raising=False)
    del sys.modules["blacksea"]
    try:
        with pytest.raises(ValueError):
            importlib.import_module("blacksea")
    finally:
        sys.modules["blacksea"] = original


import httpx


def _mock_client(handler):
    """Подменяет blacksea._client на клиент поверх MockTransport."""
    def _factory():
        return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=1)
    return _factory


@pytest.mark.asyncio
async def test_fetch_sale_url_encodes_sale_id_and_passes_token(monkeypatch):
    """sale_id вида 'v1N13...Tg==' обязан быть URL-encoded, иначе роутинг
    BlackSea отдаёт не тот путь (MEMORY/project_blacksea_sale_verification_recipe.md)."""
    seen = {}

    def handler(request):
        seen["path"]  = request.url.raw_path
        seen["token"] = request.url.params.get("access_token")
        return httpx.Response(200, json={"success": True, "sale": {"id": SALE_ID}})

    monkeypatch.setattr(blacksea, "_client", _mock_client(handler))

    status, body = await blacksea.fetch_blacksea_sale(SALE_ID, "tok-access")

    assert status == 200
    assert body["sale"]["id"] == SALE_ID
    assert b"/api/v2/sales/v1N13bcVloNleQc9iKMeTg%3D%3D" in seen["path"]
    assert seen["token"] == "tok-access"


@pytest.mark.asyncio
async def test_fetch_sale_returns_status_for_401(monkeypatch):
    monkeypatch.setattr(blacksea, "_client",
                        _mock_client(lambda request: httpx.Response(401, json={"error": "x"})))
    status, body = await blacksea.fetch_blacksea_sale(SALE_ID, "stale")
    assert status == 401


@pytest.mark.asyncio
async def test_fetch_sale_non_json_body_returns_empty_dict(monkeypatch):
    monkeypatch.setattr(blacksea, "_client",
                        _mock_client(lambda request: httpx.Response(200, text="<html>502</html>")))
    status, body = await blacksea.fetch_blacksea_sale(SALE_ID, "tok")
    assert (status, body) == (200, {})


@pytest.mark.asyncio
async def test_fetch_sale_propagates_network_error(monkeypatch):
    def handler(request):
        raise httpx.ConnectError("connection refused")

    monkeypatch.setattr(blacksea, "_client", _mock_client(handler))
    with pytest.raises(httpx.HTTPError):
        await blacksea.fetch_blacksea_sale(SALE_ID, "tok")


@pytest.mark.asyncio
async def test_refresh_token_returns_new_pair(monkeypatch):
    seen = {}

    def handler(request):
        seen["path"] = request.url.path
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"access_token": "new-access",
                                         "refresh_token": "new-refresh",
                                         "scope": "view_sales"})

    monkeypatch.setattr(blacksea, "_client", _mock_client(handler))

    access, refresh = await blacksea.refresh_blacksea_token("old-refresh")

    assert (access, refresh) == ("new-access", "new-refresh")
    assert seen["path"] == "/oauth/token"
    assert "grant_type=refresh_token" in seen["body"]
    assert "refresh_token=old-refresh" in seen["body"]


@pytest.mark.asyncio
async def test_refresh_token_raises_on_non_200(monkeypatch):
    monkeypatch.setattr(blacksea, "_client",
                        _mock_client(lambda request: httpx.Response(400, json={"error": "invalid_grant"})))
    with pytest.raises(blacksea.BlackSeaApiError):
        await blacksea.refresh_blacksea_token("old-refresh")


@pytest.mark.asyncio
async def test_refresh_token_raises_when_pair_incomplete(monkeypatch):
    """200 без refresh_token — не повод записать половину пары в app_settings."""
    monkeypatch.setattr(blacksea, "_client",
                        _mock_client(lambda request: httpx.Response(200, json={"access_token": "a"})))
    with pytest.raises(blacksea.BlackSeaApiError):
        await blacksea.refresh_blacksea_token("old-refresh")


@pytest.mark.asyncio
async def test_read_setting_returns_value_and_none(db_session):
    db_session.add(AppSetting(key=blacksea.KEY_ACCESS_TOKEN, value="tok-access"))
    await db_session.commit()

    assert await blacksea._read_setting(db_session, blacksea.KEY_ACCESS_TOKEN) == "tok-access"
    assert await blacksea._read_setting(db_session, blacksea.KEY_REFRESH_TOKEN) is None


def _api_sale(**overrides):
    """Ответ GET /api/v2/sales/{id} — поля из реального живого вызова
    (MEMORY/project_blacksea_sale_verification_recipe.md)."""
    sale = {
        "id":                 SALE_ID,
        "email":              BUYER_EMAIL,
        "paid":               True,
        "price":              PRICE_KOP,
        "product_id":         blacksea.PRODUCT_ID,
        "order_id":           568433115,
        "chargedback":        False,
        "refunded":           False,
        "partially_refunded": False,
    }
    sale.update(overrides)
    return {k: v for k, v in sale.items() if v is not None}


def _match(sale):
    return blacksea.sale_matches_webhook(
        sale, sale_id=SALE_ID, email=BUYER_EMAIL,
        price_kopecks=PRICE_KOP, product_id=blacksea.PRODUCT_ID,
    )


def test_sale_matches_webhook_accepts_verified_sale():
    assert _match(_api_sale()) is None


def test_sale_matches_webhook_accepts_response_without_id_field():
    """sale.id — defense-in-depth, а не обязательное поле: его отсутствие не отказ."""
    assert _match(_api_sale(id=None)) is None


@pytest.mark.parametrize("sale, expected", [
    (_api_sale(paid=False),                    "not_paid"),
    (_api_sale(chargedback=True),              "chargedback"),
    (_api_sale(refunded=True),                 "refunded"),
    (_api_sale(email="someone.else@test.com"), "email_mismatch"),
    (_api_sale(price=100),                     "price_mismatch"),
    (_api_sale(product_id="other-product"),    "product_id_mismatch"),
    (_api_sale(id="another-sale-id"),          "sale_id_mismatch"),
])
def test_sale_matches_webhook_rejects_mismatch(sale, expected):
    assert _match(sale) == expected


@pytest.mark.parametrize("sale, expected", [
    (_api_sale(paid=None),          "malformed_status_fields"),
    (_api_sale(paid="true"),        "malformed_status_fields"),
    (_api_sale(chargedback=None),   "malformed_status_fields"),
    (_api_sale(refunded="false"),   "malformed_status_fields"),
    (_api_sale(email=None),         "malformed_email"),
    (_api_sale(email=123),          "malformed_email"),
    (_api_sale(price=None),         "malformed_price"),
    (_api_sale(price="41000"),      "malformed_price"),
    (_api_sale(price=True),         "malformed_price"),
    (_api_sale(product_id=None),    "malformed_product_id"),
])
def test_sale_matches_webhook_is_fail_closed_on_broken_fields(sale, expected):
    """Отклонение ответа от ожидаемой формы трактуется как отказ, не как разрешение."""
    assert _match(sale) == expected


def test_sale_matches_webhook_rejects_string_price_even_if_digits_equal():
    """'41000' == 41000 в Python всегда False — сверка обязана идти между int'ами,
    иначе КАЖДАЯ покупка проваливала бы проверку (или, при небрежном приведении,
    проходила бы любая)."""
    assert _match(_api_sale(price=str(PRICE_KOP))) == "malformed_price"


async def _seed_tokens(db, access="tok-access", refresh="tok-refresh"):
    db.add(AppSetting(key=blacksea.KEY_ACCESS_TOKEN,  value=access))
    db.add(AppSetting(key=blacksea.KEY_REFRESH_TOKEN, value=refresh))
    await db.commit()


def _stub_fetch(monkeypatch, responses):
    """responses — список (status, body), отдаётся по порядку. Лишний вызов =
    провал теста: так бюджет «один повтор» проверяется структурно."""
    calls = []

    async def _fetch(sale_id: str, access_token: str):
        calls.append((sale_id, access_token))
        if not responses:
            raise AssertionError("fetch_blacksea_sale вызвана больше раз, чем допускает тест")
        return responses.pop(0)

    monkeypatch.setattr(blacksea, "fetch_blacksea_sale", _fetch)
    return calls


def _stub_alerts(monkeypatch):
    sent = {"manual": [], "purchase": []}

    async def _manual(**kwargs):
        sent["manual"].append(kwargs)

    async def _purchase(**kwargs):
        sent["purchase"].append(kwargs)

    monkeypatch.setattr(blacksea, "send_manual_review_alert", _manual)
    monkeypatch.setattr(blacksea, "send_purchase_alert", _purchase)
    return sent


async def _sales_rows():
    async for db in app.dependency_overrides[get_db]():
        return (await db.execute(select(BlackSeaSale))).scalars().all()


async def _credits_of(email):
    async for db in app.dependency_overrides[get_db]():
        user = (await db.execute(select(User).where(User.email == email))).scalar_one()
        return user.credits


@pytest.mark.asyncio
async def test_webhook_duplicate_sale_id_is_noop_without_api_call(db_session, monkeypatch):
    """Повторная доставка того же вебхука не дёргает API BlackSea повторно."""
    user = await _create_user(db_session, BUYER_EMAIL, credits=5000)
    db_session.add(BlackSeaSale(sale_id=SALE_ID, user_id=user.id,
                                credits_total=5000, uah_amount=Decimal("410.00")))
    await _seed_tokens(db_session)

    _stub_fetch(monkeypatch, [])          # любой вызов → AssertionError
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200
    assert len(await _sales_rows()) == 1
    assert await _credits_of(BUYER_EMAIL) == 5000


@pytest.mark.asyncio
async def test_webhook_foreign_product_is_noop_without_api_call(db_session, monkeypatch):
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [])
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form(product_id="somebody-elses-product"))

    assert resp.status_code == 200
    assert await _sales_rows() == []
    assert await _credits_of(BUYER_EMAIL) == 0


@pytest.mark.asyncio
async def test_webhook_network_error_does_not_credit(db_session, monkeypatch):
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    _stub_alerts(monkeypatch)

    async def _boom(sale_id, access_token):
        raise httpx.ConnectError("blacksea unreachable")

    monkeypatch.setattr(blacksea, "fetch_blacksea_sale", _boom)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200          # не 500 — BlackSea не должна ретраить вечно
    assert await _sales_rows() == []
    assert await _credits_of(BUYER_EMAIL) == 0


@pytest.mark.asyncio
async def test_webhook_api_non_200_does_not_credit(db_session, monkeypatch):
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(500, {})])
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200
    assert await _credits_of(BUYER_EMAIL) == 0


@pytest.mark.asyncio
async def test_webhook_missing_access_token_setting_fails_closed(db_session, monkeypatch):
    """app_settings не засеян → верификация невозможна → не начислять, API не звать."""
    await _create_user(db_session, BUYER_EMAIL)
    await db_session.commit()
    _stub_fetch(monkeypatch, [])
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200
    assert await _credits_of(BUYER_EMAIL) == 0


@pytest.mark.asyncio
async def test_webhook_unpaid_sale_does_not_credit(db_session, monkeypatch):
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(200, {"success": True, "sale": _api_sale(paid=False)})])
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200
    assert await _credits_of(BUYER_EMAIL) == 0


@pytest.mark.asyncio
async def test_webhook_malformed_api_field_fails_closed(db_session, monkeypatch):
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(200, {"success": True, "sale": _api_sale(paid="true")})])
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200
    assert await _credits_of(BUYER_EMAIL) == 0


@pytest.mark.asyncio
async def test_webhook_forged_email_credits_nobody(db_session, monkeypatch):
    """Подделанное тело: чужой реальный sale_id + свой email. Не начислять НИКОМУ —
    ни владельцу email из тела, ни настоящему покупателю из ответа API."""
    await _create_user(db_session, BUYER_EMAIL)
    await _create_user(db_session, "attacker@test.com")
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(200, {"success": True, "sale": _api_sale()})])
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form(email="attacker@test.com"))

    assert resp.status_code == 200
    assert await _sales_rows() == []
    assert await _credits_of(BUYER_EMAIL) == 0
    assert await _credits_of("attacker@test.com") == 0


@pytest.mark.asyncio
async def test_webhook_quantity_not_one_goes_to_manual_review(db_session, monkeypatch):
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(200, {"success": True, "sale": _api_sale()})])
    sent = _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form(quantity="2"))

    assert resp.status_code == 200
    assert await _sales_rows() == []
    assert await _credits_of(BUYER_EMAIL) == 0
    assert len(sent["manual"]) == 1
    assert sent["manual"][0]["sale_id"] == SALE_ID


@pytest.mark.parametrize("quantity", ["01", "1.0", " 1"])
@pytest.mark.asyncio
async def test_webhook_quantity_lookalikes_are_not_one(db_session, monkeypatch, quantity):
    """Сравнение строкой как есть: '01'/'1.0' эквивалентами '1' не считаются."""
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(200, {"success": True, "sale": _api_sale()})])
    sent = _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form(quantity=quantity))

    assert resp.status_code == 200
    assert await _credits_of(BUYER_EMAIL) == 0
    assert len(sent["manual"]) == 1


@pytest.mark.asyncio
async def test_webhook_unknown_email_alerts_and_does_not_credit(db_session, monkeypatch):
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(200, {"success": True, "sale": _api_sale()})])
    sent = _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200
    assert await _sales_rows() == []
    assert len(sent["manual"]) == 1
    assert sent["manual"][0]["email"] == BUYER_EMAIL
    assert sent["manual"][0]["reason"] == "email_not_found"
