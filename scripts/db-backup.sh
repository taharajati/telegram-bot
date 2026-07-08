#!/bin/bash
# ─── Foroshgram Database Backup Script ───────────────────────
# Usage: ./scripts/db-backup.sh                    # local execution
#        docker exec foroshgram_postgres bash -c "$(cat scripts/db-backup.sh)"  # Docker
#
# Set these environment variables (or edit defaults below):
#   BACKUP_DIR        — where to store backups (default: /opt/foroshgram/backups)
#   DB_HOST           — postgres host (default: localhost)
#   DB_PORT           — postgres port (default: 5432)
#   DB_NAME           — database name (default: foroshgram)
#   DB_USER           — postgres user (default: foroshgram)
#   PGPASSWORD        — postgres password (set this!)
#   RETENTION_DAYS    — keep backups for N days (default: 14)
#   S3_ENDPOINT       — optional: S3-compatible storage endpoint (Arvan, MinIO, etc.)
#   S3_BUCKET         — optional: S3 bucket name
#   S3_ACCESS_KEY     — optional: S3 access key
#   S3_SECRET_KEY     — optional: S3 secret key
# ─────────────────────────────────────────────────────────────

set -euo pipefail

# ── Config ────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-/opt/foroshgram/backups}"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"
DB_NAME="${DB_NAME:-foroshgram}"
DB_USER="${DB_USER:-foroshgram}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/${DB_NAME}_${TIMESTAMP}.sql.gz"
LATEST_LINK="${BACKUP_DIR}/latest.sql.gz"

# ── Pre-flight ────────────────────────────────────────────
mkdir -p "${BACKUP_DIR}"

if [ -z "${PGPASSWORD:-}" ]; then
  echo "❌  ERROR: PGPASSWORD environment variable is not set."
  echo "   Usage: PGPASSWORD=your_password $0"
  exit 1
fi

# ── Dump ──────────────────────────────────────────────────
echo "🔄  Starting backup of ${DB_NAME} on ${DB_HOST}:${DB_PORT}..."
echo "   → ${BACKUP_FILE}"

pg_dump \
  -h "${DB_HOST}" \
  -p "${DB_PORT}" \
  -U "${DB_USER}" \
  -d "${DB_NAME}" \
  --format=custom \
  --verbose \
  --no-owner \
  --no-privileges \
  2> /dev/null \
  | gzip > "${BACKUP_FILE}"

# Verify integrity
gunzip -t "${BACKUP_FILE}" || { echo "❌  Backup corrupted!"; rm -f "${BACKUP_FILE}"; exit 2; }

# Update latest symlink
ln -sf "${BACKUP_FILE}" "${LATEST_LINK}"

echo "✅  Backup complete: $(du -h "${BACKUP_FILE}" | cut -f1)"

# ── Retention: remove backups older than RETENTION_DAYS ───
find "${BACKUP_DIR}" -name "${DB_NAME}_*.sql.gz" -type f -mtime "+${RETENTION_DAYS}" -delete
echo "🧹  Retention: removed backups older than ${RETENTION_DAYS} days"

# ── Optional: upload to S3-compatible storage ─────────────
if [ -n "${S3_ENDPOINT:-}" ] && [ -n "${S3_BUCKET:-}" ] && [ -n "${S3_ACCESS_KEY:-}" ] && [ -n "${S3_SECRET_KEY:-}" ]; then
  echo "☁️   Uploading to ${S3_ENDPOINT}/${S3_BUCKET}..."
  
  # Use curl for S3 PUT (no extra dependency)
  RESOURCE="/${S3_BUCKET}/db-backups/$(basename "${BACKUP_FILE}")"
  CONTENT_TYPE="application/gzip"
  DATE=$(date -R)
  STRING_TO_SIGN="PUT\n\n${CONTENT_TYPE}\n${DATE}\n${RESOURCE}"
  SIGNATURE=$(echo -en "${STRING_TO_SIGN}" | openssl sha1 -hmac "${S3_SECRET_KEY}" -binary | base64)

  curl -sf -X PUT \
    -T "${BACKUP_FILE}" \
    -H "Host: ${S3_ENDPOINT}" \
    -H "Date: ${DATE}" \
    -H "Content-Type: ${CONTENT_TYPE}" \
    -H "Authorization: AWS ${S3_ACCESS_KEY}:${SIGNATURE}" \
    "https://${S3_ENDPOINT}${RESOURCE}" \
    && echo "☁️   Upload successful" \
    || echo "⚠️   Upload to S3 failed (non-fatal)"
fi

echo "🎉  All done."
