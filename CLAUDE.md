# BattleBot — Total Battle Hunter
## Конституция проекта (неизменяемый фундамент)

> Детальный статус → STATE.md | Запреты → ANTI-PATTERNS.md

---

## 🔒 0. ПРОТОКОЛ «СНАЧАЛА ПОНЯТЬ — ПОТОМ ДЕЛАТЬ» (ВЫСШИЙ ПРИОРИТЕТ)

**При любой ошибке, баге, 404, 502, «не работает»:**
1. Прочитать `MEMORY.md` и `STATE.md`
2. Найти первопричину. Если непонятно — задать ОДИН вопрос
3. Предложить минимальное решение → ждать явного «да»
4. Только потом трогать код

**Карта деплоя — знать наизусть:**
| Что | Куда | Команда |
|---|---|---|
| Фронтенд (`web/`) | Vercel | git push + hook + alias |
| Бэкенд код (`server/`) | GCP git pull | `cd /opt/totalhunter/server && sudo git pull && sudo systemctl restart totalhunter` |
| Релизы бота (`TotalHunter.zip`) | GitHub Releases (ПУБЛИЧНЫЙ) | `gh release create vX.X.X` + API version/update |

**ЗАПРЕЩЕНО:**
- Хранить файлы/архивы на GCP — только код через git
- Изменять `server/main.py` без диагностики первопричины
- Добавлять зависимости без проверки что они установлены на GCP
- Создавать или заливать `TotalHunter_Setup.exe` — дистрибутив ТОЛЬКО `TotalHunter.zip`

---

## 1. Цель проекта
Коммерческий SaaS-бот для игры Total Battle.
Автоматический поиск Бирж (Exchange) и Склепов (Crypts) на карте королевства.

---

## 2. Стек технологий

**Бот (клиент):**
- Python 3.13, OpenCV, PyAutoGUI, MSS, pytesseract
- YOLO (ultralytics) — детекция объектов на экране
- CustomTkinter — GUI, тёмная тема, 2 языка (RU/EN)
- Google OAuth — авторизация

**Сервер:**
- FastAPI + PostgreSQL (asyncpg) + SQLAlchemy async + Alembic
- GCP Compute Engine `34.68.86.57:8000` | Ubuntu 22.04 | systemd

---

## 3. Архитектурные стандарты

### Координатная система
- Глобальный синглтон: `coord_manager` из `coord_manager.py`
- Эталон: 1920×1080. REF_A=(90,925), REF_B=(1149,88)
- Все координаты → через `coord_manager.to_screen()` / `coord_manager.to_region()`
- **Никогда не использовать** `window_scaler.py` (удалён)

### Навигация
- Основной навигатор: `CoastalSnakeNavigator` (centroid воды → ⊥ к берегу)
- `CompassNavigator` — устаревший, не использовать
- Движок: `PacmanEngine` → `CoastalSnakeNavigator`
- Джойстик: CENTER=(90,925), STEP_Y=13, STEP_X=23

### 🔒 ЗОЛОТОЕ ПРАВИЛО ЗМЕЙКИ (БИРЖЕВЫЙ БОТ — НЕРУШИМО)

```
НЫРОК → СДВИГ → ВОЗВРАТ → СДВИГ → повтор
```

**Это фундамент. Любое изменение кода навигатора ОБЯЗАТЕЛЬНО проверяется:**
1. Выполняется ли полный цикл: нырок → сдвиг → возврат → сдвиг?
2. Есть ли хотя бы 1 сценарий где цикл не выполнится на 100%?
3. Если ДА — такое решение НЕ предлагается и НЕ реализуется.

**Маяк** = точка на берегу, 2 шага вправо от точки нырка, перпендикулярно нырку.
**ВОЗВРАТ = физически прийти в точку маяка ЛЮБОЙ ЦЕНОЙ.**

### 🔒 ПРАВИЛО МАЯКА (НАИВЫСШИЙ ПРИОРИТЕТ ПОСЛЕ СТАРТА)

**При RETURNING: маяк = абсолютный авторитет. Реки и ручьи НЕ являются препятствием.**
- Бот идёт к маяку по линии маяка (is_beyond_beacon_line)
- Визуальные проверки воды НЕ используются пока активен маяк
- Единственная остановка в RETURNING = достижение линии маяка
- Любой код который останавливает RETURNING ДО маяка — ЗАПРЕЩЁН

### Склепы
- `CryptHunter` — детерминированная логика, без OCR
- Формула ожидания: `T_one_way = T_max / 2^N`
- Язык игры не влияет на логику

### GUI
- CustomTkinter, 460×1010, snap вправо (always-on-top)
- Порядок вкладок: СКЛЕПЫ → БИРЖИ → РЕФЕРАЛЫ → КАЛИБРОВКА
- Профили: `profiles/profile_client.json`, `profile_chrome.json`, `profile_firefox.json`
- Настройки: `gui_config.json`

### Аутентификация
- HWID = MAC → SHA256 → 16 символов
- `auth.py`: `check_license()`, `spend_credit()`, `heartbeat()`

---

## 3.5. 🔒 АРХИТЕКТУРА ПЛАТЕЖЕЙ И СИНХРОНИЗАЦИИ (НЕРУШИМО)

