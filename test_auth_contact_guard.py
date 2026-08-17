"""
TDD: offline-guard — auth.py отслеживает время последнего успешного контакта с сервером.

Брешь: бот, заблокированный файрволом только по своему процессу (игра и остальной
интернет работают нормально), получает requests.exceptions.ConnectionError на каждый
вызов spend_credit()/get_balance_update(), но текущий код это молча проглатывает и
крутит цикл дальше бесплатно. Нужен таймер последнего УСПЕШНОГО ответа сервера —
рабочие циклы (crypt/exchange) остановятся, если он не обновлялся дольше HEARTBEAT_TIMEOUT.

Правило "успешного контакта": сервер ОТВЕТИЛ (любым HTTP-статусом, включая 402 —
это тоже подтверждение, что сеть у процесса работает). Обновление НЕ происходит,
если запрос упал с сетевым исключением до получения ответа.
"""
import time
from unittest.mock import MagicMock, patch

import auth


def test_seconds_since_last_contact_reflects_elapsed_time():
    with patch.object(auth, "last_successful_contact", time.time() - 50):
        elapsed = auth.seconds_since_last_contact()
    assert 49 <= elapsed <= 51


def test_check_license_success_updates_last_contact():
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = {"authorized": True, "credits": 10}
    with patch.object(auth, "last_successful_contact", 0), \
         patch("auth.requests.post", return_value=fake_response):
        auth.check_license()
        assert auth.seconds_since_last_contact() < 1


def test_check_license_network_error_does_not_update_last_contact():
    with patch.object(auth, "last_successful_contact", 0), \
         patch("auth.requests.post", side_effect=auth.requests.exceptions.ConnectionError()), \
         patch.object(auth, "log_error_to_server"):
        auth.check_license()
        assert auth.seconds_since_last_contact() > 1_000_000_000


def test_spend_credit_success_updates_last_contact():
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = {"success": True, "credits": 9}
    with patch.object(auth, "last_successful_contact", 0), \
         patch("auth.requests.post", return_value=fake_response):
        auth.spend_credit()
        assert auth.seconds_since_last_contact() < 1


def test_spend_credit_402_still_updates_last_contact():
    """402 — сервер ответил (баланс пуст), это НЕ обрыв связи, а нормальный ответ."""
    fake_response = MagicMock(status_code=402)
    fake_response.json.return_value = {"detail": {"message": "no credits"}}
    with patch.object(auth, "last_successful_contact", 0), \
         patch("auth.requests.post", return_value=fake_response):
        auth.spend_credit()
        assert auth.seconds_since_last_contact() < 1


def test_spend_credit_connection_error_does_not_update_last_contact():
    with patch.object(auth, "last_successful_contact", 0), \
         patch("auth.requests.post", side_effect=auth.requests.exceptions.ConnectionError()):
        auth.spend_credit()
        assert auth.seconds_since_last_contact() > 1_000_000_000


def test_get_balance_update_200_updates_last_contact():
    fake_response = MagicMock(status_code=200)
    fake_response.json.return_value = {"credits": 5, "ref_credits": 0}
    with patch.object(auth, "last_successful_contact", 0), \
         patch.object(auth, "_session") as mock_session:
        mock_session.get.return_value = fake_response
        auth.get_balance_update()
        assert auth.seconds_since_last_contact() < 1


def test_heartbeat_success_updates_last_contact():
    with patch.object(auth, "last_successful_contact", 0), \
         patch.object(auth, "_session") as mock_session:
        mock_session.post.return_value = MagicMock(status_code=200)
        auth.heartbeat()
        assert auth.seconds_since_last_contact() < 1


def test_heartbeat_network_error_does_not_update_last_contact():
    with patch.object(auth, "last_successful_contact", 0), \
         patch.object(auth, "_session") as mock_session:
        mock_session.post.side_effect = Exception("boom")
        auth.heartbeat()
        assert auth.seconds_since_last_contact() > 1_000_000_000
