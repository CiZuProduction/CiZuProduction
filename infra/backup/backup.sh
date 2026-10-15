#!/usr/bin/env bash
# ============================================================
# Backup Script — AI Chatbot MVP
# Jalankan: bash infra/backup/backup.sh
# Atau via cron: 0 2 * * * /opt/ai-chatbot/infra/backup/backup.sh
# ============================================================
set -euo pipefail

# ── Konfigurasi ────────────────────────────────────────────────────────────
BACKUP_DIR="${BACKUP_DIR:-/opt/backups/ai-chatbot}"
RETAIN_DAYS="${RETAIN_DAYS:-7}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
LOG_FILE="${BACKUP_DIR}/backup_${TIMESTAMP}.log"

# Load env jika ada
ENV_FILE="${ENV_FILE:-/opt/ai-chatbot/.env}"
if [ -f "$ENV_FILE" ]; then
  # Ekspor hanya variabel database (tidak semua)
  export $(grep -E "^(POSTGRES_DB|POSTGRES_USER|POSTGRES_PASSWORD)" "$ENV_FILE" | xargs)
fi

POSTGRES_DB="${POSTGRES_DB:-ai_chatbot}"
POSTGRES_USER="${POSTGRES_USER:-ai_chatbot_app}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"
POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-ai-chatbot-mvp-postgres-1}"
UPLOADS_VOLUME="${UPLOADS_VOLUME:-ai-chatbot-mvp_uploads_data}"

# ── Setup ──────────────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=============================="
echo "Backup dimulai: $TIMESTAMP"
echo "=============================="

# ── 1. Backup PostgreSQL ───────────────────────────────────────────────────
DB_BACKUP="${BACKUP_DIR}/db_${TIMESTAMP}.sql.gz"
echo "[1/3] Backup database ke: $DB_BACKUP"

PGPASSWORD="$POSTGRES_PASSWORD" docker exec -e PGPASSWORD="$POSTGRES_PASSWORD" \
  "$POSTGRES_CONTAINER" \
  pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-password \
  | gzip > "$DB_BACKUP"

DB_SIZE=$(du -sh "$DB_BACKUP" | cut -f1)
echo "      Database backup selesai: $DB_SIZE"

# ── 2. Backup file uploads ─────────────────────────────────────────────────
UPLOADS_BACKUP="${BACKUP_DIR}/uploads_${TIMESTAMP}.tar.gz"
echo "[2/3] Backup uploads ke: $UPLOADS_BACKUP"

docker run --rm \
  -v "${UPLOADS_VOLUME}:/data:ro" \
  -v "${BACKUP_DIR}:/backup" \
  alpine:3.20 \
  tar czf "/backup/uploads_${TIMESTAMP}.tar.gz" -C /data .

UPLOADS_SIZE=$(du -sh "$UPLOADS_BACKUP" | cut -f1)
echo "      Uploads backup selesai: $UPLOADS_SIZE"

# ── 3. Backup n8n workflows ────────────────────────────────────────────────
N8N_BACKUP="${BACKUP_DIR}/n8n_workflows_${TIMESTAMP}.tar.gz"
echo "[3/3] Backup n8n workflows ke: $N8N_BACKUP"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [ -d "${PROJECT_ROOT}/n8n/workflows" ]; then
  tar czf "$N8N_BACKUP" -C "${PROJECT_ROOT}" n8n/workflows/
  echo "      n8n workflows backup selesai"
else
  echo "      n8n/workflows tidak ditemukan, skip"
fi

# ── 4. Hapus backup lama ───────────────────────────────────────────────────
echo ""
echo "Menghapus backup lebih dari ${RETAIN_DAYS} hari..."
find "$BACKUP_DIR" -name "db_*.sql.gz" -mtime "+${RETAIN_DAYS}" -delete
find "$BACKUP_DIR" -name "uploads_*.tar.gz" -mtime "+${RETAIN_DAYS}" -delete
find "$BACKUP_DIR" -name "n8n_*.tar.gz" -mtime "+${RETAIN_DAYS}" -delete
find "$BACKUP_DIR" -name "backup_*.log" -mtime "+${RETAIN_DAYS}" -delete

# ── 5. Verifikasi ──────────────────────────────────────────────────────────
echo ""
echo "=============================="
echo "Backup selesai: $(date +"%Y-%m-%d %H:%M:%S")"
echo "File backup:"
ls -lh "${BACKUP_DIR}/"*"${TIMESTAMP}"* 2>/dev/null || echo "(tidak ada)"
echo "=============================="
