# Исходящие Claude → Gemini

> Этот файл заполняет Claude по запросу пользователя.
> Gemini читает отсюда контекст для анализа.

---

## Отчёт: Диагностика "бот бегает быстро после рестарта" + комплексный фикс
**Дата:** 2026-05-26 23:59 Kyiv | **Коммит:** 798d0ec | **Тесты:** 38 green

### Диагностика (4 параллельных агента)

**Агент 1 — тайминг `_run()` цикла:**
- `loop_start` сбрасывается ПОСЛЕ `_exchange_detected()` → таймер норм
- НАСТОЯЩАЯ ПРОБЛЕМА: старый `_run()` тред жив, новый стартует → 2 треда = 2x скорость джойстика
- Фикс: `PacmanEngine.start()` вызывает `self._thread.join(timeout=3.0)` перед стартом нового треда

**Агент 2 — дублирующие треды:**
- Подтверждено: с `delay=0`, `heartbeat` и `roy_scan` треды могут дублироваться
- Старый тред "оживает" когда `is_running` снова становится True
- Фикс: `_bg_gen` счётчик — каждый тред хранит свой `gen`, выходит если `_bg_gen != gen`

**Агент 3 — состояние навигатора:**
- `navigation_enabled=False` + YOLO инференс <2с → `sleep(0.01)` вместо 2с = "tight loop"
- YOLO гонка: блок ставится ПОСЛЕ `pacman.start()` → первая итерация видит `_yolo_unblock_time=0`
- Фикс: `_initial_yolo_block_sec=30.0` устанавливается ДО `pacman.start()`

**Агент 4 — полный flow trace:**
- С текущим `delay=10`: чистый рестарт, старый тред выходит за 10с. Гонка минимальна но есть
- С планируемым `delay=0`: окно 0–2с где оба треда работают параллельно → double click rate
- Точный "горячий участок": `engine.py:198 pacman.start()` → `engine.py:231 _yolo_unblock_time` (гонка ~0мс)

### Все найденные баги и их фиксы

| # | Баг | Причина | Фикс | Файл |
|---|-----|---------|------|------|
| 1 | **Бот бегает 2x быстро** | Двойной `_run()` тред при delay=0 | `thread.join(3s)` в `PacmanEngine.start()` | navigator.py |
| 2 | **Повторная детекция той же биржи** | YOLO блок = 0 при старте нового треда | `_initial_yolo_block_sec=30.0` ДО `pacman.start()` | engine.py |
| 3 | **Дубли heartbeat/roy_scan тредов** | Нет защиты при быстром рестарте | `_bg_gen` генерационный счётчик | engine.py |
| 4 | **Бот сразу уходит (no 10s dialog)** | `time.sleep(10)` был убран ранее | Возвращён в шаг 10 `_exchange_detected` | navigator.py |
| 5 | **Двойной звук биржи** | `_roy_update_list` считает собств. координаты "новыми" | Pre-populate `_roy_pool_known_ids` в `_on_pool_auto_refresh` | main.py |
| 6 | **restart_callback(10) ненужная задержка** | Пауза дублировалась (sleep(10) + delay(10)) | Изменено на `restart_callback(0)` | navigator.py |

### Итоговое поведение после фиксов

1. YOLO находит биржу → клик → звук → OCR
2. **time.sleep(10)** → диалог открыт 10 секунд, пользователь видит координаты
3. ESC закрывает диалог
4. `restart_callback(0)` → немедленный стоп
5. `PacmanEngine.start()` ждёт старый тред (`join(3s)`)
6. YOLO-блок `30с` устанавливается ДО старта нового треда
7. Новый тред стартует, navigator.reset() → HOMING фаза, скорость = `move_wait=2.0с`
8. Через 30с YOLO снова активен, бот ушёл далеко от старой биржи

### Состояние тестов
- `test_exchange_flow_v2.py`: 12 новых тестов (RED→GREEN) ✅
- `test_restart_after_exchange.py`: 10 тестов (обновлены под новое поведение) ✅
- `test_exchange_backtrack.py`: 2 pre-existing фикса (missing attrs) ✅
- `test_exchange_guard.py`: 1 pre-existing фикс (`on_pool_refresh_callback`) ✅
- **Итого: 38 тестов green**

