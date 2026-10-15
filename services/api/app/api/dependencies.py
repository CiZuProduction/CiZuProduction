"""
FastAPI dependencies bersama: autentikasi, otorisasi, pagination.

Auth strategy:
1. Cookie HttpOnly (browser) — lebih aman dari XSS
2. Bearer header (API client, Swagger, n8n) — tetap didukung
Cookie diprioritaskan jika keduanya ada.
"""
import logging
import uuid
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, Query, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.models.user import User
from app.db.session import get_db

logger = logging.getLogger(__name__)

# auto_error=False agar bisa fallback ke cookie
bearer_scheme = HTTPBearer(auto_error=False)

COOKIE_NAME = "access_token"


async def _get_token(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> Optional[str]:
    """
    Ambil token dari cookie HttpOnly atau Authorization header.
    Cookie diprioritaskan — lebih aman dari XSS.
    """
    # 1. Cookie (browser)
    cookie_token = request.cookies.get(COOKIE_NAME)
    if cookie_token:
        return cookie_token

    # 2. Bearer header (API client / Swagger)
    if credentials and credentials.credentials:
        return credentials.credentials

    return None


async def require_authenticated_user(
    token: Optional[str] = Depends(_get_token),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    Dependency: validasi JWT dari cookie atau Bearer header.
    Raise 401 jika tidak ada token atau token tidak valid.
    """
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Autentikasi diperlukan",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_access_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid atau sudah kedaluwarsa",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str: str | None = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token tidak valid",
        )

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Akun tidak aktif atau tidak ditemukan",
        )
    return user


async def require_admin(
    current_user: User = Depends(require_authenticated_user),
) -> User:
    """Dependency: pastikan user memiliki role admin."""
    if current_user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Akses hanya untuk admin",
        )
    return current_user


class Pagination:
    """Dependency untuk pagination standar."""

    def __init__(
        self,
        page: int = Query(default=1, ge=1, description="Nomor halaman"),
        page_size: int = Query(default=20, ge=1, le=100, description="Jumlah item per halaman"),
    ):
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size
