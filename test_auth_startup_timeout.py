"""
TDD: новые пользователи с медленным/дальним подключением (напр. Африка → GCP us-central1)
получают ConnectTimeoutError на старте бота — timeout=5 сек не хватает на первый check_auth/
generate_link_code. Владелец подтвердил: поднять до 15 сек для стартовых вызовов.
"""
from unittest.mock import MagicMock, patch

import auth


def _fake_response(status_code=200, json_data=None):
    r = MagicMock(status_code=status_code)
    r.json.return_value = json_data or {}
    return r


def test_check_license_uses_15_second_timeout():
    with patch("auth.requests.post", return_value=_fake_response()) as mock_post:
        auth.check_license()
    assert mock_post.call_args.kwargs["timeout"] == 15


def test_generate_link_code_uses_15_second_timeout():
    with patch("auth.requests.post", return_value=_fake_response(json_data={"code": "1"})) as mock_post:
        auth.generate_link_code()
    assert mock_post.call_args.kwargs["timeout"] == 15


def test_activate_referral_uses_15_second_timeout():
    with patch("auth.requests.post", return_value=_fake_response()) as mock_post:
        auth.activate_referral("CODE")
    assert mock_post.call_args.kwargs["timeout"] == 15


def test_get_free_trial_uses_15_second_timeout():
    with patch("auth.requests.post", return_value=_fake_response()) as mock_post:
        auth.get_free_trial()
    assert mock_post.call_args.kwargs["timeout"] == 15