### Что НЕ входило в этот фикс (отдельные задачи)
- Тест плавного хода при `navigation_enabled=False` (tight loop при малом move_wait)
- Полный интеграционный тест живого запуска

---

## Постдеплойный отчёт: Живой тест ROY — проблемы и слепые пятна агентов
**Дата:** 2026-05-26 21:30 Kyiv | **Статус:** IN INVESTIGATION

### Что произошло после деплоя B1–B4

После успешного деплоя (UniqueConstraint в БД, rate limit, IntegrityError, kingdom filter) пользователь провёл живой тест. Бот находил биржи, кликал, открывал диалоги — но координаты **не появлялись в пуле**, и бот визуально "останавливался" после находки.

### Два отдельных явления (часто путаются)

**Явление 1: "[ROY] Ивент не активен — скан не засчитан."**
- НЕ баг. Формула `_is_trade_routes_active()` правильная.
- Диагностика показала: NOW=21:12 Kyiv, окно ивента 25.05 20:00→26.05 20:00. Ивент закончился 1ч12мин назад.
- Это блокирует только начисление +45с баланса, но НЕ передачу координат.

**Явление 2: Координаты не передаются в пул**
- Источник: `_roy_on_found()` вызывается синхронно в потоке навигатора.
- Цепочка: YOLO detection → клик → sleep(0.5) → `on_found_callback()` → `_build_roy_wrapper` → `_roy_on_found` → `wait_and_read(4.0с)` → `_find_dialog` (HSV) → OCR → `report()`
- **Диагностика НЕ завершена**: добавлено полное логирование в `roy_debug.log` + сохранение скриншотов `roy_dbg_*.png`. Ожидаем следующего теста.

**Явление 3: "Бот не возобновляет поиск"**
- Вероятно не баг: после находки биржи navigator.py делает `sleep(10)` + YOLO-блок 20с = ~30с паузы. Это нормально.
- Если `wait_and_read` зависает (pytesseract timeout не работает), поток навигатора может блокироваться. Требует подтверждения.

### Почему перекрёстные агенты не обнаружили эту проблему

**Критический антипаттерн агентного тестирования:** Все 3 агента тестировали **серверную логику** через HTTP-запросы с `AsyncClient` + SQLite in-memory. Ни один агент не проверял:

1. **Клиентский OCR-поток**: `wait_and_read` → `_find_dialog` (HSV цвета диалога) → pytesseract. Это живой экранный захват — не тестируется без реального экрана.
2. **Синхронную блокировку**: `_roy_on_found` блокирует поток навигатора на 4с. В тестах нет навигатора, нет блокировки.
3. **Реальный диалог биржи**: HSV-маска `_DIALOG_BG_LOW/HIGH` настроена под конкретные цвета игры. Без скриншотов проверить нельзя.

**Структурная причина:** Агентный аудит был сфокусирован на "сервер + бизнес-логика". Клиентская часть (OCR, захват экрана, HSV-детекция) требует **интеграционного теста с реальной игрой** — это находится за пределами возможностей статического/unit анализа.

### Что добавлено для диагностики (2026-05-26)

- `engine.py`: `_roy_log()` пишет в `roy_debug.log` + stdout. Логируется каждый шаг `_build_roy_wrapper` и `_roy_on_found`.
- `exchange_reader.py`: `_log()` пишет в тот же `roy_debug.log`. Логируется: mss/tesseract наличие, каждая попытка `_find_dialog`, raw OCR текст, результат парсинга.
- Сохраняются скриншоты: `roy_dbg_fullscreen.png`, `roy_dbg_coord_roi.png`, `roy_dbg_progress_roi.png` при обнаружении диалога.

### Гипотезы (приоритет)

1. **HSV-маска диалога не совпадает** — цвет фона диалога в текущей версии игры отличается от захардкоженных `_DIALOG_BG_LOW/HIGH`. Тогда `_find_dialog` возвращает None каждый раз.
2. **Диалог закрывается до OCR** — `wait_and_read` вызывается с задержкой, пользователь уже закрыл диалог вручную.
3. **Tesseract не находит текст** — HSV-маска красного текста координат не срабатывает.

### Следующий шаг

Запустить бота, дождаться находки биржи, прислать `roy_debug.log` + `roy_dbg_coord_roi.png`. После этого можно точно диагностировать и исправить.

---

