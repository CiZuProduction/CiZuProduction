# ============================================================
# Backend FastAPI — Dockerfile
# Multi-stage build, non-root user, pinned base image
# ============================================================

# ── Stage 1: base ─────────────────────────────────────────────────────────
FROM python:3.12-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_ROOT_USER_ACTION=ignore

WORKDIR /app

# ── Stage 2: dependency builder ───────────────────────────────────────────
FROM base AS builder

# System deps minimal — hanya yang dibutuhkan untuk compile
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# ── Stage 3: runtime ──────────────────────────────────────────────────────
FROM base AS runtime

# Runtime system deps (tanpa build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Salin packages yang sudah di-install dari builder
COPY --from=builder /root/.local /root/.local

# Tambahkan .local/bin ke PATH
ENV PATH=/root/.local/bin:$PATH

# Buat user non-root sebelum salin kode
RUN useradd --create-home --no-log-init --shell /bin/bash appuser

WORKDIR /app

# Salin kode aplikasi
COPY --chown=appuser:appuser . .

# Buat direktori yang diperlukan dengan permission benar
RUN mkdir -p /app/data/uploads \
    && chown -R appuser:appuser /app/data

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=20s --timeout=5s --start-period=40s --retries=5 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=3)" || exit 1

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
