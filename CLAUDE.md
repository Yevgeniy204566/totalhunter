# BattleBot — Total Battle Hunter
## Конституция проекта (неизменяемый фундамент)

> Детальный статус → STATE.md | Запреты → ANTI-PATTERNS.md | **Эталон биржевого бота → docs/exchange_bot_spec.md**

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
| Бэкенд код (`server/`) | GCP git pull | `cd /opt/totalhunter && sudo git clean -fd server/alembic/versions/ && sudo git pull origin main && sudo systemctl restart totalhunter` |
| Релизы бота (`TotalHunter.zip`) | GitHub Releases (ПУБЛИЧНЫЙ) | `gh release create vX.X.X` + API version/update |

**ЗАПРЕЩЕНО:**
- Хранить файлы/архивы на GCP — только код через git
- Изменять `server/main.py` без диагностики первопричины
- Добавлять зависимости без проверки что они установлены на GCP
- Создавать или заливать `TotalHunter_Setup.exe` — дистрибутив ТОЛЬКО `TotalHunter.zip`
- Запускать `7z` для создания ZIP из КОРНЯ проекта — ТОЛЬКО из `dist/TotalHunter/` (см. ниже)
- Выпускать ZIP без `README.txt` — файл ОБЯЗАН быть в архиве (автоматически через `build_release.py`)
- Выпускать ZIP без `tesseract_bin/` — папка ОБЯЗАНА быть в архиве (автоматически через `build_release.py`)
- Изменять состав `tesseract_bin/` без проверки: `& "C:\BattleBot\tesseract_bin\tesseract.exe" --version` → exit code 0

**🔒 ОБЯЗАТЕЛЬНЫЙ ЧЕКЛИСТ ПЕРЕД СБОРКОЙ:**
```powershell
# 1. README.txt существует?
Test-Path "C:\BattleBot\README.txt"            # → True

# 2. Tesseract полный и работает?
& "C:\BattleBot\tesseract_bin\tesseract.exe" --version  # → "tesseract v5.x.x", exit 0

# 3. Эталонный состав tesseract_bin: 56 DLL + tessdata/{eng,rus,ara,jpn,chi_sim,chi_tra,kor}.traineddata
#    + tessdata/script/{Latin,Cyrillic}.traineddata = ~205 МБ (полное покрытие 19 языков бота)
# Источник: C:\Program Files\Tesseract-OCR\ (все *.dll + eng/rus.traineddata)
#           + https://github.com/tesseract-ocr/tessdata_fast (script/Latin, script/Cyrillic,
#             ara, jpn, chi_sim, chi_tra, kor)
```

