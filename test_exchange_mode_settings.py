"""Переключатель режимов Биржа 1.0 / Биржа 2.0 на вкладке БИРЖИ (сессия #148, пункт 1 хангофа #147).

Владелец: «если в боте 1.0 глубина нырка 10, то при переключении в режим 2.0 глубина нырка должна
быть до 50, и соответственно все другие ползунки, скорости должны быть согласно новой системе» —
ползунки должны ВИЗУАЛЬНО менять значения и диапазон по режиму, а не просто иметь скрытую константу.

Тесты вызывают ТЕ ЖЕ функции, что и GUI (`ExchangeModeSettings`, `exchange_mode_settings`), — урок
сессии #147 (ANTI-PATTERNS: тест дублирует числа вместо вызова реальной production-функции)."""

import pytest

from exchange_mode_settings import (
    ExchangeModeSettings, MODE_V1, MODE_V2, NAV_KEYS, INLAND_RANGE, SCOUT_DEFAULT_INLAND,
    mode_label, scout_settings_for_profile, SCOUT_DEFAULT_SPEED_FACTOR, SPEED_FACTOR_RANGE,
    SCOUT_QUEUE_PAUSE_THRESHOLD, queue_fraction, scout_queue_state, scout_text,
)


class FakeSlider:
    """Минимальный двойник CTkSlider: .get/.set/.configure(from_, to, number_of_steps)."""

    def __init__(self, value, from_=0, to=100):
        self.value = value
        self.from_ = from_
        self.to = to
        self.steps = None

    def get(self):
        return self.value

    def set(self, v):
        self.value = v

    def configure(self, **kw):
        if 'from_' in kw:
            self.from_ = kw['from_']
        if 'to' in kw:
            self.to = kw['to']
        if 'number_of_steps' in kw:
            self.steps = kw['number_of_steps']


def make_sliders():
    return {
        'step': FakeSlider(13, 10, 20), 'wait': FakeSlider(1.5, 0.4, 2.0),
        'inland': FakeSlider(5, 1, 10), 'ocean': FakeSlider(3, 1, 15),
        'waterpx': FakeSlider(500, 100, 2000), 'diagblind': FakeSlider(0.5, 0.0, 1.0),
        'footprint': FakeSlider(120, 60, 1200), 'delta': FakeSlider(0, 0, 20),
        'pitch': FakeSlider(100, 10, 100),
    }


class TestConstants:
    def test_v2_inland_range_goes_up_to_50(self):
        assert INLAND_RANGE[MODE_V2][1] == 50
        assert SCOUT_DEFAULT_INLAND == 13

    def test_v1_inland_range_unchanged(self):
        assert INLAND_RANGE[MODE_V1] == (1, 10)

    def test_nav_keys_cover_every_snake_slider(self):
        assert set(NAV_KEYS) == set(make_sliders())


class TestSwitchToV2:
    def test_inland_defaults_to_13_and_range_widens_to_50_on_first_switch(self):
        s = make_sliders()
        st = ExchangeModeSettings()
        st.switch(MODE_V1, MODE_V2, s)
        assert s['inland'].get() == 13
        assert (s['inland'].from_, s['inland'].to) == (1, 50)
        assert s['inland'].steps == 49

    def test_other_sliders_inherit_v1_values_on_first_switch(self):
        s = make_sliders()
        s['step'].set(15)
        s['ocean'].set(7)
        st = ExchangeModeSettings()
        st.switch(MODE_V1, MODE_V2, s)
        assert s['step'].get() == 15
        assert s['ocean'].get() == 7

    def test_speed_starts_at_minimum_multiplier_not_v1_seconds(self):
        """Секунды 1.0 (0.4-2.0) в множитель не переносятся: 2.0 стартует с x1 - быстрее всего."""
        s = make_sliders()
        s['wait'].set(1.8)
        st = ExchangeModeSettings()
        st.switch(MODE_V1, MODE_V2, s)
        assert s['wait'].get() == SCOUT_DEFAULT_SPEED_FACTOR == 1.0

    def test_v2_edits_are_remembered_and_do_not_leak_into_v1(self):
        s = make_sliders()
        st = ExchangeModeSettings()
        st.switch(MODE_V1, MODE_V2, s)
        s['inland'].set(30)
        s['wait'].set(2.5)
        st.switch(MODE_V2, MODE_V1, s)
        assert s['inland'].get() == 5           # значение 1.0 вернулось
        assert s['wait'].get() == 1.5
        assert (s['inland'].from_, s['inland'].to) == (1, 10)
        assert s['inland'].steps == 9
        st.switch(MODE_V1, MODE_V2, s)
        assert s['inland'].get() == 30          # значение 2.0 вспомнилось
        assert s['wait'].get() == 2.5


