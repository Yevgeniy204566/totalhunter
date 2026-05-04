#!/bin/bash
# backup_db.sh — PostgreSQL backup for Total Hunter
# Cron: 0 */6 * * * /home/ubuntu/total-hunter-backend/scripts/backup_db.sh >> ~/backups/backup.log 2>&1
#
# ⚠️  ЧТО НЕ ВХОДИТ В БЭКАП (хранить отдельно!):
#     - .env (ключи Free-Kassa, Google OAuth, JWT secret)
#     - profiles/ (калибровки на локальных машинах пользователей)
#     - targets/ (YOLO-модели)

BACKUP_DIR="$HOME/backups"
DB_NAME="totalhunter_db"
DB_USER="totalhunter_user"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILE="$BACKUP_DIR/totalhunter_$TIMESTAMP.sql.gz"

# GCS bucket — установить один раз: gsutil mb gs://totalhunter-backups
GCS_BUCKET="gs://totalhunter-backups"

mkdir -p "$BACKUP_DIR"

# ── 1. Локальный бэкап ────────────────────────────────────────────────────────
pg_dump -U "$DB_USER" "$DB_NAME" | gzip > "$FILE"

if [ $? -ne 0 ]; then
    echo "[$(date)] ❌ Backup FAILED (pg_dump error)" >&2
    exit 1
fi

SIZE=$(du -sh "$FILE" | cut -f1)
echo "[$(date)] ✅ Local backup OK: $FILE ($SIZE)"

# ── 2. Загрузка в Google Cloud Storage (защита от гибели инстанса) ────────────
if command -v gsutil &> /dev/null; then
    gsutil cp "$FILE" "$GCS_BUCKET/" 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "[$(date)] ✅ GCS upload OK: $GCS_BUCKET/$(basename $FILE)"
    else
        echo "[$(date)] ⚠️  GCS upload FAILED (bucket not configured?)" >&2
    fi
else
    echo "[$(date)] ⚠️  gsutil not found — skipping GCS upload"
fi

# ── 3. Ротация: удаляем локальные бэкапы старше 7 дней ───────────────────────
find "$BACKUP_DIR" -name "totalhunter_*.sql.gz" -mtime +7 -delete
echo "[$(date)] 🗑  Old backups cleaned (>7 days)"
