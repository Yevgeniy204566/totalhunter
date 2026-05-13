# Total Hunter — Онбординг-документ для ИИ-ассистента
## Последнее обновление: 2026-05-13 (Хангоф #50)

> Этот файл — единственный источник правды для новой сессии.
> Читаешь его → сразу понимаешь всё и можешь работать без вопросов.

---

## 1. Что такое Total Hunter

Коммерческий SaaS-бот для игры **Total Battle**. Автоматически ищет Биржи (Exchange) и Склепы (Crypts) на карте королевства. Три компонента: Python-бот (клиент, платный, Windows), FastAPI-сервер (GCP), React-сайт (Vercel). Монетизация — крипто-кредиты через NOWPayments. Текущая версия: **v1.2.2**.

- Сайт: https://total-hunter.com
- API: https://api.total-hunter.com
- GitHub (ПУБЛИЧНЫЙ): https://github.com/Yevgeniy204566/totalhunter

---

## 2. Технологический стек

**Бот (клиент, Windows):**
- Python 3.13, OpenCV, PyAutoGUI, MSS, pytesseract
- YOLO (ultralytics) — exchange.pt, crypts.pt
- CustomTkinter — GUI 460×1010, тёмная тема, 19 языков (PIL-флаги)
- Google OAuth → JWT авторизация
- HWID = MAC → SHA256 → 16 символов

**Сервер:**
- FastAPI + PostgreSQL (asyncpg) + SQLAlchemy async + Alembic
- GCP Compute Engine, Debian 12, systemd, Nginx + SSL
- IP: 34.68.86.57, app path: /opt/totalhunter/server

**Фронтенд:**
- React + Vite → Vercel
- Страницы: Landing, Dashboard, Balance, Hunts, Referrals, ReferralTree (/dashboard/tree), Guide, Earn, Devices, Transactions

**Платежи:**
- NOWPayments (крипто) — IPN raw bytes HMAC-SHA512
- Long-poll синхронизация баланса бот↔сайт: `GET /vault/sync/{hwid}`

---

## 3. 🚨 ПОВЕДЕНЧЕСКИЕ ПРАВИЛА (НЕРУШИМО)

### Правило 0 — СНАЧАЛА ПОНЯТЬ, ПОТОМ ДЕЛАТЬ
При любой ошибке / баге / 404 / «не работает»:
1. Читать `MEMORY.md` и `STATE.md`
2. Найти первопричину. Если непонятно — задать **ОДИН** вопрос
3. Предложить минимальное решение → ждать явного **«да»**
4. **Только потом** трогать код

### Правило 1 — NO CHANGES WITHOUT APPROVAL
Объяснить что собираюсь делать → ждать явного «да» → только потом писать код. Никогда не начинать редактировать файлы до одобрения.

### Правило 2 — NO SIDE EFFECTS
Если изменение **может** сломать другую механику → **СТОП**, немедленно сообщить. Не пробовать «исправить по-тихому».

### Правило 3 — TDD обязателен
Тесты пишутся **перед** кодом. Superpowers TDD workflow перед любым новым кодом.

### Правило 4 — Brainstorm перед реализацией
Перед любой новой фичей — Superpowers Brainstorm.

### Правило 5 — Beads (`bd`) для задач
Все задачи трекаются через Beads. Перед началом — завести задачу.

### Стиль общения
- Язык: **русский**
- Ответы: **короткие и по делу** — пользователь видит diff, не нужен пересказ
- Команды: copy-paste готовые, не описания
- Commit style: `feat/fix/chore/docs: ...`
- Всегда называть точное время ожидания, не оставлять без таймера
- Изменения без явного «да» — ЗАПРЕЩЕНЫ

---

## 4. 🗺️ КАРТА ДЕПЛОЯ (copy-paste готовые команды)

### Фронтенд → Vercel (3 ОБЯЗАТЕЛЬНЫХ ШАГА)

> ⚠️ `git push` в одиночку = только Preview, не Production. `npx vercel --prod` — ЗАПРЕЩЕНО.

