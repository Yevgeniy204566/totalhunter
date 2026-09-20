"""
TDD: логика выбора цели в реестре калибровки (PLAN-A Task 2, PC-03/PC-05/PC-06,
docs/superpowers/plans/exchange-scout-calibration-plan-a-*.md, файлы 39-41).

Вынесена в чистые функции модуля (без создания реального Tk-виджета) — в проекте нет теста,
который инстанцирует TotalHunterApp (ANTI-PATTERNS.md: запуск main.py пингует прод-сервер),
поэтому логика выбора/диспетчеризации/видимости тестируется отдельно от самой отрисовки
виджетов (та проверяется вручную владельцем в игре, как PT-13 в плане РОЙ).
"""
from unittest.mock import MagicMock

import main as _main_module
from coord_manager import coord_manager

CALIBRATION_TARGETS = _main_module.CALIBRATION_TARGETS
cal_target_by_id = _main_module.cal_target_by_id
cal_tune_card_visible = _main_module.cal_tune_card_visible
cal_visual_dispatch_for_kind = _main_module.cal_visual_dispatch_for_kind
cal_resolve_point_position = _main_module.cal_resolve_point_position


class TestCalTargetById:
    """PC-03: identity выбора по id, не по индексу."""

    def test_finds_entry_by_id(self):
        t = cal_target_by_id("wt_icon")
        assert t is not None and t["id"] == "wt_icon"

    def test_unknown_id_returns_none(self):
        assert cal_target_by_id("nonexistent_target") is None

    def test_every_registry_id_is_findable(self):
        for t in CALIBRATION_TARGETS:
            assert cal_target_by_id(t["id"]) is t


class TestTuneCardVisibility:
    """Design 4.4 (файл 40): 3 состояния видимости tune_card.
    None -> скрыт; storage=offset -> показан; storage=absolute -> скрыт."""

    def test_none_selected_is_hidden(self):
        assert cal_tune_card_visible(None) is False

    def test_offset_target_is_visible(self):
        assert cal_tune_card_visible("wt_icon") is True

    def test_absolute_target_is_hidden(self):
        """Находка ревью (файл 40, Stage 5): переход offset -> absolute
        обязан прятать панель предыдущей offset-цели."""
        assert cal_tune_card_visible("ref_a") is False
        assert cal_tune_card_visible("ref_b") is False

    def test_every_offset_target_is_visible(self):
        for t in CALIBRATION_TARGETS:
            if t["storage"] == "offset":
                assert cal_tune_card_visible(t["id"]) is True

    def test_every_absolute_target_is_hidden(self):
        for t in CALIBRATION_TARGETS:
            if t["storage"] == "absolute":
                assert cal_tune_card_visible(t["id"]) is False


class TestVisualDispatchForKind:
    """PC-06: единый визуальный путь на kind, все три ветки."""

    def test_tochka_dispatches_to_crosshair(self):
        assert cal_visual_dispatch_for_kind("точка") == "crosshair"

    def test_ocr_area_dispatches_to_chest_overlay(self):
        assert cal_visual_dispatch_for_kind("OCR-область") == "chest_overlay"

    def test_yolo_offset_dispatches_to_unavailable_text(self):
        assert cal_visual_dispatch_for_kind("смещение-к-YOLO") == "unavailable_text"

    def test_every_registry_kind_has_a_dispatch(self):
        for t in CALIBRATION_TARGETS:
            # не бросает KeyError ни для одной реальной записи реестра
            cal_visual_dispatch_for_kind(t["kind"])


class TestResolvePointPosition:
    """PC-05: base_pos_fn вызывается заново на каждый рендер, не кэшируется."""

    def test_returns_none_for_non_point_offset_target(self):
        assert cal_resolve_point_position("ref_a") is None
        assert cal_resolve_point_position("chest_sender") is None
        assert cal_resolve_point_position("crypt_select") is None

    def test_base_pos_fn_called_on_each_render_and_reflects_recalibration(self):
        """spec T-13 test_base_pos_fn_reflects_latest_calibration усилен счётчиком —
        доказывает «каждый рендер», не только «после recalibrate» (найдено ревью, файл 41)."""
        target = cal_target_by_id("carter")  # carter -> coord_manager.to_screen_dialog, зависит от калибровки
        spy = MagicMock(side_effect=[(100, 200), (999, 888)])
        original_fn = target["base_pos_fn"]
        target["base_pos_fn"] = spy
        try:
            pos1 = cal_resolve_point_position("carter")
            assert spy.call_count == 1
            pos2 = cal_resolve_point_position("carter")
            assert spy.call_count == 2
            assert pos1 != pos2, "base_pos_fn закэширован — второй рендер вернул то же самое"
        finally:
            target["base_pos_fn"] = original_fn

    def test_adds_current_ui_offset_to_base_position(self):
        target = cal_target_by_id("wt_icon")
        original_fn = target["base_pos_fn"]
        target["base_pos_fn"] = MagicMock(return_value=(500, 500))
        original_offset = coord_manager.get_ui_offset("wt_icon")
        try:
            coord_manager.set_ui_offset("wt_icon", 10, -5)
            assert cal_resolve_point_position("wt_icon") == (510, 495)
        finally:
            target["base_pos_fn"] = original_fn
            coord_manager.set_ui_offset("wt_icon", *original_offset)
