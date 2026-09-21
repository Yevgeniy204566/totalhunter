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
# Значение по умолчанию для 2.0 — 13 (владелец 2026-09-21: «максимум 50, но по дефолту 13»).
INLAND_RANGE = {MODE_V1: (1, 10), MODE_V2: (1, 50)}
SCOUT_DEFAULT_INLAND = 13

# Скорость змейки в 2.0 — множитель от минимального цикла ЭТОГО ПК, не секунды (решение владельца
# 2026-09-21): 1.0 = быстрее всего, что умеет ПК, 4.0 = цикл в четыре раза длиннее. В режиме 1.0 тот же
# ключ 'wait' — секунды 0.4–2.0 (в цикле 1.0 сидит нейросеть, там секунды осмысленны).
SPEED_FACTOR_RANGE = (1.0, 4.0)
SPEED_FACTOR_STEPS = 12          # шаг ползунка 0.25x
SCOUT_DEFAULT_SPEED_FACTOR = 1.0

# Очередь скриншотов: 100% индикатора = порог автопаузы змейки, ~300 кадров (решение владельца
# 2026-09-18, число подтверждается измерением). Сама автопауза — Часть B, ещё не реализована.
SCOUT_QUEUE_PAUSE_THRESHOLD = 300
# Змейка продолжает, когда очередь спала до 10% (~30 кадров) — решение владельца 2026-09-18/21.
SCOUT_QUEUE_RESUME_THRESHOLD = SCOUT_QUEUE_PAUSE_THRESHOLD // 10
# Лимит очереди выбирается в выпадающем списке (предложение владельца 2026-09-21): по умолчанию 300.
SCOUT_QUEUE_LIMIT_OPTIONS = (300, 600, 999)


def queue_resume_for(limit: int) -> int:
    """Порог возобновления змейки — 10% от выбранного лимита (300 -> 30, 600 -> 60, 999 -> 99)."""
    return limit // 10


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
            elif key == 'wait' and mode == MODE_V2:
                value = max(SPEED_FACTOR_RANGE[0], min(SPEED_FACTOR_RANGE[1], float(value)))
            sliders[key].set(value)

    def ensure_seeded(self, new, prev) -> None:
        """Режим, который ни разу не открывали, стартует с копии значений другого (глубина — по
        своему режиму: 2.0 — 50, 1.0 — зажата потолком 10)."""
        if self._values[new] is None:
            seed = dict(self._values[prev])
            if new == MODE_V2:
                seed['inland'] = SCOUT_DEFAULT_INLAND
                seed['wait'] = SCOUT_DEFAULT_SPEED_FACTOR   # секунды 1.0 не переносятся в множитель
            else:
                seed['inland'] = _clamp_inland(new, seed['inland'])
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


def queue_fraction(size: int, threshold: int = SCOUT_QUEUE_PAUSE_THRESHOLD) -> float:
    """Заполнение индикатора 0..1: 100% = порог паузы; больше порога не выходит за край."""
    if threshold <= 0:
        return 0.0
    return max(0.0, min(1.0, size / threshold))


def scout_queue_state(snake_running: bool, queue_size: int, paused: bool = False) -> str:
    """Состояние индикатора (решение владельца 2026-09-18): 'active' — змейка работает; 'paused' — змейка
    сама встала на паузу из-за заполнения очереди; 'brown' — змейка остановлена, очередь не пуста (идёт
    разбор накопленного); 'green' — очередь пуста."""
    if snake_running and paused:
        return 'paused'
    if snake_running:
        return 'active'
    return 'brown' if queue_size > 0 else 'green'


_TEXTS = {
    'RU': {
        'debug_tg': 'Находки в debug-Telegram',
        'limit_label': 'Лимит очереди:', 'st_paused': 'Пауза: ожидание обработки очереди',
        'st_paused_nn_off': 'Пауза: очередь заполнена, нейросеть выключена',
        'queue_title': 'Очередь скриншотов', 'snake_cycle': 'Цикл змейки (мин. = быстрее всего):',
        'st_active': 'Змейка работает', 'st_brown': 'Змейка остановлена — идёт разбор очереди',
        'st_brown_nn_off': 'Змейка остановлена, нейросеть выключена — очередь ждёт',
        'st_green': 'Очередь пуста', 'nn_stop': 'Остановить нейросеть', 'nn_start': 'Запустить нейросеть',
        'nn_on': 'Нейросеть работает', 'nn_off': 'Нейросеть остановлена', 'cycle_pc': 'цикл ПК',
    },
    'UK': {
        'debug_tg': 'Знахідки в debug-Telegram',
        'limit_label': 'Ліміт черги:', 'st_paused': 'Пауза: очікування обробки черги',
        'st_paused_nn_off': 'Пауза: черга заповнена, нейромережа вимкнена',
        'queue_title': 'Черга скриншотів', 'snake_cycle': 'Цикл змійки (мін. = найшвидше):',
        'st_active': 'Змійка працює', 'st_brown': 'Змійка зупинена — триває розбір черги',
        'st_brown_nn_off': 'Змійка зупинена, нейромережа вимкнена — черга чекає',
        'st_green': 'Черга порожня', 'nn_stop': 'Зупинити нейромережу', 'nn_start': 'Запустити нейромережу',
        'nn_on': 'Нейромережа працює', 'nn_off': 'Нейромережа зупинена', 'cycle_pc': 'цикл ПК',
    },
    'EN': {
        'debug_tg': 'Send finds to debug Telegram',
        'limit_label': 'Queue limit:', 'st_paused': 'Paused: waiting for the queue',
        'st_paused_nn_off': 'Paused: queue is full, neural net is off',
        'queue_title': 'Screenshot queue', 'snake_cycle': 'Snake cycle (min = fastest):',
        'st_active': 'Snake is running', 'st_brown': 'Snake stopped — processing the queue',
        'st_brown_nn_off': 'Snake stopped, neural net off — queue is waiting',
        'st_green': 'Queue is empty', 'nn_stop': 'Stop neural net', 'nn_start': 'Start neural net',
        'nn_on': 'Neural net running', 'nn_off': 'Neural net stopped', 'cycle_pc': 'PC cycle',
    },
}


def scout_text(lang: str, key: str) -> str:
    """Подписи панели 2.0: RU/UK/EN, остальные языки пока показывают английский."""
    return _TEXTS.get(lang, _TEXTS['EN']).get(key, _TEXTS['EN'][key])
