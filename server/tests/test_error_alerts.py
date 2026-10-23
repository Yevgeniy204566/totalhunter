"""Уведомления о 500: секреты вычищаются, повторы гасятся, ответ клиенту не ломается."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest
from httpx import AsyncClient, ASGITransport

import error_alerts
from main import app


def test_scrub_hides_emails_tokens_and_secret_values():
    raw = ("user bob@example.com Authorization: Bearer abc.def.ghi password=hunter2 "
           "key=AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA")
    out = error_alerts.scrub(raw)
    for secret in ("bob@example.com", "abc.def.ghi", "hunter2", "AAAAAAAAAAAAAAAAAAAAAAAA"):
        assert secret not in out


def test_same_error_is_throttled_then_allowed_after_cooldown():
    error_alerts._last_sent.clear(); error_alerts._suppressed.clear()
    assert error_alerts.should_send("k", now=1000.0) is True
    assert error_alerts.should_send("k", now=1100.0) is False
    assert error_alerts._suppressed["k"] == 1
    assert error_alerts.should_send("k", now=1000.0 + error_alerts.COOLDOWN_SEC + 1) is True
    assert error_alerts.should_send("other", now=1100.0) is True


@pytest.mark.asyncio
async def test_unhandled_exception_returns_500_and_sends_alert(monkeypatch):
    error_alerts._last_sent.clear(); error_alerts._suppressed.clear()
    sent = []
    monkeypatch.setattr(error_alerts, "_send_debug_sync", sent.append)

    @app.get("/_boom_test")
    async def boom():
        raise RuntimeError("boom for bob@example.com")

    async with AsyncClient(transport=ASGITransport(app=app, raise_app_exceptions=False), base_url="http://test") as c:
        r = await c.get("/_boom_test?token=SECRETQUERY")
    assert r.status_code == 500
    assert r.json() == {"detail": "Internal Server Error"}
    assert len(sent) == 1
    assert "/_boom_test" in sent[0] and "RuntimeError" in sent[0]
    assert "bob@example.com" not in sent[0] and "SECRETQUERY" not in sent[0]
