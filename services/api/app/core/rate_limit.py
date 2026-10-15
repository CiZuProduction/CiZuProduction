"""
Rate limiting menggunakan slowapi.
Konfigurasi per-endpoint berbeda berdasarkan sensitivitas.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Gunakan IP address sebagai identifier
# Di production dengan reverse proxy, pastikan X-Forwarded-For terkonfigurasi
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200/minute"],  # default global
)

# ── Limit per endpoint ─────────────────────────────────────────────────────
# Login: ketat untuk mencegah brute force
LIMIT_LOGIN = "10/minute"

# Chat: lebih longgar tapi tetap terbatas (LLM mahal)
LIMIT_CHAT = "30/minute"

# Upload: batasi frekuensi upload
LIMIT_UPLOAD = "20/minute"

# API umum: cukup longgar untuk browsing
LIMIT_API = "100/minute"
