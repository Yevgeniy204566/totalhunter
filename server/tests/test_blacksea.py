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
