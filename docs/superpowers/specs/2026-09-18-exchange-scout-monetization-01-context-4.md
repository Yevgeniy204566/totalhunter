# Биржа 2.0 (Exchange Scout) — ЧАСТЬ A-М (монетизация), файл 01/4: Context и Code Archaeology (2.6, 2.7, 2.8)

> Фрагмент одного документа, разрезанного на файлы ≤300 строк по решению владельца (2026-09-18).
> **Индекс, статус и раунды → [`2026-09-18-exchange-scout-monetization-design-2.md`](2026-09-18-exchange-scout-monetization-design-2.md).**
> Файлы Части A-М: **01 (этот файл)** · [02](2026-09-18-exchange-scout-monetization-02-contracts-design-5.md) · [03](2026-09-18-exchange-scout-monetization-03-adversarial-6.md) · [04](2026-09-18-exchange-scout-monetization-04-tests-gate-7.md)
> Файловый жизненный цикл, GUI-каркас и `scout_results.jsonl` — **[→ Часть A]**:
> [`2026-09-17-exchange-scout-part-a-lifecycle-design-3.md`](2026-09-17-exchange-scout-part-a-lifecycle-design-3.md).
> Нумерация секций, контрактов C-*, находок A-* и тестов T-* унаследована от Части A и при нарезке
> не менялась.

---

## Стадия 1. Context

Прочитано лично в текущей сессии перед написанием этого документа:

| Документ | Что взято |
|---|---|
| `docs/РАБОТА-С-ДОКУМЕНТАМИ.md` | целиком: стадии 1-9, формат Contract Extraction, лимит раундов, условия пропуска Stage 8 |
| Часть A (спека, 1072 строки) | целиком: контракты C-01…C-16, находки A-1…A-13, тесты T-01…T-21, порядок операций при обработке находки |
| `CLAUDE.md` | раздел 3.5 (архитектура платежей и синхронизации баланса), запрет самостоятельного выбора чисел |
| `auth.py` | `get_hwid` (32-35), `HEARTBEAT_TIMEOUT` (20), `_mark_contact_success`/`seconds_since_last_contact` (24-30), `spend_credit` (106-124), `get_balance_update` (127-143), `heartbeat` (146-156) |
| `debug_reporter.py` | целиком, 87 строк |
| `navigator.py` | `PositionReader.read` (51-74), `_exchange_detected` — участок находки/клика/колбэка (1070-1146) |
| `engine.py` | `_roy_on_found` (248-262) — ветка OCR, независимая от списания |
| `main.py` | `_update_credits_display` (3281-3286), `_start_balance_sync` (3311-3322) и его запуск (1872), `update_license_info` (3324-3334), `toggle_bot` — гейт баланса (3568-3575), `on_target_found`/`_process_found` (3751-3767) |
| `server/main.py` | `CREDIT_COST` (131-135), rate limit `/use_credit` (34-37, 305-311), эндпоинт `/use_credit` целиком (297-352) |
| `server/vault.py` | целиком, 73 строки — `notify_balance_changed` (24-27), `GET /vault/sync/{hwid}` (30-72) |
| `server/debug_router.py` | `POST /api/debug/upload-shot` (19-49), `POST /api/debug/send-text` (52-68) |
| `server/roy.py` | константы пула (35-41), `ReportRequest` (192-197), `POST /roy/report` целиком (242-296), фильтр пула по `percent` (453) |
| `roy/roy_client.py` | `RoyClient.report` (27-48) — клиентская сторона 1.0 |
| `engine.py` | `_roy_on_found` (248-281) — единственный сегодняшний вызывающий `report()` |
| `test_exchange_esc_guard.py`, `test_exchange_backtrack.py` | существующий приём подмены отправок в Telegram в тестах (87-88 и 92-93 соответственно) |

