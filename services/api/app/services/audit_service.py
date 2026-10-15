"""
Audit Service — mencatat event sensitif ke tabel audit_logs.
Dipanggil dari endpoint setelah operasi berhasil.
Redaksi otomatis untuk field sensitif.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models.audit import AuditLog

logger = logging.getLogger(__name__)

# Field yang tidak boleh masuk ke audit log
_SENSITIVE_KEYS = frozenset({
    "password", "token", "access_token", "secret",
    "api_key", "encryption_key", "cookie",
})


def _redact(data: dict) -> dict:
    """Hapus nilai field sensitif dari dict."""
    return {
        k: "***" if k.lower() in _SENSITIVE_KEYS else v
        for k, v in data.items()
    }


async def log_event(
    db: AsyncSession,
    event_type: str,
    user_id: Optional[uuid.UUID] = None,
    target_type: Optional[str] = None,
    target_id: Optional[str] = None,
    extra: Optional[dict[str, Any]] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> None:
    """
    Simpan event audit ke database.
    Fire-and-forget — jika gagal, log warning tapi tidak raise.
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            event_type=event_type,
            target_type=target_type,
            target_id=str(target_id) if target_id else None,
            extra=_redact(extra) if extra else None,
            ip_address=ip_address,
            user_agent=user_agent[:512] if user_agent else None,
            created_at=datetime.now(timezone.utc),
        )
        db.add(entry)
        # Tidak commit di sini — biar ikut commit dari request handler
        logger.debug("Audit: %s user=%s target=%s/%s", event_type, user_id, target_type, target_id)
    except Exception as e:
        logger.warning("Gagal catat audit log event=%s: %s", event_type, e)


# ── Event type constants ──────────────────────────────────────────────────

class AuditEvent:
    LOGIN_SUCCESS = "login_success"
    LOGIN_FAILED = "login_failed"
    LOGOUT = "logout"
    DOCUMENT_UPLOAD = "document_upload"
    DOCUMENT_DELETE = "document_delete"
    DOCUMENT_REPROCESS = "document_reprocess"
    CONVERSATION_DELETE = "conversation_delete"
    RATE_LIMIT_HIT = "rate_limit_hit"
    ROLE_CHANGE = "role_change"
    ADMIN_ACTION = "admin_action"
