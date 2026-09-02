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