```bash
# Шаг 1 — пушим код
git add web/src/... && git commit -m "feat: ..." && git push origin main

# Шаг 2 — триггерим деплой хуком
curl -s -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"

# Шаг 3 — ждём READY и прикрепляем домен
TOKEN="vcp_6DSYv8wkJD8vKnQUtwRi1kiO0vGXsRznVUffzynEMQL6YA2h052lWRhG"
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

**Почему:** `productionBranch=master` в Vercel. Push в `main` → Preview только. Hook + alias = Production.
**Если токен истёк:** vercel.com → Account Settings → Tokens → Create → дать Claude.

---

### Бэкенд → GCP (только git pull, никаких файлов!)

```bash
# Пользователь SSH'ится в GCP (через Cloud Shell или напрямую):
# ВАЖНО: если уже на сервере — НЕ писать gcloud compute ssh (ошибка "SSH to yourself")
cd /opt/totalhunter/server && sudo git pull origin main && sudo systemctl restart totalhunter
```

**ЗАПРЕЩЕНО:** загружать ZIP/архивы на GCP. Редактировать файлы напрямую на сервере.
**GCP VM:** total-hunter-backend, zone=us-central1-f, project=digital-arcade-274010

---

### Alembic миграции на GCP

```bash
# Получить DATABASE_URL из запущенного сервиса:
sudo strings /proc/$(systemctl show -p MainPID totalhunter | cut -d= -f2)/environ | grep DATABASE_URL
# Результат: postgresql+asyncpg://hunter:TotalHunter2026@localhost:5432/totalhunter

# Текущая ревизия:
DATABASE_URL=postgresql+asyncpg://hunter:TotalHunter2026@localhost:5432/totalhunter \
  /opt/totalhunter/venv/bin/alembic current

# Запустить миграцию (НЕ "head" — на GCP multiple heads!):
DATABASE_URL=postgresql+asyncpg://hunter:TotalHunter2026@localhost:5432/totalhunter \
  /opt/totalhunter/venv/bin/alembic upgrade <revision_id>
```

**Важно:** На GCP есть миграции которых нет в репо: `14e8d8e2a95a`, `575bdc292d9e`, `22864ea6408d`.
Нужно синхронизировать — скопировать из GCP в `server/alembic/versions/` и запушить.

---

### GitHub Releases (бот ZIP)

```bash
# Создать релиз:
gh release create v1.X.X --title "Total Hunter v1.X.X" --notes "..."

# ZIP ЗАГРУЖАТЬ ТОЛЬКО ЧЕРЕЗ БРАУЗЕР (gh release upload зависает на 300MB+):
# github.com/Yevgeniy204566/totalhunter/releases → Edit release → перетащить файл

# После релиза обновить версию на сервере:
curl -X POST "https://api.total-hunter.com/admin/version/update?version=1.X.X" \
  -H "Authorization: Bearer zQ2z8D80xEnLTET0kQ0Bl85EYlTZBLIAtc37dZAmmK8"
```

---

## 5. 🔑 Ключи и токены

> Хранить в `.env.local` или systemd `override.conf`. Никогда в git.

| Ключ | Значение |
|---|---|
| VERCEL_TOKEN | `vcp_6DSYv8wkJD8vKnQUtwRi1kiO0vGXsRznVUffzynEMQL6YA2h052lWRhG` |
| ADMIN_SECRET_KEY | `zQ2z8D80xEnLTET0kQ0Bl85EYlTZBLIAtc37dZAmmK8` |
| DATABASE_URL | `postgresql+asyncpg://hunter:TotalHunter2026@localhost:5432/totalhunter` |
| NOWPAYMENTS_API_KEY | `JKPMX8E-YS5MVV1-M0GTWDH-6WQ7SVP` |
| NOWPAYMENTS_IPN_SECRET | `iYOJZOwoI1a+M1gZ65bt0PAaul4GJvTd` |
| IPN URL | `https://api.total-hunter.com/web/payment/webhook` |
| Vercel Project | `prj_mWtcb6hJCkl40YLWheeIlxD5NmXj` |
| Vercel Team | `team_CkkRPXdwtRtsL9YCk8n4Fzla` |
| GitHub repoId | `1215361801` |