## КРИТИЧЕСКИЙ ОТЧЁТ: Корневая причина — _find_dialog захватывает весь экран
**Дата:** 2026-05-26 22:00 Kyiv | **Статус:** FIX APPLIED, PENDING TEST

### Что показал живой тест (roy_debug.log + скриншоты)

**roy_debug.log:**
```
21:16:20.564 [ROY] >>> on_found_callback сработал — запускаю ROY OCR
21:16:20.625 [OCR] _find_dialog: диалог найден @ (0,48) размер 1456×899
21:16:21.089 [OCR] _ocr_coords: сырой текст = 'Ra\n\nee 1M\n\n7\n\n4.3M (FP 74.6M ...'
21:16:21.089 [OCR] _ocr_coords: парсинг → None
... (4 попытки, все None)
21:16:24.836 [OCR] wait_and_read: таймаут — диалог не найден/не распознан
```

**Полноэкранный скриншот:** Диалог биржи "Биржа наёмников" ОТКРЫТ и виден в центре экрана (~380×320 px).

**Coord ROI скриншот:** Показывает топ-бар ресурсов (60.1M, 74.3M...) — НЕПРАВИЛЬНАЯ область.

### Корневая причина (одна, точная)

`_find_dialog` ищет самый БОЛЬШОЙ беж-контур на экране:
```python
c = max(contours, key=cv2.contourArea)  # ← БАГОВАННАЯ СТРОКА
```

Весь игровой фон (карта, UI-панели) имеет беж/кремовые цвета в диапазоне `_DIALOG_BG_LOW/HIGH`. После морфологического закрытия (20×20 ядро) весь экран сливается в один гигантский контур 1456×899.

Реальный попап биржи (~380×320) ТОЖЕ имеет беж-фон, но его контур МЕНЬШЕ фонового. Функция берёт максимальный — и выбирает весь экран.

В результате `_COORD_ROI_REL = (0.0, 0.03, 1.0, 0.20)` вырезает верхние 3-20% от (0,48)-(1456,947), что даёт топ-бар ресурсов, а не область координат внутри попапа.

### Почему раньше работало (на скриншотах Gemini)

Тесты OCR ранее проводились на изолированных PNG-файлах диалога. Там НЕТ игрового фона — только попап. `_find_dialog` корректно находил его. В живом прогоне на полном экране — фон побеждает.

### Применённый фикс (exchange_reader.py)

Добавлены константы:
```python
_MAX_DIALOG_W = 900
_MAX_DIALOG_H = 750
```

`_find_dialog` переписан: итерируется по ВСЕМ контурам (отсортированным по площади), выбирает наибольший В ДОПУСТИМОМ ДИАПАЗОНЕ размеров. Контуры больше _MAX отсекаются с логом "фон игры — пропускаем".

### Что нужно проверить при следующем тесте

1. Лог должен показать: `_find_dialog: контур 1456×899 слишком большой (фон игры) — пропускаем`
2. Затем: `_find_dialog: диалог найден @ (X,Y) размер ~380×320`
3. Coord ROI должен показывать ВЕРХНЮЮ ЧАСТЬ ПОПАПА (заголовок с координатами), а не топ-бар ресурсов
4. Если координаты K:X:Y не появятся в coord_roi — нужно скорректировать `_COORD_ROI_REL`

### Антипаттерн для будущих агентных аудитов

**Тестирование OCR только на изолированных PNG-файлах без игрового фона = ложная уверенность.** Любой модуль, работающий с полным экраном, ОБЯЗАН тестироваться с реальным скриншотом в контексте запущенной игры. Иначе детекция по цвету всегда будет уязвима к фоновому шуму.

---

## ПОЛНЫЙ АУДИТ СОСТОЯНИЯ: ROY + Бот (10 агентов)
**Дата:** 2026-05-26 23:00 Kyiv | **Версия:** 1.5.7 | **Метод:** 10 независимых агентов параллельно

---

### A. ЧТО УЖЕ ИСПРАВЛЕНО (коммит 31624a2)

