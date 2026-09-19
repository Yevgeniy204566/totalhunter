# Биржа 2.0 (Exchange Scout) — ЧАСТЬ A, файл 13: Context и Code Archaeology

> Фрагмент одного документа, разрезанного на файлы ≤300 строк по решению владельца (2026-09-18).
> **Индекс, статус и раунды → [`exchange-scout-part-a-lifecycle-design-12.md`](exchange-scout-part-a-lifecycle-design-12.md).**
> Файлы Части A: **13 (этот файл)** · [14](exchange-scout-part-a-contracts-design-14.md) · [15](exchange-scout-part-a-adversarial-15.md) · [16](exchange-scout-part-a-tests-gate-16.md)
> Деньги и debug-Telegram — **[→ Часть A-М]**: [`exchange-scout-monetization-design-07.md`](exchange-scout-monetization-design-07.md).
> Нумерация секций, контрактов C-*, находок A-* и тестов T-* сквозная по всем файлам и при нарезке
> не менялась.

---

## Стадия 1. Context

Прочитано лично в текущей сессии перед проектированием:

| Документ | Что взято |
|---|---|
| `docs/РАБОТА-С-ДОКУМЕНТАМИ.md` | протокол стадий 1-9, формат Contract Extraction, лимит 2 раундов |
| `CLAUDE.md` | золотое правило змейки, порядок вкладок, запрет правок эталона, YOLO fullscreen |
| `docs/exchange_bot_spec.md` | эталон Биржи 1.0 — документ, который эта спека НЕ имеет права затрагивать |
| `navigator.py` | `PositionReader`, `CoastalSnakeNavigator`, `PacmanEngine` — построчно |
| `engine.py` | `HuntEngine.start()/stop()` — фасадный слой, образец конструирования движка |
| `main.py` (фрагменты) | `toggle_bot()`, ESC-хук, `on_target_found`/`_process_found`, словари `LANGS` |
| `calibration.py` | единственный живой потребитель `PositionReader` — источник доказанного формата входа |

Список источников, прочитанных в раунде 2 по денежному контракту и по debug-Telegram
(`debug_reporter.py`, `auth.py`, `server/debug_router.py`, денежные участки `main.py`/`engine.py`/
`navigator.py`), перенесён вместе с этими темами — **[→ Часть A-М]**, Стадия 1.

**Стадия 0 (Scope Decomposition Gate):** решение о делении уже принято владельцем в брейнсторминге — модуль
режется на Часть A (файловый цикл + контракты + GUI) и Часть B (конкурентность). Данный документ — Часть A,
однородный: одна связная тема «что лежит на диске, кто чем владеет, какой внешний контракт». Превышение
300 строк здесь легитимно по критерию однородности протокола (Стадия 0), а не по желанию не резать.

---

## Стадия 2. Code Archaeology — что реально есть в коде

Всё ниже открыто и прочитано лично. Утверждения о коде без цитаты файла/строки в этом документе отсутствуют.

### 2.1 `PositionReader` — `navigator.py:30-74`

```python
class PositionReader:
    def __init__(self, crop_box: tuple[int, int, int, int] = (0, 1000, 250, 1080)):
        self.crop_box = crop_box
        self._pattern = re.compile(r'X\s*[:]\s*(\d+)\s+Y\s*[:]\s*(\d+)', re.IGNORECASE)
    ...
    def read(self, screenshot_np: np.ndarray) -> tuple[int, int] | None:
```

Факты, извлечённые из кода (не из предположений):

1. **Королевство (K) НЕ читается.** Регэксп (`navigator.py:33`) захватывает ровно две группы — X и Y.
   `_parse_ocr` (`navigator.py:42-49`) возвращает `(int(m.group(1)), int(m.group(2)))`. Никакого `K`.
   Для сравнения: `K` умеет читать другой, отдельный компонент — `roy/exchange_reader.py`
   (`docs/exchange_bot_spec.md:145` — `return {'kingdom':K, 'x':X, 'y':Y, 'percent':P}`), и он читает
   **открытый диалог биржи**, которого в 2.0 нет, потому что в 2.0 нет клика.
2. **Возврат:** `tuple[int, int] | None`. `None` означает одновременно «текста не было» и «OCR не смог» —
   различить нельзя: `read()` целиком обёрнут в `except Exception: return None` (`navigator.py:73-74`).