class TestSeparateSliderSets:
    """В режиме 2.0 скорость змейки — другой виджет (карточка «Навигация», не «Нейросеть»)."""

    def test_wait_goes_to_the_new_modes_own_slider(self):
        v1 = make_sliders()
        v2 = dict(v1)
        v2['wait'] = FakeSlider(0.0, 0.4, 2.0)
        v1['wait'].set(1.2)
        st = ExchangeModeSettings()
        st.switch(MODE_V1, MODE_V2, v1, v2)
        assert v2['wait'].get() == 1.0          # 2.0 стартует с x1, секунды 1.0 не переносятся
        v2['wait'].set(3.0)
        assert v1['wait'].get() == 1.2          # виджет 1.0 не тронут
        st.switch(MODE_V2, MODE_V1, v2, v1)
        assert v1['wait'].get() == 1.2
        st.switch(MODE_V1, MODE_V2, v1, v2)
        assert v2['wait'].get() == 3.0


class TestValuesForSave:
    def test_v1_values_are_live_when_view_is_v1(self):
        s = make_sliders()
        s['step'].set(17)
        st = ExchangeModeSettings()
        assert st.values_for(MODE_V1, MODE_V1, s)['step'] == 17

    def test_v1_values_come_from_store_when_view_is_v2(self):
        """Ключевой риск: сохранение профиля во время вида 2.0 не должно записать 50 в ключ 1.0."""
        s = make_sliders()
        st = ExchangeModeSettings()
        st.switch(MODE_V1, MODE_V2, s)
        s['inland'].set(40)
        v1 = st.values_for(MODE_V1, MODE_V2, s)
        assert v1['inland'] == 5
        v2 = st.values_for(MODE_V2, MODE_V2, s)
        assert v2['inland'] == 40

    def test_v2_values_none_until_user_ever_opened_v2(self):
        s = make_sliders()
        st = ExchangeModeSettings()
        assert st.values_for(MODE_V2, MODE_V1, s) is None


class TestProfileRoundTrip:
    def test_profile_dict_none_when_v2_never_used(self):
        s = make_sliders()
        st = ExchangeModeSettings()
        assert scout_settings_for_profile(st, MODE_V1, s) is None

    def test_profile_dict_has_all_keys_when_v2_used(self):
        s = make_sliders()
        st = ExchangeModeSettings()
        st.switch(MODE_V1, MODE_V2, s)
        d = scout_settings_for_profile(st, MODE_V2, s)
        assert set(d) == set(NAV_KEYS)
        assert d['inland'] == 13

    def test_load_v2_from_profile_applies_when_view_is_v2(self):
        s = make_sliders()
        st = ExchangeModeSettings()
        st.switch(MODE_V1, MODE_V2, s)
        st.load_v2({'inland': 35, 'wait': 2.5, 'step': 12})
        st.apply(MODE_V2, s)
        assert s['inland'].get() == 35
        assert s['wait'].get() == 2.5

    def test_old_seconds_style_speed_in_profile_is_clamped_to_multiplier_range(self):
        st = ExchangeModeSettings()
        st.load_v2({'wait': 0.4})
        s = make_sliders()
        st.apply(MODE_V2, s)
        assert s['wait'].get() == 1.0
        st.load_v2({'wait': 9})
        st.apply(MODE_V2, s)
        assert s['wait'].get() == 4.0

    def test_load_v2_ignores_garbage_and_clamps_inland(self):
        st = ExchangeModeSettings()
        st.load_v2({'inland': 999, 'wait': 'abc', 'unknown': 1})
        s = make_sliders()
        st.apply(MODE_V2, s)
        assert s['inland'].get() == 50           # зажато потолком 2.0
        assert s['wait'].get() == 1.5            # мусор отброшен, осталось значение слайдера

    def test_load_v2_none_keeps_store_empty(self):
        st = ExchangeModeSettings()
        st.load_v2(None)
        assert st.values_for(MODE_V2, MODE_V1, make_sliders()) is None