| # | Проблема | Статус | Где |
|---|----------|--------|-----|
| 1 | report() был daemon-поток → HTTP убивался при остановке | ✅ FIXED | `roy_client.py:40` — `t.daemon = False` перед `t.start()` |
| 2 | AFK фильтр (≥15% изменение миникарты) блокировал scan() | ✅ FIXED | `engine.py:266` — scan() вызывается безусловно каждые 30с |
| 3 | Event gate (5-дневный цикл) блокировал scan() | ✅ FIXED | `_is_trade_routes_active()` полностью удалена |
| 4 | GUI показывал "до початку: 3д 21ч 27м" вместо активного статуса | ✅ FIXED | `main.py` — `_update_trade_routes_labels()` → "🟢 Активно" каждые 60с |
| 5 | ESC в шаге 11 запускал `_emergency_stop()` через keyboard.hook | ✅ FIXED | `navigator.py:950,1089,1092` — флаг `_suppressing_esc` |
| 6 | ESC hook в main.py не проверял флаг подавления | ✅ FIXED | `main.py:1488–1495` — проверяет `_suppressing_esc` |

---

### B. ВЕРИФИКАЦИЯ ФИКСОВ (точные данные агентов)

**report() thread:**
```python
# roy_client.py:39-41
t = threading.Thread(target=_send)
t.daemon = False  # ждём завершения HTTP-запроса перед выходом процесса
t.start()
```
→ `t.daemon = False` стоит ДО `t.start()`. Таймаут 5с. Поток не убивается при стопе.

**scan() loop:**
```python
# engine.py:266
ok = self._roy_client.scan(kingdom=self.roy_kingdom or None)
_roy_log(f"scan() → {'OK +45с' if ok else 'FAIL'} | diff={diff_frac:.1%}")
```
→ `diff_frac` вычисляется, но НЕ является условием. scan() вызывается всегда. Docstring на строке 238 устарел (всё ещё упоминает ≥15%) — косметически.

**_suppressing_esc:**
- `navigator.py:950` — инициализация: `self._suppressing_esc = False`
- `navigator.py:1089` — шаг 11: `self._suppressing_esc = True`
- `navigator.py:1090` — `pyautogui.press('escape')`
- `navigator.py:1092` — `self._suppressing_esc = False`
- Других `pyautogui.press('escape')` в navigator.py НЕТ. Флаг защищает единственное нажатие ESC.

**ESC hook:**
```python
def _esc_handler(event):
    if event.name == 'esc' and event.event_type == 'down':
        pacman = getattr(self.engine, '_pacman', None) if self.is_running else None
        if pacman and getattr(pacman, '_suppressing_esc', False):
            return  # ← пропускаем, если бот сам жмёт ESC
        self.after(0, self._emergency_stop)
```
→ Работает корректно. GIL защищает от race condition на практике.

**Тесты:** `test_exchange_esc_guard.py` — 4/4 PASS.

---

### C. ЧТО НЕ РЕАЛИЗОВАНО

**Stop/auto-restart после находки биржи** — НЕ СУЩЕСТВУЕТ в коде.

Пользователь подтвердил желаемое поведение:
> "бот находит биржу → СТОП (не спать) → передаёт координаты → пауза 10с → автоматический СТАРТ"

Текущее поведение (шаги _exchange_detected):
- Шаг 9: on_found_callback (OCR → report)
- **Шаг 10: `time.sleep(10)` — жёсткая пауза 10с (БОТ НЕ ОСТАНОВЛЕН, ПРОСТО СПИТ)**
- Шаг 11: ESC, закрыть диалог
- Шаг 12: YOLO-блок 20с, навигация продолжается

→ Бот НЕ останавливается. Он спит 10с потом продолжает. Пользователь это видит как "скачет" (бот замирает на 10с, потом резко двигается).

**Что нужно реализовать:**
```
exchange found → engine.stop() → join report() thread (ждём HTTP) → 10с timer → engine.start(saved_params)
```

Требует:
1. `engine.py`: сохранить start params в `self._last_start_kwargs`
2. `engine.py`: новый метод `restart_after_exchange()` — stop() + threading.Timer(10, start)
3. `main.py`: callback обновляет GUI (кнопка СТАРТ/СТОП)

---

### D. АНАЛИЗ ЛОГОВ (roy_debug.log, последние записи)

| Timestamp | Событие | Статус |
|-----------|---------|--------|
| 22:11:11 | original_cb ERROR: RuntimeError('GUI crash') | ⚠️ GUI уничтожен, callback сработал |
| 22:23:32 | original_cb ERROR: RuntimeError('GUI crash') | ⚠️ То же |
| 22:24:03 | "Ивент не активен — скан не засчитан" | ⚠️ СТАРЫЙ КОД ещё работал |
| 22:39:39 | K=2 X=803 Y=487 64% → report() отправлен | ✅ OCR работает, координаты уходят |

