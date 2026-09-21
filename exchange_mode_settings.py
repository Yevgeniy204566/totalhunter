"""Раздельные настройки змейки для режимов Биржа 1.0 и Биржа 2.0 на вкладке БИРЖИ.

Ползунки навигации на вкладке общие для обоих режимов (один набор виджетов), но значения и диапазон
глубины нырка у режимов свои: переключатель режима сохраняет значения ушедшего режима и
восстанавливает значения нового. Чистая логика без tkinter — GUI передаёт словарь настоящих
CTkSlider, тесты — двойники с тем же .get/.set/.configure."""

MODE_V1 = 'v1'
MODE_V2 = 'v2'

NAV_KEYS = ('step', 'wait', 'inland', 'ocean', 'waterpx', 'diagblind', 'footprint', 'delta', 'pitch')

# Диапазон глубины нырка по режиму: 1.0 — потолок 10 (как в GUI 1.0 всегда), 2.0 — до 50 (решение
# владельца 2026-09-17, «до 50 шагов вглубь»). Остальные ползунки в обоих режимах в одном диапазоне.
INLAND_RANGE = {MODE_V1: (1, 10), MODE_V2: (1, 50)}
SCOUT_DEFAULT_INLAND = 50


def _clamp_inland(mode, value):
    lo, hi = INLAND_RANGE[mode]
    return max(lo, min(hi, int(round(value))))


class ExchangeModeSettings:
    def __init__(self):
        self._values = {MODE_V1: None, MODE_V2: None}

    def _snapshot(self, sliders) -> dict:
        return {k: sliders[k].get() for k in NAV_KEYS}

    def capture(self, mode, sliders) -> None:
        self._values[mode] = self._snapshot(sliders)

    def apply(self, mode, sliders) -> None:
        """Сначала диапазон глубины, потом значения: CTkSlider хранит значение нормализованным,
        поэтому configure(to=...) меняет выводимое число — set() обязан идти после него."""
        lo, hi = INLAND_RANGE[mode]
        sliders['inland'].configure(from_=lo, to=hi, number_of_steps=hi - lo)
        for key, value in (self._values[mode] or {}).items():
            if key == 'inland':
                value = _clamp_inland(mode, value)
            sliders[key].set(value)

    def ensure_seeded(self, new, prev) -> None:
        """Режим, который ни разу не открывали, стартует с копии значений другого (глубина — по
        своему режиму: 2.0 — 50, 1.0 — зажата потолком 10)."""
        if self._values[new] is None:
            seed = dict(self._values[prev])
            seed['inland'] = SCOUT_DEFAULT_INLAND if new == MODE_V2 else _clamp_inland(new, seed['inland'])
            self._values[new] = seed

    def switch(self, prev, new, sliders, new_sliders=None) -> None:
        """`new_sliders` — набор ползунков нового режима, если он отличается от набора прежнего
        (в режиме 2.0 скорость змейки — отдельный ползунок в карточке «Навигация»)."""
        self.capture(prev, sliders)
        self.ensure_seeded(new, prev)
        self.apply(new, new_sliders if new_sliders is not None else sliders)

    def values_for(self, mode, view, sliders):
        """Значения режима `mode`: живые с ползунков, если сейчас показан именно он, иначе сохранённые
        (None — режим ни разу не открывался). Нужны сохранению профиля: находясь в виде 2.0 оно не
        должно записать значения 2.0 (глубину 50) в ключи 1.0."""
        if mode == view:
            return self._snapshot(sliders)
        stored = self._values[mode]
        return dict(stored) if stored is not None else None

    def load_v2(self, raw) -> None:
        """Значения 2.0 из профиля (`scout_settings`); мусор и неизвестные ключи отбрасываются."""
        if not isinstance(raw, dict):
            self._values[MODE_V2] = None
            return
        clean = {}
        for key in NAV_KEYS:
            if key in raw and isinstance(raw[key], (int, float)) and not isinstance(raw[key], bool):
                clean[key] = raw[key]
        self._values[MODE_V2] = clean or None


def scout_settings_for_profile(settings, view, sliders):
    """Что писать в профиль под ключом `scout_settings`; None — 2.0 никогда не открывали, ключ не
    пишется и профиль пользователя только с Биржей 1.0 остаётся байт-в-байт прежним."""
    return settings.values_for(MODE_V2, view, sliders)


def mode_label(mode, scout_label: str) -> str:
    """Подпись сегмента переключателя. `scout_label` («Биржа 2.0», «Exchange 2.0», …) уже есть во всех
    19 языках, подпись 1.0 получаем заменой версии — без новых ключей перевода."""
    return scout_label if mode == MODE_V2 else scout_label.replace("2.0", "1.0")


def exchange_cfg_from_values(v1: dict, conf: float, scout) -> dict:
    """Ключи «Настроек Бирж» для профиля. Значения 1.0 и их преобразования — те же, что были в
    `_save_crypt_settings` до появления режима 2.0 (формат профиля 1.0 не меняется); `scout_settings`
    добавляется только если 2.0 когда-либо открывали."""
    cfg = {
        'step': int(v1['step']),
        'conf': round(conf, 2),
        'bot_speed': round(v1['wait'], 1),
        'max_inland_steps': int(v1['inland']),
        'ocean_land_ratio': int(v1['ocean']) / 100.0,
        'min_water_px': int(v1['waterpx']),
        'diagonal_blind_coeff': round(v1['diagblind'], 2),
        'nav_footprint_ttl': int(v1['footprint']),
        'return_delta_px': int(v1['delta']),
        'smooth_alpha': int(v1['pitch']),
    }
    if scout is not None:
        cfg['scout_settings'] = scout
    return cfg