class TestModeLabel:
    def test_v2_label_is_scout_label_as_is(self):
        assert mode_label(MODE_V2, "Биржа 2.0") == "Биржа 2.0"

    def test_v1_label_derived_from_scout_label(self):
        assert mode_label(MODE_V1, "Биржа 2.0") == "Биржа 1.0"
        assert mode_label(MODE_V1, "取引所 2.0") == "取引所 1.0"


class TestRealCtkSlider:
    """Проверка на настоящем CTkSlider: configure(to=...) меняет нормализованное значение, поэтому
    set() ОБЯЗАН идти после configure — иначе глубина 50 превратится в другое число."""

    def test_inland_50_survives_range_switch_on_real_widget(self):
        tk = pytest.importorskip("tkinter")
        ctk = pytest.importorskip("customtkinter")
        try:
            root = tk.Tk()
        except tk.TclError:
            pytest.skip("нет дисплея для Tk")
        try:
            sl = ctk.CTkSlider(root, from_=1, to=10, number_of_steps=9)
            sl.set(5)
            sliders = make_sliders()
            sliders['inland'] = sl
            st = ExchangeModeSettings()
            st.switch(MODE_V1, MODE_V2, sliders)
            assert int(round(sl.get())) == 13        # по умолчанию 13 (число не искажено переходом диапазона)
            sl.set(50)
            assert int(round(sl.get())) == 50        # потолок 2.0 достижим на настоящем виджете
            st.switch(MODE_V2, MODE_V1, sliders)
            assert int(round(sl.get())) == 5
        finally:
            root.destroy()


class TestExchangeCfgFromValues:
    """Формат профиля 1.0 не должен измениться ни на байт для тех, кто 2.0 не открывал."""

    V1 = {'step': 13.0, 'wait': 1.5, 'inland': 5.0, 'ocean': 3.0, 'waterpx': 500.0,
          'diagblind': 0.5, 'footprint': 120.0, 'delta': 0.0, 'pitch': 100.0}

    def test_v1_only_profile_keys_and_conversions_match_pre_v2_format(self):
        from exchange_mode_settings import exchange_cfg_from_values
        cfg = exchange_cfg_from_values(self.V1, 0.8, None)
        assert list(cfg) == ['step', 'conf', 'bot_speed', 'max_inland_steps', 'ocean_land_ratio',
                             'min_water_px', 'diagonal_blind_coeff', 'nav_footprint_ttl',
                             'return_delta_px', 'smooth_alpha']
        assert cfg['ocean_land_ratio'] == 0.03
        assert cfg['max_inland_steps'] == 5
        assert 'scout_settings' not in cfg

    def test_scout_settings_added_only_when_v2_was_used(self):
        from exchange_mode_settings import exchange_cfg_from_values
        cfg = exchange_cfg_from_values(self.V1, 0.8, {'inland': 50})
        assert cfg['scout_settings'] == {'inland': 50}
        assert cfg['max_inland_steps'] == 5      # ключ 1.0 не тронут значением 2.0