### Платёжный провайдер: NOWPayments (крипто)
- **НИКОГДА** не возвращаться к Free-Kassa или другим провайдерам без явного решения
- IPN подпись: `hmac.new(IPN_SECRET, raw_body_bytes, sha512)` — **только raw bytes**, без json.loads/dumps
- Статус для начисления: только `"finished"` — всё остальное игнорировать с ответом 200
- Идемпотентность: `if order.status == "paid": return 200` без повторного начисления
- SQLAlchemy: `flush()` + один `commit()` — **никогда два db.begin()** в одном эндпоинте

### Синхронизация баланса: Long Polling (vault.py)
- **НИКОГДА** не использовать таймер/polling для обновления баланса в боте
- Архитектура: `GET /vault/sync/{hwid}` — сервер держит соединение 50 сек
- Триггер: `notify_balance_changed(user.hwid)` вызывать **после commit()** в webhook и spend_credit
- Бот: бесконечный цикл в daemon-треде, `get_balance_update()` с timeout=58s
- При добавлении нового способа начисления/списания — **обязательно** добавить `notify_balance_changed`

### Env vars на GCP (в systemd override.conf)
```
NOWPAYMENTS_API_KEY=...
NOWPAYMENTS_IPN_SECRET=...
```
Никаких FK_* переменных — они удалены навсегда.

---

## 4. Правила разработки

- **TDD обязателен** — Superpowers TDD workflow перед любым новым кодом
- **Beads** (`bd`) — трекинг всех задач
- **Brainstorm** (Superpowers) — перед любой реализацией
- **🔒 ОБЯЗАТЕЛЬНЫЙ WORKFLOW**: объяснить что собираюсь делать → ждать явного «да» → только потом трогать код. Никаких изменений без одобрения.
- Комментарии в коде — только WHY (не WHAT)
- Subagents — для рутины, изолированных кусков, парсинга логов

---

## 5. Анти-детект
- Паузы: **0.4–0.9 сек** между действиями
- Смещение кликов: **5–8 пикселей** (случайное)
- ESC → аварийный стоп (`keyboard.hook`)

---

## 6. Файловая структура

```
main.py           — GUI (TotalHunterApp)
engine.py         — HuntEngine → PacmanEngine
navigator.py      — CoastalSnakeNavigator + OCR позиций
minimap_reader.py — centroid воды → угол берега, конус-детекция
minimap_debug.py  — диагностика live (coast_angle, inland, ocean/river)
auth.py           — HWID, лицензии, кредиты, heartbeat
crypt_hunter.py   — CryptHunter (слепой склеп)
button_finder.py  — HSV-детект кнопок
coord_manager.py  — 2-точечная калибровка координат
calibration_ui.py — GUI-лупа для калибровки якорных точек
calibration.py    — автокалибровка джойстика
profiles/         — JSON-профили калибровки
server/           — FastAPI бэкенд (Cloud API + Admin Panel)
targets/          — YOLO модели (exchange.pt, crypts.pt)
docs/             — буфер Gemini, документация
```

---

## 6.5. 🔒 ДЕПЛОЙ САЙТА total-hunter.com — 3 ОБЯЗАТЕЛЬНЫХ ШАГА

**Claude делает все 3 шага сам. git push НЕДОСТАТОЧНО.**

```bash
# Шаг 1
git add web/src/... && git commit -m "..." && git push origin main

# Шаг 2 — триггер хука (запускает билд)
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"

# Шаг 3 — ждать READY и прикрепить домен
TOKEN="$VERCEL_TOKEN"
TEAM="team_CkkRPXdwtRtsL9YCk8n4Fzla"
PROJECT="prj_mWtcb6hJCkl40YLWheeIlxD5NmXj"
until STATE=$(curl -s "https://api.vercel.com/v6/deployments?projectId=$PROJECT&teamId=$TEAM&limit=1" \
  -H "Authorization: Bearer $TOKEN" | grep -o '"state":"[^"]*"' | head -1 | cut -d'"' -f4) \
  && [ "$STATE" = "READY" ]; do echo "State: $STATE"; sleep 10; done
DEP_ID=$(curl -s "https://api.vercel.com/v6/deployments?projectId=$PROJECT&teamId=$TEAM&limit=1" \
  -H "Authorization: Bearer $TOKEN" | grep -o '"uid":"[^"]*"' | head -1 | cut -d'"' -f4)
curl -s -X POST "https://api.vercel.com/v2/deployments/$DEP_ID/aliases?teamId=$TEAM" \
  -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" \
  -d '{"alias":"total-hunter.com"}'
```

**Почему:** productionBranch=master в Vercel (не main). Push в main → Preview, не Production. Нужен hook + alias.
**Если токен истёк:** vercel.com → Account Settings → Tokens → Create → дать Claude.

## 7. Workflow памяти и контекста

- **«Хангоф»** — команда перед `/compact` или `/clear`. Обновляет STATE.md + ANTI-PATTERNS.md.
- **STATE.md** — бортжурнал: что готово, что в работе, известные баги
- **ANTI-PATTERNS.md** — запреты и тупиковые решения
- **MEMORY/** — персистентная память между сессиями Claude
