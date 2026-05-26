# ЭТАЛОН: Механика Биржевого Бота

> **Статус:** Канонический документ. Любое изменение механики биржевого бота ОБЯЗАНО быть сверено с этим файлом.
> **Последнее обновление:** 2026-05-26 (v1.5.8 — hardcoded ROI, remove _find_dialog)
> **Связанные файлы:** `navigator.py`, `engine.py`, `roy/exchange_reader.py`, `CLAUDE.md`

---

## 🔒 ЗОЛОТОЕ ПРАВИЛО БИРЖЕВОГО БОТА

**Змейка — инструмент. Биржа — цель.**

Любое изменение кода биржевого бота проверяется по чеклисту:
1. Продолжает ли бот двигаться после находки биржи?
2. Не создаёт ли изменение повторный клик по той же бирже?
3. Сохраняется ли state змейки (DIVING/RETURNING/etc) между биржами?
4. Не блокирует ли OCR основной поток навсегда?

Если хотя бы один пункт нарушен — изменение НЕ принимается.

---

## СХЕМА: Полный цикл нахождения биржи

```
┌─────────────────────────────────────────────────────────────┐
│ ГЛАВНЫЙ ЦИКЛ (PacmanEngine._run)                            │
│                                                             │
│  while is_running:                                          │
│    1. Захват frame                                          │
│    2. is_water = проверка центра экрана                     │
│    3. [если time.time() >= _yolo_unblock_time]:             │
│         YOLO.predict(frame) → нашли биржу?                  │
│              ↓ ДА                                           │
│         _exchange_detected() ◄──── ОСНОВНАЯ ОБРАБОТКА       │
│         loop_start = time.time()  (сброс таймера)           │
│              ↓ после возврата                               │
│    4. joystick.step()  ← змейка продолжает с того же места │
│    5. sleep(move_wait - elapsed)                            │
│    6. Захват нового frame                                   │
└─────────────────────────────────────────────────────────────┘
```

---

## СХЕМА: _exchange_detected (12 шагов)

```
ШАГ 1:  FIND-скрин → Telegram debug (async, не блокирует)
         │
ШАГ 2:  sleep(0.5) ← гасим инерцию карты
         │
ШАГ 3:  fresh_scan() ← новый YOLO с актуальными координатами
         │
         ├── НАШЛИ ────────────────────────────────┐
         │                                         │
ШАГ 4:  НЕ НАШЛИ → _backtrack_step()              │
         │          └─ клик джойстиком назад        │
         │             sleep(0.3)                   │
         │             fresh_scan()                 │
         │             ├── НАШЛИ ──────────────────┤
         │             └── НЕТ → return (ложная    │
         │                        детекция)         │
         │                                         ↓
ШАГ 5:  pyautogui.click(cx, cy=верхняя_треть_bbox)
         │
ШАГ 6:  winsound (звук попадания, async)
         │
ШАГ 7:  sleep(0.5) ← ждём открытие диалога
         │
ШАГ 8:  DIALOG-скрин → Telegram debug (async)
         │
ШАГ 9:  on_found_callback() ← ROY OCR (СИНХРОННО, до ~4с)
         │  └─ wait_and_read(timeout=4.0)
         │      └─ pytesseract(timeout=3) → K:XXX X:XXX Y:XXX
         │      └─ _roy_client.report() → сервер → пул
         │
ШАГ 10: sleep(10) ← бот стоит, игрок отправляет войска
         │
ШАГ 11: pyautogui.press('escape') + sleep(0.3)
         │
ШАГ 12: _trigger_yolo_block(20)
         └─ _yolo_unblock_time = time.time() + 20
              ↓
         ВОЗВРАТ В _run() → joystick.step() → змейка продолжается
```

---

## ВРЕМЕННА́Я ШКАЛА одного полного цикла

```
t=0.00  YOLO детектировал биржу
t=0.50  Свежий скан (инерция погашена)
t=0.50  Клик по бирже
t=1.00  Диалог открыт
t=1.00  ROY OCR (0-4 сек, timeout=3 на каждый pytesseract вызов)
t=5.00  OCR завершён (максимум)
t=15.30 10 секунд паузы истекли
t=15.60 ESC, диалог закрыт
t=15.60 YOLO-блок запущен: _yolo_unblock_time = t + 20с
t=15.60 ПЕРВЫЙ ШАГ НАВИГАТОРА (змейка возобновляется)
t=35.60 YOLO снова активен — ищем следующую биржу
```

---

## YOLO-БЛОК (антиспам)

**Реализация:** timestamp, не daemon thread.
```python
# Активация (шаг 12):
self._yolo_unblock_time = time.time() + 20.0

# Проверка в цикле:
if time.time() >= self._yolo_unblock_time:  # разрешён
    results = yolo_model.predict(...)

# Сброс при СТАРТ:
self._yolo_unblock_time = 0.0  # time.time() > 0 всегда → YOLO сразу активен
```

