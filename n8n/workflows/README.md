# n8n Workflows — AI Chatbot MVP

Workflow disimpan sebagai JSON dan diimpor ke n8n.

## Cara Import

1. Buka n8n di http://localhost:5678
2. Klik **+** → **Import from file**
3. Pilih file JSON di folder ini
4. Konfigurasi credentials yang diperlukan
5. Aktifkan workflow

## Daftar Workflow

### 01_document_processing.json
Trigger otomatis saat dokumen baru diupload.
- Trigger: Webhook dari API
- Action: Panggil endpoint `/api/v1/ingestion/trigger/{id}`
- Notifikasi: Log status completion

### 02_ai_assistant.json
Workflow AI assistant via webhook eksternal.
- Trigger: POST webhook terautentikasi
- Action: Panggil endpoint `/api/v1/chat`
- Response: Kembalikan jawaban ke pemanggil

### 03_operational_alert.json
Alert operasional untuk monitoring.
- Trigger: Schedule (setiap jam)
- Action: Cek health endpoint
- Alert: Kirim notifikasi jika tidak available

## Keamanan

- Semua webhook menggunakan header authentication
- Credentials disimpan di n8n credential store
- Export JSON tidak mengandung secret
- Akses editor n8n dibatasi via network internal
