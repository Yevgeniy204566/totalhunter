"""
TDD: логика выбора цели в реестре калибровки (PLAN-A Task 2, PC-03/PC-05/PC-06,
docs/superpowers/plans/exchange-scout-calibration-plan-a-*.md, файлы 39-41).

Вынесена в чистые функции модуля (без создания реального Tk-виджета) — в проекте нет теста,
который инстанцирует TotalHunterApp (ANTI-PATTERNS.md: запуск main.py пингует прод-сервер),
поэтому логика выбора/диспетчеризации/видимости тестируется отдельно от самой отрисовки
виджетов (та проверяется вручную владельцем в игре, как PT-13 в плане РОЙ).
"""
from unittest.mock import MagicMock, patch

import main as _main_module
from coord_manager import coord_manager

CALIBRATION_TARGETS = _main_module.CALIBRATION_TARGETS
LANGS = _main_module.LANGS
cal_target_by_id = _main_module.cal_target_by_id
cal_tune_card_visible = _main_module.cal_tune_card_visible
cal_visual_dispatch_for_kind = _main_module.cal_visual_dispatch_for_kind
cal_resolve_point_position = _main_module.cal_resolve_point_position
cal_apply_offset_delta = _main_module.cal_apply_offset_delta
cal_merge_calibration_point = _main_module.cal_merge_calibration_point


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

    def test_unavailable_text_key_exists_in_every_language(self):
        """Design 4.3 (файл 40): текст «статичное превью недоступно» для смещение-к-YOLO
        (crypt_select) — видимый UI-элемент, не молчание, во всех 19 языках."""
        for lang in LANGS:
            assert "cal_tune_preview_unavailable" in LANGS[lang]


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


class TestApplyOffsetDelta:
    """Self-Audit (файл 42): явный 0 обязан доходить до coord_manager.set_ui_offset как есть,
    не считаться «не задано»; вызов не пропускается ни при каком dx/dy, включая (0, 0)."""

    def test_none_target_id_is_noop(self):
        with patch_set_ui_offset() as spy:
            cal_apply_offset_delta(None, 5, 5)
            spy.assert_not_called()

    def test_zero_delta_still_calls_set_ui_offset(self):
        """Находка ревью: код, который пропускает вызов при dx=dy=0 (`if dx or dy:`),
        внешне неотличим по чтению get_ui_offset() — тест обязан проверять сам вызов."""
        with patch_set_ui_offset() as spy:
            cal_apply_offset_delta("wt_icon", 0, 0)
            spy.assert_called_once()

    def test_delta_added_to_current_offset(self):
        original_offset = coord_manager.get_ui_offset("wt_icon")
        try:
            coord_manager.set_ui_offset("wt_icon", 10, 10)
            cal_apply_offset_delta("wt_icon", -10, -10)
            assert coord_manager.get_ui_offset("wt_icon") == (0, 0)
            cal_apply_offset_delta("wt_icon", -1, 0)
            assert coord_manager.get_ui_offset("wt_icon") == (-1, 0)
        finally:
            coord_manager.set_ui_offset("wt_icon", *original_offset)

    def test_does_not_write_profile_to_disk(self):
        """Анти-паттерн Стадии 1 (файл 38): D-Pad не пишет файл на каждый клик — только
        coord_manager.save() пишет на диск (main.py:_save_profile), cal_apply_offset_delta
        его не вызывает и не может вызывать (не знает о профилях/путях вообще). Проверяются
        реально используемые имена в байт-коде (co_names), не текст докстринга."""
        used_names = cal_apply_offset_delta.__code__.co_names
        assert "save" not in used_names and "os" not in used_names


def patch_set_ui_offset():
    return patch.object(coord_manager, "set_ui_offset", wraps=coord_manager.set_ui_offset)


class TestMergeCalibrationPoint:
    """Баг, найденный владельцем при живой проверке: клик по ref_b показывал калибровку
    Точки А. Корень — run_calibration() всегда стартует с А; cal_merge_calibration_point
    проверяет, что вторая точка берётся из ТЕКУЩЕЙ калибровки, не путается местами."""

    def test_ref_a_replaces_only_point_a(self):
        new_a, new_b = cal_merge_calibration_point("ref_a", (111, 222), (1, 1), (999, 999))
        assert (new_a, new_b) == ((111, 222), (999, 999))

    def test_ref_b_replaces_only_point_b(self):
        new_a, new_b = cal_merge_calibration_point("ref_b", (111, 222), (777, 777), (1, 1))
        assert (new_a, new_b) == ((777, 777), (111, 222))


class TestVideoLink:
    """PC-07 (файл 39): CALIBRATION_VIDEO_URL="" — заглушка, неактивна пока пустая, не
    битая ссылка. webbrowser.open(url) при непустом url."""

    def test_video_link_url_is_empty_placeholder(self):
        assert _main_module.CALIBRATION_VIDEO_URL == ""

    def test_video_link_label_key_exists_in_every_language(self):
        for lang in LANGS:
            assert "cal_video_link" in LANGS[lang]

    def test_click_returns_none_when_url_empty(self):
        assert _main_module.cal_video_link_click_url() is None

    def test_click_returns_url_when_set(self):
        original = _main_module.CALIBRATION_VIDEO_URL
        _main_module.CALIBRATION_VIDEO_URL = "https://www.youtube.com/watch?v=placeholder"
        try:
            assert _main_module.cal_video_link_click_url() == "https://www.youtube.com/watch?v=placeholder"
        finally:
            _main_module.CALIBRATION_VIDEO_URL = original