**Почему не daemon thread:** При СТОП→СТАРТ старый тред мог досрочно снять блокировку → повторный клик по той же бирже. Timestamp не имеет этой проблемы.

---

## ROY OCR PIPELINE

```
_exchange_detected (шаг 9)
  └─ on_found_callback()
       └─ _roy_found_wrapper() [engine.py, только если roy_enabled=True]
            ├─ original_cb() → GUI: spend_credit + обновить баланс
            └─ _roy_on_found()
                 try:
                   wait_and_read(timeout=4.0)
                     loop(0.3с между попытками):
                       _grab_region(636, 330, 651, 115)
                         → coord_manager.to_region() → screen px
                         → mss.grab(screen_region) → BGR
                       gray → resize 4x → threshold(180) → THRESH_BINARY
                       pytesseract.image_to_string(psm=11, timeout=3)
                       _parse_coords() → (kingdom, x, y)
                       _grab_region(636, 540, 651, 120) → _measure_progress()
                   return {'kingdom':K, 'x':X, 'y':Y, 'percent':P}
                 if result:
                   on_last_exchange_callback(result)   → GUI карточка
                   if percent < 90:
                     _roy_client.report(K, X, Y, P)   → пул координат
                 except Exception as e:
                   _roy_log(f"_roy_on_found ERROR: {e!r}")
```

**Hardcoded ROI (reference 1920×1080, верифицировано по Биржа_15.04.png):**
- Диалог биржи: x=656, y=335, w=611, h=393 (центр ~x=961, y=531)
- K:X:Y ROI: x=636, y=330, w=651, h=115 (+20px запас по всем сторонам)
- Прогресс ROI: x=636, y=540, w=651, h=120
- OCR preprocessing: 4x upscale + threshold=180 (dark text on light dialog bg)
- `coord_manager.to_region()` масштабирует reference→screen по профилю пользователя

**ЗАПРЕЩЕНО:** динамический поиск диалога через HSV/contours (`_find_dialog`).
Причина: игровой фон совпадает по цвету с диалогом → захватывается весь экран.

**Условия попадания в пул:** `percent < 90` (биржа не выкуплена) + `roy_enabled=True`.

---

## СОХРАНЕНИЕ STATE ЗМЕЙКИ

`_exchange_detected` НЕ сбрасывает навигатор. State сохраняется:

| Поле | При бирже | После биржи |
|---|---|---|
| `_state` (DIVING/RETURNING/...) | заморожено | продолжается |
| `_inland_steps` | заморожено | продолжается |
| `_return_steps` | заморожено | продолжается |
| `_last_move_vec` | заморожено | используется для backtrack |
| `_yolo_unblock_time` | устанавливается в step 12 | автоматически истекает |

`joystick.reset()` вызывается ТОЛЬКО в `PacmanEngine.start()` — то есть при запуске бота, не при нахождении биржи.

---

## BACKTRACKING (возврат к улетевшей бирже)

Срабатывает **часто** — карта по инерции проскакивает биржу.

```python
def _backtrack_step(self):
    lx, ly = self.joystick._last_move_vec  # последний вектор движения
    self.joystick._click_vec(-lx, -ly)    # один клик в обратную сторону
```

**Правило:** backtrack НЕ меняет счётчики навигатора (`_inland_steps`, `_return_steps`). Он только физически сдвигает карту. Змейка не знает что произошёл шаг назад — это намеренно, иначе рушится геометрия сетки.

---

## ЧЕКЛИСТ ДЛЯ НОВЫХ ИДЕЙ

Перед реализацией любого изменения биржевого бота:

- [ ] Не нарушает ли это 12-шаговый порядок `_exchange_detected`?
- [ ] Не блокирует ли новый код основной поток (без timeout)?
- [ ] Не меняет ли это `_yolo_unblock_time` в неожиданных местах?
- [ ] Если меняется ROY pipeline — не зависнет ли `on_found_callback`?
- [ ] Если меняется навигатор — сохраняется ли state после биржи?
- [ ] Покрыто ли изменение TDD-тестами?

---

## ВЕРСИЯ И ТЕСТЫ

**Эталон актуален для:** v1.5.5
**Тестовые файлы:**
- `test_exchange_guard.py` — YOLO блок (3 теста)
- `test_exchange_backtrack.py` — backtracking (5 тестов)
- Итого: **13/13 ✅**

**Ключевые коммиты:**
| Коммит | Что |
|---|---|
| a656426 | Backtracking (`_backtrack_step`, `_last_move_vec`) |
| edd6d41 | ROY OCR (tesseract_cmd, psm11, coord ROI) |
| 083928e | roy/ в EXE (hiddenimports, datas, __init__.py) |
| 5d58903 | pytesseract timeout=3 (бот не зависает) |
| 86a470b | YOLO timestamp (race condition fix) |