---

## 6. ⛔ КРИТИЧЕСКИЕ АНТИ-ПАТТЕРНЫ

**AP-DEPLOY-1: `npx vercel --prod` — ЗАПРЕЩЕНО**
→ Vercel читает `rootDirectory:"web"` → ищет `web/web` → не существует.

**AP-DEPLOY-2: `git push` без hook + alias**
→ `productionBranch=master` → push в `main` = Preview. Всегда 3-шаговый деплой.

**AP-DEPLOY-3: alias до нового READY билда**
→ Alias указывает на старый деплой. Ждать новый DEP_ID со state=READY.

**AP-DEPLOY-4: Спрашивать пользователя параметры деплоя**
→ Всё есть в этом документе. Читать, брать, деплоить самостоятельно.

**AP-GCP-1: Загружать файлы на GCP**
→ GCP = только git pull + systemctl restart. ZIP бота = только GitHub Releases.

**AP-GCP-2: Изменять server/main.py без диагностики**
→ Сначала найти первопричину.

**AP-GCP-3: Добавлять зависимости без проверки на GCP**
→ pip install локально ≠ установлено на сервере.

**AP-DB-1: Два db.begin() в одном эндпоинте**
→ SQLAlchemy: `flush()` + один `commit()`. Никогда два `db.begin()`.

**AP-PAY-1: json.loads/dumps для NOWPayments IPN подписи**
→ HMAC-SHA512 только от raw_body_bytes.

**AP-RELEASE-1: gh release upload для файлов 300MB+**
→ Зависает. ZIP только через браузер (Edit release → drag & drop).

**AP-VERSION-1: Текст в поле версии Admin Panel**
→ Только формат `1.0.8`. Текст = сломает автообновление у всех. Фикс: curl admin/version/update.

**AP-NUITKA-1: .pyd в корне проекта**
→ Python загружает .pyd вместо .py → правки в .py не работают. `Remove-Item *.pyd` перед запуском из исходников.

---

## 7. Статус модулей

| Модуль | Файл | Статус |
|---|---|---|
| Платежи NOWPayments | server/payments.py | ✅ IPN raw bytes |
| Long-poll синхронизация | server/vault.py | ✅ |
| Earn/Casino | server/earn.py | ✅ лимит 5/день |
| Рекламные слоты | web/AdSlot.jsx | 🟡 Заглушка, PopAds на модерации |
| MLM Реферальное дерево | web/pages/ReferralTreePage.jsx | ✅ /dashboard/tree, pan+zoom |
| Движок бирж | engine.py + navigator.py | ✅ 54 теста |
| CryptHunter | crypt_hunter.py | ✅ Anti-groundhog |
| GUI — 19 языков | main.py | ✅ PIL-флаги |
| Auto-update | updater.py | ✅ v1.2.2 |
| Лендинг | web/LandingPage.jsx | ✅ мобильный |
| SEO | web/ | ✅ useMeta, FAQ Schema |
| Silent Observer | main.py + web_routes.py | ✅ crash reporter |
| Mobile OAuth | web_routes.py + LoginPage.jsx | ✅ |
| Admin Panel | server/admin/index.html | ✅ adjust_credits + Краши |
| Авто-калибровка | auto_calibration.py | ✅ 2 этапа, 13 тестов |
| Installer | installer.iss | ✅ Win10+, 64-bit |
| Combo | combiner.py | ⛔ ЗАМОРОЖЕН |

---

## 8. Приоритетные задачи

1. **PopAds** — одобрение → вставить код в `web/src/components/AdSlot.jsx` → деплой Vercel
2. **Alembic sync** — скопировать с GCP в репо: `14e8d8e2a95a`, `575bdc292d9e`, `22864ea6408d`
3. **Тест v1.2.2** — 19 языков, флаги, anti-groundhog у пользователей
4. **Хедер Layout.jsx** — обновить ссылку Скачать: EXE → ZIP
5. **Discord интеграция** — не к спеху

---

## 9. Файловая структура (ключевые файлы)

```
C:\BattleBot\
├── main.py              — GUI (TotalHunterApp), 19 языков
├── engine.py            — HuntEngine → PacmanEngine
├── navigator.py         — CoastalSnakeNavigator + OCR позиций
├── minimap_reader.py    — centroid воды → угол берега
├── auth.py              — HWID, лицензии, кредиты, heartbeat
├── crypt_hunter.py      — CryptHunter (слепой, T_max/2^N)
├── button_finder.py     — HSV-детект кнопок
├── coord_manager.py     — 2-точечная калибровка (REF_A=90,925 REF_B=1149,88)
├── updater.py           — auto-update, ZIP download
├── profiles/            — JSON калибровки (client/chrome/firefox)
├── server/
│   ├── web_routes.py    — все /web/* эндпоинты (referral tree, auth, payments...)
│   ├── payments.py      — NOWPayments IPN
│   ├── vault.py         — long-poll баланс
│   ├── earn.py          — earn endpoint
│   ├── schemas.py       — Pydantic модели
│   ├── models.py        — SQLAlchemy ORM (User, Transaction, Hunt, Order...)
│   ├── admin/           — Admin Panel HTML
│   └── alembic/         — миграции БД
├── web/src/
│   ├── pages/           — LandingPage, ReferralsPage, ReferralTreePage, GuidePage...
│   ├── components/      — Layout, AdSlot, ReferralTree (ZoomableCanvas)...
│   ├── dashboard_content.js / .en.js — i18n строки
│   └── styles/          — mobile.css, theme.css
├── docs/gemini_buffer.md — ЭТОТ ФАЙЛ
├── STATE.md             — текущий статус
├── ANTI-PATTERNS.md     — что запрещено (подробно)
└── CLAUDE.md            — конституция проекта (полные правила)
```

---

## 10. 🔒 Архитектурные константы (не менять без понимания)

### Навигация (биржевый бот)
- Навигатор: `CoastalSnakeNavigator`
- Правило змейки: **НЫРОК → СДВИГ → ВОЗВРАТ → СДВИГ → повтор** (нерушимо)
- Правило маяка: RETURNING останавливается ТОЛЬКО на линии маяка. Реки — не помеха.
- `CompassNavigator` — устаревший, не использовать

### Платежи
- NOWPayments IPN: только raw bytes HMAC-SHA512
- Начислять только при `"finished"`
- После commit() → обязательно `notify_balance_changed(hwid)`
- Long-poll (не polling/таймер) для обновления баланса в боте

### Координаты
- Всегда через `coord_manager.to_screen()` / `coord_manager.to_region()`
- `window_scaler.py` удалён — не восстанавливать

### Анти-детект
- Паузы: 0.4–0.9 сек, смещение кликов: 5–8 пикселей

---

## 11. Быстрые команды

```bash
# Статус сервиса GCP:
sudo systemctl status totalhunter

# Логи сервиса (последние 100 строк):
sudo journalctl -u totalhunter -n 100 --no-pager

# Проверить версию в API:
curl https://api.total-hunter.com/version/latest

# Обновить версию бота:
curl -X POST "https://api.total-hunter.com/admin/version/update?version=1.X.X" \
  -H "Authorization: Bearer zQ2z8D80xEnLTET0kQ0Bl85EYlTZBLIAtc37dZAmmK8"

# Проверить Alembic на GCP:
DATABASE_URL=postgresql+asyncpg://hunter:TotalHunter2026@localhost:5432/totalhunter \
  /opt/totalhunter/venv/bin/alembic current
```

---

*Документ обновляется командой «Хангоф» перед /compact или /clear.*
*Следующее обновление: Хангоф #51*
