"""
Konfigurasi structured logging.
Redaksi otomatis untuk field sensitif.
"""
import logging
import sys
from typing import Any

# Field yang tidak boleh muncul di log
_SENSITIVE_FIELDS = frozenset({
    "password", "token", "access_token", "refresh_token",
    "api_key", "secret", "authorization", "cookie",
    "jwt", "encryption_key",
})


class SensitiveFilter(logging.Filter):
    """Filter yang meredaksi nilai field sensitif dari log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.args, dict):
            record.args = self._redact_dict(record.args)
        return True

    def _redact_dict(self, data: dict[str, Any]) -> dict[str, Any]:
        return {
            k: "***REDACTED***" if k.lower() in _SENSITIVE_FIELDS else v
            for k, v in data.items()
        }


def setup_logging(level: str = "INFO") -> None:
    """Inisialisasi logging ke stdout dengan format JSON-friendly."""
    numeric_level = getattr(logging, level.upper(), logging.INFO)

    handler = logging.StreamHandler(sys.stdout)
    handler.addFilter(SensitiveFilter())

    formatter = logging.Formatter(
        fmt='{"time": "%(asctime)s", "level": "%(levelname)s", '
            '"logger": "%(name)s", "message": "%(message)s"}',
        datefmt="%Y-%m-%dT%H:%M:%S",
    )
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    root_logger.handlers.clear()
    root_logger.addHandler(handler)

    # Kurangi noise dari library pihak ketiga
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