**Критическое наблюдение по логу:**
- На 22:24:03 ещё работал старый код с event gate → balance оставался 0 → `/roy/pool` возвращал `no_balance`
- Это и есть причина "пул пуст" — НЕ было накоплено баланса из-за блокированных сканов

**RuntimeError('GUI crash'):** Возникает в `on_last_exchange_callback` → `_on_last_exchange_found()` в main.py. После emergency stop GUI может быть уничтожен, но callback из потока навигатора ещё вызывается. Не критично (обёрнут в try/except в engine.py:217), но шумит в логах.

---

### E. СЕРВЕРНАЯ ЛОГИКА ROY (server/roy.py)

| Эндпоинт | Ключевые условия |
|----------|-----------------|
| `/roy/scan` | Rate limit: 28с между вызовами. Клиент шлёт каждые 30с → OK |
| `/roy/pool` | Требует `balance_sec > 0`, TTL 20мин, percent < 90. Kingdom — опционально (если не задан — ВСЕ ГОСы) |
| `/roy/report` | Без фильтра по percent при INSERT. Хранит всё. Фильтр только при выдаче пула |

**Цепочка "пул пуст" полностью объяснена:**
1. Старый event gate блокировал scan() → balance_sec = 0
2. report() был daemon → HTTP не доходил
3. Фикс применён в 31624a2
4. **Требуется перезапуск main.py с новым кодом** — после этого:
   - scan() каждые 30с → balance растёт
   - report() non-daemon → координаты доходят до сервера
   - `/roy/pool` должен отдавать записи

---

### F. ИТОГОВЫЙ СПИСОК ЗАДАЧ

| Задача | Приоритет | Статус |
|--------|-----------|--------|
| Перезапустить main.py (новый код 31624a2) | 🔴 КРИТИЧНО | Требует действия пользователя |
| Stop/auto-restart после биржи | 🔴 ВЫСОКИЙ | Не реализован |
| Убрать sleep(10) шаг 10 (заменить на stop/restart) | 🔴 ВЫСОКИЙ | Часть stop/auto-restart |
| RuntimeError GUI crash в callback | 🟡 СРЕДНИЙ | Не мешает работе |
| Обновить docstring _start_roy_scan | 🟢 НИЗКИЙ | Косметика |

---

## Отчёт: Перекрёстный аудит системы Биржи / РОЙ
**Дата:** 2026-05-26 (Kyiv) | **Метод:** 3 независимых агента | **Статус:** NEEDS FIXES

---

### Контекст

Провели полный кросс-аудит тремя независимыми агентами параллельно.

**Область проверки:**
- Захват диалога биржи и OCR координат (`roy/exchange_reader.py`)
- Цепочка доставки координат в РОЙ-пул (engine.py → roy_client → server/roy.py /report)
- Система начисления времени за сканирование (Proof of Scan: /scan, /pool, /balance)

**Стек:** Python 3.13 / FastAPI / PostgreSQL / SQLAlchemy async / OpenCV / pytesseract / mss.

---

## ИТОГ: 8 БАГОВ + 13 РИСКОВ

---

## 🔴 БАГИ

### BUG-1 🔴🔴 КРИТИЧНО — Нет rate limit на POST /roy/scan
**Файл:** `server/roy.py`

`/roy/report` защищён `_report_rate` (10 сек между запросами). `/roy/scan` — не защищён вообще.
Любой знающий свой HWID может слать POST /roy/scan каждую секунду: `balance_sec += 45` без ограничений.
Баланс растёт неограниченно → бесплатный доступ к пулу координат.

**Фикс:** добавить `_scan_rate: dict[str, float]` аналогично `_report_rate`, интервал 25–28 сек.

```python
# В начале файла:
_scan_rate: dict[str, float] = {}

# В report_scan():
if time.time() - _scan_rate.get(req.hwid, 0) < 25:
    return {"success": True, "note": "rate_limited"}
_scan_rate[req.hwid] = time.time()
```

---

### BUG-2 🔴 ВЫСОКИЙ — Исключение в `original_cb` глушит `_roy_on_found`
**Файл:** `engine.py:167–172`

