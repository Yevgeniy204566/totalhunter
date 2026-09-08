"""
TDD: пункты меню «Тонкая настройка» (вкладка Калибровка) должны быть
пронумерованы одинаково для ЛЮБОГО языка, и генерироваться ОДНОЙ функцией
и при первом построении вкладки, и при смене языка (change_lang) — иначе
эти два места расходятся, как это случилось на практике:

- дублирование логики нумерации привело к тому, что change_lang() строил
  список пунктов БЕЗ префикса "N. ", а _tune_labels()/_tune_on_select
  внутри вкладки сравнивали значения дропдауна СО префиксом — после смены
  языка _tune_on_select() никогда не находил совпадение, self._tune_idx
  переставал обновляться, и картинка калибровки застревала на последнем
  пункте, выбранном до смены языка.
"""
import main as _main_module

tune_menu_labels = _main_module.tune_menu_labels
tune_chest_group_entry_indices = _main_module.tune_chest_group_entry_indices
TUNE_TARGET_NAMES = _main_module.TUNE_TARGET_NAMES
TUNE_CHEST_GROUP = _main_module.TUNE_CHEST_GROUP
LANGS = _main_module.LANGS


class TestTuneMenuLabels:
    def test_first_item_is_calibration_header(self):
        labels = tune_menu_labels("RU", TUNE_TARGET_NAMES)
        assert labels[0] == LANGS["RU"]["tab_cal"]

    def test_items_are_numbered_starting_at_1(self):
        labels = tune_menu_labels("RU", TUNE_TARGET_NAMES)
        assert labels[1].startswith("1. ")
        assert labels[2].startswith("2. ")
        assert labels[-1].startswith(f"{len(TUNE_TARGET_NAMES)}. ")

    def test_numbering_present_for_every_language(self):
        """Раньше нумерация была только там, где вкладка строилась впервые
        (обычно RU по умолчанию) — после смены языка префиксы пропадали."""
        for lang in LANGS:
            labels = tune_menu_labels(lang, TUNE_TARGET_NAMES)
            for i, label in enumerate(labels[1:], start=1):
                assert label.startswith(f"{i}. "), \
                    f"{lang}: пункт {i} без номера — {label!r}"

    def test_same_length_for_every_language(self):
        expected_len = len(TUNE_TARGET_NAMES) + 1
        for lang in LANGS:
            assert len(tune_menu_labels(lang, TUNE_TARGET_NAMES)) == expected_len

    def test_switching_language_keeps_labels_consistent(self):
        """Регрессия: построение вкладки (init) и смена языка (change_lang)
        обязаны давать ИДЕНТИЧНЫЙ формат — иначе _tune_on_select не находит
        совпадение и картинка калибровки перестаёт обновляться."""
        init_labels = tune_menu_labels("RU", TUNE_TARGET_NAMES)
        after_switch_labels = tune_menu_labels("EN", TUNE_TARGET_NAMES)
        # Формат (наличие номера) должен совпадать позиционно.
        for a, b in zip(init_labels[1:], after_switch_labels[1:]):
            a_num = a.split(". ", 1)[0]
            b_num = b.split(". ", 1)[0]
            assert a_num == b_num


class TestTuneChestGroupEntryIndices:
    def test_last_three_targets_are_the_chest_group(self):
        """Группа калибровки сбора сундуков — последние 3 пункта меню
        (Отправитель сундука, Тип сундука, Сбор сундука)."""
        assert TUNE_TARGET_NAMES[-3:] == TUNE_CHEST_GROUP

    def test_returns_dropdown_entry_indices_for_chest_group(self):
        """Индексы entry в dropdown-меню (1-based: entry 0 — заголовок
        «Калибровка», entry i — i-й пронумерованный пункт) — должны
        указывать ровно на последние 3 пункта."""
        indices = tune_chest_group_entry_indices(TUNE_TARGET_NAMES)
        assert indices == [len(TUNE_TARGET_NAMES) - 2,
                            len(TUNE_TARGET_NAMES) - 1,
                            len(TUNE_TARGET_NAMES)]

    def test_indices_match_the_numbered_labels(self):
        """Индекс из tune_chest_group_entry_indices обязан указывать на
        entry с числом-префиксом, совпадающим с самим индексом — иначе
        подсветка попадёт не на тот пункт."""
        labels = tune_menu_labels("RU", TUNE_TARGET_NAMES)
        for i in tune_chest_group_entry_indices(TUNE_TARGET_NAMES):
            assert labels[i].startswith(f"{i}. ")