3. **Стоимость вызова:** 4 варианта кропа × 2 варианта препроцессинга × 3 psm-конфига
   (`navigator.py:57-70`) = **до 24 вызовов `pytesseract.image_to_string` на один кадр** в худшем случае
   (когда координаты не распознаются вообще). Ранний выход — на первом успехе.
4. **Таймаута нет.** В отличие от ROY-пайплайна (`docs/exchange_bot_spec.md:226` — «pytesseract timeout=3
   (бот не зависает)»), `PositionReader` вызывает `image_to_string` без `timeout=`.
5. **Доказанный формат входа — 4-канальный BGRA от `mss`, без конвертации.** Единственный живой
   потребитель `PositionReader` в проекте — `calibration.py:29,36` — кормит его результатом
   `calibration.py:17-21`:

   ```python
   def grab_screen() -> np.ndarray:
       with _mss() as sct:
           monitor = sct.monitors[1]
           return np.array(sct.grab(monitor))      # BGRA, 4 канала, БЕЗ cvtColor
   ```

   А `read()` делает `Image.fromarray(screenshot_np)` (`navigator.py:54`), то есть PIL интерпретирует
   эти байты как RGBA. **Красный и синий каналы фактически переставлены — и именно в таком виде OCR
   работает сегодня.** Это не косметика: кадр `PacmanEngine` — трёхканальный BGR после
   `cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)` (`navigator.py:1012`), то есть **другая** подача каналов.
   Прямое следствие для 2.0 — контракт C-11 ниже.
6. **`crop_box` не масштабируется `coord_manager`.** В `navigator.py` нет ни одного упоминания
   `coord_manager` (проверено грепом по файлу). Первые три кропа — абсолютные пиксели эталона 1920×1080,
   четвёртый (`navigator.py:61`) привязан к высоте кадра `h` и потому переживает другое разрешение.
   `calibration.py:29` использует доказанный на практике `crop_box=(0, 990, 300, 1080)`.

### 2.2 `CoastalSnakeNavigator` — `navigator.py:421-923`

Реальная сигнатура конструктора (`navigator.py:439-456`, приведены значимые для 2.0 параметры):

```python
class CoastalSnakeNavigator:
    DIVE_DEPTH_CAP = 10  # потолок роста глубины нырка — максимум GUI-ползунка   (navigator.py:437)

    def __init__(self, center_x=90, center_y=925, step=13,
                 max_inland_steps=5, ocean_land_ratio=0.03, min_water_px=500,
                 homing_max_steps=10, smooth_alpha=0.5, footprint_ttl=120.0,
                 footprint_enabled=True, pixels_per_step=20, force_shift_after=0,
                 diagonal_blind_coeff=0.5, coast_detect_radius=50, return_delta_px=0):
```

Главный шаг (`navigator.py:808`):

```python
    def step(self, is_water: bool = False, frame=None) -> bool:
```

Сброс состояния (`navigator.py:502`): `def reset(self):` — переводит в `HOMING`, обнуляет счётчики,
`self._footprint.reset()`.

**Проверка утверждения владельца про `max_inland_steps=50` — подтверждено кодом, не принято на веру:**

- Конструктор присваивает значение напрямую: `self.max_inland_steps = max_inland_steps`
  (`navigator.py:465`). **Клэмпа к `DIVE_DEPTH_CAP` в конструкторе нет.**
- `DIVE_DEPTH_CAP` используется как ограничение роста только в `_maybe_grow_dive_depth` (`navigator.py:629`):
  `while now >= self._dive_growth_next_at and self.max_inland_steps < self.DIVE_DEPTH_CAP:`.
  При `max_inland_steps=50` второе условие ложно с первой итерации → тело цикла не исполняется,
  значение **не понижается** и бесконечного цикла не возникает (условие короткозамкнуто по `and`).
- Производные величины на глубине 50: `_return_steps = max_inland_steps + 15` = 65 (`navigator.py:876`),
  `_return_blind_steps = round((max_inland_steps - 3) * blind_factor)` ≤ 47 (`navigator.py:885-887`).
  Модульная константа `MAX_STEPS_SAFETY = 80` (`navigator.py:85`) используется только в `CompassNavigator`
  (`navigator.py:379,401`) — на `CoastalSnakeNavigator` не влияет, то есть 65 < 80 её и не задевает.

**По прямому указанию владельца число 50 не превращается в отдельную тему и не получает собственного
smoke-теста поведения цикла** — это то же самое, уже оттестированное поведение с другим числом итераций.
Единственная проверка — одна строка `assert nav.max_inland_steps == 50` в тесте конструирования (T-16).

