#!/bin/bash
# ==========================================================
# Setup rclone for S3-compatible remote backup
# Run ONCE on VPS to configure remote storage
# ==========================================================
set -euo pipefail

echo "🔧 Foroshgram rclone setup for S3-compatible backup"
echo ""

# Check if already configured
if rclone config show foroshgram-backup &>/dev/null; then
  echo "✅ 'foroshgram-backup' remote already configured"
  rclone lsd foroshgram-backup:
  exit 0
fi

echo "Choose your S3-compatible provider:"
echo "  1) AWS S3"
echo "  2) MinIO (self-hosted)"
echo "  3) DigitalOcean Spaces"
echo "  4) Backblaze B2"
echo "  5) Wasabi"
echo "  6) Generic S3-compatible"
read -p "Enter choice [1-6]: " CHOICE

case $CHOICE in
  1) PROVIDER="AWS" ;;
  2) PROVIDER="MinIO" ;;
  3) PROVIDER="DigitalOcean" ;;
  4) PROVIDER="BackblazeB2" ;;
  5) PROVIDER="Wasabi" ;;
  6) PROVIDER="S3" ;;
  *) echo "Invalid"; exit 1 ;;
esac

read -p "Access Key ID: " ACCESS_KEY
read -s -p "Secret Access Key: " SECRET_KEY; echo
read -p "Region (e.g., us-east-1, auto for MinIO): " REGION
read -p "Bucket name (will create if not exists): " BUCKET
read -p "Endpoint (leave empty for AWS): " ENDPOINT

# Configure rclone
if [ -n "$ENDPOINT" ]; then
  rclone config create foroshgram-backup s3 \
    provider="$PROVIDER" \
    access_key_id="$ACCESS_KEY" \
    secret_access_key="$SECRET_KEY" \
    region="$REGION" \
    endpoint="$ENDPOINT" \
    acl="private"
else
  rclone config create foroshgram-backup s3 \
    provider="$PROVIDER" \
    access_key_id="$ACCESS_KEY" \
    secret_access_key="$SECRET_KEY" \
    region="$REGION" \
    acl="private"
fi

# Test connection
echo ""
echo "Testing connection..."
rclone mkdir foroshgram-backup:foroshgram/daily
rclone mkdir foroshgram-backup:foroshgram/weekly
rclone mkdir foroshgram-backup:foroshgram/monthly

echo "✅ Remote 'foroshgram-backup' configured and bucket structure created"
echo "Bucket: $BUCKET"
rclone lsd foroshgram-backup: