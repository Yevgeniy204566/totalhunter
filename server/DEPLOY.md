# Деплой Total Hunter API на GCP (Compute Engine)

Сервер: `34.68.86.57` | ОС: Ubuntu 22.04 | Порт: `8000`

---

## Шаг 1 — Подключиться к серверу

```bash
ssh your_user@34.68.86.57
```

---

## Шаг 1.5 — Зафиксировать статический IP в GCP (ОБЯЗАТЕЛЬНО)

По умолчанию внешний IP инстанса **эфемерный** — сменится при ребуте.
Бот зашивает адрес сервера в `auth.py`. Если IP изменится — бот перестанет работать у всех пользователей одновременно.

**Как сделать IP постоянным:**
1. GCP Console → `VPC network` → `IP addresses`
2. Найди внешний IP своего инстанса → статус `Ephemeral`
3. Нажми `...` → `Promote to static address`
4. Дай имя (например: `totalhunter-api`)
5. `Reserve`

После этого IP `34.68.86.57` останется за сервером навсегда.

---

## Шаг 2 — Установить зависимости системы

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv python3-pip postgresql postgresql-contrib git
```

---

## Шаг 3 — Настроить PostgreSQL

```bash
sudo -u postgres psql
```

В консоли PostgreSQL:
```sql
CREATE USER hunter WITH PASSWORD 'ПРИДУМАЙ_СИЛЬНЫЙ_ПАРОЛЬ';
CREATE DATABASE totalhunter OWNER hunter;
\q
```

Проверка подключения:
```bash
psql -U hunter -d totalhunter -h localhost
# Должен войти без ошибок
```

---

## Шаг 4 — Загрузить код на сервер

```bash
sudo mkdir -p /opt/totalhunter

# Скопировать папку server/ с локальной машины на сервер:
# (выполнить на ЛОКАЛЬНОЙ машине, не на сервере)
scp -r C:/BattleBot/server your_user@34.68.86.57:/opt/totalhunter/

# Передать владение папки пользователю www-data (от имени которого работает сервис)
# БЕЗ этого systemd не сможет читать файлы и писать логи
sudo chown -R www-data:www-data /opt/totalhunter
```

---

## Шаг 5 — Создать виртуальное окружение и установить пакеты

```bash
cd /opt/totalhunter/server
python3.11 -m venv ../venv
source ../venv/bin/activate
pip install -r requirements.txt
```

---

## Шаг 6 — Применить миграции (создать таблицы)

```bash
cd /opt/totalhunter/server
export DATABASE_URL="postgresql+asyncpg://hunter:ТВОЙ_ПАРОЛЬ@localhost:5432/totalhunter"
alembic upgrade head
```

Ожидаемый вывод:
```
Running upgrade  -> dc8b275f4ed6, initial_schema
Running upgrade dc8b275f4ed6 -> eeaef22b78d1, add_ip_address
```

Проверка таблиц:
```bash
psql -U hunter -d totalhunter -c "\dt"
# Должно появиться: users, transactions, hunts, logs, broadcasts, app_settings
```

---

## Шаг 6.5 — Сгенерировать Admin Token

**Не придумывай вручную.** Используй команду прямо на сервере:
```bash
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
# Пример вывода: K7gNU3sdo-OL0wNhqoVWhr3g6s1xYv72ol_pe_Luo_I
```

Скопируй результат в `.service` файл. **Важно: без пробелов вокруг `=`:**
```
# ✅ Правильно:
Environment="ADMIN_SECRET_KEY=K7gNU3sdo-OL0wNhqoVWhr3g6s1xYv72ol_pe_Luo_I"

# ❌ Неправильно (сломает сервис):
Environment="ADMIN_SECRET_KEY = K7gNU3sdo..."
```

---

## Шаг 7 — Настроить systemd-сервис

```bash
# Отредактируй пароль БД в .service файле:
nano /opt/totalhunter/server/totalhunter.service
# Найди строку: Environment="DATABASE_URL=...CHANGE_ME..."
# Замени CHANGE_ME на реальный пароль

sudo cp /opt/totalhunter/server/totalhunter.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable totalhunter   # автозапуск при ребуте
sudo systemctl start totalhunter
```

Проверка — ПЕРВАЯ команда после запуска:
```bash
sudo journalctl -u totalhunter.service -f
# Ты увидишь момент «рождения»: SQLAlchemy создаёт пул соединений
# Ожидаемые строки:
#   Started Total Hunter API
#   Application startup complete

# Статус одной строкой:
sudo systemctl status totalhunter
# Должно быть: Active: active (running)
```

---

## Шаг 8 — Открыть порт в GCP Firewall

В консоли GCP (`console.cloud.google.com`):
1. `VPC network` → `Firewall` → `Create firewall rule`
2. Настройки:
   - Name: `allow-totalhunter-api`
   - Direction: `Ingress`
   - Targets: `All instances in the network`
   - Source IP: `0.0.0.0/0`
   - Protocols/ports: `TCP: 8000`
3. `Create`

---

## Шаг 8.5 — Чек-лист перед первым запросом

| # | Что проверить | Команда / Место |
|---|---|---|
| 1 | Порт 8000 открыт в GCP Firewall | GCP Console → VPC → Firewall |
| 2 | `alembic upgrade head` выполнен | 6 таблиц в БД |
| 3 | `ADMIN_SECRET_KEY` задан в `.service` | Не `change-me-before-deploy` |
| 4 | `CORS` настроен (уже в коде) | При переходе на домен: заменить `"*"` на реальный URL |
| 5 | systemd сервис `active (running)` | `systemctl status totalhunter` |

---

## Шаг 9 — Проверить работу API

```bash
# С локальной машины:
curl http://34.68.86.57:8000/docs
# Должен открыться Swagger UI (JSON-ответ)

curl -X POST http://34.68.86.57:8000/check_auth \
  -H "Content-Type: application/json" \
  -d '{"hwid": "TEST1234TEST1234"}'
# Ожидаемый ответ: {"authorized": true, "credits": 0, ...}
```

---

## Шаг 10 — Первый тест с ботом

В `auth.py` бота проверь что `SERVER_URL = "http://34.68.86.57:8000"`.
Запусти бота → в логах сервера должно появиться:
```
POST /check_auth  200
POST /heartbeat   200  (через 2 минуты)
```

---

## Управление сервисом

```bash
sudo systemctl stop totalhunter      # остановить
sudo systemctl restart totalhunter   # перезапустить (после обновления кода)
sudo journalctl -u totalhunter -n 50 # последние 50 строк логов
```

## Обновление кода (после изменений)

```bash
# Скопировать новые файлы на сервер (с локальной машины):
scp -r C:/BattleBot/server your_user@34.68.86.57:/opt/totalhunter/

# На сервере:
cd /opt/totalhunter/server
export DATABASE_URL="postgresql+asyncpg://hunter:ПАРОЛЬ@localhost:5432/totalhunter"
alembic upgrade head          # применить новые миграции (если есть)
sudo systemctl restart totalhunter
```
