"""
Security utilities: password hashing, JWT encode/decode.

Menggunakan:
- bcrypt langsung (bukan passlib) — kompatibel dengan bcrypt >= 4.x
- PyJWT (bukan python-jose) — python-jose punya CVE aktif (PYSEC-2024-232/233)
"""
import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt
from jwt.exceptions import InvalidTokenError

from app.core.config import settings

logger = logging.getLogger(__name__)


# ── Password ────────────────────────────────────────────────────────────────

def hash_password(plain_password: str) -> str:
    """Return bcrypt hash dari password."""
    password_bytes = plain_password.encode("utf-8")
    hashed = bcrypt.hashpw(password_bytes, bcrypt.gensalt(rounds=12))
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifikasi password terhadap hash yang tersimpan."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        return False


# ── JWT ─────────────────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    extra_claims: dict[str, Any] | None = None,
    expires_delta: timedelta | None = None,
) -> str:
    """Buat JWT access token menggunakan PyJWT."""
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    payload: dict[str, Any] = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    if extra_claims:
        payload.update(extra_claims)

    return jwt.encode(
        payload,
        settings.jwt_secret_key.get_secret_value(),
        algorithm=settings.jwt_algorithm,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """
    Decode dan validasi JWT access token menggunakan PyJWT.
    Raise ValueError jika token tidak valid atau expired.
    """
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
        )
        return payload
    except InvalidTokenError as exc:
        logger.warning("JWT decode gagal: %s", str(exc))
        raise ValueError("Token tidak valid atau sudah kedaluwarsa") from exc