```python
def _roy_found_wrapper(*args, **kwargs):
    if original_cb:
        original_cb(*args, **kwargs)   # ← если бросит исключение
    self._roy_on_found()               # ← сюда не дойдёт
```

Если GUI-callback бросит любое исключение — координата не уйдёт в РОЙ.
`_roy_on_found` сам по себе защищён try/except, но до него выполнение не доходит.

**Фикс:**
```python
def _roy_found_wrapper(*args, **kwargs):
    if original_cb:
        try:
            original_cb(*args, **kwargs)
        except Exception as e:
            print(f"[ROY] original_cb ERROR: {e!r}")
    self._roy_on_found()
```

---

### BUG-3 🔴 ВЫСОКИЙ — Нет UniqueConstraint(kingdom, x, y) в RoyPool
**Файл:** `server/models.py`

В модели `RoyPool` есть одиночные индексы на `kingdom`, `reporter_hwid`, `expires_at`,
но нет составного уникального индекса на `(kingdom, x, y)`.

Следствие: два одновременных репорта одной биржи создают дубликаты в таблице тихо, без ошибок.
Пул засоряется дублями, SELECT возвращает один объект дважды.

**Фикс:** Alembic миграция + обработка IntegrityError в `/roy/report`:
```python
# models.py — добавить в RoyPool:
__table_args__ = (
    UniqueConstraint('kingdom', 'x', 'y', name='uq_roypool_kingdom_x_y'),
)

# server/roy.py — в report_exchange():
from sqlalchemy.exc import IntegrityError
try:
    async with db.begin():
        ...  # существующий upsert код
except IntegrityError:
    pass  # дубль вставлен параллельно — ок
```

---

### BUG-4 🔴 ВЫСОКИЙ — Race condition в /roy/report (TOCTOU)
**Файл:** `server/roy.py:194–215`

Два параллельных запроса:
1. Оба выполняют `SELECT ... scalar_one_or_none()` → оба получают `None`
2. Оба входят в `async with db.begin()`
3. Оба выполняют `db.add(RoyPool(...))` → два дубликата

Без UniqueConstraint (BUG-3) IntegrityError не бросается. Исправляется вместе с BUG-3.

---

### BUG-5 🔴 СРЕДНИЙ — Race condition в GET /roy/pool?consume=true (TOCTOU)
**Файл:** `server/roy.py:326–340`

Текущая логика:
```python
# Чтение вне транзакции:
bal_row = await db.execute(select(RoyBalance)...).scalar_one_or_none()
balance = bal_row.balance_sec   # читаем 90
...
# Списание в отдельной транзакции:
if consume and bal_row:
    async with db.begin():
        bal_row.balance_sec = max(0, bal_row.balance_sec - POOL_COST_SEC)
```

Два одновременных запроса оба прочитают `balance=90`, оба спишут 60 → итог 30 вместо 0.
Один запрос получает пул бесплатно.

**Важно:** `consume=True` нигде в текущем боте не вызывается (`_roy_refresh_pool` всегда `consume=False`). Баг не активен сейчас, но должен быть закрыт до включения consume-функциональности.

**Фикс:** Объединить чтение и списание в одну транзакцию с SELECT FOR UPDATE:
```python
async with db.begin():
    bal_row = (await db.execute(
        select(RoyBalance).where(RoyBalance.hwid == hwid).with_for_update()
    )).scalar_one_or_none()
    balance = bal_row.balance_sec if bal_row else 0
    if balance <= 0:
        return {"success": False, "reason": "no_balance", "balance_sec": 0, "pool": []}
    # ... запрос entries ...
    if consume:
        bal_row.balance_sec = max(0, balance - POOL_COST_SEC)
        bal_row.updated_at = datetime.now(timezone.utc)
```

---

### BUG-6 🔴 СРЕДНИЙ — bal_row вне транзакции при consume (DIRTY READ)
**Файл:** `server/roy.py:320–340`

`bal_row` читается без транзакции (implicit read), затем изменяется внутри `async with db.begin()`.
Значение `balance_sec` может устареть между чтением и записью.
Решается тем же фиксом что BUG-5.

---

### BUG-7 🔴 СРЕДНИЙ — Жадный `[^\d]*` в _parse_coords
**Файл:** `roy/exchange_reader.py:175`

Паттерн:
```python
pattern = r'K[:\s]*(\d+)[^\d]*X[:\s]*(\d+)[^\d]*Y[:\s]*(\d+)'
```

