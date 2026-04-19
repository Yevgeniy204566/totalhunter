# ТЕХНИЧЕСКИЙ ПАСПОРТ — Total Hunter Bot
**Версия:** 2026-04-16 | **Источник:** Claude Code, прямое чтение исходников

---

## 1. ЦЕЛЬ И АРХИТЕКТУРА

**Total Hunter** — Windows-десктоп бот для автоматизации поиска игровых объектов в **Total Battle** (браузер/клиент). Два независимых модуля:

| Модуль | Цель | Статус |
|---|---|---|
| **Exchange Hunter** | Поиск Бирж (Exchange) на карте королевства | ✅ Prod |
| **Crypt Hunter** | Автопрохождение Склепов через меню Дозорной башни | ✅ Prod |

**Архитектурная схема:**
```
main.py (CustomTkinter GUI)
  ├── HuntEngine → PacmanEngine → CoastalSnakeNavigator
  │     └── minimap_reader.py → navigator.get_land_water_masks()
  ├── CryptHunter
  │     ├── button_finder.py (HSV-детекция кнопок)
  │     ├── template_finder.py (template matching)
  │     └── coord_manager.py (2-точечная калибровка)
  ├── auth.py → GCP backend :8000
  └── calibration_ui.py → profiles/*.json
```

---

## 2. ТЕХНОЛОГИЧЕСКИЙ СТЕК

| Компонент | Версия |
|---|---|
| Python | 3.13.5 |
| PyTorch | 2.10.0 |
| ultralytics (YOLOv8) | 8.4.21 |
| opencv-python | 4.12.0.88 |
| numpy | 2.2.6 |
| CustomTkinter | 5.2.2 |
| PyAutoGUI | 0.9.54 |
| pytesseract | 0.3.13 (Tesseract-OCR 5.x) |
| mss | 10.1.0 |
| requests | 2.32.4 |
| OS | Windows 10 Pro 10.0.19045 |
| Целевое разрешение | 1920×1080 |

**Модели YOLO:**
- `exchange.pt` — детекция Бирж на карте мира
- `targets/crypts.pt` — детекция иконок склепов в меню (31 класс)

---

## 3. ЛОГИКА НАВИГАЦИИ — CoastalSnakeNavigator (актуальный)

> `CompassNavigator` устарел, не используется. `PacmanEngine` создаёт `CoastalSnakeNavigator`.

### 3.1 Концепция
Бот движется строго **⊥ к береговой линии** во всех фазах. Вдоль берега — только один `_shift_click()` между полосами сканирования.

### 3.2 Три состояния
```
HOMING → [берег найден] → DIVING → [max глубина достигнута]
→ SHIFT → RETURNING → [берег] → SHIFT → HOMING → ...
```

**HOMING (зрячий):** читает мини-карту каждый шаг через `detect_coast_angle()` + EMA-сглаживание. Движется к воде по `-inland_vec`. Hard-stop при `homing_steps >= 10`.

**DIVING (слепой):** только счётчик `inland_steps`. Без чтения карты. Переход в RETURNING при `inland_steps >= max_inland_steps`.

**RETURNING (две фазы):**
- *Слепая*: первые `blind_steps = round((max_inland-1) * blind_factor)` шагов — реки внутри ГОС игнорируются.
- *Зрячая*: `_is_at_coast_now()` каждый шаг — ждёт реального берега.
- Cap: `max_inland + 15` шагов — safety net.

### 3.3 Определение угла берега (`minimap_reader.detect_coast_angle`)
1. Получить все пиксели воды на мини-карте (180×180 px)
2. Вычислить центроид воды → `water_angle = atan2(row_offset, col_offset)`
3. `coast_angle = water_angle + π/2`
4. `inland_vec = coast_angle + π/2` (прочь от воды)
5. EMA-сглаживание с `coast_ema_alpha=0.3`
6. Fallback `0.0` если воды < 50 px или центроид < 5 px от центра

### 3.4 Сдвиг (`_shift_click`)
```python
sv = (-inland_vec[1], inland_vec[0])  # 90° CCW rotation
assert dot(sv, inland_vec) < 1e-9     # математически гарантировано ⊥
```

### 3.5 FootprintCanvas
Сетка 401×401 шагов (центр = 200). Хранит timestamp последнего посещения. При каждом переходе HOMING→DIVING рисует две "стены" (левую и зеркальную). Пятна видны на мини-карте красным (BGR 0,0,255) — не интерпретируются как вода.

