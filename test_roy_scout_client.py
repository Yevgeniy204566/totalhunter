"""Клиент публикации находок Биржи 2.0 (спека ...-roy-publication-design.md, P-06/P-07/P-08)."""
import threading
import time
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from roy.roy_client import RoyClient


def _spy_threads():
    created = []
    def make(*a, **kw):
        t = threading.Thread(*a, **kw)
        created.append(t)
        return t
    return created, SimpleNamespace(Thread=make)


def test_skips_publish_when_kingdom_zero():
    with patch("roy.roy_client.requests.post") as post:
        assert RoyClient("HW").report_scout_find(0, 10, 20) is False
        assert RoyClient("HW").report_scout_find(-3, 10, 20) is False
    post.assert_not_called()


def test_posts_kingdom_x_y_to_scout_find():
    created, fake_threading = _spy_threads()
    resp = MagicMock(); resp.json.return_value = {"success": True}
    with patch("roy.roy_client.threading", fake_threading), \
         patch("roy.roy_client.requests.post", return_value=resp) as post:
        assert RoyClient("HW1").report_scout_find(7, 512, 318) is True
        for t in created:
            t.join(5)
    args, kwargs = post.call_args
    assert args[0].endswith("/roy/scout-find")
    assert kwargs["json"] == {"hwid": "HW1", "kingdom": 7, "x": 512, "y": 318}
    assert kwargs["timeout"] == 5


def test_publish_does_not_block_caller():
    """P-07: медленный сервер не задерживает consumer — метод возвращается сразу."""
    created, fake_threading = _spy_threads()
    release = threading.Event()
    def slow_post(*a, **k):
        release.wait(5)
        return MagicMock()
    with patch("roy.roy_client.threading", fake_threading), \
         patch("roy.roy_client.requests.post", side_effect=slow_post):
        t0 = time.monotonic()
        assert RoyClient("HW").report_scout_find(7, 1, 2) is True
        elapsed = time.monotonic() - t0
        release.set()
        for t in created:
            t.join(5)
    assert elapsed < 0.5


def test_publish_failure_is_swallowed():
    """P-08: сеть (ConnectionError, тот же except Exception что Timeout/битый JSON) не выбрасывает
    исключение из треда."""
    created, fake_threading = _spy_threads()
    with patch("roy.roy_client.threading", fake_threading), \
         patch("roy.roy_client.requests.post", side_effect=ConnectionError("down")), \
         patch("threading.excepthook") as hook:
        assert RoyClient("HW").report_scout_find(7, 1, 2) is True
        for t in created:
            t.join(5)
    hook.assert_not_called()


def test_publish_rejected_response_does_not_raise():
    """P-08: сервер ответил без исключения (HTTP 500 + валидный JSON success=false) — это ДРУГАЯ ветка
    кода (не except, а `if not r.json().get("success")`), её ConnectionError-тест не покрывает."""
    created, fake_threading = _spy_threads()
    resp = MagicMock(status_code=500)
    resp.json.return_value = {"success": False}
    with patch("roy.roy_client.threading", fake_threading), \
         patch("roy.roy_client.requests.post", return_value=resp), \
         patch("threading.excepthook") as hook:
        assert RoyClient("HW").report_scout_find(7, 1, 2) is True
        for t in created:
            t.join(5)
    hook.assert_not_called()
