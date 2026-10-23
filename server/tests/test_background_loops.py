"""Фоновые циклы сервера (архив сезонов, автоудаление кланов) не умирают от одного исключения (аудит 2026-10-23)."""
import asyncio
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import pytest

import error_alerts


@pytest.mark.asyncio
async def test_loop_survives_an_exception_and_alerts_once(monkeypatch):
    error_alerts._last_sent.clear()
    error_alerts._suppressed.clear()
    sent = []
    monkeypatch.setattr(error_alerts, "_send_debug_sync", sent.append)
    calls = {"n": 0}

    async def tick():
        calls["n"] += 1
        if calls["n"] <= 2:
            raise RuntimeError("tick boom")      # два падения подряд — цикл должен жить дальше

    task = asyncio.create_task(error_alerts.supervised_loop("test.loop", 0.001, tick))
    for _ in range(200):
        if calls["n"] >= 5:
            break
        await asyncio.sleep(0.005)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    assert calls["n"] >= 5                       # после исключений тики продолжаются
    assert len(sent) == 1                        # одинаковая ошибка — одно уведомление (дедуп)
    assert "BG test.loop" in sent[0] and "RuntimeError" in sent[0]


@pytest.mark.asyncio
async def test_cancellation_is_not_swallowed(monkeypatch):
    monkeypatch.setattr(error_alerts, "_send_debug_sync", lambda text: None)

    async def tick():
        await asyncio.sleep(10)

    task = asyncio.create_task(error_alerts.supervised_loop("test.cancel", 0.001, tick))
    await asyncio.sleep(0.02)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task


def test_all_server_background_loops_use_the_supervised_wrapper():
    import chest_history, ancient_retention, inspect
    for mod, names in ((chest_history, ("_archive_loop", "_retention_loop", "_inactive_collector_retention_loop")),
                       (ancient_retention, ("_retention_loop",))):
        for name in names:
            assert "supervised_loop(" in inspect.getsource(getattr(mod, name)), f"{mod.__name__}.{name}"
