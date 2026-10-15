# ADR-001: Technology Stack MVP

**Status:** Accepted  
**Date:** 2026-10-13

## Konteks

Membangun MVP AI Chatbot berbasis website yang dapat berjalan di VPS Ubuntu dengan Docker Compose.

## Keputusan

| Komponen | Pilihan | Alasan |
|----------|---------|--------|
| Frontend | Next.js 15, TypeScript, App Router | SSR/SSG, ekosistem besar, standalone output untuk Docker |
| Backend | FastAPI (Python 3.12) | Async native, Pydantic validation, auto docs, cocok untuk AI pipeline |
| Database | PostgreSQL 17 + PGVector | RDBMS terpercaya + vector similarity search dalam satu service |
| Embedding | OpenAI text-embedding-3-small (1536d) | Kualitas tinggi, mudah diubah ke model lain via adapter |
| LLM | OpenAI gpt-4o-mini (default) | Biaya rendah, cukup untuk MVP, mudah diganti |
| OCR | PaddleOCR | Open source, dukungan Bahasa Indonesia, CPU-compatible |
| Workflow | n8n | Visual, self-hosted, integrasi luas |
| Container | Docker Compose | Cukup untuk MVP, tidak butuh Kubernetes |
| Reverse Proxy | Nginx | Stabil, konfigurasi luas, TLS termination |
| Auth | JWT (python-jose) + bcrypt (passlib) | Stateless, tidak butuh Redis untuk MVP awal |

## Konsekuensi

- LLM dan embedding tergantung koneksi internet ke OpenAI; perlu adapter untuk local LLM.
- PaddleOCR butuh CPU cukup; batasi concurrency worker.
- JWT tanpa revocation: logout hanya hapus token di client. Perlu token blocklist jika dibutuhkan.
- Alembic untuk migrasi: setiap perubahan schema harus melalui revision file.

## Alternatif yang Dipertimbangkan

- **Django**: terlalu berat untuk API-first, kurang cocok dengan async pipeline AI.
- **Supabase**: vendor lock-in, kurang kontrol untuk RAG pipeline.
- **Kubernetes**: overkill untuk MVP, direncanakan sebagai future scaling dengan OpenShift AI.
