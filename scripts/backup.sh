#!/bin/bash
# ==========================================================
# Automatic PostgreSQL backup for Foroshgram
# - Runs inside postgres container (pg_dump via docker exec)
# - Saves to local ./backups/{daily,weekly,monthly}
# - Syncs to remote S3-compatible storage via rclone
# - Rotates local backups: daily=7, weekly=4, monthly=12
# ==========================================================
set -euo pipefail

# ── Config ────────────────────────────────────────────────
BACKUP_DIR="/backups"                           # mount from docker-compose
DB_HOST="postgres"                               # service name in docker-compose
DB_USER="foroshgram"
DB_NAME="foroshgram"
PGPASSWORD="${POSTGRES_PASSWORD:-foroshgram_secure_2024}"
PG_DUMP="pg_dump -h $DB_HOST -U $DB_USER -d $DB_NAME"

# Timestamp
DATE=$(date +%Y%m%d_%H%M%S)
DOW=$(date +%u)          # 1=Mon .. 7=Sun
DOM=$(date +%d)
FNAME="foroshgram_${DATE}.sql.gz"

# ── Ensure dirs ──────────────────────────────────────────
mkdir -p "${BACKUP_DIR}"/{daily,weekly,monthly}

# ── Dump ─────────────────────────────────────────────────
echo "[$(date +%H:%M:%S)] Dumping $DB_NAME from $DB_CONTAINER..."
$PG_DUMP --no-owner --no-acl | gzip > "${BACKUP_DIR}/${FNAME}"

# Verify
FILE_SIZE=$(stat -c%s "${BACKUP_DIR}/${FNAME}" 2>/dev/null || stat -f%z "${BACKUP_DIR}/${FNAME}")
if [ "$FILE_SIZE" -lt 100 ]; then
  echo "ERROR: Backup file suspiciously small (${FILE_SIZE} bytes)"
  rm -f "${BACKUP_DIR}/${FNAME}"
  exit 1
fi
echo "OK: ${FNAME} (${FILE_SIZE} bytes)"

# ── Rotate into dated folders ────────────────────────────
cp "${BACKUP_DIR}/${FNAME}" "${BACKUP_DIR}/daily/${FNAME}"
if [ "$DOW" = "7" ]; then   # Sunday → weekly
  cp "${BACKUP_DIR}/${FNAME}" "${BACKUP_DIR}/weekly/${FNAME}"
fi
if [ "$DOM" = "01" ]; then  # 1st of month → monthly
  cp "${BACKUP_DIR}/${FNAME}" "${BACKUP_DIR}/monthly/${FNAME}"
fi

# ── Cleanup old local backups ────────────────────────────
find "${BACKUP_DIR}/daily"   -name "foroshgram_*.sql.gz" -mtime +7  -delete
find "${BACKUP_DIR}/weekly"  -name "foroshgram_*.sql.gz" -mtime +30 -delete
find "${BACKUP_DIR}/monthly" -name "foroshgram_*.sql.gz" -mtime +365 -delete
# Remove root copies older than 2 days
find "${BACKUP_DIR}" -maxdepth 1 -name "foroshgram_*.sql.gz" -mtime +2 -delete

# ── Remote sync (rclone) ─────────────────────────────────
if command -v rclone &>/dev/null && rclone config show &>/dev/null 2>&1; then
  echo "Syncing to remote..."
  rclone copy "${BACKUP_DIR}/daily/"   "foroshgram-backup:foroshgram/daily/"   --quiet
  rclone copy "${BACKUP_DIR}/weekly/"  "foroshgram-backup:foroshgram/weekly/"  --quiet
  rclone copy "${BACKUP_DIR}/monthly/" "foroshgram-backup:foroshgram/monthly/" --quiet
  echo "Remote sync OK"
else
  echo "WARNING: rclone not configured — backup is LOCAL ONLY"
fi

echo "[$(date +%H:%M:%S)] Backup complete."
