#!/bin/bash
# ─── Foroshgram Database Backup Cron (runs inside postgres container) ───────
# Add this to crontab: 0 3 * * * /scripts/db-backup-cron.sh
# Or run manually: docker exec foroshgram_postgres /scripts/db-backup-cron.sh

set -euo pipefail

BACKUP_DIR="/backups"
DB_NAME="foroshgram"
DB_USER="foroshgram"
RETENTION_DAYS=14
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"
LATEST_LINK="${BACKUP_DIR}/latest.sql.gz"

mkdir -p "${BACKUP_DIR}"

echo "[$(date)] Starting backup of ${DB_NAME}..."

pg_dump \
  -h localhost \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  --format=custom \
  --verbose \
  --no-owner \
  --no-privileges \
  2>/dev/null \
  | gzip > "${BACKUP_FILE}"

gunzip -t "${BACKUP_FILE}" || { echo "[$(date)] ❌ Backup corrupted!"; rm -f "${BACKUP_FILE}"; exit 2; }

ln -sf "${BACKUP_FILE}" "${LATEST_LINK}"
echo "[$(date)] ✅ Backup complete: $(du -h "${BACKUP_FILE}" | cut -f1)"

# Retention
find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql.gz" -type f -mtime "+${RETENTION_DAYS}" -delete
echo "[$(date)] 🧹 Retention: removed backups older than ${RETENTION_DAYS} days"

# Optional: Upload to S3 (uncomment and configure)
# if [ -n "${S3_ENDPOINT:-}" ] && [ -n "${S3_BUCKET:-}" ] && [ -n "${S3_ACCESS_KEY:-}" ] && [ -n "${S3_SECRET_KEY:-}" ]; then
#   echo "[$(date)] Uploading to S3..."
#   RESOURCE="/${S3_BUCKET}/db-backups/$(basename "${BACKUP_FILE}")"
#   CONTENT_TYPE="application/gzip"
#   DATE=$(date -R)
#   STRING_TO_SIGN="PUT\n\n${CONTENT_TYPE}\n${DATE}\n${RESOURCE}"
#   SIGNATURE=$(echo -en "${STRING_TO_SIGN}" | openssl sha1 -hmac "${S3_SECRET_KEY}" -binary | base64)
#   curl -sf -X PUT \
#     -T "${BACKUP_FILE}" \
#     -H "Host: ${S3_ENDPOINT}" \
#     -H "Date: ${DATE}" \
#     -H "Content-Type: ${CONTENT_TYPE}" \
#     -H "Authorization: AWS ${S3_ACCESS_KEY}:${SIGNATURE}" \
#     "https://${S3_ENDPOINT}${RESOURCE}" \
#     && echo "[$(date)] Upload successful" \
#     || echo "[$(date)] Upload failed (non-fatal)"
# fi