`[^\d]*` между числами матчит любое количество не-цифр.
Если в ROI попадают чужие числа (`K:471 12% X:383 Y:812`), `[^\d]*` остановится на `1` от `12%` и вернёт X=12 вместо 383.

**Фикс:** ограничить количество символов между числами:
```python
pattern = r'K[:\s]*(\d+)\D{0,20}X[:\s]*(\d+)\D{0,20}Y[:\s]*(\d+)'
```

---

### BUG-8 🔴 НИЗКИЙ — mss=None бросает RuntimeError на каждой бирже
**Файл:** `roy/exchange_reader.py:96`

`pytesseract=None` → тихий `return None` (graceful).
`mss=None` → `raise RuntimeError("mss not installed")` на каждой бирже.
Несимметричное поведение: оба должны вести себя одинаково.

**Фикс:** в `_grab_screen()` добавить `if mss is None: return None`, propagate None через _try_read.

---

## ⚠️ РИСКИ (не баги, но требуют внимания)

| # | Область | Описание |
|---|---|---|
| R1 | Финансы | `balance_sec` без верхней границы (следствие BUG-1) |
| R2 | Финансы | `notify_balance_changed` не вызывается после `/roy/scan` — long-poll vault не разбудит бот |
| R3 | OCR | Цветовые маски `_RED_LOW1/HIGH1` объявлены в exchange_reader.py, но в `_ocr_coords()` **не применяются** — OCR работает на сыром grayscale |
| R4 | OCR | `_GREEN_LOW/HIGH` объявлены, но в fallback `_measure_progress()` не используются — fallback использует другой захардкоженный диапазон |
| R5 | OCR | `_MIN_DIALOG_W=200, _MIN_DIALOG_H=150` слишком малы — tooltip/нотификация 200×150 ложно опознаётся как диалог биржи. Рекомендуется W≥320, H≥240 |
| R6 | OCR | `max(contours)` без проверки aspect ratio — HUD или инвентарь с бежевым фоном может быть опознан как диалог |
| R7 | OCR | S-диапазон 20–100 для поиска диалога может промахнуться на мониторах с насыщенными цветами |
| R8 | OCR | `pytesseract=None` — тихая потеря всех координат без предупреждения пользователю в GUI |
| R9 | OCR | Блокировка навигатора 4+3с (wait_and_read + tesseract timeout) — дрейф маршрута при плотном сканировании |
| R10 | AFK | Фаза RETURNING с пустым океаном → diff <15% → скан не засчитывается (потеря начислений при длинном возврате) |
| R11 | Архитектура | GET /roy/pool без фильтра по kingdom — пользователь видит биржи из чужих ГОСов |
| R12 | Архитектура | In-memory rate limiter на `/report` сбрасывается при рестарте сервиса |
| R13 | Треды | `scan()` синхронный в фоновом треде — при таймауте 5с цикл скана сдвигается |

---

## Вопросы к Gemini

1. **BUG-1 Rate limit:** Правильный интервал для `_scan_rate` — 25 или 28 сек? Клиент шлёт раз в 30с, нужно дать запас на задержку сети.

2. **BUG-3 UniqueConstraint:** Стоит ли добавить уникальный индекс на `(kingdom, x, y, expires_at)` (составной с TTL) вместо просто `(kingdom, x, y)`? Чтобы две разные временны́е "волны" одной биржи хранились отдельно?

3. **R11 Глобальный vs per-kingdom пул:** Архитектурный выбор — РОЙ сейчас глобальный (все ГОСы в одной таблице). Правильно ли это? Биржи живут 2–5 мин, координаты актуальны только в своём ГОСе. Предлагаю добавить фильтр `?kingdom=N` в GET /pool — обратно совместимо (без параметра = все).

4. **R2 notify_balance_changed после scan:** Стоит ли добавить вызов если vault/sync используется только для основных кредитов, а ROY-баланс отображается отдельной кнопкой? Или это оверинжиниринг?

5. **Цветовые маски в OCR (R3):** Применять `_RED_LOW1/HIGH1` маску к ROI перед tesseract — повысит точность или создаст новые ложные срабатывания при недостаточном освещении экрана?


---

## ПОЛНЫЙ ПРОГОН ROY + БИРЖА: Хардкод ROI — финальный аудит
**Дата:** 2026-05-26 22:30 Kyiv | **Статус:** FIX COMPLETE, READY FOR LIVE TEST

