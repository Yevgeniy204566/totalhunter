"""
Нейтральный домен (clbx.date, владелец 2026-10-28): ответ данных клана с ?neutral=1 не содержит адреса сервиса
(во вкладке Network он выдавал бы связь с Total Hunter) — вместо public_url отдаётся только путь public_path.
Без параметра ответ прежний (старый сайт и кабинет читают public_url).
"""
import os
import secrets
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

from main import app
from models import ChestCollector, User


def _client():
    return AsyncClient(transport=ASGITransport(app=app), base_url="http://test")


async def _clan(db):
    u = User(hwid=secrets.token_hex(8), ref_code=secrets.token_urlsafe(6), email="o@x.com")
    db.add(u)
    await db.flush()
    c = ChestCollector(kingdom="229", clan="Feniks", user_id=u.id, slug="neutral-1")
    db.add(c)
    await db.commit()
    return c


@pytest.mark.asyncio
@pytest.mark.parametrize("url", ["/api/v1/chests/by/229/feniks", "/api/v1/chests/summary/neutral-1"])
async def test_neutral_response_has_no_service_address(db_session, url):
    await _clan(db_session)
    async with _client() as c:
        plain = await c.get(url)
        neutral = await c.get(url + "?neutral=1")
    assert plain.status_code == neutral.status_code == 200
    assert "total-hunter" in plain.text and plain.json()["public_url"].startswith("https://")   # прежнее поведение
    assert "total-hunter" not in neutral.text.lower()
    body = neutral.json()
    assert "public_url" not in body
    assert body["public_path"] == "/c/229/feniks"
