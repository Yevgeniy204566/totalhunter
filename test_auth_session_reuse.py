"""
TDD: get_balance_update() и heartbeat() должны переиспользовать один requests.Session,
а не открывать requests.get()/post() напрямую — иначе каждое переподключение
long-poll'а (~раз в 50-58 сек, пока бот открыт) делает новый TLS-handshake,
что лишняя нагрузка на сервер без выгоды для функциональности.
"""
from unittest.mock import MagicMock, patch

import auth


def test_get_balance_update_uses_shared_session_not_bare_requests_get():
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = {"credits": 42, "ref_credits": 1}

    with patch.object(auth, "_session") as mock_session, \
         patch("auth.requests.get") as bare_get:
        mock_session.get.return_value = fake_response

        result = auth.get_balance_update()

        mock_session.get.assert_called_once()
        bare_get.assert_not_called()
        assert result == {"credits": 42, "ref_credits": 1}


def test_heartbeat_uses_shared_session_not_bare_requests_post():
    with patch.object(auth, "_session") as mock_session, \
         patch("auth.requests.post") as bare_post:
        mock_session.post.return_value = MagicMock(status_code=200)

        auth.heartbeat()

        mock_session.post.assert_called_once()
        bare_post.assert_not_called()


def test_shared_session_is_a_single_reused_requests_session_instance():
    import requests
    assert isinstance(auth._session, requests.Session)
