"""
test_profile_switch_regression.py — калибровка игрока НЕ меняется и НЕ теряется (владелец 2026-09-27).

Живой случай 26.09 (v2.1.0): выпадающий список профиля на вкладке «Калибровка» не загружал
выбранный профиль — название менялось, а в памяти/на экране оставалась калибровка прежнего.
«СОХРАНИТЬ ПРОФИЛЬ» записывал её поверх выбранного: калибровка Клиента/Браузера 1 «слетела».

Инвариант: имя выбранного профиля и данные профиля в памяти ВСЕГДА соответствуют друг другу.
Плюс совместимость: профиль прошлой версии читается один в один, сохранение не теряет полей.
"""
import json
import os

import customtkinter as ctk
import keyboard
import pytest

import main
from coord_manager import CoordinateManager, coord_manager

CLIENT = {
    "point_a": [120, 1248], "point_b": [1531, 107],
    "scale_x": 1.3324, "scale_y": 1.3632,
    "dialog_offset_x": 0, "dialog_offset_y": 0, "scroll_clicks": 3,
    "ui_offsets": {"wt_icon": [0, 10], "carter": [0, -10], "crypt_open": [0, -5],
                   "crypt_select": [0, -2], "top_accel": [0, -13], "march_accel": [0, 0],
                   "arena_reset": [0, 0], "chest_sender": [0, 0], "chest_type": [-1, -2],
                   "chest_collect": [0, 0]},
    "crypt_selected": ["Epic_2", "Epic_3"], "crypt_conf": 0.2,
    "crypt_max_march_sec": 120, "step": 16,
}
BROWSER1 = {
    "point_a": [119, 1240], "point_b": [1530, 184],
    "scale_x": 1.3333, "scale_y": 1.4104,
    "dialog_offset_x": 0, "dialog_offset_y": 50, "scroll_clicks": 129,
    "ui_offsets": {"wt_icon": [0, 0], "carter": [0, -5], "crypt_open": [0, -5],
                   "crypt_select": [0, 3], "top_accel": [0, 65], "march_accel": [0, 60],
                   "arena_reset": [0, 0], "chest_sender": [0, 0], "chest_type": [-1, -2],
                   "chest_collect": [0, 0]},
    "crypt_selected": ["Ordinary_1"], "crypt_conf": 0.5,
    "crypt_max_march_sec": 300, "step": 18,
}


