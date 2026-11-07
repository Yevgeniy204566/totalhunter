"""Переписка админ ↔ игрок через «Обратную связь» (владелец 2026-11-07)."""
import os
import sys

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

ADMIN = {"Authorization": f"Bearer {os.environ['ADMIN_TOKEN']}"}
CLAIMS = {"email": "talker@example.com", "name": "Talker", "sub": "google-sub-talker"}


async def _login(client, claims=CLAIMS):
    with patch("web_routes._verify_google_token", return_value=claims):
        resp = await client.post("/web/auth/google", json={"id_token": "tok"})
    return {"Authorization": f"Bearer {resp.json()['jwt']}"}


async def _user_id(client, hdr):
    return (await client.get("/web/me", headers=hdr)).json()["id"]


@pytest.mark.asyncio
async def test_full_dialog_both_directions():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        me = await _login(c)
        uid = await _user_id(c, me)

        await c.post("/web/feedback", json={"text": "Не хватает функции"}, headers=me)

        # админ видит ветку игрока: одно новое сообщение
        threads = (await c.get("/admin/feedback/threads", headers=ADMIN)).json()
        assert threads[0]["user_id"] == uid and threads[0]["unread"] == 1
        assert (await c.get("/admin/feedback/unread", headers=ADMIN)).json()["count"] == 1

        # открытие ветки отдаёт данные игрока + историю и помечает прочитанным
        det = (await c.get(f"/admin/feedback/thread/{uid}", headers=ADMIN)).json()
        assert det["user"]["email"] == "talker@example.com"
        assert "credits" in det["user"] and "created_at" in det["user"]
        assert [m["sender"] for m in det["messages"]] == ["user"]
        assert (await c.get("/admin/feedback/unread", headers=ADMIN)).json()["count"] == 0

        # ответ админа
        r = await c.post("/admin/feedback/reply", json={"user_id": uid, "text": "Спасибо!"}, headers=ADMIN)
        assert r.status_code == 200

        # у игрока один непрочитанный ответ, в «Входящих» он помечен как новый
        assert (await c.get("/web/feedback/unread", headers=me)).json()["count"] == 1
        thread = (await c.get("/web/feedback/thread", headers=me)).json()
        assert [m["sender"] for m in thread["messages"]] == ["user", "admin"]
        assert thread["messages"][1]["is_new"] is True
        # после открытия — прочитано
        assert (await c.get("/web/feedback/unread", headers=me)).json()["count"] == 0
        again = (await c.get("/web/feedback/thread", headers=me)).json()
        assert again["messages"][1]["is_new"] is False

        # игрок отвечает — переписка идёт в той же ветке
        await c.post("/web/feedback", json={"text": "Ещё вопрос"}, headers=me)
        det = (await c.get(f"/admin/feedback/thread/{uid}", headers=ADMIN)).json()
        assert [m["sender"] for m in det["messages"]] == ["user", "admin", "user"]


@pytest.mark.asyncio
async def test_user_sees_only_own_thread():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        a = await _login(c)
        b = await _login(c, {"email": "other@example.com", "name": "O", "sub": "google-sub-other"})
        uid_a = await _user_id(c, a)
        await c.post("/web/feedback", json={"text": "секрет A"}, headers=a)
        await c.post("/admin/feedback/reply", json={"user_id": uid_a, "text": "ответ A"}, headers=ADMIN)
        thread_b = (await c.get("/web/feedback/thread", headers=b)).json()
        assert thread_b["messages"] == []


@pytest.mark.asyncio
async def test_admin_endpoints_require_admin_and_user_exists():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        me = await _login(c)
        assert (await c.get("/admin/feedback/threads", headers=me)).status_code == 403
        r = await c.post("/admin/feedback/reply", json={"user_id": 99999, "text": "x"}, headers=ADMIN)
        assert r.status_code == 404
        r = await c.post("/admin/feedback/reply",
                         json={"user_id": await _user_id(c, me), "text": "   "}, headers=ADMIN)
        assert r.status_code == 422 or r.status_code == 400


@pytest.mark.asyncio
async def test_export_and_list_do_not_break_with_admin_messages():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        me = await _login(c)
        uid = await _user_id(c, me)
        await c.post("/web/feedback", json={"text": "идея"}, headers=me)
        await c.post("/admin/feedback/reply", json={"user_id": uid, "text": "ответ"}, headers=ADMIN)
        exp = await c.get("/admin/feedback/export", headers=ADMIN)
        assert "идея" in exp.text and "ответ" in exp.text