### 2.3 `PacmanEngine` — `navigator.py:930-1178` (эталон формы, НЕ изменяется)

```python
    def start(self):                                            # navigator.py:988
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        if self._yolo_unblock_time <= time.time():
            self._yolo_unblock_time = 0.0
        self.joystick.reset()
        self.is_running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):                                             # navigator.py:999
        self.is_running = False
```

Два факта, важных для контракта 2.0:

- `start()`/`stop()` — **без аргументов**; все параметры принимаются в `__init__` (`navigator.py:931-959`).
- `stop()` **не джойнит поток**. Он только выставляет флаг; фактический джойн отложен до следующего
  `start()` (`navigator.py:989-990`). То есть возврат из `PacmanEngine.stop()` НЕ означает, что поток
  завершился. Слепо копировать эту слабость в 2.0 нельзя — 2.0 владеет файлами на диске, а не только
  кликами (см. контракт C-05 и его честное ограничение).

Вызов YOLO — дословно (`navigator.py:1025-1026`, идентичный второй вызов в `_fresh_scan`,
`navigator.py:1092-1093`):

```python
                        results = self.yolo_model.predict(
                            frame, conf=self.conf, imgsz=1280, verbose=False)
```

Разбор результата (`navigator.py:1028-1032`): `for r in results: if len(r.boxes) > 0: ... r.boxes[0]`.
У бокса используются `box.conf[0]` (`navigator.py:1078`) и `box.xyxy.cpu().tolist()[0]`
(`navigator.py:1116`).

Захват кадра (`navigator.py:1007-1012` и `1061-1062`):

```python
        from mss import mss
        with mss() as sct:
            monitor = sct.monitors[1]
            screen  = np.array(sct.grab(monitor))
            frame   = cv2.cvtColor(screen, cv2.COLOR_BGRA2BGR)
```

Звук находки (`navigator.py:1127-1131`): `winsound.PlaySound(self.sound_path, SND_FILENAME | SND_ASYNC)`
с запасным `winsound.Beep(1000, 500)`.

### 2.4 GUI — `main.py`

- `toggle_bot()` (`main.py:3568-3628`) — единственная точка старта/стопа 1.0. Флаг состояния —
  `self.is_running` (`main.py:3613`, `3628`), инициализация `main.py:1628`.
- Гейт баланса при старте 1.0: `if self.current_credits <= 0: ... return` (`main.py:3574-3575`).
- Списание кредита происходит **по факту находки**: `on_target_found` → `_process_found` →
  `spend_credit("exchange")` (`main.py:3751-3763`).
- ESC: глобальный хук `keyboard.hook(_esc_handler)` (`main.py:1888`), ведёт в `_emergency_stop`
  (`main.py:3717+`), который выставляет `self._esc_stopped = True` и глушит движки.
- Вкладка называется `tab_hunt`, подписи «БИРЖИ»/«EXCHANGE» лежат в двух словарях `LANGS`
  (`main.py:188` и `main.py:261`) — любая новая строка UI обязана быть добавлена в оба.
- Прецедент «новый экземпляр движка на каждый старт»: `HuntEngine.start()` конструирует новый
  `PacmanEngine` при каждом вызове (`engine.py:178-196`), а не переиспользует старый.

### 2.5 Аналоги для файлового цикла — честная фиксация

Прямого аналога «сессионная папка с кадрами + jsonl-журнал» в проекте **нет**. Ближайшие фундаментальные
механизмы, которые реально существуют и на которые опирается Часть A: одноразовый захват `mss`
(`navigator.py:1007-1012`), журналирование строками в файл с немедленной записью (`engine.py:19-27`,
`_roy_log`), и потоковая модель «daemon-тред + флаг `is_running`» (`navigator.py:988-1000`,
`engine.py:334-337`). Притягивать нерелевантные «похожие» подсистемы ради галочки не стал.

### 2.6 `debug_reporter.py` — **[→ Часть A-М]**

Шесть фактов о существующем канале в debug-Telegram (глушение ошибок, синхронная часть `report_find`,
формат bbox, источник `hwid`, отсутствие валидации `shot_type` на сервере) перенесены без изменений в
Часть A-М, секция 2.6. Часть A этот канал не использует.

### 2.7 Монетизация 1.0 — **[→ Часть A-М]**

Семизвенная цепочка списания 1.0 (гейт баланса → привязка callback'а → момент вызова → `spend_credit` →
реакции GUI → независимость от OCR) перенесена без изменений в Часть A-М, секция 2.7.

---
