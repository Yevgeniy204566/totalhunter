# BlackSea Payment Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Принимать вебхуки BlackSea, верифицировать продажу через их API и начислять 5000 алмазов покупателю ровно один раз на `sale_id`.
**Architecture:** Новый роутер `server/blacksea.py` (`POST /web/payment/blacksea/webhook`) — form-парсинг → предварительная проверка идемпотентности по новой таблице `blacksea_sales` → верификация продажи через `GET /api/v2/sales/{sale_id}` (с однократным refresh токена при 401, сериализованным `with_for_update()` на `app_settings`) → атомарная вставка `BlackSeaSale` в savepoint под `UNIQUE(sale_id)` → начисление кредитов, `Transaction`, реферальный каскад → один `commit()` → пост-коммит эффекты. Вебхук BlackSea не подписан, поэтому единственная граница безопасности — ответ API, а не тело запроса.
**Tech Stack:** Python 3.13, FastAPI 0.136, SQLAlchemy 2.0.49 (async), Alembic 1.18.4, httpx 0.28.1, PostgreSQL (прод) / SQLite in-memory (тесты), pytest + pytest-asyncio (`asyncio_mode = auto`).
**Spec:** `docs/superpowers/specs/2026-09-01-blacksea-payment-integration-design.md`

## Global Constraints

Инварианты спеки. Каждый обязан выполняться после КАЖДОЙ задачи, а не только в конце.

