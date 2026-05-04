#!/bin/bash
# restore_db.sh — Safe PostgreSQL restore for Total Hunter
#
# Использование:
#   bash restore_db.sh ~/backups/totalhunter_20260504_120000.sql.gz
#
# ⚠️  ВНИМАНИЕ: перезапишет текущую БД полностью!

DB_NAME="totalhunter_db"
DB_USER="totalhunter_user"
SERVICE="totalhunter"
BACKUP_DIR="$HOME/backups"

if [ -z "$1" ]; then
    echo "Использование: $0 <файл.sql.gz>"
    echo ""
    echo "Доступные бэкапы:"
    ls -lht "$BACKUP_DIR"/totalhunter_*.sql.gz 2>/dev/null | head -10
    exit 1
fi

FILE="$1"

if [ ! -f "$FILE" ]; then
    echo "❌ Файл не найден: $FILE"
    exit 1
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "⚠️  ВОССТАНОВЛЕНИЕ БД из: $FILE"
echo "⚠️  Текущая БД '$DB_NAME' будет ПЕРЕЗАПИСАНА"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
read -p "Продолжить? (yes/no): " CONFIRM

if [ "$CONFIRM" != "yes" ]; then
    echo "Отменено."
    exit 0
fi

# ── 1. Создать страховочный бэкап текущего состояния ─────────────────────────
echo "[$(date)] Создаю страховочный бэкап текущей БД..."
bash "$(dirname $0)/backup_db.sh"

# ── 2. Остановить сервис (обязательно — активные коннекты повредят данные) ───
echo "[$(date)] Останавливаю сервис $SERVICE..."
sudo systemctl stop "$SERVICE"

# ── 3. Восстановить ──────────────────────────────────────────────────────────
echo "[$(date)] Восстанавливаю из $FILE..."
gunzip -c "$FILE" | psql -U "$DB_USER" "$DB_NAME"

if [ $? -eq 0 ]; then
    echo "[$(date)] ✅ Восстановление завершено успешно"
else
    echo "[$(date)] ❌ Ошибка восстановления!" >&2
    echo "Запусти сервис вручную: sudo systemctl start $SERVICE"
    exit 1
fi

# ── 4. Запустить сервис ───────────────────────────────────────────────────────
sudo systemctl start "$SERVICE"
echo "[$(date)] ✅ Сервис $SERVICE запущен"
echo "[$(date)] Проверь: sudo journalctl -u $SERVICE -n 20"
