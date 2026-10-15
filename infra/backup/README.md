# Backup & Restore — AI Chatbot MVP

## Apa yang di-backup

| Item | File | Keterangan |
|------|------|------------|
| Database | `db_<timestamp>.sql.gz` | Full dump PostgreSQL (compressed) |
| File uploads | `uploads_<timestamp>.tar.gz` | Volume file terenkripsi |
| n8n workflows | `n8n_workflows_<timestamp>.tar.gz` | Export workflow JSON |

## Menjalankan backup manual

```bash
bash infra/backup/backup.sh
```

## Konfigurasi via environment

```bash
BACKUP_DIR=/opt/backups/ai-chatbot   # direktori penyimpanan backup
RETAIN_DAYS=7                         # berapa hari backup disimpan
ENV_FILE=/opt/ai-chatbot/.env         # lokasi file .env
```

## Cron (VPS production)

```cron
# Backup setiap hari jam 02:00
0 2 * * * BACKUP_DIR=/opt/backups/ai-chatbot bash /opt/ai-chatbot/infra/backup/backup.sh
```

## Restore

```bash
# Lihat backup tersedia
ls /opt/backups/ai-chatbot/

# Restore dari timestamp tertentu
bash infra/backup/restore.sh 20261013_020000
```

## ⚠️ Catatan penting

- **ENCRYPTION_KEY wajib dijaga** — tanpa key yang sama, file uploads tidak bisa didekripsi
- Backup harus disimpan di lokasi **berbeda dari server** (off-site)
- **Uji restore secara berkala** di environment terisolasi
- Jangan hapus backup terakhir meski sudah melewati RETAIN_DAYS