### 3.6 Текущие параметры (`gui_config.json` — реальный пользователь)
```json
center_x: 91, center_y: 929  (джойстик мини-карты)
step: 14                      (базовый шаг, горизонтальный = round(14 * 16/9) = 25px)
max_inland_steps: 3           (глубина нырка)
ocean_land_ratio: 0.04        (4% суши = ещё не океан)
min_water_px: 900             (мин. водоём для детекции)
diagonal_blind_coeff: 0.5     (мягкая диагональ)
coast_detect_radius: 50       (конус детекции берега, px)
nav_footprint_ttl: 120        (TTL следов, сек)
conf: 0.8                     (порог YOLO Exchange)
scan_interval: 0.8            (пауза между YOLO-сканами, сек)
move_wait: 0.6                (пауза после каждого джойстик-клика)
```

### 3.7 Анти-детект
- Пауза после клика: `move_wait + random.uniform(0.1, 0.4)` = 0.7–1.0 сек
- Смещение кликов: `p_range_y=step`, `p_range_x=round(step * screen_w/screen_h)` — аспект-коррекция

---

## 4. КОМПЬЮТЕРНОЕ ЗРЕНИЕ

### 4.1 Exchange Hunter (YOLO)
- **Модель:** `exchange.pt` (YOLOv8, формат `.pt`)
- **Запуск:** `model.predict(frame, conf=0.8, imgsz=1280, verbose=False)`
- **Вход:** полный скриншот 1920×1080, BGR, через `mss`
- **Классы:** Биржа (Exchange) — 1 класс, детектируется на карте мира
- **Текущий порог:** conf=0.8 (пользователь использует)

### 4.2 Crypt Hunter (YOLO)
- **Модель:** `targets/crypts.pt`
- **31 класс:** Ordinary 1–12 (`crypt_0..11`), Epic 2–18 (`crypt_12..28`), R 1–2 (`crypt_29..30`)
- **Регион сканирования:** `MENU_SCAN_REGION = (597, 242, 721, 575)` — меню Дозорной башни
- **Текущий порог:** conf=0.41

### 4.3 Детекция воды (мини-карта)
```python
# HSV-маска воды
WATER_HSV = [(100, 60, 50), (140, 255, 255)]
# Fallback — BGR: синий доминирует
water_bgr = (blue > green*1.25) AND (blue > red*1.25)
# Для центра экрана (проверка океана)
b > g*1.2 AND b > r*1.2, radius=120px
```

### 4.4 Кнопки (`button_finder.py`)
HSV-диапазоны:
```python
'green':  H(35–85), S(40–255), V(40–200)   # «Исследовать», «Открыть»
'purple': H(125–160), S(50–255), V(50–255)  # Событие Картера
```

### 4.5 OCR (`pytesseract`)
- **Координаты карты:** зона `(0, 1000, 250, 1080)`, 4 варианта кропа × 2 обработки × 3 PSM (6/11/12), масштаб ×4
- **Время марша:** `MARCH_TIME_REGION = (890, 777, 134, 34)`, нормализация M/C/H → кириллица
- **Масло:** `CRYPT_OIL_REGION = (1064, 544, 185, 36)`, парсер `parse_oil()`: к→×1000, м→×1_000_000

---

## 5. ИНТЕГРАЦИЯ С GOOGLE CLOUD

### 5.1 Backend-сервер
- **IP:** `34.68.86.57` (GCP)
- **Порт:** `8000` (FastAPI/Flask)
- **Протокол:** HTTP (не HTTPS)

### 5.2 API Endpoints
| Endpoint | Метод | Назначение |
|---|---|---|
| `/check_auth` | POST `{hwid}` | Лицензия, credits, email, ref_id, broadcast, banned |
| `/use_credit` | POST `{hwid}` | Списать 1 кредит (вызов при нахождении Биржи/Склепа) |
| `/activate_referral` | POST `{hwid, ref_code}` | Реферальный бонус |
| `/claim_trial` | POST `{hwid}` | Получить 300 стартовых кредитов |
| `/log_error` | POST `{hwid, error}` | Телеметрия ошибок (timeout=2s) |
| `/google_login?hwid=` | GET (redirect) | OAuth2 авторизация через Google |

### 5.3 Идентификация пользователя
```python
hwid = SHA256(str(uuid.getnode()))[:16].upper()  # MAC → SHA256 → 16 символов
```

