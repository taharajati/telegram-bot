#!/bin/bash
# ==========================================================
# Restore PostgreSQL backup for Foroshgram
# Usage:
#   ./restore.sh backups/daily/foroshgram_20260714_030000.sql.gz
#   ./restore.sh backups/monthly/foroshgram_20260701_030000.sql.gz
# ==========================================================
set -euo pipefail

BACKUP_FILE="${1:-}"
DB_CONTAINER="foroshgram_postgres"
DB_USER="foroshgram"
DB_NAME="foroshgram"

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: $0 <backup_file.sql.gz>"
  echo ""
  echo "Available local backups:"
  find /opt/foroshgram/backups -name "foroshgram_*.sql.gz" -type f | sort -r | head -10
  exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
  echo "ERROR: File not found: $BACKUP_FILE"
  exit 1
fi

# Verify the backup is a valid gzip
if ! gzip -t "$BACKUP_FILE" 2>/dev/null; then
  echo "ERROR: Backup file is corrupted (gzip check failed)"
  exit 1
fi

# Show backup info
echo "📦 Backup file: $(basename $BACKUP_FILE)"
echo "   Size: $(stat -c%s "$BACKUP_FILE") bytes"
echo "   Date: $(date -r "$BACKUP_FILE" '+%Y-%m-%d %H:%M:%S' 2>/dev/null || echo 'unknown')"
echo ""

# Confirmation
echo "⚠️  WARNING: This will DROP and RESTORE the '$DB_NAME' database!"
read -p "Type 'RESTORE' to confirm: " CONFIRM
if [ "$CONFIRM" != "RESTORE" ]; then
  echo "Aborted."
  exit 1
fi

echo ""
echo "[$(date +%H:%M:%S)] Stopping services..."
docker stop foroshgram_bot foroshgram_website 2>/dev/null || true

echo "[$(date +%H:%M:%S)] Dropping and recreating database..."
docker exec $DB_CONTAINER psql -U $DB_USER -d postgres -c "DROP DATABASE IF EXISTS $DB_NAME;"
docker exec $DB_CONTAINER psql -U $DB_USER -d postgres -c "CREATE DATABASE $DB_NAME OWNER $DB_USER;"

echo "[$(date +%H:%M:%S)] Restoring from $BACKUP_FILE..."
gunzip -c "$BACKUP_FILE" | docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME --single-transaction 2>&1 | tail -5

echo "[$(date +%H:%M:%S)] Applying init scripts..."
for f in /opt/foroshgram/init-scripts/*.sql; do
  docker exec -i $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -f /dev/stdin < "$f" 2>/dev/null || true
done

echo "[$(date +%H:%M:%S)] Restarting services..."
cd /opt/foroshgram && docker-compose up -d

echo ""
echo "✅ Restore complete!"
echo ""
echo "Verification commands:"
echo "  docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c 'SELECT count(*) FROM orders;'"
echo "  docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c 'SELECT count(*) FROM products;'"
echo "  docker exec $DB_CONTAINER psql -U $DB_USER -d $DB_NAME -c 'SELECT count(*) FROM users;'"