**Стадия 0 (Scope Decomposition Gate).** Решение делить принято владельцем 2026-09-18 и здесь не
переоценивается. Содержательный критерий протокола выполняется: в одном документе Части A были смешаны
два разных слоя — файловый жизненный цикл (детерминированные операции с ФС, тестируемые на `tmp_path`) и
денежный контракт с внешним сервером (сетевой вызов, серверные состояния, 402/429, синхронизация баланса).
Второй слой — это именно «деньги-биллинг», по которому протокол отдельно запрещает пропуск Stage 8.

---

## Стадия 2. Code Archaeology — что реально есть в коде

Всё ниже открыто и прочитано лично в текущей сессии. Секции 2.6 и 2.7 перенесены из Части A и
перепроверены по коду заново (не скопированы на доверии); секция 2.8 написана здесь впервые.

### 2.6 `debug_reporter.py` — существующий канал в debug-Telegram

> ⛔ **ЗАМЕНЕНО в раунде 3 (2026-09-18).** Владелец отменил канал debug-Telegram для 2.0: находка выкладывается на сайт в разделе «Рой» — см. `2026-09-18-exchange-scout-roy-publication-design-1.md` (контракты P-01…P-12). Текст ниже сохранён только ради нумерации и истории, к реализации не принимается.

Файл прочитан целиком (87 строк). Для 2.0 значимы шесть фактов, каждый — из кода, не из описания.

1. **Ошибки сети глушатся полностью.** `_send` (`debug_reporter.py:14-24`) целиком обёрнут в
   `try: ... except Exception: pass` (`debug_reporter.py:23-24`). Таймаут — модульная константа
   `_TIMEOUT = 10` (`debug_reporter.py:11`), передаётся в `requests.post` (`debug_reporter.py:21`).
   То есть недоступный сервер, 500, DNS-сбой и таймаут 10 с — все одинаково приводят к тихому `return`,
   без исключения у вызывающего. Это факт кода, а не предположение.
2. **Fire-and-forget — только сетевая часть, и это важно.** `report_find` (`debug_reporter.py:27-56`)
   выполняет **синхронно, в потоке вызывающего**: `frame_bgr.copy()` (строка 29), отрисовку bbox и подписи
   (30-41) и DPI-диагностику, которая лезет за живыми `mss().monitors[1]` и `pyautogui.size()` (42-54).
   В фоновый `threading.Thread(..., daemon=True)` уходит **только** `_send` (`debug_reporter.py:56`).
   Формулировка «report_find не блокирует вызывающего» была бы неточной — блокирует, но на копию кадра и
   два локальных замера, а не на HTTP.
3. **Формат bbox жёсткий.** Отрисовка делает `bbox.xyxy.cpu().tolist()[0]` (`debug_reporter.py:32`), то есть
   ждёт объект бокса YOLO, а не список float. Список из поля `box` записи журнала (Часть A, 4.6) сюда не
   подойдёт. Сбой отрисовки не теряет кадр: он проглатывается (`debug_reporter.py:40-41`), и кадр уходит
   без рамки.
4. **Исходный кадр не мутируется** — рисование идёт по `img = frame_bgr.copy()` (`debug_reporter.py:29`).
   Значит отправка в Telegram не может испортить кадр, который параллельно пишется/читается с диска.
5. **`hwid` не берётся внутри `debug_reporter`** — он параметр (`debug_reporter.py:14,27,59,77`). Реальный
   источник у 1.0 — ленивый импорт в месте вызова: `from debug_reporter import report_find` +
   `from auth import get_hwid` и `report_find(get_hwid(), frame, box, conf=_conf)`
   (`navigator.py:1076-1079`), тот же приём в `navigator.py:1138-1140` (`report_dialog`) и
   `engine.py:252-256` (`report_ocr_result`). Сам `get_hwid` — `auth.py:32-35`:
   `SHA256(str(uuid.getnode()))[:16].upper()`, без сети и без кэша. Вызов в `navigator.py` дополнительно
   обёрнут в `try/except Exception: pass` (`navigator.py:1074-1081`) — то есть даже падение импорта не
   роняет охоту.
