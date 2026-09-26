"""Тесты clan_roster_reader.py (отдельный скрипт «Фаза 0 ERP», бот его не импортирует).

Прежний файл тестов проверял API, которого в модуле никогда не было (clean_might,
detect_panel_bbox, build_roster_from_rows, … — модуль в итоге написан иначе), — 28
тестов падали на AttributeError. Здесь — тесты реально существующих функций."""
import numpy as np
import pytest

import clan_roster_reader as cr


@pytest.mark.parametrize("raw, expected", [
    ("был в сети 3 ч. назад\nOlla (K:229 X:478 Y:516)", "Olla"),   # статус предыдущей карточки
    ("|Jack K:229 X:1 Y:2", "Jack"),                                # артефакт рамки + координаты без скобки
    ("в сети\n  VikTor ", "VikTor"),
    ("Rock 12", "Rock"),                                            # хвост-цифры
    ("[K229] Galushka", "Galushka"),                                # тег королевства
    ("", ""),
])
def test_clean_name(raw, expected):
    assert cr._clean_name(raw) == expected


def test_measure_scroll_shift_identical_frames_is_zero():
    panel = np.random.RandomState(0).randint(0, 255, (cr.PANEL_HEIGHT, cr.PANEL_WIDTH, 3), dtype=np.uint8)
    assert cr.measure_scroll_shift(panel, panel) == 0


def test_measure_scroll_shift_tiny_frames_is_zero():
    tiny = np.zeros((5, 5, 3), np.uint8)
    assert cr.measure_scroll_shift(tiny, tiny) == 0


def test_ocr_might_empty_roi_is_none():
    assert cr.ocr_might(np.zeros((0, 0, 3), np.uint8)) is None


def test_ocr_name_empty_roi_is_empty():
    assert cr.ocr_name(np.zeros((0, 0, 3), np.uint8)) == ''
