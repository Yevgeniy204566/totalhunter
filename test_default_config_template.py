"""Шаблон настроек для НОВЫХ установок (владелец 2026-11-14): раньше в сборку шёл рабочий gui_config.json
владельца, и новые игроки получали его королевство/клан («Феникс», потом ELDORADO 229), его язык и пары
кланов. Теперь шаблон — отдельный gui_config.default.json только с техническими значениями.
Существующих игроков это не касается: их gui_config.json рядом с exe обновление не трогает."""
import json
import os

ROOT = os.path.dirname(os.path.abspath(__file__))
PERSONAL_KEYS = {
    "chest_kingdom", "chest_clan", "chest_saved_pairs", "chest_click_pause", "chest_auto_send",
    "chest_full_lang_ocr", "ancient_full_lang_ocr", "roy_kingdom", "roy_enabled", "lang", "theme",
    "last_calibration_profile", "scout_queue_limit", "found_sound",
}


def _template():
    with open(os.path.join(ROOT, "gui_config.default.json"), encoding="utf-8") as f:
        return json.load(f)


def test_template_has_no_personal_settings():
    assert PERSONAL_KEYS.isdisjoint(_template().keys())


def test_template_keeps_the_technical_defaults():
    t = _template()
    for key in ("step", "conf", "bot_speed", "max_inland_steps", "ocean_land_ratio", "min_water_px",
                "diagonal_blind_coeff", "nav_footprint_ttl", "return_delta_px", "smooth_alpha"):
        assert key in t, key


def test_build_spec_bundles_the_clean_template_not_the_working_config():
    spec = open(os.path.join(ROOT, "build.spec"), encoding="utf-8").read()
    assert "('gui_config.default.json', '.')" in spec
    assert "('gui_config.json', '.')" not in spec


def test_first_run_copies_the_clean_template():
    src = open(os.path.join(ROOT, "main.py"), encoding="utf-8").read()
    assert "'gui_config.default.json')" in src and "_bundled_config" in src
