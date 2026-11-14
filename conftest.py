import sys

import pytest


@pytest.fixture(autouse=True)
def _reset_heartbeat_throttle():
    # heartbeat() помнит время последней отправки (не чаще раза в минуту) — без сброса
    # вызов в одном тесте молча глушит heartbeat в следующем.
    auth = sys.modules.get("auth")
    if auth is not None:
        auth._last_heartbeat_sent = None
    yield


@pytest.fixture(autouse=True)
def _chest_log_isolated(tmp_path, monkeypatch):
    # Лог сбора сундуков (chest_log) в тестах не пишет в logs/ проекта и НИКОГДА не шлёт
    # события на боевой сервер (/log_error) — тесты сундуков запускают collect_chests напрямую.
    import chest_log
    monkeypatch.setattr(chest_log, "_default_log_dir", lambda: str(tmp_path / "chest_logs"))
    monkeypatch.setattr(chest_log, "_send_to_server", lambda text: None)
    chest_log._state["file"] = None
    yield
