"""
TDD: кнопка 💾 в Склепах показывает результат сохранения (владелец 2026-09-26):
✓ при успехе, ✗ при ошибке записи, через 1 с снова 💾. Раньше сохраняла молча,
а ошибка записи профиля тихо проглатывалась.
"""
import json
from unittest.mock import MagicMock

import main as _main_module

App = _main_module.TotalHunterApp


def _fake_app(save_ok):
    app = MagicMock()
    app._save_crypt_settings.return_value = save_ok
    return app


def test_success_shows_check_then_restores_floppy():
    app = _fake_app(True)
    App._save_crypt_settings_all(app)

    app.crypt_save_settings_btn.configure.assert_called_with(text="✓")
    delay, restore = app.after.call_args[0]
    assert delay == 1000
    restore()
    app.crypt_save_settings_btn.configure.assert_called_with(text="💾")


def test_failure_shows_cross_then_restores_floppy():
    app = _fake_app(False)
    App._save_crypt_settings_all(app)

    app.crypt_save_settings_btn.configure.assert_called_with(text="✗")
    delay, restore = app.after.call_args[0]
    assert delay == 1000
    restore()
    app.crypt_save_settings_btn.configure.assert_called_with(text="💾")


def test_save_crypt_settings_returns_false_when_profile_unwritable(tmp_path):
    app = MagicMock()
    app._cal_profile_var.get.return_value = "Client"
    app._PROFILES = {"Client": str(tmp_path / "no_such_dir" / "profile.json")}
    assert App._save_crypt_settings(app) is False


def test_save_crypt_settings_returns_true_and_keeps_calibration(tmp_path, monkeypatch):
    path = tmp_path / "profile.json"
    path.write_text(json.dumps({"point_a": [90, 925], "point_b": [1149, 88]}))
    app = MagicMock()
    app._cal_profile_var.get.return_value = "Client"
    app._PROFILES = {"Client": str(path)}
    app._crypt_vars = {}
    app._crypt_autostop_count = None
    app._crypt_autostop_seconds = None
    app._crypt_periodic_reset_min = None
    app._swing1_var.get.return_value = 0
    app._swing2_var.get.return_value = 0
    for name in ("crypt_conf_slider", "crypt_accel_slider", "crypt_break_slider",
                 "crypt_scroll_slider", "crypt_march_slider", "crypt_speed_slider",
                 "scroll_clicks_slider", "conf_slider"):
        getattr(app, name).get.return_value = 1
    monkeypatch.setattr(_main_module, "exchange_cfg_from_values", lambda *a: {})
    monkeypatch.setattr(_main_module, "scout_settings_for_profile", lambda *a: {})

    assert App._save_crypt_settings(app) is True
    saved = json.loads(path.read_text())
    assert saved["point_a"] == [90, 925]
    assert saved["point_b"] == [1149, 88]
    assert "crypt_conf" in saved