1. **Единственный источник чисел — `PACKAGES["ultra"]`** (`server/payments.py:38-40`, `{"usd": 10.00, "credits": 5000}`). Литералы `5000` / `10.00` в `server/blacksea.py` запрещены.
2. **`db.begin_nested()`, НИКОГДА `db.begin()`** — сессия уже в autobegin после первого SELECT; `db.begin()` даст `InvalidRequestError: A transaction is already begun` (`ANTI-PATTERNS.md:842-847`, Хангоф #70).
3. **`try` / `except IntegrityError` — СНАРУЖИ `async with db.begin_nested():`**, не внутри (паттерн `server/roy.py:264-287`).
4. **Пользователь ищется по `sale["email"]` из API-ответа, НЕ по `email` из тела вебхука** — тело недоверенное (подписи нет).
5. **Fail-closed:** отсутствующее, `null` или не того типа обязательное поле ответа API (`paid`/`chargedback`/`refunded`/`email`/`price`/`product_id`) = верификация ПРОВАЛЕНА, лог ERROR, не начислять.
6. **Бюджет: не больше одного refresh и не больше одного повтора запроса продажи на один входящий вебхук.**
7. **`with_for_update()`** — на строке `User` (до `commit()`) и на строке `app_settings['blacksea_access_token']` (на всё время refresh-обмена).
8. **HTTP-коды: 400 только на синтаксически невалидное тело формы. Все остальные ветки, включая любые отказы — 200.** 500 не является допустимым исходом ни одной ветки тестовой матрицы.
9. **`notify_balance_changed` и `send_purchase_alert` — строго ПОСЛЕ `await db.commit()`.**
10. **Поле `test` из вебхука не используется нигде** (осознанно: `test:true` наблюдался на настоящей боевой оплате).
11. **`quantity` сравнивается как строка с `"1"`**, без `int()` — `"01"`/`"1.0"` эквивалентами не считаются.
12. **`price_kopecks = int(price)` сразу при разборе формы**, дальше по потоку только число; сверка `price_kopecks == sale["price"]` (оба `int`).
13. **`sale_id` из тела — только ключ запроса к API.** Доверие даёт исключительно успешный ответ API плюс совпадение всех сверяемых полей.
14. **`_apply_referral_cascade` и `send_purchase_alert` переиспользуются без изменения сигнатур.**

## Окружение тестов (проверено в этой сессии, не по памяти)

Тесты сервера не запускаются без переменных окружения — `server/main.py:543-545` и `server/web_routes.py:56` падают на импорте:

```bash
cd /c/BattleBot/server
ADMIN_TOKEN=dev-admin-token JWT_SECRET_KEY=dev-jwt-secret python -m pytest tests/test_payments.py -q
# → 10 passed
```

PowerShell-эквивалент (основная оболочка проекта):

```powershell
Set-Location C:\BattleBot\server
$env:ADMIN_TOKEN="dev-admin-token"; $env:JWT_SECRET_KEY="dev-jwt-secret"
python -m pytest tests/test_blacksea.py -v
```

`BLACKSEA_CLIENT_ID` / `BLACKSEA_CLIENT_SECRET` / `BLACKSEA_PRODUCT_ID` в оболочке задавать НЕ нужно — Задача 2 добавляет их `os.environ.setdefault(...)` в `server/tests/conftest.py` до `from main import app`. Без этого стартовая валидация из спеки уронила бы ВЕСЬ тестовый набор проекта, не только новый файл.

## File Structure

| Файл | Что делает | Задача |
|---|---|---|
| `server/models.py` | +класс `BlackSeaSale` — единственная таблица идемпотентности BlackSea | 1 |
| `server/alembic/versions/b1a2c3k4s5e6_add_blacksea_sales.py` | новая ревизия, `down_revision = 's2e3s4s5i6o7'` (текущий единственный head, проверено `alembic heads`) | 1 |
| `server/blacksea.py` | весь контур BlackSea: конфиг+валидация env, HTTP-функции к API, чистая сверка продажи, refresh токена под локом, эндпоинт вебхука | 2,3,4,5,6,7 |
| `server/tg_channel.py` | +`send_manual_review_alert` — алерт владельцу на ручной разбор | 5 |
| `server/main.py` | +`from blacksea import router as blacksea_router` и `app.include_router(blacksea_router)` | 2 |
| `server/tests/conftest.py` | +три `os.environ.setdefault` до `from main import app` | 2 |
| `server/tests/test_blacksea.py` | все тесты контура — модель, HTTP-слой, чистая сверка, эндпоинт, конкурентность, refresh | 1-7 |

Один модуль на весь контур, а не разбиение по слоям: файлы, которые меняются вместе, живут вместе (эндпоинт, его конфиг и его HTTP-клиент меняются одним изменением бизнес-правила BlackSea). `payments.py` не трогается вообще — из него только импортируются `PACKAGES` и `_apply_referral_cascade`.

## Осознанно НЕ в объёме (зафиксировано, чтобы исполнитель не додумывал)

- **Проверка `user.is_banned`.** NOWPayments-вебхук (`payments.py:203-204`) отклоняет забаненного покупателя, спека BlackSea про бан не говорит ни слова. Плану запрещено добавлять правило, которого нет в спеке; вопрос вынесен владельцу отдельно и до его ответа не реализуется.
- Автосоздание аккаунта по незнакомому email, поллинг списка продаж как fallback, автопроверка лицензионных ключей, редирект покупателя — исключены самой спекой (раздел «Что НЕ входит в объём»).
- Поведение NOWPayments (`NP_API_KEY` молча пустой) не меняется.

## Известная неточность прозы спеки (не менять код, чтобы «исправить»)

Спека пишет, что `str(PACKAGES["ultra"]["usd"])` даёт `"10.00"`. Фактически `PACKAGES["ultra"]["usd"]` — это `float` `10.00`, и `str(10.00) == "10.0"`. В БД разницы нет (`Transaction.usd_amount` — `Numeric(10,2)`, сохранится `10.00`), в Telegram-алерте будет `$10.0` вместо `$10.00`. План следует БУКВЕ спеки (`str(PACKAGES["ultra"]["usd"])`, Global Constraint 1) и НЕ вводит форматирование `f"{...:.2f}"` — текст уведомления это решение владельца, а не исполнителя. Тесты проверяют числовое значение (`float(...) == 10.0`), а не строку.

---

## Задача 1 — Модель `BlackSeaSale` + миграция

**Файлы:**
- Изменить: `server/models.py` (добавить класс после `Order`, ~строка 359)
- Создать: `server/alembic/versions/b1a2c3k4s5e6_add_blacksea_sales.py`
- Создать: `server/tests/test_blacksea.py`

**Интерфейсы:**
- Consumes: `Base`, `User` (`server/models.py`), naming convention `MetaData(naming_convention=convention)` (`models.py:24-34`).
- Produces: `BlackSeaSale(sale_id: str, user_id: int, credits_total: int, uah_amount: Decimal, created_at)` — уникальный индекс `ix_blacksea_sales_sale_id` (`unique=True`), на который опирается идемпотентность в Задаче 6.

**Шаги:**

- [ ] 1. Создать ветку: `git checkout -b feat/blacksea-payment`

- [ ] 2. Написать падающий тест — создать `server/tests/test_blacksea.py`:

```python
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
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

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
```

- [ ] 3. Убедиться, что тест падает (`ImportError: cannot import name 'BlackSeaSale'`):

```powershell
Set-Location C:\BattleBot\server
$env:ADMIN_TOKEN="dev-admin-token"; $env:JWT_SECRET_KEY="dev-jwt-secret"
python -m pytest tests/test_blacksea.py -v
```

- [ ] 4. Добавить модель в `server/models.py` сразу после класса `Order` (после строки `user = relationship("User", backref="orders")`):

```python
# ─────────────────────────────────────────────
# BlackSeaSale — идемпотентность фиатных продаж BlackSea
# ─────────────────────────────────────────────

class BlackSeaSale(Base):
    """
    Одна строка на УСПЕШНО начисленную продажу BlackSea.

    Стадии pending нет (в отличие от Order): заказ у нас заранее не создаётся —
    покупатель уходит на фиксированную ссылку товара, единственный сигнал это
    вебхук. Само наличие строки по sale_id и есть идемпотентность, а
    UNIQUE(sale_id) — последний рубеж при двух конкурентных вебхуках.
    """
    __tablename__ = "blacksea_sales"

    id            = Column(Integer, primary_key=True)
    sale_id       = Column(String(50), unique=True, nullable=False, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    credits_total = Column(Integer, nullable=False)
    uah_amount    = Column(Numeric(10, 2), nullable=False)
    created_at    = Column(TIMESTAMP(timezone=True), nullable=False,
                           server_default=func.now())

    user = relationship("User", backref="blacksea_sales")
```

- [ ] 5. Прогнать тесты — оба должны пройти:

```powershell
python -m pytest tests/test_blacksea.py -v
```

- [ ] 6. Создать миграцию `server/alembic/versions/b1a2c3k4s5e6_add_blacksea_sales.py` (`down_revision` — текущий единственный head, проверено `python -m alembic heads` → `s2e3s4s5i6o7 (head)`):

```python
"""add_blacksea_sales

Revision ID: b1a2c3k4s5e6
Revises: s2e3s4s5i6o7
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa


revision = 'b1a2c3k4s5e6'
down_revision = 's2e3s4s5i6o7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'blacksea_sales',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('sale_id', sa.String(50), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('credits_total', sa.Integer(), nullable=False),
        sa.Column('uah_amount', sa.Numeric(10, 2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True),
                  server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'],
                                name=op.f('fk_blacksea_sales_user_id_users')),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_blacksea_sales')),
    )
    op.create_index(op.f('ix_blacksea_sales_sale_id'), 'blacksea_sales',
                    ['sale_id'], unique=True)
    op.create_index(op.f('ix_blacksea_sales_user_id'), 'blacksea_sales', ['user_id'])


def downgrade() -> None:
    op.drop_index(op.f('ix_blacksea_sales_user_id'), table_name='blacksea_sales')
    op.drop_index(op.f('ix_blacksea_sales_sale_id'), table_name='blacksea_sales')
    op.drop_table('blacksea_sales')
```

`sale_id` — уникальный ИНДЕКС, а не `UniqueConstraint`: в модели указаны одновременно `unique=True` и `index=True`, SQLAlchemy в этом случае создаёт один unique-индекс. Дублировать его ещё и constraint'ом нельзя — получатся два объекта БД на одну колонку.

- [ ] 7. Проверить, что голова ревизий осталась одна и SQL рендерится (без подключения к БД):

```powershell
Set-Location C:\BattleBot\server
python -m alembic heads          # → b1a2c3k4s5e6 (head), ровно одна строка
python -m alembic upgrade s2e3s4s5i6o7:b1a2c3k4s5e6 --sql   # → CREATE TABLE blacksea_sales ...
```

- [ ] 8. Коммит:

```bash
git add server/models.py server/alembic/versions/b1a2c3k4s5e6_add_blacksea_sales.py server/tests/test_blacksea.py
git commit -m "feat(blacksea): таблица blacksea_sales — идемпотентность фиатных продаж"
```

---

## Задача 2 — Модуль `blacksea.py`: конфиг, стартовая валидация, роутер, разбор формы

**Файлы:**
- Создать: `server/blacksea.py`
- Изменить: `server/main.py` (импорт рядом со строкой 49, `include_router` рядом со строкой 103)
- Изменить: `server/tests/conftest.py` (три `setdefault` между `sys.path.insert` и `from database import get_db`)
- Изменить: `server/tests/test_blacksea.py`

**Интерфейсы:**
- Consumes: `get_db` (`server/database.py:35`), `BlackSeaSale` (Задача 1).
- Produces: `router` (`APIRouter(prefix="/web/payment/blacksea")`), `POST /web/payment/blacksea/webhook`; константы модуля `CLIENT_ID`, `CLIENT_SECRET`, `PRODUCT_ID`, `BLACKSEA_API_BASE`, `HTTP_TIMEOUT`, `KEY_ACCESS_TOKEN`, `KEY_REFRESH_TOKEN`, `MAX_SALE_ID_LEN`; исключение `BlackSeaApiError`; хелпер `_form_str(form, key) -> str`.

**Шаги:**

- [ ] 1. Написать падающие тесты — дописать в `server/tests/test_blacksea.py`:

```python
from httpx import AsyncClient, ASGITransport

import blacksea

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
```

- [ ] 2. Убедиться, что тесты падают (`ModuleNotFoundError: No module named 'blacksea'`):

```powershell
python -m pytest tests/test_blacksea.py -v
```

- [ ] 3. Создать `server/blacksea.py`:

```python
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
```

- [ ] 4. Зарегистрировать роутер в `server/main.py` — импорт после строки `from payments import router as payments_router`:

```python
from blacksea import router as blacksea_router
```

и вызов после `app.include_router(payments_router)`:

```python
app.include_router(blacksea_router)
```

- [ ] 5. Добавить env-значения в `server/tests/conftest.py` — между `sys.path.insert(...)` и `from database import get_db`:

```python
# blacksea.py валидирует эти переменные на импорте (см. спеку) — без них
# упадёт весь набор тестов, а не только тесты BlackSea.
os.environ.setdefault("BLACKSEA_CLIENT_ID",     "test-blacksea-client-id")
os.environ.setdefault("BLACKSEA_CLIENT_SECRET", "test-blacksea-client-secret")
os.environ.setdefault("BLACKSEA_PRODUCT_ID",    "test-blacksea-product-id")
```

- [ ] 6. Прогнать тесты нового файла и всего сервера (регресс от стартовой валидации):

```powershell
python -m pytest tests/test_blacksea.py -v
python -m pytest tests/ -q
```

- [ ] 7. Коммит:

```bash
git add server/blacksea.py server/main.py server/tests/conftest.py server/tests/test_blacksea.py
git commit -m "feat(blacksea): роутер вебхука + валидация тела формы и BLACKSEA_* env на старте"
```

---

## Задача 3 — HTTP-слой к BlackSea API (`fetch_blacksea_sale`, `refresh_blacksea_token`, `_read_setting`)

**Файлы:**
- Изменить: `server/blacksea.py`
- Изменить: `server/tests/test_blacksea.py`

**Интерфейсы:**
- Consumes: `CLIENT_ID`, `CLIENT_SECRET`, `BLACKSEA_API_BASE`, `HTTP_TIMEOUT`, `BlackSeaApiError` (Задача 2); `AppSetting` (`server/models.py:185`).
- Produces:
  - `def _client() -> httpx.AsyncClient` — единственное место сборки клиента (тесты подменяют на `MockTransport`).
  - `async def fetch_blacksea_sale(sale_id: str, access_token: str) -> tuple[int, dict]` — `(status_code, тело)`; сетевые сбои пробрасывает как `httpx.HTTPError`.
  - `async def refresh_blacksea_token(refresh_token: str) -> tuple[str, str]` — `(access_token, refresh_token)`; `BlackSeaApiError` на не-200/битый ответ.
  - `async def _read_setting(db: AsyncSession, key: str) -> str | None`.

Обе публичные функции — на уровне модуля именно для того, чтобы тесты эндпоинта подменяли их через `monkeypatch.setattr(blacksea, ...)`. Внутри модуля их ВСЕГДА вызывать как глобальные имена, никогда не через локальный алиас — иначе подмена перестанет работать.

**Шаги:**

- [ ] 1. Написать падающие тесты — дописать в `server/tests/test_blacksea.py`:

```python
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
        seen["path"]  = request.url.path
        seen["token"] = request.url.params.get("access_token")
        return httpx.Response(200, json={"success": True, "sale": {"id": SALE_ID}})

    monkeypatch.setattr(blacksea, "_client", _mock_client(handler))

    status, body = await blacksea.fetch_blacksea_sale(SALE_ID, "tok-access")

    assert status == 200
    assert body["sale"]["id"] == SALE_ID
    assert seen["path"].endswith("/api/v2/sales/v1N13bcVloNleQc9iKMeTg%3D%3D")
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
```

- [ ] 2. Убедиться, что тесты падают (`AttributeError: module 'blacksea' has no attribute '_client'`):

```powershell
python -m pytest tests/test_blacksea.py -v
```

- [ ] 3. Реализовать HTTP-слой в `server/blacksea.py` — добавить импорты `import urllib.parse`, `import httpx`, `from models import AppSetting, BlackSeaSale` и функции после `class BlackSeaApiError`:

```python
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
```

- [ ] 4. Прогнать тесты — все восемь новых должны пройти:

```powershell
python -m pytest tests/test_blacksea.py -v
```

- [ ] 5. Коммит:

```bash
git add server/blacksea.py server/tests/test_blacksea.py
git commit -m "feat(blacksea): HTTP-слой — verify продажи, refresh токена, чтение app_settings"
```

---

## Задача 4 — Чистая сверка ответа API с телом вебхука (`sale_matches_webhook`)

**Файлы:**
- Изменить: `server/blacksea.py`
- Изменить: `server/tests/test_blacksea.py`

**Интерфейсы:**
- Consumes: ничего (чистая функция, без БД и сети).
- Produces: `def sale_matches_webhook(sale: dict, *, sale_id: str, email: str, price_kopecks: int, product_id: str) -> str | None` — `None` = продажа верифицирована и совпала; строка = причина отказа для лога. Задача 5 вызывает её и на любой не-`None` отвечает 200 без начисления.

**Шаги:**

- [ ] 1. Написать падающие тесты — дописать в `server/tests/test_blacksea.py`:

```python
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
```

- [ ] 2. Убедиться, что тесты падают (`AttributeError: ... 'sale_matches_webhook'`):

```powershell
python -m pytest tests/test_blacksea.py -k sale_matches -v
```

- [ ] 3. Реализовать функцию в `server/blacksea.py` (после `_read_setting`):

```python
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
```

- [ ] 4. Прогнать тесты:

```powershell
python -m pytest tests/test_blacksea.py -v
```

- [ ] 5. Коммит:

```bash
git add server/blacksea.py server/tests/test_blacksea.py
git commit -m "feat(blacksea): fail-closed сверка ответа API с телом вебхука"
```

---

## Задача 5 — Эндпоинт: идемпотентность, гейт товара, верификация, все ветки отказа + алерт на ручной разбор

**Файлы:**
- Изменить: `server/blacksea.py`
- Изменить: `server/tg_channel.py` (добавить функцию после `send_purchase_alert`, конец файла)
- Изменить: `server/tests/test_blacksea.py`

**Интерфейсы:**
- Consumes: `fetch_blacksea_sale`, `_read_setting`, `BlackSeaApiError`, `KEY_ACCESS_TOKEN` (Задача 3); `sale_matches_webhook` (Задача 4); `BlackSeaSale` (Задача 1); `_send_debug_sync` (`server/tg_channel.py:46`).
- Produces:
  - `async def send_manual_review_alert(*, reason: str, sale_id: str, email: str, uah_amount: str) -> None` в `server/tg_channel.py`.
  - `async def _verify_sale(db: AsyncSession, sale_id: str) -> dict` в `blacksea.py` — возвращает объект `sale` или бросает `BlackSeaApiError` (в Задаче 7 к ней добавится ветка 401).
  - Эндпоинт доходит до найденного `User`; начисление появляется в Задаче 6.

**Шаги:**

- [ ] 1. Написать падающие тесты — дописать в `server/tests/test_blacksea.py`:

```python
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
```

- [ ] 2. Убедиться, что тесты падают:

```powershell
python -m pytest tests/test_blacksea.py -v
```

- [ ] 3. Добавить алерт в конец `server/tg_channel.py`:

```python
async def send_manual_review_alert(
    *, reason: str, sale_id: str, email: str, uah_amount: str,
) -> None:
    """Fire-and-forget: продажа BlackSea, которую нельзя начислить автоматически.
    Не бросает исключений."""
    if not _DEBUG_TOKEN or not _DEBUG_CHAT_ID:
        return
    text = (
        "⚠️ BlackSea — нужен ручной разбор\n"
        f"❓ Причина: {reason}\n"
        f"📧 Email: {email}\n"
        f"🧾 sale_id: {sale_id}\n"
        f"💳 Сумма: {uah_amount} UAH"
    )
    await asyncio.to_thread(_send_debug_sync, text)
```

Текст уведомления — предложение исполнителя; владелец подтверждает формулировку при ревью плана, менять её самостоятельно после утверждения нельзя.

- [ ] 4. Дописать верификацию и ветки отказа в `server/blacksea.py`. Новые импорты сверху:

```python
from decimal import Decimal

from models import AppSetting, BlackSeaSale, User
from tg_channel import send_manual_review_alert
```

Функция `_verify_sale` — после `sale_matches_webhook`:

```python
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
```

Тело эндпоинта — заменить `logger.info(...)` + `return JSONResponse(...)` из Задачи 2 на:

```python
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

    logger.info("[BLACKSEA] sale %s verified for user %s", sale_id, user.id)
    return JSONResponse({"status": "ok"})
```

- [ ] 5. Прогнать тесты — все ветки отказа зелёные:

```powershell
python -m pytest tests/test_blacksea.py -v
```

- [ ] 6. Коммит:

```bash
git add server/blacksea.py server/tg_channel.py server/tests/test_blacksea.py
git commit -m "feat(blacksea): идемпотентность, гейт товара, верификация продажи и алерт на ручной разбор"
```

---

## Задача 6 — Атомарное начисление, реферальный каскад, пост-коммит эффекты

**Файлы:**
- Изменить: `server/blacksea.py`
- Изменить: `server/tests/test_blacksea.py`

**Интерфейсы:**
- Consumes: `PACKAGES` и `_apply_referral_cascade` (`server/payments.py:38`, `:92` — сигнатура `async def _apply_referral_cascade(db: AsyncSession, buyer: User, credits_total: int) -> None`, не завязана на `Order`); `notify_balance_changed(hwid: str | None) -> None` (`server/vault.py:24`); `send_purchase_alert(*, name, hwid, package, usd_amount, credits, ip, bot_version)` (`server/tg_channel.py:59`); `Transaction` (`server/models.py:92`).
- Produces: полный успешный путь начисления. Эндпоинт после этой задачи функционально завершён для случая, когда токен валиден (ветка 401 — Задача 7).

**Шаги:**

- [ ] 1. Написать падающие тесты — дописать в `server/tests/test_blacksea.py`:

```python
@pytest.mark.asyncio
async def test_webhook_happy_path_credits_buyer(db_session, monkeypatch):
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(200, {"success": True, "sale": _api_sale()})])
    sent = _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200
    assert await _credits_of(BUYER_EMAIL) == 5000
    assert sent["manual"] == []

    async for db in app.dependency_overrides[get_db]():
        row = (await db.execute(
            select(BlackSeaSale).where(BlackSeaSale.sale_id == SALE_ID)
        )).scalar_one()
        assert row.credits_total == 5000
        assert float(row.uah_amount) == 410.00

        txn = (await db.execute(
            select(Transaction).where(Transaction.type == "purchase")
        )).scalar_one()
        assert txn.amount == 5000
        assert txn.package == "ultra"
        assert float(txn.usd_amount) == 10.00
        assert txn.meta["blacksea_sale_id"] == SALE_ID
        assert txn.user_id == row.user_id

    assert len(sent["purchase"]) == 1
    assert sent["purchase"][0]["package"] == "ultra"
    assert sent["purchase"][0]["credits"] == 5000


@pytest.mark.asyncio
async def test_webhook_happy_path_applies_referral_cascade(db_session, monkeypatch):
    """Те же 10%/5%/1%, что у NOWPayments — функция переиспользуется как есть."""
    l2 = await _create_user(db_session, "bs_l2@test.com")
    l1 = await _create_user(db_session, "bs_l1@test.com", invited_by_id=l2.id)
    await _create_user(db_session, BUYER_EMAIL, invited_by_id=l1.id)
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(200, {"success": True, "sale": _api_sale()})])
    _stub_alerts(monkeypatch)

    await _post_webhook(_form())

    async for db in app.dependency_overrides[get_db]():
        ref1 = (await db.execute(select(User).where(User.email == "bs_l1@test.com"))).scalar_one()
        ref2 = (await db.execute(select(User).where(User.email == "bs_l2@test.com"))).scalar_one()
        assert ref1.ref_credits == 500   # 10% от 5000
        assert ref2.ref_credits == 250   # 5% от 5000


@pytest.mark.asyncio
async def test_webhook_without_quantity_field_credits_single_package(db_session, monkeypatch):
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(200, {"success": True, "sale": _api_sale()})])
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form(quantity=None))

    assert resp.status_code == 200
    assert await _credits_of(BUYER_EMAIL) == 5000


@pytest.mark.asyncio
async def test_webhook_redelivery_credits_exactly_once(db_session, monkeypatch):
    """Вторая доставка того же вебхука: 200, кредиты не удваиваются, API не зовётся
    повторно (в стабе ровно один ответ — второй вызов уронил бы тест)."""
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(200, {"success": True, "sale": _api_sale()})])
    _stub_alerts(monkeypatch)

    first  = await _post_webhook(_form())
    second = await _post_webhook(_form())

    assert (first.status_code, second.status_code) == (200, 200)
    assert await _credits_of(BUYER_EMAIL) == 5000
    assert len(await _sales_rows()) == 1


@pytest.mark.asyncio
async def test_webhook_notifies_bot_and_owner_only_after_commit(db_session, monkeypatch):
    """notify_balance_changed и алерт владельцу не должны срабатывать до commit —
    иначе бот проснётся на long-poll раньше, чем баланс реально сохранён."""
    from sqlalchemy.ext.asyncio import AsyncSession as _AsyncSession

    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    _stub_fetch(monkeypatch, [(200, {"success": True, "sale": _api_sale()})])

    events = []
    original_commit = _AsyncSession.commit

    async def _spy_commit(self):
        events.append("commit")
        return await original_commit(self)

    async def _purchase(**kwargs):
        events.append("purchase_alert")

    monkeypatch.setattr(_AsyncSession, "commit", _spy_commit)
    monkeypatch.setattr(blacksea, "notify_balance_changed", lambda hwid: events.append("notify"))
    monkeypatch.setattr(blacksea, "send_purchase_alert", _purchase)

    await _post_webhook(_form())

    assert "commit" in events and "notify" in events
    assert events.index("commit") < events.index("notify")
    assert events.index("notify") < events.index("purchase_alert")


@pytest.mark.asyncio
async def test_webhook_concurrent_duplicate_credits_exactly_once(db_session, monkeypatch):
    """Два одновременных вебхука с одним sale_id. UNIQUE(sale_id) в SQLite работает
    по-настоящему, поэтому тест содержателен: ровно одна строка, 5000 кредитов, ни
    одного 500. Блокировочную семантику PostgreSQL он НЕ доказывает (Задача 8)."""
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session)
    sale_body = (200, {"success": True, "sale": _api_sale()})
    _stub_fetch(monkeypatch, [sale_body, sale_body])
    _stub_alerts(monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        results = await asyncio.gather(
            client.post("/web/payment/blacksea/webhook", data=_form()),
            client.post("/web/payment/blacksea/webhook", data=_form()),
        )

    assert [r.status_code for r in results] == [200, 200]
    assert len(await _sales_rows()) == 1
    assert await _credits_of(BUYER_EMAIL) == 5000
```

Если конкурентный тест окажется нестабильным из-за `StaticPool` (обе сессии делят одно SQLite-соединение) — **производственный код ослаблять запрещено**. Порядок действий: зафиксировать факт, оставить детерминированный `test_webhook_redelivery_credits_exactly_once` как обязательное доказательство идемпотентности, вынести конкурентность на ручной прогон против PostgreSQL (Задача 8) и сообщить владельцу.

- [ ] 2. Убедиться, что тесты падают (кредиты 0, строк нет):

```powershell
python -m pytest tests/test_blacksea.py -v
```

- [ ] 3. Дописать начисление в `server/blacksea.py`. Новые импорты сверху:

```python
from sqlalchemy.exc import IntegrityError

from models import AppSetting, BlackSeaSale, Transaction, User
from payments import PACKAGES, _apply_referral_cascade
from tg_channel import send_manual_review_alert, send_purchase_alert
from vault import notify_balance_changed
```

Заменить в эндпоинте финальные `logger.info("[BLACKSEA] sale %s verified ...")` + `return` на:

```python
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
```

- [ ] 4. Прогнать тесты BlackSea и весь набор сервера:

```powershell
python -m pytest tests/test_blacksea.py -v
python -m pytest tests/ -q
```

- [ ] 5. Прогнать конкурентный тест 5 раз подряд — убедиться, что он стабилен:

```powershell
python -m pytest tests/test_blacksea.py -k concurrent_duplicate --count=1 -v
python -m pytest tests/test_blacksea.py -k concurrent_duplicate -v
python -m pytest tests/test_blacksea.py -k concurrent_duplicate -v
python -m pytest tests/test_blacksea.py -k concurrent_duplicate -v
python -m pytest tests/test_blacksea.py -k concurrent_duplicate -v
```

(`--count` требует pytest-repeat; если плагина нет — просто пять одинаковых прогонов, как выше.)

- [ ] 6. Коммит:

```bash
git add server/blacksea.py server/tests/test_blacksea.py
git commit -m "feat(blacksea): атомарное начисление алмазов, каскад рефералов, пост-коммит уведомления"
```

---

## Задача 7 — Refresh токена при 401: лок на `app_settings`, ровно один обмен и один повтор

**Файлы:**
- Изменить: `server/blacksea.py`
- Изменить: `server/tests/test_blacksea.py`

**Интерфейсы:**
- Consumes: `refresh_blacksea_token`, `_read_setting`, `KEY_ACCESS_TOKEN`, `KEY_REFRESH_TOKEN`, `BlackSeaApiError` (Задача 3); `AppSetting` (`server/models.py:185`).
- Produces: `async def _obtain_fresh_access_token(db: AsyncSession, stale_token: str) -> str` — коммитит собственную транзакцию и возвращает актуальный `access_token`; `_verify_sale` получает ветку 401 → refresh → ровно один повтор.

**Шаги:**

- [ ] 1. Написать падающие тесты — дописать в `server/tests/test_blacksea.py`:

```python
def _stub_refresh(monkeypatch, pair=("new-access", "new-refresh"), exc=None):
    calls = []

    async def _refresh(refresh_token: str):
        calls.append(refresh_token)
        if exc is not None:
            raise exc
        return pair

    monkeypatch.setattr(blacksea, "refresh_blacksea_token", _refresh)
    return calls


async def _settings_pair():
    async for db in app.dependency_overrides[get_db]():
        access  = await blacksea._read_setting(db, blacksea.KEY_ACCESS_TOKEN)
        refresh = await blacksea._read_setting(db, blacksea.KEY_REFRESH_TOKEN)
        return access, refresh


@pytest.mark.asyncio
async def test_401_triggers_single_refresh_and_single_retry(db_session, monkeypatch):
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session, access="stale-access", refresh="old-refresh")
    fetches = _stub_fetch(monkeypatch, [
        (401, {}),
        (200, {"success": True, "sale": _api_sale()}),
    ])
    refreshes = _stub_refresh(monkeypatch)
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200
    assert refreshes == ["old-refresh"]                 # обменяли ровно один раз
    assert [token for _, token in fetches] == ["stale-access", "new-access"]
    assert await _settings_pair() == ("new-access", "new-refresh")
    assert await _credits_of(BUYER_EMAIL) == 5000


@pytest.mark.asyncio
async def test_second_401_after_refresh_stops_without_second_refresh(db_session, monkeypatch):
    """Refresh не помог → доступ отозван или сменился scope. Второй обмен запрещён:
    он может лишь повторить тот же результат."""
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session, access="stale-access", refresh="old-refresh")
    _stub_fetch(monkeypatch, [(401, {}), (401, {})])
    refreshes = _stub_refresh(monkeypatch)
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200
    assert len(refreshes) == 1
    assert await _credits_of(BUYER_EMAIL) == 0


@pytest.mark.asyncio
async def test_refresh_network_error_leaves_tokens_untouched(db_session, monkeypatch):
    """Сбой именно refresh-вызова: savepoint откатывается, старая пара в
    app_settings остаётся, продажа не начисляется, 500 наружу не уходит."""
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session, access="stale-access", refresh="old-refresh")
    _stub_fetch(monkeypatch, [(401, {})])
    _stub_refresh(monkeypatch, exc=httpx.ConnectError("oauth unreachable"))
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200
    assert await _settings_pair() == ("stale-access", "old-refresh")
    assert await _credits_of(BUYER_EMAIL) == 0


@pytest.mark.asyncio
async def test_refresh_api_error_leaves_tokens_untouched(db_session, monkeypatch):
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session, access="stale-access", refresh="old-refresh")
    _stub_fetch(monkeypatch, [(401, {})])
    _stub_refresh(monkeypatch, exc=blacksea.BlackSeaApiError("invalid_grant"))
    _stub_alerts(monkeypatch)

    resp = await _post_webhook(_form())

    assert resp.status_code == 200
    assert await _settings_pair() == ("stale-access", "old-refresh")
    assert await _credits_of(BUYER_EMAIL) == 0


@pytest.mark.asyncio
async def test_obtain_fresh_token_reuses_value_rotated_by_someone_else(db_session, monkeypatch):
    """Ключевая ветка защиты от двойного обмена: значение в БД уже != stale →
    берём чужой результат и НЕ трогаем refresh_token."""
    await _seed_tokens(db_session, access="already-rotated", refresh="untouched-refresh")

    async def _must_not_run(refresh_token):
        raise AssertionError("refresh_blacksea_token не должна вызываться на этой ветке")

    monkeypatch.setattr(blacksea, "refresh_blacksea_token", _must_not_run)

    async for db in app.dependency_overrides[get_db]():
        token = await blacksea._obtain_fresh_access_token(db, "stale-access")

    assert token == "already-rotated"
    assert await _settings_pair() == ("already-rotated", "untouched-refresh")


@pytest.mark.asyncio
async def test_obtain_fresh_token_fails_closed_when_refresh_setting_missing(db_session):
    """Есть access-строка, нет refresh-строки — обменивать нечем, отказ, не молчание."""
    db_session.add(AppSetting(key=blacksea.KEY_ACCESS_TOKEN, value="stale-access"))
    await db_session.commit()

    async for db in app.dependency_overrides[get_db]():
        with pytest.raises(blacksea.BlackSeaApiError):
            await blacksea._obtain_fresh_access_token(db, "stale-access")


@pytest.mark.asyncio
async def test_concurrent_401_webhooks_both_credit_and_leave_valid_tokens(db_session, monkeypatch):
    """Два одновременных вебхука с разными sale_id, оба получают 401.

    ЧТО ЭТОТ ТЕСТ ДОКАЗЫВАЕТ на SQLite: обе продажи начислены, каждая один раз,
    в app_settings лежит пара, реально полученная от обмена, 500 нет.
    ЧЕГО НЕ ДОКАЗЫВАЕТ: «refresh ровно один раз» — SQLite вырезает FOR UPDATE
    (dialects/sqlite/base.py: for_update_clause → ''), сериализации нет, поэтому
    число обменов здесь не детерминировано. Однократность обмена обеспечивает
    PostgreSQL и проверяется ручным прогоном (Задача 8); алгоритмическая часть
    (перечитывание значения под локом) закрыта тестом
    test_obtain_fresh_token_reuses_value_rotated_by_someone_else.
    """
    second_sale_id = "SECONDsale0000000000=="
    await _create_user(db_session, BUYER_EMAIL)
    await _seed_tokens(db_session, access="stale-access", refresh="old-refresh")

    async def _fetch(sale_id, access_token):
        if access_token == "stale-access":
            return 401, {}
        return 200, {"success": True, "sale": _api_sale(id=sale_id)}

    monkeypatch.setattr(blacksea, "fetch_blacksea_sale", _fetch)
    refreshes = _stub_refresh(monkeypatch)
    _stub_alerts(monkeypatch)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        results = await asyncio.gather(
            client.post("/web/payment/blacksea/webhook", data=_form()),
            client.post("/web/payment/blacksea/webhook", data=_form(sale_id=second_sale_id)),
        )

    assert [r.status_code for r in results] == [200, 200]
    assert len(refreshes) >= 1
    assert await _settings_pair() == ("new-access", "new-refresh")
    assert len(await _sales_rows()) == 2
    assert await _credits_of(BUYER_EMAIL) == 10000
```

- [ ] 2. Убедиться, что тесты падают (`AttributeError: ... '_obtain_fresh_access_token'`, 401 не обрабатывается):

```powershell
python -m pytest tests/test_blacksea.py -v
```

- [ ] 3. Реализовать refresh в `server/blacksea.py` — функция перед `_verify_sale`:

```python
async def _obtain_fresh_access_token(db: AsyncSession, stale_token: str) -> str:
    """Обменять протухший токен, сериализовав обмен на строке app_settings.

    Сравнить прочитанное значение до сетевого вызова недостаточно: гонка живёт в
    промежутке между чтением и записью (round-trip к BlackSea). Поэтому строка
    берётся FOR UPDATE и перечитывается уже под локом — конкурентный вебхук ждёт
    и получает готовый результат вместо второго обмена тем же refresh_token,
    который BlackSea уже ротировала.

    Транзакция здесь своя и коммитится сразу: лок держится только на время
    редкого refresh-пути, начисление кредитов идёт следующей транзакцией.
    Сетевая ошибка обмена выходит наружу как есть — savepoint откатывается,
    старая пара токенов остаётся нетронутой.
    """
    async with db.begin_nested():
        access_row = (await db.execute(
            select(AppSetting)
            .where(AppSetting.key == KEY_ACCESS_TOKEN)
            .with_for_update()
        )).scalar_one_or_none()
        if access_row is None:
            raise BlackSeaApiError(f"app_settings['{KEY_ACCESS_TOKEN}'] is missing")

        if access_row.value != stale_token:
            # кто-то уже обменял, пока мы ждали лок — берём его результат,
            # refresh_token в этой ветке не читается и не трогается
            fresh_access = access_row.value
        else:
            refresh_row = (await db.execute(
                select(AppSetting)
                .where(AppSetting.key == KEY_REFRESH_TOKEN)
                .with_for_update()
            )).scalar_one_or_none()
            if refresh_row is None:
                raise BlackSeaApiError(f"app_settings['{KEY_REFRESH_TOKEN}'] is missing")

            fresh_access, fresh_refresh = await refresh_blacksea_token(refresh_row.value)
            access_row.value  = fresh_access
            refresh_row.value = fresh_refresh
            logger.info("[BLACKSEA] access token refreshed")

    await db.commit()
    return fresh_access
```

- [ ] 4. Вставить ветку 401 в `_verify_sale` — между первым `fetch_blacksea_sale` и проверкой `status != 200`:

```python
    status, body = await fetch_blacksea_sale(sale_id, access_token)

    if status == 401:
        # Бюджет «один refresh + один повтор» обеспечен структурно: прямой код без
        # цикла. Второй 401 сюда не возвращается — уходит в BlackSeaApiError ниже.
        access_token = await _obtain_fresh_access_token(db, access_token)
        status, body = await fetch_blacksea_sale(sale_id, access_token)

    if status != 200:
        raise BlackSeaApiError(f"sales API returned HTTP {status}")
```

- [ ] 5. Прогнать тесты BlackSea и весь набор:

```powershell
python -m pytest tests/test_blacksea.py -v
python -m pytest tests/ -q
```

- [ ] 6. Коммит:

```bash
git add server/blacksea.py server/tests/test_blacksea.py
git commit -m "feat(blacksea): refresh access_token под FOR UPDATE — один обмен и один повтор на вебхук"
```

---

## Задача 8 — Деплой и ручная проверка перед боевым включением (кода не пишем)

**Файлы:** изменений в репозитории нет. Все значения берутся из `MEMORY/reference_secrets.md` (раздел BlackSea, создан в сессии #134) — **сами значения не копировать ни в план, ни в спеку, ни в коммиты**.

**Интерфейсы:**
- Consumes: `BLACKSEA_CLIENT_ID` / `BLACKSEA_CLIENT_SECRET` / `BLACKSEA_PRODUCT_ID` (Задача 2), ключи `blacksea_access_token` / `blacksea_refresh_token` в `app_settings` (Задача 7), миграция `b1a2c3k4s5e6` (Задача 1).
- Produces: работающий боевой контур.

**Шаги:**

- [ ] 1. Прогнать весь серверный набор тестов начисто перед деплоем:

```powershell
Set-Location C:\BattleBot\server
$env:ADMIN_TOKEN="dev-admin-token"; $env:JWT_SECRET_KEY="dev-jwt-secret"
python -m pytest tests/ -q
```

- [ ] 2. Влить ветку в `main` и запушить (по регламенту проекта — только после явного «да» владельца):

```bash
git checkout main && git merge --no-ff feat/blacksea-payment
git push origin main
```

- [ ] 3. Прописать три env vars в systemd на GCP (значения из `reference_secrets.md`), рядом с `NOWPAYMENTS_*`:

```bash
sudo systemctl edit totalhunter      # добавить BLACKSEA_CLIENT_ID/SECRET/PRODUCT_ID в [Service] Environment=
sudo systemctl daemon-reload
```

- [ ] 4. Подтянуть код и применить миграцию на сервере:

```bash
cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main
cd /opt/totalhunter/server && sudo -E python -m alembic upgrade head
sudo systemctl restart totalhunter
sudo systemctl status totalhunter          # active (running), без ValueError о BLACKSEA_*
```

Если сервис не поднялся с `ValueError: BLACKSEA_... is not set` — это ожидаемое поведение стартовой валидации, а не баг: вернуться к шагу 3.

- [ ] 5. Засеять начальную пару токенов в `app_settings` (значения — из `reference_secrets.md`; в env vars их класть НЕЛЬЗЯ, они ротируются при refresh и после рестарта сервиса читались бы протухшими):

```sql
INSERT INTO app_settings (key, value) VALUES
  ('blacksea_access_token',  '<ACCESS_TOKEN>'),
  ('blacksea_refresh_token', '<REFRESH_TOKEN>')
ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value;
```

- [ ] 6. Прописать вебхук в BlackSea: Налаштування → Додатково → «Вебхук URL» = `https://api.total-hunter.com/web/payment/blacksea/webhook` → «Оновити налаштування» → **перезагрузить страницу и убедиться, что значение сохранилось** (поле показывает старое значение до полной перезагрузки — известная особенность их UI, не баг).

- [ ] 7. Ручная проверка конкурентности против PostgreSQL — то, что SQLite-тесты доказать не могут (спека, «Честная граница тестовой среды»). На staging или локальном Postgres с `DATABASE_URL` на него: отправить два одинаковых вебхука одновременно и убедиться, что в `blacksea_sales` одна строка, а у покупателя ровно +5000:

```bash
URL=https://<staging-host>/web/payment/blacksea/webhook
BODY='sale_id=<REAL_SALE_ID>&email=<BUYER>&price=41000&product_id=<PRODUCT_ID>&quantity=1'
curl -s -X POST "$URL" -d "$BODY" & curl -s -X POST "$URL" -d "$BODY" & wait
psql -c "SELECT count(*) FROM blacksea_sales WHERE sale_id='<REAL_SALE_ID>';"   # → 1
```

- [ ] 8. Боевая контрольная покупка владельцем на минимальную сумму: проверить в логах `[BLACKSEA] sale ... credited 5000`, в админке `/admin/purchases` — строку с пакетом `ultra`, в боте — обновление баланса без перезапуска (long-poll `vault.py`).

- [ ] 9. Обновить `STATE.md` (модуль BlackSea, статус, версия) и `docs/gemini_buffer.md` по регламенту хангофа.

---

## SPEC→PLAN Consistency Check

Обязательный gate из `docs/РАБОТА-С-ДОКУМЕНТАМИ.md` (Стадия 9): каждый инвариант спеки должен иметь задачу и тест по имени.

| Требование спеки | Задача | Тест |
|---|---|---|
| Таблица `blacksea_sales`, `UNIQUE(sale_id)`, строка только при успешном начислении | 1, 6 | `test_blacksea_sale_sale_id_is_unique`, `test_webhook_happy_path_credits_buyer` |
| Миграция alembic, head сверен | 1 | шаг «`alembic heads` → одна голова» |
| Form-парсинг (не JSON), `price_kopecks = int(price)` | 2 | `test_webhook_non_numeric_price_returns_400` |
| Валидация до БД и сети: нет поля / `sale_id` > 50 / `price` не int → 400 | 2 | `test_webhook_missing_required_field_returns_400`, `test_webhook_oversized_sale_id_returns_400` |
| Стартовая валидация трёх env vars | 2 | `test_module_refuses_to_import_without_env_var` |
| Шаг 2: предварительный SELECT по `sale_id` → 200 no-op без вызова API | 5 | `test_webhook_duplicate_sale_id_is_noop_without_api_call` |
| Шаг 3: чужой `product_id` → 200 no-op | 5 | `test_webhook_foreign_product_is_noop_without_api_call` |
| Шаг 4: вызов `/api/v2/sales/{id}`, URL-encode `sale_id` | 3 | `test_fetch_sale_url_encodes_sale_id_and_passes_token` |
| Шаг 4: `paid`/`chargedback`/`refunded` | 4, 5 | `test_sale_matches_webhook_rejects_mismatch`, `test_webhook_unpaid_sale_does_not_credit` |
| Шаг 4: сверка email/price/product_id API-ответа с телом; `price_kopecks == sale.price` (оба int) | 4, 5 | `test_sale_matches_webhook_rejects_string_price_even_if_digits_equal`, `test_webhook_forged_email_credits_nobody` |
| Шаг 4: `sale.id` (если есть) обязан совпасть с запрошенным | 4 | `test_sale_matches_webhook_rejects_mismatch[sale_id_mismatch]`, `test_sale_matches_webhook_accepts_response_without_id_field` |
| Шаг 4: fail-closed на отсутствующее/`null`/не тот тип | 4, 5 | `test_sale_matches_webhook_is_fail_closed_on_broken_fields`, `test_webhook_malformed_api_field_fails_closed` |
| Шаг 4: сетевая ошибка/невалидный ответ → 200, лог ERROR, без начисления | 5 | `test_webhook_network_error_does_not_credit`, `test_webhook_api_non_200_does_not_credit` |
| Шаг 4: `test`-поле не используется | 2-7 | ни один тест и ни одна строка кода его не читает (в `_form()` оно присутствует и игнорируется) |
| Шаг 4: `quantity != "1"` → алерт, без начисления; отсутствие = `"1"` + WARNING | 5, 6 | `test_webhook_quantity_not_one_goes_to_manual_review`, `test_webhook_quantity_lookalikes_are_not_one`, `test_webhook_without_quantity_field_credits_single_package` |
| Шаг 5: поиск `User` по `sale.email` c `with_for_update()`; не найден → алерт | 5 | `test_webhook_unknown_email_alerts_and_does_not_credit`, `test_webhook_forged_email_credits_nobody` |
| Шаг 6: `begin_nested()` + `except IntegrityError` снаружи | 6 | `test_webhook_concurrent_duplicate_credits_exactly_once`, `test_webhook_redelivery_credits_exactly_once` |
| Шаг 7: `Transaction` с `user_id`/`usd_amount`/`package`/`meta` | 6 | `test_webhook_happy_path_credits_buyer` |
| Шаг 8: реферальный каскад | 6 | `test_webhook_happy_path_applies_referral_cascade` |
| Шаг 9: один `commit()`, затем `notify_balance_changed` + `send_purchase_alert` | 6 | `test_webhook_notifies_bot_and_owner_only_after_commit` |
| Шаг 10: 200 на всё, кроме невалидного тела | 2-7 | каждый тест ветки отказа проверяет `status_code == 200` |
| Токены: статичные в env, изменяемые в `app_settings` | 2, 7, 8 | `test_401_triggers_single_refresh_and_single_retry` (запись пары в `app_settings`) |
| Refresh под `with_for_update()`, перечитывание значения под локом | 7 | `test_obtain_fresh_token_reuses_value_rotated_by_someone_else` |
| Сетевая ошибка именно refresh-вызова → токены не изменены, 200, без начисления | 7 | `test_refresh_network_error_leaves_tokens_untouched`, `test_refresh_api_error_leaves_tokens_untouched` |
| Бюджет «1 refresh + 1 повтор» | 7 | `test_second_401_after_refresh_stops_without_second_refresh` |
| Конкурентные 401 | 7 | `test_concurrent_401_webhooks_both_credit_and_leave_valid_tokens` (+ честная граница в докстринге) |
| Честная граница SQLite, ручной прогон против Postgres | 6, 7, 8 | шаг 7 Задачи 8 |

**Расхождения плана со спекой — зафиксированы явно, не молча:**

1. **Бюджет refresh реализован прямым кодом без цикла, а не булевым флагом** («флаг «refresh уже выполнялся» в области видимости обработчика» в спеке). Контракт тот же и обеспечен строже: второго обмена нет структурно, флаг забыть или обойти нечем.
2. **Тест конкурентного 401 не утверждает «refresh вызван ровно один раз»** — на SQLite без `FOR UPDATE` это недоказуемо, и спека сама честно об этом пишет в разделе про границу тестовой среды. Алгоритмическая часть (перечитывание значения под локом → обмена нет) вынесена в детерминированный `test_obtain_fresh_token_reuses_value_rotated_by_someone_else`, реальная однократность — ручной прогон против PostgreSQL (Задача 8, шаг 7).
3. **`send_manual_review_alert` — новая функция в `tg_channel.py`.** Спека требует алерт (решение п.2 и ветка `quantity`), но не называет механизм; сигнатура и текст введены планом и подлежат подтверждению владельцем.
4. **Проверка `user.is_banned` не реализуется** — в спеке её нет, см. раздел «Осознанно НЕ в объёме»; вынесено владельцу как отдельный вопрос.
5. **`str(PACKAGES["ultra"]["usd"])` даёт `"10.0"`, а не `"10.00"`** — см. раздел «Известная неточность прозы спеки»; код следует спеке буквально.
