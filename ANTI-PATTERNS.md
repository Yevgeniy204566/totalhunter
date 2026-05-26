# ANTI-PATTERNS.md — Запреты и Грабли

> Не тратить время повторно на эти решения.
> Обновляется командой **«Хангоф»**.
> Последнее обновление: 2026-05-26 (Хангоф #70 — Реферальная система TDD)

---

## ⛔ `db.begin()` ВНУТРИ ЭНДПОИНТА С `get_web_user` — 500 ДЛЯ ВСЕХ (Хангоф #70)

**Что было:** `async with db.begin():` в `/referral/activate`. Dependency `get_web_user` делает SELECT → SQLAlchemy autobegin срабатывает. Затем `db.begin()` → `InvalidRequestError: A transaction is already begun` → 500 для каждого первого вызова.
**Симптом:** Эндпоинт возвращает 500, хотя логика правильная. В тестах падает с `sqlalchemy.exc.InvalidRequestError`.
**Решение:** Использовать `async with db.begin_nested():` (savepoint) + `await db.commit()` снаружи.
**Правило:** В эндпоинтах с `get_web_user` (или любой dependency с SELECT) НИКОГДА не использовать `db.begin()`. Только `db.begin_nested()` или прямой `await db.commit()`.

---

## ⛔ HMAC В ТЕСТАХ — ПОДПИСЫВАТЬ И ОТПРАВЛЯТЬ ОДНИМИ БАЙТАМИ (Хангоф #70)

**Что было:** `_make_np_sig(body)` считал HMAC от `json.dumps(body, sort_keys=True).encode()`. Тест отправлял `json=body` через httpx — тот сериализует без `sort_keys` → другие байты → сервер получал неподписанные байты → 400.
**Симптом:** Webhook-тесты падали с 400 несмотря на правильный секрет и формат.
**Решение:** Всегда отправлять `content=json.dumps(body, sort_keys=True).encode()` + `"content-type": "application/json"` — те же байты, что были подписаны.
**Правило:** Байты, которые подписываешь, и байты, которые отправляешь — должны быть идентичны.

---

## ⛔ NAIVE/AWARE DATETIME В ТЕСТАХ (SQLite) vs ПРОДЕ (PostgreSQL) (Хангоф #70)

**Что было:** `datetime.now(timezone.utc)` (aware) сравнивался с `web_user.hwid_reset_at` из SQLite (naive). `TypeError: can't compare offset-naive and offset-aware datetimes`.
**Симптом:** Тест `test_hwid_reset_cooldown_enforced` падал с TypeError, на PostgreSQL работало нормально.
**Решение:** Нормализовать перед сравнением: `if reset_at.tzinfo is None: reset_at = reset_at.replace(tzinfo=timezone.utc)`.
**Правило:** При работе с datetime из БД всегда нормализовать tzinfo перед сравнением — SQLite хранит naive, PostgreSQL может хранить aware.

---

## ⛔ VERCEL ANALYTICS — ВКЛЮЧАТЬ ДО ДЕПЛОЯ, НЕ ПОСЛЕ (2026-05-25)

**Что было:** Vercel Web Analytics включён через Dashboard уже после последнего деплоя. Существующий сборки не знали об аналитике → `/_vercel/insights/script.js` отдавал 404 → `<Analytics />` в дереве есть, но скрипт не загружался → в Dashboard 0 посещений.
**Симптом:** Analytics включён в проекте, код правильный (`@vercel/analytics/react`, `<Analytics />` в main.jsx) — но статистика 0.
**Решение:** Сделать свежий редеплой (hook → ждать READY → alias). Новый билд подхватит аналитику автоматически. Проверка: `curl -sI https://total-hunter.com/_vercel/insights/script.js` → должен быть 200.
**Правило:** Vercel Web Analytics активируется только при следующем билде. Включить сервис → немедленно редеплой.

---

## ⛔ ДИНАМИЧЕСКИЙ ИМПОРТ ИЗ СКОМПИЛИРОВАННОГО .pyd — PyInstaller НЕ ВИДИТ (v1.5.2)

**Что было:** `engine.py` скомпилирован Nuitka → `engine.pyd`. Внутри — `from roy.exchange_reader import wait_and_read` (динамический импорт). PyInstaller не анализирует `.pyd` файлы → `roy/` не попал в бандл → `ModuleNotFoundError` → `except Exception: pass` → тихо.
**Симптом:** ROY координаты не попадают в пул, карточка «Последняя биржа» пустая.
**Решение:**
1. Создать `roy/__init__.py` (пустой) — PyInstaller распознаёт пакет
2. В `build.spec` добавить в `hiddenimports`: `'roy', 'roy.exchange_reader', 'roy.roy_client'`
3. В `build.spec` добавить в `datas`: `('roy', 'roy')` — страховка
**Правило:** Любой модуль импортируемый из `.pyd` файла ОБЯЗАН быть в `hiddenimports` + `datas` в `build.spec`.

---

## ⛔ pytesseract.image_to_string() БЕЗ ТАЙМАУТА — ПОДВЕШИВАЕТ ПОТОК НАВСЕГДА (v1.5.3)

**Что было:** `pytesseract.image_to_string(gray, config='--psm 11')` без `timeout=N` в `exchange_reader.py`. При определённых входных данных tesseract.exe мог зависнуть → `_exchange_detected` не завершался → бот стоял после каждой биржи вечно.
**Симптом:** Бот находит биржу, кликает, стоит на месте и никуда не идёт. Навсегда.
**Решение:** Всегда передавать `timeout=3` в каждый вызов `pytesseract.image_to_string()`. Оборачивать в `try/except` для graceful fallback.
**Правило:** Любой внешний процесс (tesseract, ffmpeg и т.д.) ОБЯЗАН иметь таймаут.

---

## ⛔ DAEMON THREAD ДЛЯ YOLO-БЛОКА — RACE CONDITION ПРИ СТОП→СТАРТ (v1.5.5)

**Что было:** `_trigger_yolo_block(N)` создавал daemon thread с `time.sleep(N)` → `_yolo_blocked = False`. При СТОП→СТАРТ пользователя старый тред продолжал жить в фоне. Если новая биржа найдена → новый блок запущен → через несколько секунд СТАРЫЙ тред просыпался и досрочно снимал блокировку → YOLO снова активен → повторный клик по той же бирже.
**Симптом:** Бот дважды кликает одну биржу при быстром СТОП→СТАРТ.
**Решение:** Заменить на timestamp:
```python
self._yolo_unblock_time = time.time() + block_seconds  # активация
# в _run(): if time.time() >= self._yolo_unblock_time:
# в start(): self._yolo_unblock_time = 0
```
**Правило:** Для временны́х блокировок использовать timestamp, не daemon thread.

---

## ⛔ `fresh_box is None → return` В _exchange_detected БЕЗ BACKTRACKING — ЛОМАЕТ ВСЁ (Хангоф #64)

**Что было:** После первого свежего YOLO-скана: `if fresh_box is None: return` — выход ДО клика, звука, стопа и OCR.
**Последствие:** Бот видел биржу (фото в Telegram), но не останавливался, не играл звук, не читал координаты, не отправлял в РОЙ.
**Почему ломает:** Карта за 0.5с смещается, биржа уходит за порог conf → `fresh_box=None` → `return` → всё pipeline не выполняется.
**Решение v1.4.3:** `if fresh_box is None: fresh_box = box` — fallback на исходный bbox.
**Решение v1.5.x (backtracking):** `if fresh_box is None: _backtrack_step() → sleep(0.3) → второй скан`. Если и второй скан пустой — тогда `return` допустим (ложное срабатывание).
**Правило:** `return` допустим ТОЛЬКО после двух неудачных YOLO-сканов (первый + после шага назад). Один неудачный скан → НЕ делать `return`, делать `_backtrack_step`.

---

## ⛔ РЕЛИЗ — Обновлять сервер ДО загрузки ZIP — ЗАПРЕЩЕНО (Хангоф #63)

**Что было:** `POST /admin/version/update?version=1.4.2` выполнен сразу после `gh release create` — до загрузки TotalHunter.zip в релиз.
**Последствие:** Все клиенты с v1.4.1 получили 404 при попытке скачать обновление. Auto-updater сломан для всех пользователей.
**Нерушимый порядок:**
1. Загрузить ZIP в GitHub Release (вручную через браузер)
2. Проверить доступность: `curl -I https://github.com/.../releases/download/vX.X.X/TotalHunter.zip` → HTTP 302/200
3. ТОЛЬКО потом: `POST /admin/version/update?version=X.X.X`

---

## ⛔ СБОРКУ ЗАПУСКАТЬ БЕЗ ЯВНОГО «ДА» — ЗАПРЕЩЕНО (НАИВЫСШИЙ ПРИОРИТЕТ)

**Что было:** Claude несколько раз самостоятельно запускал `python build_release.py` без команды пользователя.
**Правило:** `build_release.py` запускается ТОЛЬКО когда пользователь явно говорит «собирай», «делай сборку» или аналогичное. Никаких инициативных сборок.

---

## ⛔ BUILD.SPEC — `collect_submodules('ultralytics')` тащит polars (154 MB) — КОНТРОЛИРОВАТЬ (Хангоф #63)

**Что было:** `polars` (data science библиотека, 154 MB) и два `opencv_videoio_ffmpeg` DLL (54 MB суммарно) попали в dist через `collect_submodules('ultralytics')`. ZIP вырос с 389 MB до 789 MB.
**Диагностика:** После сборки проверять топ-10 файлов по размеру: `Get-ChildItem dist/TotalHunter -Recurse | Sort-Object Length -Desc | Select -First 10`
**Исправление:** В `build.spec` в `excludes` добавить: `'polars', 'pyarrow', 'dask', 'numba', 'statsmodels'`
**Признак проблемы:** ZIP > 500 MB = что-то лишнее затащилось.

---

## ⛔ ROY event gate через GUI-флаг — ЗАПРЕЩЕНО (Хангоф #62)

**Что было:** `if not self.event_active:` в петле скана — флаг устанавливался из GUI-тика раз в 60 сек. При старте движка = `False` → скан не засчитывался даже когда ивент шёл.
**Почему ломает:** GUI-тик срабатывает до старта движка. После старта движка флаг `False` пока следующий тик не придёт (до 60 сек). Весь этот период скан блокируется.
**Решение:** `_is_trade_routes_active()` — вычислять состояние ивента inline, независимо от GUI. Никаких внешних флагов для временны́х состояний.

---

## ⛔ ROY OCR в фоновом потоке при синхронном движке — ЗАПРЕЩЕНО (Хангоф #62)

**Что было:** `threading.Thread(target=self._roy_on_found, daemon=True).start()` — навигация возобновлялась немедленно пока OCR читал диалог в фоне.
**Почему ломает:** Бот линейный. Нельзя читать координаты биржи пока движок уже делает следующий шаг. OCR возвращал None (диалог мог закрыться), координаты не уходили в РОЙ.
**Решение:** `self._roy_on_found()` — синхронный вызов. Навигация ждёт до 4 сек пока OCR прочитает, потом стоп 10с, потом движение.
**Правило:** Бот работает линейно. Любой обработчик найденной цели выполняется до конца перед возобновлением движения.

---

## ⛔ AP-UPDATER-NESTING: Не-плоский ZIP → День Сурка у клиентов — ЗАПРЕЩЕНО (v1.5.0)

**Симптом:** Пользователи уходят в бесконечный цикл скачивания одной и той же версии.
**Причина:** `7z a TotalHunter.zip "dist/TotalHunter/*"` из КОРНЯ создаёт вложенные пути `dist/TotalHunter/TotalHunter.exe`. xcopy копирует папку `dist/` в exe_dir — оригинальный exe не заменяется.
**Как надо:** ВСЕГДА запускать 7z ИЗНУТРИ `dist/TotalHunter/`:
```
cd C:\BattleBot\dist\TotalHunter
7z a -tzip C:\BattleBot\TotalHunter.zip "*"
```
**Проверка перед загрузкой:** `7z l TotalHunter.zip | grep TotalHunter.exe` → путь должен быть `TotalHunter.exe` (БЕЗ `dist/TotalHunter/` префикса). Если есть префикс — СТОП, переделать.

---

## ⛔ UPDATER — Грабли xcopy (Хангоф #61 — ИСПРАВЛЕНО)

### НЕРУШИМОЕ ПРАВИЛО: ZIP и xcopy обязаны соответствовать друг другу

**Стандарт проекта (v1.4.0+):** ZIP ПЛОСКИЙ + xcopy `extract_dir\*`

```
7z: cd dist/TotalHunter && 7z a -tzip ../../TotalHunter.zip "*"  ← ПЛОСКАЯ (из папки!)
7z: "7z.exe" a -tzip TotalHunter.zip "dist/TotalHunter/*"  ← НЕПЛОСКАЯ (из корня!) ЗАПРЕЩЕНО
xcopy: xcopy /s /y /e "{extract_dir}\*" "{exe_dir}\"        ← плоское копирование
```

**Результат в ZIP:** `TotalHunter.exe` лежит в КОРНЕ архива (без вложенной папки).

---

## 🔒 ЗОЛОТОЕ ПРАВИЛО ЗМЕЙКИ — НЕРУШИМО

```
НЫРОК → СДВИГ → ВОЗВРАТ → СДВИГ
```

**Любое предложение по navigator.py, которое нарушает этот цикл хотя бы в одном сценарии — ЗАПРЕЩЕНО.**
Маяк — на берегу, 2 шага вправо от точки нырка, перпендикулярно нырку. Возврат — физически на маяк.

## 🔒 ПРАВИЛО МАЯКА — НАИВЫСШИЙ ПРИОРИТЕТ

**RETURNING останавливается ТОЛЬКО на линии маяка. Ничто иное не останавливает возврат.**
- Реки, ручьи, вода на пути возврата — НЕ помеха, бот идёт сквозь них
- Визуальные проверки воды в RETURNING при активном маяке — ЗАПРЕЩЕНЫ
- Любой код, останавливающий RETURNING до линии маяка — ЗАПРЕЩЁН

---

## ⛔ Остальные антипаттерны (хангофы #1–#61)

> Подробности в git history или предыдущих версиях ANTI-PATTERNS.md.
> Краткий список актуальных:
> - OCR времени марша через pytesseract — нестабильно, удалено
> - Template matching мультиязычных кнопок — только HSV+геометрия
> - window_scaler.py — удалён, только coord_manager
> - CompassNavigator — устарел, только CoastalSnakeNavigator
> - tk.Tk() в calibration_ui — конфликт root
> - is_water в RETURNING — нарушает Правило Маяка
> - CORS allow_origins=["*"] с Authorization — браузер блокирует
> - Nuitka .pyd перекрывает .py в корне — удалять после сборки
> - Калибровка через AnyDesk — смещение координат
> - Секретные токены в STATE.md — репо публичный → автоотзыв