def _write(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


@pytest.fixture(scope="module")
def _app_once(tmp_path_factory):
    """Одно окно бота на весь файл: второе TotalHunterApp в том же процессе после
    destroy() натыкается на остатки Tk первого (картинки/after-таймеры)."""
    mp = pytest.MonkeyPatch()
    # Без сети и фоновых таймеров: тест про профили, не про сервер
    for name in ("update_license_info", "_start_balance_sync", "_tick_trade_routes",
                 "_tick_scout_queue", "_tick_roy_drain"):
        mp.setattr(main.TotalHunterApp, name, lambda self: None)
    mp.setattr(main.messagebox, "showinfo", lambda *a, **k: None)
    mp.setattr(main.messagebox, "showerror", lambda *a, **k: None)
    mp.setattr(main, "GUI_CONFIG_PATH", str(tmp_path_factory.mktemp("cfg") / "gui_config.json"))
    a = main.TotalHunterApp()
    a.withdraw()
    a.update()
    yield a
    try:
        keyboard.unhook_all()
    except Exception:
        pass
    a.destroy()
    mp.undo()


@pytest.fixture
def app(_app_once, tmp_path, monkeypatch):
    a = _app_once
    monkeypatch.setattr(main, "GUI_CONFIG_PATH", str(tmp_path / "gui_config.json"))
    client, browser = tmp_path / "profile_client.json", tmp_path / "profile_chrome.json"
    _write(client, CLIENT)
    _write(browser, BROWSER1)
    a._PROFILES["Client"] = str(client)      # тот же dict, что PROFILES вкладки Калибровки
    a._PROFILES["Browser 1"] = str(browser)
    yield a, client, browser


def _assert_loaded(a, prof):
    assert list(coord_manager._point_a) == prof["point_a"]
    assert list(coord_manager._point_b) == prof["point_b"]
    assert coord_manager.dialog_offset_y == prof["dialog_offset_y"]
    assert coord_manager.scroll_clicks == prof["scroll_clicks"]
    for k, v in prof["ui_offsets"].items():
        assert list(coord_manager.ui_offsets[k])[:2] == v, k
    # UI показывает ту же калибровку и настройки, что в памяти
    assert a._dialog_offset_y_var.get() == prof["dialog_offset_y"]
    assert int(a.crypt_march_slider.get()) == prof["crypt_max_march_sec"]
    assert int(a.nav_step_slider.get()) == prof["step"]
    assert sorted(k for k, v in a._crypt_vars.items() if v.get()) == sorted(prof["crypt_selected"])


def test_switching_profile_on_calibration_tab_loads_it_and_save_never_touches_the_other(app):
    a, client, browser = app
    client_bytes_before = client.read_bytes()

    # 1. Загрузить «Клиент» (через тот же список на вкладке Калибровка)
    a._cal_profile_menu._dropdown_callback("Client")
    a.update()
    _assert_loaded(a, CLIENT)

    # 2-3. Переключить на «Браузер 1» — в память и UI загружается весь «Браузер 1»
    a._cal_profile_menu._dropdown_callback("Browser 1")
    a.update()
    assert a._cal_profile_var.get() == "Browser 1"
    _assert_loaded(a, BROWSER1)

    # 4. Сохранить профиль (кнопка «СОХРАНИТЬ ПРОФИЛЬ» вкладки Калибровка)
    a._cal_save_profile()

    # 5. «Клиент» не изменился ни на байт; «Браузер 1» сохранил свои значения
    assert client.read_bytes() == client_bytes_before
    saved = json.loads(browser.read_text(encoding="utf-8"))
    for k in ("point_a", "point_b", "dialog_offset_y", "scroll_clicks"):
        assert saved[k] == BROWSER1[k], k
    for k, v in BROWSER1["ui_offsets"].items():
        assert saved["ui_offsets"][k][:2] == v, k
    assert saved["crypt_max_march_sec"] == BROWSER1["crypt_max_march_sec"]
    assert saved["step"] == BROWSER1["step"]
    assert sorted(saved["crypt_selected"]) == sorted(BROWSER1["crypt_selected"])


# ── Совместимость между версиями (чистые, без окна) ──────────────────────────

def test_previous_version_profile_loads_identically(tmp_path):
    p = tmp_path / "profile_client.json"
    _write(p, CLIENT)
    cm = CoordinateManager()
    cm.load(str(p))
    assert list(cm._point_a) == CLIENT["point_a"] and list(cm._point_b) == CLIENT["point_b"]
    assert cm.dialog_offset_y == CLIENT["dialog_offset_y"]
    for k, v in CLIENT["ui_offsets"].items():
        assert list(cm.ui_offsets[k])[:2] == v


def test_saving_calibration_keeps_every_other_field_of_the_profile(tmp_path):
    """Раньше coord_manager.save перезаписывал файл целиком — настройки склепов/бирж и
    неизвестные этой версии ключи тюнинга пропадали."""
    p = tmp_path / "profile_client.json"
    data = dict(CLIENT, crypt_selected=["Epic_2"], scout_settings={"depth": 50})
    data["ui_offsets"] = dict(CLIENT["ui_offsets"], future_target=[3, 4])
    _write(p, data)
    cm = CoordinateManager()
    cm.load(str(p))
    cm.save(str(p))
    saved = json.loads(p.read_text(encoding="utf-8"))
    for k in data:
        assert k in saved, k
    assert saved["crypt_selected"] == ["Epic_2"]
    assert saved["scout_settings"] == {"depth": 50}
    assert saved["ui_offsets"]["future_target"] == [3, 4]


def test_interrupted_write_leaves_old_profile_intact(tmp_path, monkeypatch):
    import safe_json
    p = tmp_path / "profile_client.json"
    _write(p, CLIENT)
    before = p.read_bytes()

    def boom(*a, **k):
        raise OSError("выключили свет посреди записи")
    monkeypatch.setattr(safe_json.json, "dump", boom)
    with pytest.raises(OSError):
        safe_json.atomic_write_json(str(p), {"point_a": [0, 0]})
    assert p.read_bytes() == before
    assert not [f for f in os.listdir(tmp_path) if f.startswith(".tmp_")]


# ── Кириллица в настройках (v2.1.1: «Феникс» портился в «Р¤РµРЅРёРєСЃ») ────────

def test_written_settings_are_ascii_and_survive_cp1251_read(tmp_path):
    import safe_json
    p = tmp_path / "gui_config.json"
    safe_json.atomic_write_json(str(p), {"chest_clan": "Феникс"})
    assert p.read_bytes().isascii()                       # прежний формат \u0424…
    with open(p, encoding="cp1251") as f:                 # как читают места без encoding
        assert json.load(f)["chest_clan"] == "Феникс"


def test_corrupted_clan_names_are_repaired(tmp_path):
    import safe_json
    once = "Феникс".encode("utf-8").decode("cp1251")
    twice = once.encode("utf-8").decode("cp1251")
    assert safe_json.repair_mojibake(twice) == "Феникс"
    assert safe_json.repair_mojibake("Феникс") == "Феникс"   # нормальный текст не трогаем
    assert safe_json.repair_mojibake("ELDORADO") == "ELDORADO"
    p = tmp_path / "gui_config.json"
    p.write_text(json.dumps({"chest_saved_pairs": [{"kingdom": "229", "clan": twice}],
                             "chest_clan": "ELDORADO"}, ensure_ascii=False), encoding="utf-8")
    assert safe_json.repair_file(str(p)) is True
    data = json.loads(p.read_text(encoding="utf-8"))
    assert data["chest_saved_pairs"][0]["clan"] == "Феникс"
    assert data["chest_clan"] == "ELDORADO"
    assert p.read_bytes().isascii()


def test_unreadable_gui_config_is_never_overwritten_by_sound_button(app):
    """Нечитаемый gui_config: кнопка-динамик и сохранение ключа НЕ записывают файл
    с одним ключом поверх всех настроек игрока."""
    a, _, _ = app
    p = main.GUI_CONFIG_PATH
    with open(p, "wb") as f:
        f.write(b'{"lang": "UK", "chest_clan": "ELDOR')          # оборванный файл
    before = open(p, "rb").read()
    a._toggle_found_sound()
    with pytest.raises(Exception):
        a._save_gui_config_key("theme", "Deep Night")
    assert open(p, "rb").read() == before


def test_gui_config_written_by_v211_is_read_without_loss(tmp_path):
    import safe_json
    p = tmp_path / "gui_config.json"
    p.write_bytes(json.dumps({"chest_clan": "Феникс", "lang": "UK"},
                             ensure_ascii=False).encode("utf-8"))
    assert safe_json.read_json_strict(str(p)) == {"chest_clan": "Феникс", "lang": "UK"}


@pytest.mark.parametrize("name", ["Феникс", "Їжаки", "Сила і Честь", "Єдність", "Ґрунт", "Ёжик"])
def test_repair_restores_any_depth_of_v211_corruption(name):
    import safe_json
    bad, depths = name, 0
    for depth in range(1, 4):
        try:
            bad = bad.encode("utf-8").decode("cp1251")
        except UnicodeDecodeError:
            break   # дальше порча невозможна: байт 0x98 не читается как cp1251 — чтение падает
        depths += 1
        assert safe_json.repair_mojibake(bad) == name, (name, depth)
    assert depths >= 1


@pytest.mark.parametrize("name", ["Лі", "Сі", "Мі", "Дё", "Феникс", "Сила і Честь", "Клан №1",
                                  "ELDORADO", "Café", "النسور", "龙之队", "Р2Д2", ""])
def test_repair_never_touches_normal_names(name):
    import safe_json
    assert safe_json.repair_mojibake(name) == name


def test_repair_on_real_string_from_owner_pc():
    import safe_json
    real = "Р\xa0В¤Р\xa0ВµР\xa0Р…Р\xa0С‘Р\xa0С”РЎРѓ"   # gui_config владельца после 2.1.1
    assert safe_json.repair_mojibake(real) == "Феникс"
