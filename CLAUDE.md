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
- **Нет изменений без явного «да»** от пользователя
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

## 7. Workflow памяти и контекста

- **«Хангоф»** — команда перед `/compact` или `/clear`. Обновляет STATE.md + ANTI-PATTERNS.md.
- **STATE.md** — бортжурнал: что готово, что в работе, известные баги
- **ANTI-PATTERNS.md** — запреты и тупиковые решения
- **MEMORY/** — персистентная память между сессиями Claude