6. **`shot_type` сервером НЕ валидируется.** Приёмник — `server/debug_router.py:19-49`; поле объявлено как
   свободная строка `shot_type: str = Form(...)` (`debug_router.py:23`, комментарий `# "FIND" | "DIALOG"` —
   это комментарий, а не проверка). Значение попадает только в подпись сообщения (`debug_router.py:36`) и в
   одно условие: строка «🎯 Точность» добавляется, **только если `shot_type == "FIND"`**
   (`debug_router.py:35`). Практическое следствие для 2.0: новый тип снимка можно ввести **без изменения и
   деплоя сервера**, но `conf` отобразится только под типом ровно `"FIND"`.

### 2.7 Монетизация 1.0 — точная цепочка

Владелец потребовал для 2.0 «точно такую же логику, что и 1.0». Цепочка 1.0 прослежена по коду целиком,
звено за звеном, чтобы «такая же» означало проверенное, а не правдоподобное:

1. **Гейт на старте:** `toggle_bot()` → `if self.current_credits <= 0: messagebox.showwarning(...); return`
   (`main.py:3574-3575`) — до любой инициализации движка (`engine.start(...)` идёт ниже, `main.py:3587`).
2. **Привязка callback'а:** `self.engine.on_found_callback = self.on_target_found` (`main.py:1600`) →
   `self._pacman.on_found_callback = self.on_found_callback` (`engine.py:203`; при включённом ROY — тот же
   callback внутри обёртки, `engine.py:201`, `236-245`).
3. **Момент вызова:** `PacmanEngine` зовёт его последним шагом обработки находки —
   `if self.on_found_callback: self.on_found_callback()` (`navigator.py:1145-1146`), то есть **после**
   повторного подтверждающего скана `_fresh_scan()` и **после** фактического клика. Обе ранние ветки
   «биржа не подтвердилась» (`navigator.py:1111-1112`) и «клик не удался» (`navigator.py:1123-1124`)
   возвращаются `return` до этой строки — кредит в этих случаях не тратится.
4. **Списание:** `on_target_found` → `self.after(0, self._process_found)` (`main.py:3751-3753`) →
   `res = spend_credit("exchange")` (`main.py:3759`).
5. **Контракт `spend_credit`** (`auth.py:106-124`): POST `/use_credit` с `timeout=5` (`auth.py:114-118`),
   `_mark_contact_success()` при любом полученном ответе (`auth.py:119`), при HTTP 402 —
   `{"success": False, "low_credits": True, ...}` (`auth.py:120-121`), при любом другом статусе — сырой
   `response.json()` (`auth.py:122`), при сетевом сбое/таймауте — `{"success": False}` (`auth.py:123-124`).
6. **Реакции GUI** (`main.py:3760-3767`), ровно три ветки: успех → обновить счётчик; `low_credits` →
   `self.toggle_bot()` (то есть **стоп охоты**) + открыть страницу пополнения; иначе, если
   `seconds_since_last_contact() > HEARTBEAT_TIMEOUT` (`auth.py:20,29-30`, порог 120 с) → стоп + окно
   «offline_stopped». Обычный сетевой сбой без превышения 120 с находку не оплачивает и охоту не
   останавливает.
7. **Списание не зависит от OCR.** `_process_found` вызывает `spend_credit` безусловно; чтение координат
   у 1.0 живёт в отдельной ветке ROY (`engine.py:248-262`) и на списание не влияет вообще. Этот факт —
   прямое основание решения по `coords_ok:false` в C-17.

### 2.8 Серверная сторона `/use_credit` и синхронизация баланса (новое, написано здесь)

В Части A это место было честно помечено как **непроверенный факт** (A-16). В этом документе оно
прочитано лично; ниже — результат, а не гипотеза.

1. **Цена биржи — 10 кредитов на сервере:** `CREDIT_COST = {"exchange": 10, "crypt": 1, "chest": 10}`
   (`server/main.py:131-135`), используется как `cost = CREDIT_COST.get(req.hunt_type, req.amount)`
   (`server/main.py:313`). Клиентская сторона своего числа не передаёт для `exchange`.
