# INFRA_HEALTH.md — Профилактика инфраструктуры Total Hunter

> Читать при каждом хангофе и раз в неделю самостоятельно.
> Цель: не допустить падения из-за заполненного диска, истёкшего токена или переполненной БД.

---

## 📌 БЫСТРЫЙ ЧЕКЛИСТ (раз в неделю, 5 минут)

```
[ ] GCP: df -h — диск > 80%? Чистить логи
[ ] GCP: free -h — RAM > 90%? Смотреть процессы
[ ] GCP: systemctl status totalhunter — active?
[ ] GitHub: репо ПУБЛИЧНЫЙ? Токены в коде не утекли?
[ ] Vercel: токен не истёк? (срок указан в settings.local.json)
[ ] БД: SELECT COUNT(*) FROM transactions — растёт нормально?
```

---

## 1. GCP — Сервер (34.68.86.57, e2-micro, Ubuntu 22.04)

### Доступ
```bash
# Из Cloud Shell (console.cloud.google.com):
gcloud compute ssh total-hunter-backend --zone=us-central1-f --project=digital-arcade-274010

# Или напрямую если уже на VM:
# Просто работать в терминале — ты уже там
```

### Диск (критично — e2-micro имеет ~30GB)

```bash
# Посмотреть общее состояние
df -h

# Что занимает место
du -sh /opt/totalhunter/*
du -sh /var/log/
du -sh /tmp/

# Очистка журналов systemd (самое частое засорение)
sudo journalctl --vacuum-size=50M      # оставить только 50MB
sudo journalctl --vacuum-time=7d       # или только за последние 7 дней

# Очистка Python кэша
find /opt/totalhunter -name "__pycache__" -exec rm -rf {} + 2>/dev/null
find /opt/totalhunter -name "*.pyc" -delete 2>/dev/null

# Очистка apt кэша
sudo apt-get clean
sudo apt-get autoremove -y
```

**Пороги:**
- 🟢 < 60% — всё хорошо
- 🟡 60–80% — запланировать чистку
- 🔴 > 80% — чистить немедленно (journalctl vacuum)
- 🚨 > 90% — сервер может упасть!

### RAM (e2-micro = 1GB, критично)

```bash
free -h
ps aux --sort=-%mem | head -10   # топ процессов по памяти
```

**Пороги:**
- 🟢 < 700MB used — норма
- 🟡 700–850MB — следить
- 🔴 > 850MB — рестартовать если есть утечки: `sudo systemctl restart totalhunter`

**Апгрейд VM:** если RAM > 90% постоянно → переходить на e2-small (2GB, ~$13/мес)

### Сервис

```bash
sudo systemctl status totalhunter        # статус
sudo journalctl -u totalhunter -n 50     # последние 50 строк логов
sudo journalctl -u totalhunter -f        # live-лог (Ctrl+C для выхода)
```

### База данных PostgreSQL

```bash
# Зайти в psql
sudo -u postgres psql -d totalhunter

# Размер БД
SELECT pg_size_pretty(pg_database_size('totalhunter'));

# Таблицы по размеру
SELECT relname, pg_size_pretty(pg_total_relation_size(relid))
FROM pg_catalog.pg_statio_user_tables
ORDER BY pg_total_relation_size(relid) DESC;

# Счётчики транзакций (рост = норма)
SELECT COUNT(*) FROM transactions;
SELECT type, COUNT(*) FROM transactions GROUP BY type;

# Выйти
\q
```

**Когда чистить:**
- `transactions` — никогда не чистить (финансовая история)
- `crash_reports` — можно чистить старше 90 дней:
  ```sql
  DELETE FROM crash_reports WHERE created_at < NOW() - INTERVAL '90 days';
  ```

**Бэкап БД** (запускать перед любой миграцией):
```bash
sudo -u postgres pg_dump totalhunter > /tmp/backup_$(date +%Y%m%d).sql
ls -lh /tmp/backup_*.sql
```

### Автоматическая очистка (cron — уже настроен)
```bash
crontab -l   # проверить что cron работает
# Должно быть: journalctl vacuum + pycache cleanup раз в неделю
```

---

## 2. Vercel — Фронтенд

### Доступ
- Сайт: vercel.com → войти через GitHub
- API: через Bearer Token

### Токен

**Где хранится:** `C:\BattleBot\.claude\settings.local.json` → `env.VERCEL_TOKEN`
**Название токена:** указано в STATE.md (текущий: "16.05.2026")
**Срок:** токены Vercel не истекают автоматически, но могут быть отозваны

**Проверить что токен живой:**
```bash
TOKEN=$(node -e "const s=require('C:/BattleBot/.claude/settings.local.json');console.log(s.env.VERCEL_TOKEN)")
curl -s "https://api.vercel.com/v2/user" -H "Authorization: Bearer $TOKEN" | python -c "import sys,json; d=json.load(sys.stdin); print('OK:', d.get('user',{}).get('email','ERR'))"
```

