"""
Endpoint untuk monitoring dan trigger ingestion pipeline.
"""
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import require_authenticated_user
from app.db.models.document import Document, IngestionJob
from app.db.models.user import User
from app.db.session import get_db

router = APIRouter(prefix="/ingestion", tags=["ingestion"])


@router.get("/jobs/{document_id}")
async def get_ingestion_status(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> dict:
    """Lihat status ingestion job untuk dokumen tertentu."""
    # Cek kepemilikan dokumen
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc or (doc.owner_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")

    # Ambil job terbaru
    job_result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .order_by(IngestionJob.created_at.desc())
        .limit(1)
    )
    job = job_result.scalar_one_or_none()

    return {
        "document_id": str(document_id),
        "document_name": doc.original_filename,
        "ingest_status": doc.ingest_status,
        "page_count": doc.page_count,
        "job": {
            "id": str(job.id) if job else None,
            "status": job.status if job else None,
            "attempt_count": job.attempt_count if job else 0,
            "error_code": job.error_code if job else None,
            "error_summary": job.error_summary if job else None,
            "created_at": job.created_at.isoformat() if job else None,
            "started_at": job.started_at.isoformat() if job and job.started_at else None,
            "finished_at": job.finished_at.isoformat() if job and job.finished_at else None,
        } if job else None,
    }


@router.post("/trigger/{document_id}", status_code=status.HTTP_202_ACCEPTED)
async def trigger_ingestion(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> dict:
    """
    Trigger manual ingestion untuk dokumen yang stuck di queued.
    Berguna untuk debugging tanpa harus restart worker.
    """
    doc_result = await db.execute(
        select(Document).where(Document.id == document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc or (doc.owner_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(status_code=404, detail="Dokumen tidak ditemukan")

    if doc.ingest_status == "completed":
        return {"message": "Dokumen sudah completed", "status": "completed"}

    # Jalankan pipeline langsung (async, tidak blocking request)
    import asyncio
    from app.services.ingestion.pipeline import process_document

    # Buat job baru jika tidak ada yang queued
    job_result = await db.execute(
        select(IngestionJob)
        .where(IngestionJob.document_id == document_id)
        .where(IngestionJob.status.in_(["queued", "processing"]))
        .limit(1)
    )
    existing_job = job_result.scalar_one_or_none()

    if not existing_job:
        new_job = IngestionJob(document_id=document_id, status="queued")
        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)
        job_id = str(new_job.id)
    else:
        job_id = str(existing_job.id)

    # Jalankan di background tanpa blocking
    from app.db.session import get_session_factory
    asyncio.create_task(_run_pipeline_background(job_id, get_session_factory()))

    return {
        "message": "Ingestion dimulai",
        "job_id": job_id,
        "document_id": str(document_id),
    }


async def _run_pipeline_background(job_id: str, session_factory) -> None:
    from app.services.ingestion.pipeline import process_document
    import logging
    logger = logging.getLogger(__name__)
    async with session_factory() as session:
        try:
            await process_document(job_id, session)
        except Exception as e:
            logger.error("Background pipeline error: %s", e)