2. **Списание атомарно на уровне БД:** один `UPDATE ... WHERE hwid = ... AND credits >= cost AND
   is_banned == False ... RETURNING id, credits` (`server/main.py:317-322`) внутри `async with db.begin()`
   (`315`). Отдельного `SELECT FOR UPDATE` нет и не нужно: гонка двух одновременных списаний закрывается
   самим условием `credits >= cost`.
3. **Ветки отказа:** нет строки → определяется причина: пользователь не найден → 404
   (`server/main.py:329-330`), забанен → 403 (`331-332`), иначе → **402** с `detail.message/credits/required`
   (`333-340`). Клиент распознаёт из них только 402 (`auth.py:120-121`); 403 и 404 придут в GUI как сырой
   `response.json()` без ключа `success` — то есть будут выглядеть как «не оплачено, продолжаем».
4. **🔴 На сервере есть rate limit, которого нет ни в одном описании 2.0:**
   `_credit_ratelimit: dict[str, float]` и `_CREDIT_COOLDOWN_SEC = 2.0` (`server/main.py:34-37`),
   проверка — первое, что делает эндпоинт: ключ `f"{hwid}:{hunt_type}"`, при попадании в окно —
   `raise HTTPException(status_code=429, detail="Too many requests")` (`server/main.py:305-311`).
   То есть **чаще одного списания `exchange` в 2 секунды на один HWID сервер не проводит**.
   Разбор последствий для 2.0 — находка A-19 и контракт C-20 (владелец решил снять лимит для 2.0,
   не трогая 1.0).
5. **`/use_credit` НЕ вызывает `notify_balance_changed`.** Грепом по `server/`: вызовы есть только в
   `blacksea.py:425`, `earn.py:98`, `payments.py:229`, `web_routes.py:628` — все это **начисления**.
   В эндпоинте `/use_credit` (`server/main.py:297-352`) вызова нет. Списание long-poll бота не будит.
6. **Но long-poll и без побудки возвращает актуальный баланс.** `GET /vault/sync/{hwid}`
   (`server/vault.py:30-72`) ждёт события максимум 50 с, а по таймауту идёт дальше по коду
   (`vault.py:39-44`, комментарий в исходнике: «Нормальный heartbeat — всё равно вернуть баланс») и
   **всегда** возвращает текущие `credits`/`ref_credits` из БД через `UPDATE ... RETURNING`
   (`vault.py:53-72`). На стороне бота: `get_balance_update()` с `timeout=58` (`auth.py:127-143`),
   бесконечный цикл в daemon-треде `_start_balance_sync` (`main.py:3311-3322`), запущенный при старте GUI
   (`main.py:1872`), применяет результат через `self.after(0, ... _update_credits_display(c))`
   (`main.py:3319`), а `_update_credits_display` присваивает `self.current_credits = n` (`main.py:3283`).
   **Вывод (проверенный, не предполагаемый):** расхождение локального счётчика с реальным балансом после
   потерянного ответа на списание самоустраняется на следующем цикле long-poll, то есть за ≈50 секунд
   плюс время переподключения — без какого-либо уведомления со стороны `/use_credit`. Это выравнивает баланс на экране, но не сообщает, была ли оплачена конкретная находка.

7. **Различение режимов на сервере — только по строке `hunt_type`.** Ключ лимита
   `rl_key = f"{req.hwid}:{req.hunt_type}"` (`server/main.py:308`); цена берётся сервером —
   `cost = CREDIT_COST.get(req.hunt_type, req.amount)` (`server/main.py:313`) при
   `CREDIT_COST = {"exchange": 10, "crypt": 1, "chest": 10}` (`server/main.py:131-135`), то есть для типа,
   записанного в `CREDIT_COST`, клиентское поле `amount` (`server/schemas.py:20-24`) игнорируется.
   Длина имени типа ограничена схемой: `hunt_type = Column(String(20), nullable=False)`
   (`server/models.py:143`).