### 5.4 Google OAuth
- Домен: `http://34.68.86.57.nip.io:8000` (nip.io — обход ограничений OAuth на IP)
- Открывается через `webbrowser.open()`, браузер → callback → backend привязывает email к HWID
- После успеха в GUI появляется email пользователя

### 5.5 Что хранится на сервере
- HWID → email mapping
- credits balance
- referral chains
- error logs (телеметрия)
- broadcast-сообщения для GUI

---

## 6. ТЕКУЩИЙ СТАТУС КОДА — МОДУЛИ

### `main.py` (GUI)
- `TotalHunterApp` — CustomTkinter, 460×1010, тёмная тема
- 4 вкладки: БИРЖИ / СКЛЕПЫ / РЕФЕРАЛЫ / КАЛИБРОВКА
- 2 языка: RU / EN (переключатель в шапке)
- Always-on-top, snap вправо (screen_width - 460)
- ESC → аварийный стоп через `keyboard.hook`
- Слайдеры навигации: 5 параметров CoastalSnakeNavigator
- Таймер обратного отсчёта в склепах (золотой, 26pt)

### `engine.py`
- `HuntEngine` — загружает `exchange.pt`, создаёт `PacmanEngine`, управляет потоком
- `start()` принимает 11 параметров конфигурации
- Звук при нахождении: WAV-файл из директории

### `navigator.py`
- `CoastalSnakeNavigator` — основной навигатор (описан выше)
- `CompassNavigator` — устарел, сохранён для совместимости
- `PacmanEngine` — главный цикл: grab → water_check → YOLO → joystick.step
- `FootprintCanvas` — visited-cell memory, 401×401 grid
- `PositionReader` — OCR координат карты

### `minimap_reader.py`
- `detect_coast_angle(mm)` — центроид воды → угол
- `analyze_forward_zone(mm, vec, radius)` — конус-анализ ±45°
- `analyze_footprint_zone(mm, vec)` — детекция красных следов
- `get_minimap_snapshot(cx, cy)` — live скриншот 180×180

### `crypt_hunter.py`
- `CryptHunter` — полный цикл автопрохождения склепов
- Использует `coord_manager` для всех кликов
- `_scroll_and_find()` — YOLO-поиск в меню + прерываемый скролл
- `_accelerate(n)` → возвращает `remaining_after × 2` (float)
- `_verify_action(name, fn, timeout)` — Action Verification pattern

### `coord_manager.py`
- `CoordinateManager` — 2-точечная калибровка
- REF_A = `(90, 925)`, REF_B = `(1149, 88)` (верифицировано 2026-04-11)
- `to_screen()`, `to_region()`, `to_screen_dialog()` (с dialog_offset)
- Профили: `profiles/profile_client.json`, `profile_chrome.json`, `profile_firefox.json`

### `calibration_ui.py`
- GUI-лупа 600% для 2-точечной калибровки
- Нельзя создавать `tk.Tk()` — использует `parent=root` (CTk is root)

### `button_finder.py` / `template_finder.py`
- HSV-детекция цветных кнопок
- Template matching через OpenCV `matchTemplate`
- `find_at_ref(template, ref_x, ref_y, radius)` — поиск шаблона вокруг точки

---

## 7. РЕШЁННЫЕ ПРОБЛЕМЫ И ТЕКУЩИЕ БАГИ

### Решённые (последние)
| Проблема | Решение |
|---|---|
| Бот шёл вдоль берега вместо ⊥ | `_shift_vec_set` lock + assert perpendicular в `_shift_click` |
| PCA возвращал angle+π (180° flip) | EMA с детекцией разницы > π/2 → принудительный flip перед усреднением |
| shift_vec == inland_vec при fallback 0.0 | `_update_coast_angle` синхронизирует shift_vec = coast_vec пока не заблокирован |
| Реки внутри ГОС останавливали возврат | Слепая фаза RETURNING: `blind_steps = round((max_inland-1) * blind_factor)` |
| Диалоги в браузере смещены вниз | `dialog_offset_x/y` в профилях калибровки |
| Кнопки не находились через HSV (фон трава) | Template matching + узкий регион по X:700–1300 |
| `_scroll_and_find` блокировал UI при стопе | Заменён `time.sleep` на `_interruptible_sleep(scroll_speed + 0.2)` |
| Склеп в нижних 28% меню — кнопка не видна | Доскролл на -2 + re-YOLO перед кликом |
| OCR латинские M/C/H не парсились | Нормализация в `parse_time`: latin → cyrillic |
| Статус "Жду Картера" вешал UI | Убран — только `on_countdown_callback` + золотой таймер |

