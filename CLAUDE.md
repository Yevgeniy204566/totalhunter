# BattleBot — Total Battle Hunter
## Конституция проекта (неизменяемый фундамент)

> Детальный статус → STATE.md | Запреты → ANTI-PATTERNS.md

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
TOKEN="vcp_2OacfkL9S4wbYB31ngyotlULFv7nedPLGMp6ICpIILlk13PbwP3NVtBj"
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
