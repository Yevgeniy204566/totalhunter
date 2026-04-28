# STATE.md — Бортжурнал Total Hunter

> Обновляется командой **«Хангоф»** перед `/compact` или `/clear`
> Последнее обновление: 2026-04-28 (Хангоф #17 — визуальный возврат к маяку)

---

## Статус модулей

| Модуль | Файл | Статус | Дата |
|---|---|---|---|
| GUI | main.py | ✅ Готов, карточки Навигация + Дополнительно, слайдеры: Угол нырка (5-30°, дефолт 15°), Перекрытие следов (10-100%, дефолт 50%) | 2026-04-28 |
| Движок бирж | engine.py + navigator.py | ⚠️ TESTING — визуальный возврат к маяку реализован, 69 тестов ✅, на полевой проверке | 2026-04-28 |
| CoastalSnakeNavigator | navigator.py | ⚠️ TESTING — RETURNING: HSV magenta beacon + canvas tracking, 69 тестов ✅ | 2026-04-28 |
| MiniMap Reader | minimap_reader.py | ✅ Готов, analyze_footprint_zone теперь возвращает zone_px | 2026-04-28 |
| CryptHunter (слепой склеп) | crypt_hunter.py | ✅ Готов, 39 тестов, oil dialog HSV detect добавлен | 2026-04-26 |
| CoordManager | coord_manager.py | ✅ Готов, 14 тестов, верифицирован | 2026-04-09 |
| Cloud API (бэкенд) | server/ | ✅ Задеплоен на GCP, PostgreSQL, systemd | 2026-04-20 |
| Admin Panel | server/admin/index.html | ✅ Feedback badge + Leaderboard TOP-50 | 2026-04-21 |
| Web Platform (личный кабинет) | server/web_routes.py + web/ | ✅ Phase 2D + Diamond Rebrand завершены | 2026-04-22 |
| Economy (Free-Kassa + рефералы) | server/payments.py | ✅ Phase 2B завершена | 2026-04-21 |

---

## 🟡 CoastalSnakeNavigator — Визуальный возврат к маяку (Хангоф #17, 2026-04-28)

### Что сделано в этой сессии

**✅ Реализовано:**
- Визуальная навигация RETURNING к маяку: magenta beacon (255,0,255) BGR рисуется на миникарте, детектируется HSV
- Маяк всегда видим: clamped к краям миникарты
- `pixels_per_step` = реальный джойстик-шаг (не хардкод 20); передаётся из `nav_pps` gui_config.json
- Backstop: `ceil(dive_distance) + 10` вместо `inland_steps + 3`
- Canvas tracking: float-позиции `_cx`, `_cy` для дробных шагов
- `frac = min(1.0, dist/step_px)` — точные шаги к маяку
- `_is_at_coast_now`: `beacon_line OR визуальная вода` (OR-логика)
- `is_water` в RETURNING: УБРАНО (реки давали ложные срабатывания — см. AP-32)
- 69 тестов зелёные

**Калибровка (calibration_ui.py):**
- `measure_step_pixels()`: 5 шагов + matchTemplate = `nav_pps`
- Единая кнопка КАЛИБРОВАТЬ: оба этапа (экран + шаг) последовательно
- `nav_pps` сохраняется в `gui_config.json`, передаётся как `pixels_per_step`

**❌ Что пробовали и НЕ работает:**
- Pixel-детект красных пикселей → mirror wall на той же canvas-строке → ложные срабатывания (AP-32)
- `_return_steps = MAX_STEPS_SAFETY=80` → 80 шагов в океан (AP-33)
- `is_at_beacon` в `at_coast` (HOMING) → смешивает с ocean-column skip → stuck-in-water loop (AP-35)
- `is_water` в RETURNING без streak → 1 кадр реки = ложный стоп на середине пути (AP-32 нов.)
- `pixels_per_step` хардкодом 20 → ошибка 67%, маяк в неверном месте (AP-34)

**⚠️ На полевой проверке:**
- Достаточно ли `beacon_line OR is_water` для диагональных берегов
- Корректность HSV-детекции magenta на реальных скриншотах миникарты

---

## 🔴 КРИТИЧНО: CoastalSnakeNavigator — НАВИГАЦИЯ СЛОМАНА (Хангоф #15)

### Что было сделано за сессию 2026-04-27/28

**✅ Успешно реализовано:**
- Ocean march fix — 4 строки в HOMING→DIVING (fwd['land_px'] == 0 → shift)
- Angular damper `max_pitch_delta` (default 15°) — ограничение угла поворота нырка
- Footprint overlap check (max_footprint_overlap, default 50%) — не нырять в уже исследованное
- `analyze_footprint_zone` теперь возвращает `zone_px` для % расчёта
- GUI: слайдер "Угол нырка" (5-30°), слайдер "Перекрытие следов" (10-100%)
- Убраны слайдеры diagblind и coastrad (захардкожены в дефолтах)
- `_peek_step(direction)` — метод чтения миникарты перед шагом (радиусы 30/60/90px)
- `_move_perpendicular(multiplier)` — масштабирование шага джостика
- `_dive_distance` — отслеживание физической дистанции нырка

**❌ Что сломалось:**
- Убрана blind phase из RETURNING → бот стал останавливаться на внутренних реках (is_water = True)
- Добавили is_water для остановки в RETURNING → бот останавливается в воде (не на берегу)
- `_peek_step` в RETURNING: когда бот уже в воде, seaward direction показывает сушу (берег позади) → peek возвращает 1.0 → бот продолжает идти В воду
- `_dive_distance` + `_return_steps` — сложная механика, плохо взаимодействует с реальными тестами

### Принцип змейки (НЕЛЬЗЯ НАРУШАТЬ)

```
Бот стоит на границе земля/вода
↓ HOMING (зрячий): движение к берегу, читает миникарту каждый шаг
↓ DIVING (слепой счётчик, max_inland_steps кликов вглубь суши)
↓ RETURNING (счётчик назад, то же количество кликов обратно)
↓ SHIFT: сдвиг вправо вдоль берега
↓ Повтор (следующая полоса)
```

**Всё что добавляется — должно ТОЛЬКО обеспечивать эту функцию, не менять её.**

### Что нужно сделать в следующей сессии

**Вариант A — Минимальный (рекомендуется):**
Вернуть классическую RETURNING логику (blind phase + coast detection), добавить ТОЛЬКО peek для size:
```python
if self._state == 'RETURNING':
    # Blind phase — сначала N шагов вслепую (возвращаемся от глубины)
    if self._return_blind_steps > 0:
        self._return_blind_steps -= 1
        self._return_steps -= 1
        self._move_perpendicular(toward_water=True)  # multiplier=1.0, без peek
        return True
    
    # Зрячая фаза — проверяем берег
    at_coast = self._is_at_coast_now()
    cap_hit  = self._return_steps <= 0
    if at_coast or cap_hit:
        self._shift_click()
        self._state = 'HOMING'
        ...
        return True
    self._return_steps -= 1
    self._move_perpendicular(toward_water=True)  # multiplier=1.0
```
Peek в RETURNING — НЕ для остановки и НЕ для шагов. Только DIVING использует peek.

**Вариант B — Полный (peek симметрично):**
Если peek используется в RETURNING, нужно разделить:
1. Определение размера шага: peek возвращает multiplier для прыжка через воду
2. Остановка: `is_water` из center screen ИЛИ `_is_at_coast_now()` — НЕ peek(None)

Проблема peek(None) в RETURNING: когда бот УЖЕ в воде, smотря в сторону берега, он видит берег → peek = 1.0 (не None) → думает что всё ок → продолжает идти.

### Текущие тесты: 59 passed (но RETURNING сломан на практике)

---

## Рабочие механизмы

### CoastalSnakeNavigator — что работает корректно
- HOMING: читает миникарту каждый шаг, определяет угол берега через EMA
- Ocean check при HOMING→DIVING: `fwd['land_px'] == 0` → skip (4 строки) ✅
- Footprint overlap check при HOMING→DIVING ✅
- Angular damper `_prev_inland_vec` + `_max_pitch_delta` ✅
- `_peek_step()` метод реализован ✅
- DIVING: peek перед каждым шагом, прыжки через воду ✅

### GUI (main.py) — актуально
- Карточка «Навигация»: Шаг (10-20px), Скорость (0.5-5с), Глубина нырка (1-10)
- Карточка «Дополнительно» (скроллируемая height=120): Граница океан/суша, Мин. размер водоёма, Угол нырка (5-30°), Перекрытие следов (10-100%), Память следов (TTL)
- Убраны слайдеры: diagblind (захардкожен 0.5), coastrad (захардкожен 50)
- HuntEngine.start() принимает: max_pitch_delta, max_footprint_overlap ✅

### CryptHunter ✅
- OCR удалён. Формула `T_one_way = T_max / 2^N`. 39 тестов.

### Координатная система ✅
- REF_A=(90,925), REF_B=(1149,88)

### Серверный API ✅
- 8 таблиц БД, 18+ роутов, Free-Kassa, рефералы, leaderboard

---

## Известные баги / TODO

| Приоритет | Баг/TODO | Файл |
|---|---|---|
| **🟡 TESTING** | CoastalSnakeNavigator RETURNING — визуальный маяк реализован, проверить на реальной карте | navigator.py |
| **HIGH** | Прописать webhook URL в кабинете Free-Kassa | FK merchant dashboard |
| **MED** | Вставить иллюстрации в GuidePage | web/src/pages/GuidePage.jsx |
| LOW | КАЛИБРОВКА: картинки и описания точек А/Б | main.py |

---

## SaaS Master Plan — следующие модули

**~~Phase 2B (Economy / Модуль 4)~~ — ЗАВЕРШЕНА** ✅
**Phase 2C (Community):** Публичный leaderboard, Notifications
**Phase 3 (Bot):** Translations (EN/CN/DE)

---

## Архив закрытого

### Закрыто (Хангоф #14 — 2026-04-26)
- ~~Ocean march bug~~ — спроектирован (4 строки)
- ~~UI карточка Навигация~~ — добавлена
- ~~Oil HSV detect~~ — добавлен в CryptHunter
- ~~39 тестов~~ — все зелёные

### Закрыто (Хангоф #13 — 2026-04-25)
- ~~Gemini Sync~~ — `sync_to_gemini.py` реализован и протестирован

### Закрыто (Хангоф #12 — 2026-04-24)
- ~~Gemini Sync попытка через MCP~~ — base64 PowerShell не работает

### Закрыто (Хангоф #11 — 2026-04-24)
- ~~OCR-проверка масла~~ — удалена

### Закрыто (Хангоф #10 — 2026-04-22)
- ~~Diamond Rebrand~~ — завершён

### Закрыто (Хангоф #9 — 2026-04-21)
- ~~LoginPage / GuidePage редизайн~~

### Закрыто (Хангоф #6 — 2026-04-20)
- ~~Phase 2A Tasks 5–17~~ — все задачи выполнены и задеплоены
- ~~Бот ходил по воде~~ — EMA np.clip убран

### Закрыто (Хангоф #5 — 2026-04-20)
- ~~Авторизация через Google~~
