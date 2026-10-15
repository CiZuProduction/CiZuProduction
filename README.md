# AI Chatbot MVP — Website Only

Monorepo untuk MVP AI Chatbot berbasis website. Stack: **Next.js + FastAPI + PostgreSQL/PGVector + n8n + Docker Compose**.

## Status Fase

| Fase | Deskripsi | Status |
|------|-----------|--------|
| 0 | Struktur repo, `.env`, `.gitignore` | ✅ Selesai |
| 1 | Next.js, FastAPI health, DB schema, Compose | ✅ Selesai |
| 2 | Login, JWT, RBAC | 🔧 In Progress |
| 3 | Upload, OCR, Chunking | ⏳ Belum |
| 4 | Embedding, PGVector, RAG dasar | ⏳ Belum |
| 5 | Agentic RAG, n8n workflow | ⏳ Belum |
| 6–11 | UI, Security, CI/CD, VPS, Monitoring | ⏳ Belum |

## Prasyarat

```
Node.js 22 LTS    → https://nodejs.org
Python 3.12       → https://python.org
Docker Desktop    → https://docker.com/products/docker-desktop
Git               → https://git-scm.com
```

## Mulai Cepat (Local)

```powershell
# 1. Salin dan isi env
cp .env.example .env
# Edit .env: isi POSTGRES_PASSWORD, APP_SECRET_KEY, JWT_SECRET_KEY

# 2. Jalankan database
docker compose up -d postgres

# 3. Tunggu postgres healthy, lalu jalankan migrasi
docker compose exec api alembic upgrade head

# 4. Jalankan seluruh stack
docker compose up -d

# 5. Buka browser
# Frontend : http://localhost
# API docs : http://localhost:8000/docs  (development only)
# API health: http://localhost:8000/health
```

## Struktur

```
ai-chatbot-mvp/
├── apps/web/           # Next.js 15 (TypeScript, App Router)
├── services/api/       # FastAPI backend
├── ai/                 # RAG, Ingestion, Embeddings
├── n8n/workflows/      # Workflow JSON (terversi)
├── infra/              # Nginx, monitoring, backup, scripts
├── tests/              # Integration, E2E, evaluasi RAG
├── docs/               # ADR dan arsitektur
├── .github/workflows/  # CI/CD
├── compose.yaml
└── Makefile
```

## Perintah Berguna

```powershell
# Jalankan stack
docker compose up -d

# Lihat log
docker compose logs -f api

# Status container
docker compose ps

# Masuk ke shell API
docker compose exec api bash

# Jalankan migrasi
docker compose exec api alembic upgrade head

# Hentikan (tanpa hapus data)
docker compose down
```

## Environment Variables

Lihat `.env.example` untuk semua variabel yang dibutuhkan.  
**Jangan pernah commit file `.env` ke Git.**

## Dokumentasi Lengkap

Lihat `README AI Chatbot MVP.md` untuk arsitektur, keamanan, dan panduan deployment lengkap.
