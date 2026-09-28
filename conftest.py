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
