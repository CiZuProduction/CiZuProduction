"""
Background worker untuk memproses antrian ingestion.
Berjalan sebagai asyncio task di dalam proses API yang sama.
Polling database setiap beberapa detik untuk job baru.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

logger = logging.getLogger(__name__)

# Interval polling dalam detik
POLL_INTERVAL = 5
# Maksimum job yang diproses bersamaan
MAX_CONCURRENT = 2


async def _get_pending_jobs(session: AsyncSession) -> list[str]:
    """Ambil job dengan status queued, klaim untuk diproses."""
    from app.db.models.document import IngestionJob

    result = await session.execute(
        select(IngestionJob.id)
        .where(IngestionJob.status == "queued")
        .order_by(IngestionJob.created_at)
        .limit(MAX_CONCURRENT)
        .with_for_update(skip_locked=True)  # hindari race condition multi-worker
    )
    return [str(row[0]) for row in result.fetchall()]


async def run_worker() -> None:
    """
    Loop utama worker — poll dan proses job ingestion.
    Dipanggil saat aplikasi startup.
    """
    from app.core.config import settings
    from app.db.session import get_engine, get_session_factory
    from app.services.ingestion.pipeline import process_document

    logger.info("Ingestion worker dimulai (poll_interval=%ds)", POLL_INTERVAL)

    # Tunggu sebentar agar DB connection siap
    await asyncio.sleep(3)

    while True:
        try:
            session_factory = get_session_factory()

            async with session_factory() as session:
                job_ids = await _get_pending_jobs(session)

            if job_ids:
                logger.info("Ditemukan %d job baru", len(job_ids))
                tasks = []
                for job_id in job_ids:
                    tasks.append(_process_single(job_id, get_session_factory()))
                await asyncio.gather(*tasks, return_exceptions=True)
                # Jeda singkat sebelum poll berikutnya
                await asyncio.sleep(1)
            else:
                await asyncio.sleep(POLL_INTERVAL)

        except asyncio.CancelledError:
            logger.info("Ingestion worker dihentikan")
            break
        except Exception as e:
            logger.error("Worker error (akan retry): %s", e, exc_info=True)
            await asyncio.sleep(POLL_INTERVAL)


async def _process_single(job_id: str, session_factory: async_sessionmaker) -> None:
    """Proses satu job dalam session terpisah."""
    from app.services.ingestion.pipeline import process_document

    async with session_factory() as session:
        try:
            success = await process_document(job_id, session)
            if success:
                logger.info("Job %s selesai", job_id)
            else:
                logger.warning("Job %s gagal", job_id)
        except Exception as e:
            logger.error("Error proses job %s: %s", job_id, e, exc_info=True)
            await session.rollback()