8. **Статистика привязана к строке типа буквально:** `where(Hunt.hunt_type == "exchange")`
   (`server/main.py:615`), `func.cast(Hunt.hunt_type == "exchange", Integer)` (`server/main.py:919`),
   `if metric in ("crypt", "exchange", "chest")` → `.where(Hunt.hunt_type == metric)`
   (`server/main.py:998-1003`), `group_by(Hunt.hunt_type)` + `counts.get("exchange", 0)`
   (`server/web_routes.py:298-314`).

### 2.9 Система РОЙ — существующий приём координат (новое, написано здесь)

Прочитано лично: `server/roy.py`, `roy/roy_client.py`, `engine.py:248-281`.

1. **Контракт запроса жёсткий, все пять полей обязательны:** `class ReportRequest(BaseModel)` —
   `hwid: str, kingdom: int, x: int, y: int, percent: int` (`server/roy.py:192-197`). Значений по
   умолчанию нет ни у `kingdom`, ни у `percent`.
2. **Аутентификации и оплаты у `/roy/report` нет.** Эндпоинт (`server/roy.py:243-296`) принимает `hwid`
   в теле, не проверяет ни членство в РОЙ, ни баланс времени, ни активность ивента; `RoyBalance` в нём
   не участвует вовсе (списания времени живут в `/roy/scan`, `/roy/idle`, `/roy/pool`).
3. **Rate limit 10 секунд на hwid, и отказ выглядит как успех:**
   `if now_ts - _report_rate.get(req.hwid, 0) < RATE_LIMIT_SEC: return {"success": True,
   "note": "rate_limited"}` (`server/roy.py:256-258`, константа `RATE_LIMIT_SEC = 10` —
   `server/roy.py:39`). То есть отброшенный репорт возвращает `success: True`, и клиент 1.0, который
   смотрит именно на `success` (`roy/roy_client.py:39`), считает его доставленным.
4. **Дедупликация — по тройке (K, X, Y) среди непросроченных записей** (`server/roy.py:269-277`):
   найденная запись обновляет `percent`, `updated_at`, `expires_at`; иначе INSERT с `is_new = True`
   (`278-285`). Конкурентный INSERT той же координаты гасится `except IntegrityError: pass` (`286-287`).
5. **Время жизни координаты — 20 минут:** `POOL_TTL_MIN = 20` (`server/roy.py:35`),
   `expires = now + timedelta(minutes=POOL_TTL_MIN)` (`262`).
6. **Пул показывает только `percent < 90`:** `RoyPool.percent < PERCENT_THRESHOLD` (`server/roy.py:453`,
   константа `PERCENT_THRESHOLD = 90` — `roy.py:38`). Репорт с `percent >= 90` сохраняется, но в выдаче
   пула не появляется.
7. **Клиент 1.0:** `RoyClient.report(kingdom, x, y, percent, on_success)` (`roy/roy_client.py:27-48`) —
   HTTP в отдельном **не**-daemon треде, `timeout=5` (`roy_client.py:9`), все ошибки глушатся
   (`44-45`), `on_success` зовётся только при `success: True` (`39-43`).
8. **Кто зовёт это сегодня:** `HuntEngine._roy_on_found` (`engine.py:248-281`) — после OCR **открытого
   диалога биржи** (`roy.exchange_reader.wait_and_read`, `engine.py:252-254`), который даёт
   `kingdom/x/y/percent`. Гейт публикации у 1.0 клиентский: `if result['percent'] < 90 and not
   (self.roy_enabled and self.event_active)` → не отправляем; отправка идёт только при `percent < 90`
   **и** включённом РОЙ **и** активном ивенте (`engine.py:263-274`).

**Что в этой секции осталось непроверенным (явно):** (i) какая ревизия `server/main.py` реально запущена
на GCP — из локального репозитория это не определяется, а в текущей сессии я на сервер не ходил;
(ii) сколько worker-процессов у uvicorn на проде — это влияет на то, глобален ли in-memory rate limit
(`server/main.py:36`) или считается в каждом процессе отдельно. Для 2.0 после C-20 второй пункт значения
не имеет (лимит к 2.0 не применяется), для оставшейся защиты 1.0 — имеет.

---