**🔒 КРИТИЧЕСКОЕ ПРАВИЛО ZIP (АНТИ-ДЕНЬ СУРКА):**
ZIP-архив для автообновления ОБЯЗАН быть плоским. Нарушение = петля обновлений у всех клиентов.
```powershell
# ПРАВИЛЬНО — запускать из dist/TotalHunter:
Set-Location "C:\BattleBot\dist\TotalHunter"
& "C:\Program Files\7-Zip\7z.exe" a -tzip "C:\BattleBot\TotalHunter.zip" "*" -mx=5
Set-Location "C:\BattleBot"

# ПРОВЕРКА ОБЯЗАТЕЛЬНА перед загрузкой:
# 7z l TotalHunter.zip | grep TotalHunter.exe → должно быть "TotalHunter.exe" БЕЗ dist/ префикса
```

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
BLACKSEA_CLIENT_ID=...
BLACKSEA_CLIENT_SECRET=...
BLACKSEA_PRODUCT_ID=...
```
Никаких FK_* переменных — они удалены навсегда.
`server/blacksea.py` падает `ValueError` на импорте, если хоть одна из трёх `BLACKSEA_*`
не задана — а `server/main.py` импортирует его безусловно, значит без них не стартует
весь API, не только BlackSea. Задавать эти три переменные ДО стандартного git pull +
restart, не после.

---

## 4. Правила разработки

- **TDD обязателен** — Superpowers TDD workflow перед любым новым кодом
- **Beads** (`bd`) — трекинг всех задач
- **Brainstorm** (Superpowers) — перед любой реализацией
- **🔒 РАБОТА С ДОКУМЕНТАМИ (спеки/планы) — `docs/РАБОТА-С-ДОКУМЕНТАМИ.md`**, обязательный протокол для
  ЛЮБОЙ спеки/плана (импортирован из Nutrition 2026-09-01 после того, как спека BlackSea сама дошла до 4
  раундов правок подряд): 10 стадий (Context → Code Archaeology → Contract Extraction → Design → Adversarial
  Review → Test Matrix → Self-Audit → External Agent Review → Final Gate → User Review), лимит **2 раунда
  правок документа**, дальше — обязательный `AskUserQuestion` (декомпозировать/продолжить осознанно/решает
  пользователь), не молчаливое суждение «продолжаю». Читать документ целиком перед КАЖДОЙ новой спекой/планом.
- **🔒 WORKFLOW (обновлено 2026-08-17, методология перенесена из Nutrition)**: диагностика → план → рутина (мелкие обратимые правки, очевидные фиксы, TDD-код по уже согласованному плану, тесты) — автономно, без «да»; архитектурные/рискованные/scope-изменяющие решения (числа, тайминги, дизайн/тексты, новые механики, необратимые действия) — жёсткий gate, нужен явный «да», общий позитивный тон разговора approval'ом не считается. Критерии и полный протокол → `MEMORY/feedback_autonomous_work_protocol.md`.
- **🔒 ОДИН ПОТОК ПО УМОЛЧАНИЮ**: не переключаться на новую задачу, пока текущая не доведена до терминального состояния (тесты прогнаны, результат зафиксирован). Если пользователь попросил что-то ещё раньше — явно сказать «сначала доделываю X, потом Y», не молча переключаться.
- **🔒 ЗАПРЕТ БЫСТРЫХ ФИКСОВ**: никогда не предлагать "просто поставь X" или "попробуй так". Любое исправление = системное: диагностика→план→код→тест→сборка→релиз. Быстрые фиксы ведут к хаосу.
- Комментарии в коде — только WHY (не WHAT)
- Subagents — для рутины, изолированных кусков, парсинга логов; один агент за раз на общие артефакты (код/спека/план) — параллельно только если задачи реально независимы

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

- **«Хангоф»** — команда перед `/compact` или `/clear`. Выполнить ВСЕ шаги:
  1. Прочитать `version.py` → зафиксировать текущую версию
  2. Оценить: накопились ли изменения для нового релиза? Написать вывод явно
  3. **Проверить сервер GCP** (`docs/INFRA_HEALTH.md` → End-of-Session Check): `free -h`,
     `df -h /`, `uptime`, `systemctl status totalhunter`, размер БД. Зона 🟡/🔴 → почистить
     (`sudo /opt/totalhunter/cleanup.sh`) сразу же, не оставлять на следующий раз. Это
     ОБЯЗАТЕЛЬНЫЙ шаг хангофа, не отдельная по запросу процедура — без напоминания владельца.
  4. Обновить `STATE.md` (модули, статус, версия, результат проверки сервера)
  5. Обновить `docs/gemini_buffer.md` (что сделано, что осталось)
  6. Обновить `ANTI-PATTERNS.md` если появились новые антипаттерны
  7. **Файл хангофа** (перенесено из Nutrition, 2026-08-17) — создать `Хангофы/Хангоф_YYYY-MM-DD_HH-MM.md` с двумя разделами: «Что сделано» и «Что делать в следующей сессии». Отдельный файл на КАЖДЫЙ хангоф, не перезаписывать предыдущие — история должна накапливаться, как коммиты.
- **STATE.md** — бортжурнал: что готово, что в работе, известные баги
- **ANTI-PATTERNS.md** — запреты и тупиковые решения
- **Хангофы/** — папка с датированными файлами каждого хангофа (см. шаг 7 выше)
- **MEMORY/** — персистентная память между сессиями Claude
- **docs/INFRA_HEALTH.md** — профилактика инфраструктуры. **Claude прогоняет End-of-Session Check в конце каждой крупной сессии** (diск/RAM/статус сервиса/размер БД на GCP) и выдаёт владельцу статус по зонам 🟢/🟡/🔴 (см. файл). Автоочистка раз в неделю висит в cron на сервере независимо от сессий — это не замена внешнему 24/7-мониторингу.
- **Смежный проект ASTRO** (`C:\ASTRO`, создан 2026-06-12) — отдельная конституция (CLAUDE.md/ANTI-PATTERNS.md/STATE.md), методология перенесена из BattleBot. Gemini-буфер (`docs/Исходящие_Claude.md`, `docs/Входящие_Gemini.md`) — ОБЩИЙ для обоих проектов; записи из Astro помечаются `[ASTRO]`
