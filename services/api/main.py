"""
Entry point FastAPI — AI Chatbot MVP Backend
Jalankan: uvicorn main:app --reload --host 127.0.0.1 --port 8000
"""
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.rate_limit import limiter

# Inisialisasi logging sebelum import lain
setup_logging(level=settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    import asyncio
    from app.workers.ingestion_worker import run_worker

    logger.info("Memulai %s (env=%s)", settings.app_name, settings.app_env)

    # Jalankan ingestion worker sebagai background task
    worker_task = asyncio.create_task(run_worker())
    logger.info("Ingestion worker background task dimulai")

    yield

    # Hentikan worker saat shutdown
    worker_task.cancel()
    try:
        await worker_task
    except asyncio.CancelledError:
        pass
    logger.info("Mematikan %s", settings.app_name)


app = FastAPI(
    title="AI Chatbot API",
    version="0.1.0",
    description="MVP AI Chatbot — Backend API",
    lifespan=lifespan,
    # Matikan docs di production
    docs_url=None if settings.is_production else "/docs",
    redoc_url=None if settings.is_production else "/redoc",
    openapi_url=None if settings.is_production else "/openapi.json",
)

# ── Rate limiting ──────────────────────────────────────────────────────────
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── CORS ───────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.frontend_url,
        "http://localhost",
        "http://localhost:80",
        "http://127.0.0.1",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=True,  # wajib untuk cookie
    allow_methods=["GET", "POST", "DELETE", "PUT", "PATCH"],
    allow_headers=["Authorization", "Content-Type"],
)


# ── Global exception handler ───────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.error("Unhandled exception: %s", str(exc), exc_info=True)
    # Jangan kirim stack trace ke client
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Terjadi kesalahan internal. Silakan coba lagi."},
    )


# ── Health & Readiness ────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health() -> dict:
    """Liveness check — tidak mengekspos info sensitif."""
    return {"status": "ok"}


@app.get("/ready", tags=["system"])
async def readiness() -> dict:
    """Readiness check — periksa koneksi database."""
    from sqlalchemy import text
    from app.db.session import get_session_factory

    try:
        session_factory = get_session_factory()
        async with session_factory() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "ready", "database": "ok"}
    except Exception as exc:
        logger.error("Readiness check gagal: %s", str(exc))
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={"status": "not_ready", "database": "unavailable"},
        )


# ── API Routes ─────────────────────────────────────────────────────────────
from app.api.routes.auth import router as auth_router
from app.api.routes.chat import router as chat_router
from app.api.routes.documents import router as documents_router
from app.api.routes.ingestion import router as ingestion_router

API_PREFIX = "/api/v1"
app.include_router(auth_router, prefix=API_PREFIX)
app.include_router(documents_router, prefix=API_PREFIX)
app.include_router(chat_router, prefix=API_PREFIX)
app.include_router(ingestion_router, prefix=API_PREFIX)

logger.info("Semua router terdaftar dengan prefix %s", API_PREFIX)