class TestRealAppMethods:
    """Настоящие методы TotalHunterApp на фейковом self — тот же путь, что и живой GUI."""

    def _fake_app(self):
        from unittest.mock import MagicMock
        app = MagicMock()
        app._exchange_mode = MODE_V1
        app.active_mode = None
        app.current_lang = "RU"
        app._mode_settings = ExchangeModeSettings()
        app._exchange_mode_labels = {MODE_V1: "Биржа 1.0", MODE_V2: "Биржа 2.0"}
        sl = make_sliders()
        v2wait = FakeSlider(1.5, 0.4, 2.0)
        app._sliders = {MODE_V1: sl, MODE_V2: {**sl, 'wait': v2wait}}
        app._nav_sliders.side_effect = lambda mode=None: app._sliders[mode or app._exchange_mode]
        return app

    def test_set_exchange_mode_switches_sliders_and_view(self):
        import main as m
        app = self._fake_app()
        m.TotalHunterApp._set_exchange_mode(app, MODE_V2)
        assert app._exchange_mode == MODE_V2
        assert app._sliders[MODE_V2]['inland'].get() == 13
        app._apply_exchange_view.assert_called_once_with(MODE_V2)
        app._exchange_mode_seg.set.assert_called_with("Биржа 2.0")

    def test_set_exchange_mode_refused_while_a_mode_is_running(self):
        import main as m
        app = self._fake_app()
        app.active_mode = 'v1'
        m.TotalHunterApp._set_exchange_mode(app, MODE_V2)
        assert app._exchange_mode == MODE_V1
        assert app._sliders[MODE_V1]['inland'].get() == 5
        app._apply_exchange_view.assert_not_called()
        app._exchange_mode_seg.set.assert_called_with("Биржа 1.0")   # сегмент вернули на место

    def test_bot1_start_from_roy_tab_restores_v1_sliders_first(self, monkeypatch):
        """Кнопка 1.0 на вкладке РОЙ вызывает тот же toggle_bot: в виде 2.0 он обязан сначала вернуть
        на ползунки значения 1.0, иначе бот 1.0 стартует с глубиной 50."""
        import main as m
        app = self._fake_app()
        app._exchange_mode = MODE_V2
        app.is_running = False
        app.current_credits = 0                       # остановит toggle_bot сразу после гарда
        app.always_on_top_var.get.return_value = False
        monkeypatch.setattr(m.messagebox, "showwarning", lambda *a, **k: None)
        m.TotalHunterApp.toggle_bot(app)
        app._set_exchange_mode.assert_called_once_with(MODE_V1)

    def test_scout_start_refused_in_v1_view(self):
        import main as m
        app = self._fake_app()
        app._exchange_mode = MODE_V1
        m.TotalHunterApp._toggle_scout(app)
        assert app.active_mode is None
        app._scout_button.configure.assert_not_called()


class TestBuildScoutNavigatorDepth:
    _CFG = {'ocean_land_ratio': 0.03, 'min_water_px': 500, 'diagonal_blind_coeff': 0.5,
            'footprint_ttl': 120.0, 'return_delta_px': 0, 'smooth_alpha': 0.5, 'pixels_per_step': 20}

    def test_depth_comes_from_v2_slider_value(self):
        import main as m
        nav = m.build_scout_navigator(90, 925, 13, {**self._CFG, 'max_inland_steps': 30})
        assert nav.max_inland_steps == 30

    def test_depth_clamped_to_v2_ceiling(self):
        import main as m
        nav = m.build_scout_navigator(90, 925, 13, {**self._CFG, 'max_inland_steps': 999})
        assert nav.max_inland_steps == m.SCOUT_MAX_INLAND_STEPS == INLAND_RANGE[MODE_V2][1]


class TestQueueIndicatorLogic:
    def test_speed_range_is_1_to_4(self):
        assert SPEED_FACTOR_RANGE == (1.0, 4.0)

    def test_fraction_scales_to_pause_threshold(self):
        assert queue_fraction(0) == 0.0
        assert queue_fraction(SCOUT_QUEUE_PAUSE_THRESHOLD // 2) == 0.5
        assert queue_fraction(SCOUT_QUEUE_PAUSE_THRESHOLD) == 1.0

    def test_fraction_capped_at_100_percent(self):
        assert queue_fraction(SCOUT_QUEUE_PAUSE_THRESHOLD * 5) == 1.0

    def test_state_active_while_snake_runs_regardless_of_queue(self):
        assert scout_queue_state(True, 0) == 'active'
        assert scout_queue_state(True, 250) == 'active'

    def test_state_brown_when_snake_stopped_and_queue_not_empty(self):
        assert scout_queue_state(False, 1) == 'brown'

    def test_state_green_when_queue_empty_and_snake_stopped(self):
        assert scout_queue_state(False, 0) == 'green'

    def test_texts_fallback_to_english_for_unlisted_language(self):
        assert scout_text('DE', 'nn_stop') == scout_text('EN', 'nn_stop')
        assert scout_text('UK', 'nn_start') != scout_text('EN', 'nn_start')

    def test_every_language_has_the_same_keys(self):
        from exchange_mode_settings import _TEXTS
        assert set(_TEXTS['RU']) == set(_TEXTS['UK']) == set(_TEXTS['EN'])