### Что изменилось с предыдущего отчёта

Предыдущий фикс (_MAX_DIALOG_W/H) был полумерой — оставлял динамический поиск контуров.
Окончательное решение: _find_dialog полностью УДАЛЁН. Вместо него хардкод ROI.

### Новая архитектура OCR (exchange_reader.py, коммит ad98a0a)

Удалено: _find_dialog, _grab_screen, _crop_roi, _DIALOG_BG_LOW/HIGH, весь HSV код.

Добавлено: Hardcoded ROI в reference-системе 1920x1080, верифицировано по 3 скриншотам:
- COORD_ROI: x=636, y=330, w=651, h=115 (строка K:X:Y, +20px запас с каждой стороны)
- PROGRESS_ROI: x=636, y=540, w=651, h=120 (прогресс сделок)

Привязка к профилю: coord_manager.to_region(x_ref, y_ref, w_ref, h_ref) масштабирует
reference coords по scale_x/scale_y профиля пользователя.

OCR pipeline: mss.grab → 4x upscale → threshold(180, THRESH_BINARY) → psm11, timeout=3

### Результаты тестирования на 3 скриншотах (1920x1080)

Биржа_15.04.png:    K=1013, X=605, Y=857, progress=26% OK
Биржа_15.04_2.png:  K=1013, X=605, Y=857, progress=46% OK
Биржа_15.04_3.png:  K=1013, X=605, Y=857, progress=69% OK

### Перекрёстный аудит (3 независимых агента, все PASS)

Agent 1 — engine.py (12-шаговый цикл): 6/6 PASS
  - 12 шагов в navigator.py:1006-1092 в правильном порядке
  - on_found_callback синхронно ДО sleep(10)
  - _build_roy_wrapper: original_cb потом _roy_on_found
  - _trigger_yolo_block(20)
  - AFK (>=15% diff minimap) + event gate оба присутствуют
  - _is_trade_routes_active() блокирует только scan(), НЕ report()

Agent 2 — exchange_reader.py: 6/6 PASS
  - _find_dialog полностью удалён
  - _grab_region -> coord_manager.to_region() -> mss.grab()
  - 4x upscale + threshold(180) + PSM 11
  - Screen coords с профилем client: (636, 331, 651, 115) — правильно
  - Retry loop 0.3с, return None при неудаче
  - ВАЖНО: to_region() (не to_region_dialog()) — ПРАВИЛЬНО.
    dialog_offset=60 предназначен для криптов. Reference coords измерены
    с полного desktop экрана -> dialog_offset добавлять нельзя (сдвинет ROI на 60px вниз)

Agent 3 — ROY client/server: 7/7 PASS
  - report() -> POST https://api.total-hunter.com/roy/report
  - Сетевые ошибки: try/except, бот не крашится
  - Pydantic принимает: kingdom, x, y, percent
  - UniqueConstraint('kingdom','x','y') в RoyPool
  - IntegrityError -> 200 OK
  - percent<90 guard в engine.py + на сервере (двойная защита)
  - roy/__init__.py существует (PyInstaller/Nuitka)

### Полная цепочка передачи координат (актуальная)

YOLO -> navigator.py:_exchange_detected (12 шагов)
-> on_found_callback() -> _build_roy_wrapper -> _roy_on_found()
-> wait_and_read(4.0s) каждые 0.3с:
   _grab_region(636, 330, 651, 115)
   -> coord_manager.to_region() -> screen_rect
   -> mss.grab() -> BGR -> 4x -> threshold(180) -> psm11
   -> _parse_coords() -> (K, X, Y)
-> if percent < 90: _roy_client.report(K, X, Y, P)
-> POST /roy/report -> DB INSERT/UPDATE

### Для финального теста

1. Новая сборка или git pull + .py напрямую
2. Бот находит биржу, roy_debug.log должен показать:
   _grab_region: ref=(636,330,651,115) -> screen=(636,331,651,115)
   _ocr_coords: парсинг -> (1013, 605, 857)  (или другие реальные координаты)
3. Координаты должны появиться в пуле на сервере

### Коммиты

ad98a0a - fix: exchange_reader hardcoded ROI, remove _find_dialog
3779de3 - docs: exchange_bot_spec updated ROY OCR pipeline