**Если токен истёк:**
1. vercel.com → Account Settings → Tokens
2. Delete старый → Create new
3. Обновить в `C:\BattleBot\.claude\settings.local.json` → `env.VERCEL_TOKEN`

### Лимиты Vercel (Hobby план)

| Ресурс | Лимит | Как проверить |
|---|---|---|
| Bandwidth | 100GB/мес | vercel.com → Usage |
| Builds | 6000 мин/мес | vercel.com → Usage |
| Deployments | 100/день | vercel.com → Deployments |
| Function invocations | 100K/мес | vercel.com → Usage |

**Проверять раз в месяц** — если Bandwidth > 80GB, рассмотреть Pro ($20/мес).

### Старые деплои (cleanup)
Vercel хранит все деплои. Периодически можно чистить через UI:
vercel.com → Project → Deployments → фильтр по старым → Delete

---

## 3. GitHub — Репозиторий

### Доступ
- github.com/Yevgeniy204566/totalhunter
- **ПУБЛИЧНЫЙ** — всё видно всем!

### Безопасность (критично!)

**Что НИКОГДА не должно попасть в репо:**
- Токены Vercel / GCP / NOWPayments
- `.env` файлы с секретами
- `settings.local.json` (уже в .gitignore — проверить!)
- Пароли, ключи API

**Проверить .gitignore:**
```bash
cat "C:/BattleBot/.gitignore" | grep -E "local|secret|env|token"
```

**Проверить что секреты не утекли (периодически):**
```bash
git log --all --full-history -- "*.local.json" "*.env" ".env*"
# Если что-то нашлось — немедленно инвалидировать все утёкшие токены!
```

### Размер репозитория

```bash
# Локально
git count-objects -vH

# Если репо > 500MB — время чистить большие файлы
git lfs ls-files   # если используется LFS
```

**Самые большие файлы в истории:**
```bash
git rev-list --objects --all | git cat-file --batch-check='%(objecttype) %(objectname) %(objectsize) %(rest)' | sort -t' ' -k3 -rn | head -20
```

### Releases (GitHub)

**Правило:** только `TotalHunter.zip` через Edit release в браузере (gh release upload зависает на 300MB+)

**Чистить старые релизы:** хранить последние 3–5 версий. Старые можно удалять через UI если нет активных пользователей на них.

**Проверить что ZIP доступен:**
```bash
curl -I "https://github.com/Yevgeniy204566/totalhunter/releases/latest/download/TotalHunter.zip"
# Должно быть 302 Found (редирект на файл)
```

---

## 4. Версии — Протокол при хангофе

### Обязательно проверять при каждом хангофе:

```bash
# 1. Текущая версия в коде
cat C:/BattleBot/version.py

# 2. Версия в последнем релизе GitHub
"C:/Program Files/GitHub CLI/gh.exe" release list --repo Yevgeniy204566/totalhunter --limit 3

# 3. Версия на сервере
curl -s "https://api.total-hunter.com/version"
```

### Когда выкатывать новую версию?

**Выкатывать (собирать v1.X.Y+1) если:**
- Накопилось 3+ значимых изменения в `main.py` / логике бота
- Исправлен критический баг который воспроизводится у пользователей
- Добавлена новая фича в бот (новый модуль, новая вкладка)

**НЕ выкатывать если:**
- Изменения только на сайте (Vercel деплоится автоматически)
- Изменения только на сервере (GCP деплоится через git pull)
- Мелкие правки GUI которые не ломают и не добавляют функциональность

### Схема версий: `1.MAJOR.MINOR`
- **MAJOR** — новый большой модуль (РОЙ, Combo, новый движок)
- **MINOR** — улучшения, баги, мелкие фичи
- Текущая: **1.3.0** | Следующая при необходимости: **1.3.1**

---

## 5. Мониторинг доступности

**Быстрая проверка что всё живое:**

```bash
# Сервер API
curl -s "https://api.total-hunter.com/health" | python -c "import sys; print(sys.stdin.read())"

# Сайт
curl -s -o /dev/null -w "%{http_code}" "https://total-hunter.com"
# Должно быть 200

# Версия на сервере
curl -s "https://api.total-hunter.com/version"

# Zip скачивается
curl -I "https://github.com/Yevgeniy204566/totalhunter/releases/latest/download/TotalHunter.zip" 2>&1 | grep "HTTP\|Location"
```

---

## 6. График профилактики

| Частота | Что делать |
|---|---|
| **При каждом хангофе** | Проверить version.py, оценить нужен ли релиз, обновить STATE.md |
| **Раз в неделю** | `df -h` и `free -h` на GCP, `systemctl status totalhunter` |
| **Раз в месяц** | Vercel Usage (bandwidth/builds), размер БД, проверить токены |
| **Раз в квартал** | Чистить crash_reports > 90 дней, старые GitHub Releases, git history size |
| **При любом сбое** | Сначала `journalctl -u totalhunter -n 100` — смотреть ошибки |
