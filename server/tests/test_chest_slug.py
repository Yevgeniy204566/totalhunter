"""
test_chest_slug.py — транслитерация названия клана в URL-слаг (входящие; владелец
2026-09-25: клан "Феникс" на кириллице давал ПУСТОЙ слаг в короткой ссылке /c/229/,
"ELDORADO" на латинице работал случайно).
"""
from chest_slug import clan_to_slug, transliterate


def test_cyrillic_clan_name_produces_non_empty_latin_slug():
    """Регрессия: раньше это давало '' (all-Cyrillic вырезался regex'ом целиком)."""
    assert clan_to_slug("Феникс") == "feniks"


def test_latin_clan_name_unaffected():
    assert clan_to_slug("ELDORADO") == "eldorado"


def test_mixed_cyrillic_and_latin_and_digits():
    assert clan_to_slug("BERS 229") == "bers-229"
    assert clan_to_slug("Клан №1") == "klan-1"


def test_ukrainian_letters_transliterated():
    assert transliterate("Королівство") == "korolivstvo"


def test_soft_and_hard_signs_are_dropped_not_left_as_separators():
    """ь/ъ не несут звука — транслитерация в пустую строку, а не в '-'."""
    assert clan_to_slug("Сталь") == "stal"


def test_fully_unsupported_script_falls_back_to_empty_string():
    """Язык вне таблицы транслитерации (например иероглифы) — пустой слаг, вызывающий
    код (chest_dashboard.py) должен в этом случае не показывать short_url вовсе,
    а не давать битую ссылку /c/{kingdom}/ с пустым хвостом."""
    assert clan_to_slug("日本語") == ""


def test_public_url_readable_latin_slug():
    from chest_slug import public_url
    assert public_url("229", "Феникс", None, "raw123") == "https://total-hunter.com/c/229/feniks"
    assert public_url("229", "ELDORADO", None, "raw123") == "https://total-hunter.com/c/229/eldorado"


def test_public_url_prefers_custom_slug_and_falls_back_to_raw():
    from chest_slug import public_url
    assert public_url("229", "Феникс", "myclan", "raw123") == "https://total-hunter.com/c/229/myclan"
    # название без латинской транслитерации -> старая рабочая ссылка, не %D0... и не пустой хвост
    assert public_url("229", "龍", None, "raw123") == "https://total-hunter.com/chests/raw123"
