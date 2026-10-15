"""
Endpoint autentikasi: login, logout, profil.
Token disimpan di HttpOnly cookie untuk keamanan XSS.
Bearer token tetap didukung untuk API client (Swagger, n8n).
"""
import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_authenticated_user
from app.core.config import settings
from app.core.rate_limit import limiter, LIMIT_LOGIN
from app.core.security import create_access_token, verify_password
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.auth import LoginRequest, TokenResponse, UserProfile
from app.services.audit_service import AuditEvent, log_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])

# Nama cookie
COOKIE_NAME = "access_token"
COOKIE_PATH = "/"


async def _get_user_by_email(db: AsyncSession, email: str) -> User | None:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one_or_none()


@router.post("/login", response_model=TokenResponse)
@limiter.limit(LIMIT_LOGIN)
async def login(
    request: Request,
    response: Response,
    payload: LoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    """
    Login — token dikembalikan sebagai JSON dan disimpan di HttpOnly cookie.
    Cookie: HttpOnly, Secure (production), SameSite=Lax.
    """
    user = await _get_user_by_email(db, payload.email)

    password_ok = (
        verify_password(payload.password, user.hashed_password)
        if user else False
    )

    if not user or not password_ok or not user.is_active:
        logger.warning(
            "Login gagal: email=%s ip=%s",
            payload.email,
            request.client.host if request.client else "unknown",
        )
        await log_event(
            db,
            event_type=AuditEvent.LOGIN_FAILED,
            extra={"email": payload.email},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent"),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Kredensial tidak valid",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = create_access_token(
        subject=str(user.id),
        extra_claims={"role": user.role, "email": user.email},
        expires_delta=timedelta(minutes=settings.access_token_expire_minutes),
    )
    logger.info("Login berhasil: user_id=%s", user.id)

    await log_event(
        db,
        event_type=AuditEvent.LOGIN_SUCCESS,
        user_id=user.id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )

    # Set HttpOnly cookie — tidak bisa diakses JavaScript
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=settings.is_production,   # HTTPS only di production
        samesite="lax",
        max_age=settings.access_token_expire_minutes * 60,
        path=COOKIE_PATH,
    )

    return TokenResponse(
        access_token=token,
        expires_in=settings.access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    """Logout — hapus cookie."""
    response.delete_cookie(
        key=COOKIE_NAME,
        path=COOKIE_PATH,
        httponly=True,
        secure=settings.is_production,
        samesite="lax",
    )


@router.get("/me", response_model=UserProfile)
async def get_me(
    current_user: User = Depends(require_authenticated_user),
) -> UserProfile:
    """Kembalikan profil pengguna yang sedang login."""
    return UserProfile.model_validate(current_user)
