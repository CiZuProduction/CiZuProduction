"""
Database session factory menggunakan SQLAlchemy async engine.
Engine dibuat secara lazy (tidak saat import) agar modul dapat diimport
tanpa koneksi database aktif (berguna untuk testing dan startup cepat).
"""
from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import TYPE_CHECKING

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class untuk semua model ORM."""
    pass


# ── Lazy engine & session factory ──────────────────────────────────────────
# Tidak diinisialisasi di module level agar import tidak membutuhkan libpq.
_engine = None
_AsyncSessionLocal = None


def _get_db_url() -> str:
    """Ambil URL database dari settings (lazy)."""
    from app.core.config import settings
    return settings.database_url.get_secret_value()


def get_engine():
    """Return (atau buat) async engine — dipanggil lazily."""
    global _engine
    if _engine is None:
        from sqlalchemy.ext.asyncio import create_async_engine
        from app.core.config import settings

        _engine = create_async_engine(
            _get_db_url(),
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            echo=settings.app_env == "development",
        )
    return _engine


def get_session_factory():
    """Return (atau buat) async session factory — dipanggil lazily."""
    global _AsyncSessionLocal
    if _AsyncSessionLocal is None:
        from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
        _AsyncSessionLocal = async_sessionmaker(
            bind=get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autoflush=False,
            autocommit=False,
        )
    return _AsyncSessionLocal


async def get_db() -> AsyncGenerator:
    """
    FastAPI dependency — yield sesi database dan tutup setelah request.
    Gunakan: db: AsyncSession = Depends(get_db)
    """
    AsyncSessionLocal = get_session_factory()
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# Alias untuk backward compatibility (Alembic env.py menggunakannya)
class AsyncSessionLocal:
    """Proxy class agar kode lama yang mengimport AsyncSessionLocal tetap berfungsi."""
    def __new__(cls):
        return get_session_factory()()

    def __class_getitem__(cls, item):
        return get_session_factory()
