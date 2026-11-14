"""Ползунок скорости клика (владелец 2026-11-14): раньше 0 = самая быстрая, и игроки, тянувшие
«до упора» ради скорости, получали самую медленную. Теперь как везде: влево — медленно, вправо —
быстро. В gui_config.json по-прежнему лежит ПАУЗА (chest_click_pause) — настройки игроков не
меняются, старое сохранённое значение просто показывается с другой стороны."""
from unittest.mock import MagicMock

import main as _main_module

App = _main_module.TotalHunterApp


def test_slider_position_is_inverse_of_pause():
    assert App._chest_slider_from_pause(0.0) == 1.0     # пауза 0 — быстро — ползунок справа
    assert App._chest_slider_from_pause(1.0) == 0.0     # пауза 1 — медленно — ползунок слева
    assert App._chest_slider_from_pause(0.22) == 0.78


def test_pause_from_slider_roundtrip():
    for pause in (0.0, 0.1, 0.22, 0.5, 1.0):
        assert App._chest_pause_from_slider(App._chest_slider_from_pause(pause)) == pause


def test_out_of_range_saved_value_is_clamped():
    assert App._chest_slider_from_pause(5) == 0.0
    assert App._chest_slider_from_pause(-1) == 1.0


def test_speed_change_saves_pause_not_slider_value():
    app = App.__new__(App)
    app.current_lang = "RU"
    app._save_gui_config_key = MagicMock()
    app.chest_speed_label = MagicMock()
    app._on_chest_speed_change(0.78)    # ползунок почти справа = быстро
    app._save_gui_config_key.assert_called_once_with("chest_click_pause", 0.22)
    assert "0.22" in app.chest_speed_label.configure.call_args.kwargs["text"]


def test_fast_slider_gives_shorter_pause_range_than_slow():
    app = App.__new__(App)
    fast = app._chest_pause_range(App._chest_pause_from_slider(1.0))
    slow = app._chest_pause_range(App._chest_pause_from_slider(0.0))
    assert fast[0] < slow[0]


def test_full_language_switch_stays_on_chest_tab():
    """Владелец 2026-11-14: Full ОСТАЁТСЯ (нужен корейским/арабским/китайским/японским именам).
    Переключатель вкладки «Сундуки» и его сохранение в gui_config не убираем."""
    app = App.__new__(App)
    app.chest_full_lang_var = MagicMock()
    app.chest_full_lang_var.get.return_value = True
    app._save_gui_config_key = MagicMock()
    app._on_chest_full_lang_change()
    app._save_gui_config_key.assert_called_once_with("chest_full_lang_ocr", True)