### Текущие известные баги
| Баг | Описание | Обходной путь |
|---|---|---|
| **Ранняя остановка у берега** | `coast_detect_radius=50` — бот останавливается на 1 шаг раньше берега | Уменьшить до ~25 в GUI |
| **image-diff в конце списка** | Не работает когда много одинаковых склепов подряд | Надёжный fix — сравнивать скроллбар (не контент) |
| **`_open_watchtower()` нет верификации** | Башня может не открыться, бот продолжит | TODO: проверить появление `tab_crypts.png` |
| **`force_shift_after=0`** | Стена-счётчик выключена — бот может застрять без принудительного сдвига | Рекомендуется `max_inland*2+10` |

---

## 8. ТЕСТОВОЕ ПОКРЫТИЕ

| Файл | Тестов | Статус |
|---|---|---|
| `test_coastal_snake.py` | 42 | ✅ |
| `test_minimap_reader.py` | 15 | ✅ |
| `test_crypt_hunter.py` | 62 | ✅ |
| `test_coord_manager.py` | 14 | ✅ |
| `test_button_finder.py` | — | ✅ |
| `test_calibration.py` | — | ✅ |
| `test_navigator.py` | — | ✅ |
| `test_footprint_canvas.py` | — | ✅ |
| **Итого** | **133+** | **✅** |

---

## 9. СЛЕДУЮЩИЕ ШАГИ (ПРИОРИТЕТ)

### Высокий приоритет
1. **Уменьшить `coast_detect_radius` 50 → 15–25** — бот подходит ближе к берегу (текущий баг ранней остановки). Ползунок «Конус детекции берега» в GUI.

2. **Скроллбар-детекция конца списка склепов** — текущий image-diff ненадёжен при повторяющихся иконках. Читать позицию скроллбара вместо контента.

3. **Верификация `_open_watchtower()`** — после клика по иконке башни проверять появление `tab_crypts.png` в сайдбаре (timeout 3–4 с).

### Средний приоритет
4. **Веб-сайт и веб-админка** — Material Design 3 интерфейс. Управление лицензиями, просмотр статистики пользователей, broadcast-сообщения. Backend уже есть на GCP.

5. **Калибровка — документация с картинками** — вкладка КАЛИБРОВКА пустая (место зарезервировано). Добавить описание Точки А и Б с визуальными подсказками.

6. **`force_shift_after` по умолчанию** — сейчас 0 (выключен). Установить `max_inland_steps * 2 + 10` как безопасный default.

### Низкий приоритет
7. **Поддержка мультимониторных конфигураций** — `mss.monitors[1]` захватывает основной, не настраивается из GUI.

8. **OCR координат карты** — `PositionReader` реализован но не используется в основном цикле (пассивный код).

---

## 10. СТРУКТУРА ФАЙЛОВ

```
C:\BattleBot\
├── main.py              GUI, TotalHunterApp
├── engine.py            HuntEngine → PacmanEngine
├── navigator.py         CoastalSnakeNavigator, FootprintCanvas, PacmanEngine
├── minimap_reader.py    detect_coast_angle, analyze_forward_zone
├── crypt_hunter.py      CryptHunter — полный цикл склепов
├── coord_manager.py     2-точечная калибровка, синглтон coord_manager
├── calibration_ui.py    GUI-лупа 600% для калибровки
├── calibration.py       Автокалибровка джойстика (nav_config.json)
├── button_finder.py     HSV-детекция кнопок
├── template_finder.py   OpenCV template matching
├── auth.py              HWID, лицензии, GCP API
├── exchange.pt          YOLO-модель Бирж
├── targets/crypts.pt    YOLO-модель склепов (31 класс)
├── targets/*.png        Иконки склепов (эталоны)
├── profiles/            JSON-профили калибровки (3 шт.)
├── gui_config.json      Сохранённые настройки GUI
└── test_*.py            Unit-тесты (133+ тестов)
```

---

*Документ сгенерирован путём прямого чтения исходного кода. Все версии, координаты и параметры — актуальные на дату составления: 2026-04-16.*
