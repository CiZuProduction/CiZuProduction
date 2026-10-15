#!/usr/bin/env bash
# ============================================================
# Restore Script — AI Chatbot MVP
# Penggunaan: bash infra/backup/restore.sh <timestamp>
# Contoh:     bash infra/backup/restore.sh 20261013_020000
# ============================================================
set -euo pipefail

TIMESTAMP="${1:-}"
if [ -z "$TIMESTAMP" ]; then
  echo "Usage: $0 <timestamp>"
  echo "Contoh: $0 20261013_020000"
  echo ""
  echo "Backup tersedia:"
  ls /opt/backups/ai-chatbot/db_*.sql.gz 2>/dev/null | sed 's/.*db_//' | sed 's/.sql.gz//' || echo "(tidak ada)"
  exit 1
fi

BACKUP_DIR="${BACKUP_DIR:-/opt/backups/ai-chatbot}"
ENV_FILE="${ENV_FILE:-/opt/ai-chatbot/.env}"

if [ -f "$ENV_FILE" ]; then
  export $(grep -E "^(POSTGRES_DB|POSTGRES_USER|POSTGRES_PASSWORD)" "$ENV_FILE" | xargs)
fi

POSTGRES_DB="${POSTGRES_DB:-ai_chatbot}"
POSTGRES_USER="${POSTGRES_USER:-ai_chatbot_app}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-ai-chatbot-mvp-postgres-1}"

DB_BACKUP="${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz"

echo "=============================="
echo "RESTORE dari timestamp: $TIMESTAMP"
echo "=============================="
echo "⚠️  PERINGATAN: Ini akan menimpa data yang ada!"
echo "Tekan Ctrl+C untuk batalkan, atau Enter untuk lanjut..."
read -r

# ── Restore database ──────────────────────────────────────────────────────
if [ ! -f "$DB_BACKUP" ]; then
  echo "ERROR: File backup tidak ditemukan: $DB_BACKUP"
  exit 1
fi

echo "[1/2] Restore database dari: $DB_BACKUP"
gunzip -c "$DB_BACKUP" | PGPASSWORD="$POSTGRES_PASSWORD" docker exec -i \
  -e PGPASSWORD="$POSTGRES_PASSWORD" \
  "$POSTGRES_CONTAINER" \
  psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"

echo "      Database restore selesai"

# ── Restore uploads ───────────────────────────────────────────────────────
UPLOADS_BACKUP="${BACKUP_DIR}/uploads_${TIMESTAMP}.tar.gz"
if [ -f "$UPLOADS_BACKUP" ]; then
  echo "[2/2] Restore uploads dari: $UPLOADS_BACKUP"
  docker run --rm \
    -v "ai-chatbot-mvp_uploads_data:/data" \
    -v "${BACKUP_DIR}:/backup:ro" \
    alpine:3.20 \
    sh -c "rm -rf /data/* && tar xzf /backup/uploads_${TIMESTAMP}.tar.gz -C /data"
  echo "      Uploads restore selesai"
else
  echo "[2/2] File uploads backup tidak ditemukan, skip"
fi

echo ""
echo "=============================="
echo "Restore selesai: $(date +"%Y-%m-%d %H:%M:%S")"
echo "Verifikasi aplikasi berjalan dengan benar!"
echo "=============================="
