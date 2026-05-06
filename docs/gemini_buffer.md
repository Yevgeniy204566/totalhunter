# Gemini Buffer — Хангоф #37 — 2026-05-07 01:00

---

## ✅ Что сделано сегодня (06-07 мая)

### 1. Иконки — полностью обновлены
- `web/public/favicon.ico` + `Icon_16/32/48/64/128/256.png` → алмаз (обрезан паддинг 54%)
- `server/admin/favicon.ico` → Рост_PNG (на GCP подтверждено MD5)
- `assets/icon.ico` → multi-size 16–256px для EXE
- `updater.py` → `ie4uinit.exe -show` сброс кеша иконок Windows после обновления

### 2. Автообновление — работает
- Репо `totalhunter` сделан **публичным** → ZIP скачивается без авторизации
- v1.0.9 собрана, опубликована на GitHub Releases, сервер обновлён
- Проверено: `ZIP v1.0.9: 200 OK`, `/version/latest` → `1.0.9`

### 3. Протокол «сначала понять — потом делать»
- 5 ячеек памяти (deploy arch, no server files, diagnose first, github public, all commands)
- CLAUDE.md раздел 0 — протокол деплоя и запреты
- 2 хука в settings.local.json (UserPromptSubmit + PreToolUse)

### 4. Vercel токен — защищён
- Старый токен был в публичном репо → Vercel отозвал автоматически
- Новый токен → в `.claude/settings.local.json` и memory (не в репо)
- Хранится только в `.claude/settings.local.json` (gitignored) и memory

### 5. Сайт — подготовлен к NOWPayments
- `/contacts` — новая страница (email, Telegram, цены, legal)
- `/legal` → email `totalhunter.support@gmail.com`, `@TotalHunter_bot`, NOWPayments вместо Free-Kassa
- Лендинг → Pricing секция (Lite $1, Pro $5, Ultra $10)
- Деплой total-hunter.com ✅

---

## 🔴 Задачи на завтра (2026-05-07)

### 1. Тест автообновления (ПЕРВЫМ ДЕЛОМ)
- Запустить v1.0.8 → не должен предлагать обновление (сейчас сервер на 1.0.9, надо сначала выставить 1.0.8 для теста)
- Точный порядок:
  ```bash
  # 1. Поставить сервер на 1.0.9 (уже стоит)
  # 2. Запустить старый v1.0.8 → должен показать "New version available: 1.0.9"
  # 3. Нажать обновить → скачает с GitHub → установит → запустится v1.0.9
  # 4. Убедиться что иконка алмаза на рабочем столе обновилась
  ```

### 2. NOWPayments — регистрация и модерация
- Зайти на nowpayments.io → Create account → Business type: **SaaS and Web Services**
- Указать сайт: `total-hunter.com`
- Email поддержки: `totalhunter.support@gmail.com`
- Сайт готов к проверке: есть `/contacts`, `/legal` (ToS, Privacy, Refund), Pricing на лендинге
- После одобрения → получить API Key + IPN Secret

### 3. NOWPayments — техническая интеграция (бэкенд)
После получения API Key:
```python
# Этап 2 из буфера Gemini:
# - POST /payments/create — создание invoice, сохранение в БД
# - POST /payments/webhook — обработка IPN с проверкой x-nowpayments-sig
# - Логика: status=finished → начислить алмазы пользователю
# - Статусы: waiting, confirming, expired
```

### 4. Реклама
- Пользователь хочет подать заявку на рекламу — уточнить платформу (Google/Facebook/VK/Telegram)

---

## Шпаргалка команд

```powershell
# Сборка новой версии:
# version.py → VERSION = "X.X.X"
Set-Location C:\BattleBot; $env:PYTHONIOENCODING="utf-8"; python build_release.py
Set-Location C:\BattleBot\dist\TotalHunter; Compress-Archive -Path * -DestinationPath ..\..\TotalHunter.zip -Force
& "C:\Program Files\GitHub CLI\gh.exe" release create vX.X.X "C:\BattleBot\TotalHunter.zip" --title "vX.X.X" --repo "Yevgeniy204566/totalhunter"
curl -X POST "https://api.total-hunter.com/admin/version/update?version=X.X.X" -H "Authorization: Bearer dev-admin-token"
```

```bash
# Деплой GCP:
cd /opt/totalhunter/server && sudo git pull origin main && sudo systemctl restart totalhunter

# Деплой сайта (Клод делает сам — 3 шага):
git push origin main
curl -X POST "https://api.vercel.com/v1/integrations/deploy/prj_mWtcb6hJCkl40YLWheeIlxD5NmXj/D0wsErcYcw"
# + poll READY + alias (TOKEN в settings.local.json)

# Экстренный сброс версии:
curl -X POST "https://api.total-hunter.com/admin/version/update?version=1.0.9" -H "Authorization: Bearer dev-admin-token"
```

---

## Текущие версии
- Бот: **v1.0.9** (GitHub Release + сервер)
- Сайт: задеплоен с Pricing + /contacts + NOWPayments в legal
- Сервер API: работает, `/version/latest` → `1.0.9`
