"""
Регрессия лавин запросов на сервер (владелец 2026-09-28, журнал nginx за 27.09):
1. SSE РОЙ переподключался мгновенно при 502/закрытом потоке — сотни запросов на каждый рестарт сервера;
2. long-poll баланса крутился без паузы, когда сервер не отвечал;
3. heartbeat шёл на каждый старт движка — до 687 запросов в минуту.
"""
import time
from unittest.mock import MagicMock, patch

import pytest

import auth
from roy import roy_client


# ── 1. SSE РОЙ ────────────────────────────────────────────────────────────────

def _response(status, lines=()):
    r = MagicMock()
    r.status_code = status
    r.iter_lines.return_value = iter(lines)
    r.__enter__.return_value = r
    r.__exit__.return_value = False
    return r


def _run_sse(responses):
    """Гоняет listen_status_stream по списку ответов (Exception = обрыв сети), возвращает
    (события, паузы)."""
    events, sleeps = [], []
    it = iter(responses)
    remaining = [len(responses)]

    def fake_get(*a, **kw):
        remaining[0] -= 1
        item = next(it)
        if isinstance(item, Exception):
            raise item
        return item

    roy_client.listen_status_stream(
        "https://x/roy/status-stream", events.append,
        keep_running=lambda: remaining[0] > 0,
        get=fake_get, sleep=sleeps.append,
    )
    return events, sleeps


def test_sse_pauses_after_502_before_reconnect():
    _, sleeps = _run_sse([_response(502), _response(502)])
    assert sleeps == [roy_client.SSE_RECONNECT_PAUSE_SEC] * 2
    assert roy_client.SSE_RECONNECT_PAUSE_SEC == 5


def test_sse_pauses_after_stream_closed_and_after_network_error():
    _, sleeps = _run_sse([_response(200, ["data: {}"]), ConnectionError("down")])
    assert sleeps == [5, 5]


def test_sse_delivers_data_lines_without_delay_while_stream_is_open():
    events, sleeps = _run_sse([_response(200, [
        'data: {"pool_updated": true}', ": keepalive", "", "data: not-json",
        'data: {"k": 1}',
    ])])
    assert events == [{"pool_updated": True}, {"k": 1}]
    assert sleeps == [5]   # только после закрытия потока, не между событиями


def test_sse_ignores_body_of_error_response():
    events, _ = _run_sse([_response(502, ['data: {"pool_updated": true}'])])
    assert events == []


# ── 2. Long-poll баланса ─────────────────────────────────────────────────────

def test_balance_step_pauses_when_server_gave_no_answer():
    sleeps, credits = [], []
    with patch.object(auth, "get_balance_update", return_value=None):
        auth.balance_sync_step(credits.append, sleep=sleeps.append)
    assert sleeps == [auth.BALANCE_RETRY_PAUSE_SEC]
    assert auth.BALANCE_RETRY_PAUSE_SEC == 5
    assert credits == []


def test_balance_step_reports_credits_and_reconnects_immediately():
    sleeps, credits = [], []
    with patch.object(auth, "get_balance_update", return_value={"credits": 42}):
        auth.balance_sync_step(credits.append, sleep=sleeps.append)
    assert credits == [42]
    assert sleeps == []   # штатный long-poll: следующий запрос сразу, как раньше


# ── 3. Heartbeat ─────────────────────────────────────────────────────────────

@pytest.fixture
def hb_session():
    with patch.object(auth, "_session") as s, patch.object(auth, "_last_heartbeat_sent", None):
        s.post.return_value = MagicMock(status_code=200)
        yield s


def test_heartbeat_burst_sends_only_once(hb_session):
    for _ in range(50):   # 50 стартов движка подряд
        auth.heartbeat()
    assert hb_session.post.call_count == 1
    assert auth.HEARTBEAT_MIN_INTERVAL_SEC == 60


def test_heartbeat_normal_two_minute_cadence_is_unchanged(hb_session):
    now = [1000.0]
    with patch.object(auth.time, "monotonic", side_effect=lambda: now[0]):
        auth.heartbeat()
        now[0] += 120   # штатный цикл движка — раз в 2 минуты
        auth.heartbeat()
        now[0] += 60    # ровно граница — ещё разрешено
        auth.heartbeat()
        now[0] += 59
        auth.heartbeat()
    assert hb_session.post.call_count == 3


def test_heartbeat_failure_also_counts_so_offline_bot_does_not_hammer(hb_session):
    hb_session.post.side_effect = Exception("down")
    auth.heartbeat()
    auth.heartbeat()
    assert hb_session.post.call_count == 1
