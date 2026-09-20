"""
TDD: единый реестр 12 целей калибровки (PLAN-A, docs/superpowers/plans/
exchange-scout-calibration-plan-a-*.md, файлы 38-43). Заменяет TUNE_TARGET_NAMES,
_TUNE_POINT_TARGETS, _CHEST_TUNE_RECTS (PC-04) одним источником метаданных.

PC-01: реестр — ровно 12 записей, обязательные/запрещённые поля строго по kind/storage.
PC-02: множество id с storage="offset" равно (двусторонне) coord_manager._UI_BUTTON_NAMES.
"""
import main as _main_module
from coord_manager import coord_manager

CALIBRATION_TARGETS = _main_module.CALIBRATION_TARGETS
LANGS = _main_module.LANGS
_UI_BUTTON_NAMES = coord_manager._UI_BUTTON_NAMES

# Design 4.1 (docs/superpowers/specs/exchange-scout-calibration-design-35.md) — id/kind/storage
# дословно, порядок — Design 4.8 (калибровка -> Склепы -> общие/биржи -> Сундуки).
EXPECTED_TABLE = [
    ("ref_a",        "точка",         "absolute"),
    ("ref_b",        "точка",         "absolute"),
    ("crypt_select", "смещение-к-YOLO", "offset"),
    ("crypt_open",   "точка",         "offset"),
    ("carter",       "точка",         "offset"),
    ("wt_icon",      "точка",         "offset"),
    ("top_accel",    "точка",         "offset"),
    ("march_accel",  "точка",         "offset"),
    ("arena_reset",  "точка",         "offset"),
    ("chest_sender", "OCR-область",   "offset"),
    ("chest_type",   "OCR-область",   "offset"),
    ("chest_collect", "точка",        "offset"),
]

# PC-01 (файл 39): ровно 7 записей kind="точка"+storage="offset" обязаны иметь base_pos_fn.
POINT_OFFSET_IDS = {"wt_icon", "carter", "crypt_open", "top_accel", "march_accel",
                     "arena_reset", "chest_collect"}
OCR_AREA_IDS = {"chest_sender", "chest_type"}


class TestRegistryMatchesDesignTable:
    def test_registry_has_exactly_12_entries_matching_design_table(self):
        assert len(CALIBRATION_TARGETS) == 12
        actual = [(t["id"], t["kind"], t["storage"]) for t in CALIBRATION_TARGETS]
        assert actual == EXPECTED_TABLE

    def test_all_targets_have_valid_kind(self):
        """Spec T-02 (tests-gate-37.md) — поглощён этим более широким тестом (файл 39/41)."""
        valid_kinds = {"точка", "OCR-область", "смещение-к-YOLO"}
        for t in CALIBRATION_TARGETS:
            assert t["kind"] in valid_kinds, f"{t['id']}: недопустимый kind {t['kind']!r}"

    def test_label_key_exists_in_every_language(self):
        """Стадия 5 находка 6 (файл 40) -> уточнение PC-01 (файл 39)."""
        for t in CALIBRATION_TARGETS:
            for lang in LANGS:
                assert t["label_key"] in LANGS[lang], \
                    f"{t['id']}: label_key {t['label_key']!r} отсутствует в LANGS[{lang!r}]"


class TestRegistryOptionalFields:
    def test_ref_rect_present_only_for_ocr_area(self):
        for t in CALIBRATION_TARGETS:
            if t["kind"] == "OCR-область":
                assert t.get("ref_rect") is not None, f"{t['id']}: ref_rect обязателен"
            else:
                assert t.get("ref_rect") is None, f"{t['id']}: ref_rect запрещён"

    def test_base_pos_fn_present_and_callable_only_for_point_offset(self):
        for t in CALIBRATION_TARGETS:
            if t["id"] in POINT_OFFSET_IDS:
                assert t["kind"] == "точка" and t["storage"] == "offset"
                assert callable(t.get("base_pos_fn")), f"{t['id']}: base_pos_fn обязателен и callable"
            else:
                assert t.get("base_pos_fn") is None, f"{t['id']}: base_pos_fn запрещён"

    def test_registry_optional_fields_present_only_for_matching_kind(self):
        """Объединённая проверка обеих сторон (PC-01, файл 39, раунд правок 2)."""
        for t in CALIBRATION_TARGETS:
            has_ref_rect = t.get("ref_rect") is not None
            has_base_pos_fn = callable(t.get("base_pos_fn"))
            assert has_ref_rect == (t["id"] in OCR_AREA_IDS)
            assert has_base_pos_fn == (t["id"] in POINT_OFFSET_IDS)


class TestRegistryBidirectionalWithUiButtonNames:
    def test_registry_offset_ids_match_ui_button_names_bidirectionally(self):
        registry_offset_ids = {t["id"] for t in CALIBRATION_TARGETS if t["storage"] == "offset"}
        assert registry_offset_ids == set(_UI_BUTTON_NAMES)


class TestNoLegacyTuneStructuresRemain:
    """PC-04 (файл 39): TUNE_TARGET_NAMES/_TUNE_POINT_TARGETS/_CHEST_TUNE_RECTS удалены
    атомарно вместе с реестром — grep по всему проекту, по образцу правила AP-DUP-HARDCODE
    («grep по всему файлу перед тем как считать задачу завершённой»)."""

    LEGACY_NAMES = ("TUNE_TARGET_NAMES", "_TUNE_POINT_TARGETS", "_CHEST_TUNE_RECTS",
                     "_tune_option_menu", "_ui_tune_btn_var", "tune_menu_labels",
                     "tune_chest_group_entry_indices")

    def test_no_legacy_tune_structures_remain(self):
        import pathlib
        root = pathlib.Path(__file__).parent
        hits = []
        for py_file in root.glob("*.py"):
            if py_file.name == "test_calibration_registry.py":
                continue  # этот файл сам перечисляет имена в LEGACY_NAMES — не self-match
            text = py_file.read_text(encoding="utf-8")
            for name in self.LEGACY_NAMES:
                if name in text:
                    hits.append(f"{py_file.name}: {name}")
        assert hits == [], f"найдены литералы старых структур: {hits}"
