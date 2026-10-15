# ============================================================
# Makefile — Shortcut commands untuk development lokal
# Gunakan: make <target>
# ============================================================

.PHONY: help setup up down restart logs db-up api-up web-up migrate shell-api lint-api test-api install-web build-web clean

help: ## Tampilkan daftar commands
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

# ── Environment ──────────────────────────────────────────────────────────

setup: ## Setup awal: salin .env.example ke .env
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env dibuat. Isi nilainya sebelum lanjut."; else echo ".env sudah ada."; fi

# ── Docker Compose ────────────────────────────────────────────────────────

db-up: ## Jalankan hanya PostgreSQL
	docker compose up -d postgres

up: ## Jalankan seluruh stack (postgres + api + web + nginx)
	docker compose up -d

up-full: ## Jalankan stack lengkap + n8n
	docker compose --profile automation up -d

down: ## Hentikan dan hapus container (tanpa hapus volume)
	docker compose down

restart: ## Restart semua service
	docker compose restart

logs: ## Lihat log semua service
	docker compose logs -f

logs-api: ## Lihat log API
	docker compose logs -f api

logs-web: ## Lihat log frontend
	docker compose logs -f web

ps: ## Status container
	docker compose ps

# ── Database & Migration ──────────────────────────────────────────────────

migrate: ## Jalankan migrasi Alembic (dari container api)
	docker compose exec api alembic upgrade head

migrate-create: ## Buat migrasi baru: make migrate-create MSG="nama_migrasi"
	docker compose exec api alembic revision --autogenerate -m "$(MSG)"

migrate-history: ## Lihat history migrasi
	docker compose exec api alembic history

# ── Backend (lokal tanpa Docker) ──────────────────────────────────────────

venv: ## Buat virtual environment Python
	cd services/api && python -m venv .venv

install-api: ## Install dependency backend
	cd services/api && .venv/Scripts/pip install -r requirements.txt  # Windows
	# Linux/Mac: cd services/api && .venv/bin/pip install -r requirements.txt

lint-api: ## Jalankan linter backend
	cd services/api && ruff check .

test-api: ## Jalankan unit test backend
	cd services/api && pytest tests/ -v

shell-api: ## Masuk ke shell container API
	docker compose exec api bash

# ── Frontend (lokal tanpa Docker) ─────────────────────────────────────────

install-web: ## Install dependency frontend
	cd apps/web && npm ci

build-web: ## Build frontend
	cd apps/web && npm run build

lint-web: ## Lint frontend
	cd apps/web && npm run lint

# ── Cleanup ───────────────────────────────────────────────────────────────

clean: ## Hapus artefak build (TANPA hapus Docker volume)
	cd apps/web && rm -rf .next node_modules
	cd services/api && rm -rf __pycache__ .pytest_cache .ruff_cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null; true
