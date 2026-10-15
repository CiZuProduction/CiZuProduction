"""
Pipeline ingestion utama.
Mengkoordinasikan: ekstraksi → chunking → embedding → simpan ke DB.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select, text, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.models.document import Document, DocumentChunk, IngestionJob
from app.services.ingestion.chunker import TextChunk, chunk_pages
from app.services.ingestion.embedder import get_embedding_adapter
from app.services.ingestion.extractor import ExtractionResult, extract_file

logger = logging.getLogger(__name__)

MAX_RETRIES = 3


async def process_document(job_id: str, db: AsyncSession) -> bool:
    """
    Proses satu dokumen dari awal sampai akhir.
    Return True jika berhasil, False jika gagal.
    """
    # ── 1. Ambil job dan dokumen ────────────────────────────────────────
    job_result = await db.execute(
        select(IngestionJob).where(IngestionJob.id == uuid.UUID(job_id))
    )
    job = job_result.scalar_one_or_none()
    if not job:
        logger.error("Job tidak ditemukan: %s", job_id)
        return False

    doc_result = await db.execute(
        select(Document).where(Document.id == job.document_id)
    )
    doc = doc_result.scalar_one_or_none()
    if not doc:
        await _mark_job_failed(job, "DOCUMENT_NOT_FOUND", db)
        return False

    # ── 2. Cek apakah sudah diproses sebelumnya (idempotency) ──────────
    if doc.ingest_status == "completed":
        logger.info("Dokumen %s sudah completed, skip", doc.id)
        return True

    if job.attempt_count >= MAX_RETRIES:
        logger.warning("Job %s melebihi batas retry (%d)", job_id, MAX_RETRIES)
        await _mark_job_failed(job, "MAX_RETRIES_EXCEEDED", db)
        return False

    # ── 3. Tandai sedang diproses ───────────────────────────────────────
    job.status = "processing"
    job.attempt_count += 1
    job.started_at = datetime.now(timezone.utc)
    doc.ingest_status = "processing"
    await db.commit()

    logger.info("Mulai proses dokumen: %s (job=%s attempt=%d)",
                doc.original_filename, job_id, job.attempt_count)

    try:
        # ── 4. Ekstraksi teks ───────────────────────────────────────────
        file_path = Path(doc.storage_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File tidak ada: {file_path}")

        # Baca dan dekripsi file jika terenkripsi
        from app.services.storage_service import get_storage_service
        storage = get_storage_service()
        try:
            file_content = await storage.read(file_path)
        except ValueError as e:
            raise ValueError(f"DECRYPT_ERROR: {e}") from e

        # Tulis ke file temp untuk ekstraksi (pypdf butuh file path)
        import tempfile
        suffix = file_path.name.split("_")[0][-4:] if "_" in file_path.name else ""
        # Tentukan ekstensi dari mime_type
        ext = ".pdf" if "pdf" in doc.mime_type else ".bin"
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_content)
            tmp_path = Path(tmp.name)

        try:
            extraction: ExtractionResult = extract_file(tmp_path, doc.mime_type)
        finally:
            tmp_path.unlink(missing_ok=True)  # Hapus file temp

        if extraction.error:
            raise ValueError(extraction.error)

        if not extraction.has_text and not extraction.needs_ocr:
            raise ValueError("NO_TEXT_EXTRACTED")

        # Update jumlah halaman
        doc.page_count = extraction.total_pages

        # Jika butuh OCR tapi tidak ada teks sama sekali
        if extraction.needs_ocr and not extraction.has_text:
            doc.ingest_status = "needs_review"
            job.status = "failed"
            job.error_code = "NEEDS_OCR"
            job.error_summary = "Dokumen membutuhkan OCR. PaddleOCR belum aktif."
            job.finished_at = datetime.now(timezone.utc)
            await db.commit()
            logger.warning("Dokumen %s butuh OCR, tandai needs_review", doc.id)
            return False

        # ── 5. Chunking ─────────────────────────────────────────────────
        chunks: list[TextChunk] = chunk_pages(
            pages=extraction.pages,
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
        )

        if not chunks:
            raise ValueError("NO_CHUNKS_PRODUCED")

        logger.info("Chunking selesai: %d chunk dari dokumen %s", len(chunks), doc.id)

        # ── 6. Hapus chunk lama jika ada (reprocess) ────────────────────
        await db.execute(
            text("DELETE FROM document_embeddings WHERE chunk_id IN "
                 "(SELECT id FROM document_chunks WHERE document_id = :doc_id)"),
            {"doc_id": str(doc.id)}
        )
        await db.execute(
            text("DELETE FROM document_chunks WHERE document_id = :doc_id"),
            {"doc_id": str(doc.id)}
        )

        # ── 7. Simpan chunk ke DB ───────────────────────────────────────
        adapter = get_embedding_adapter()
        chunk_texts = [c.text for c in chunks]

        # Embed semua chunk sekaligus
        logger.info("Membuat embedding untuk %d chunk (model=%s)...",
                    len(chunks), adapter.model_name)
        embeddings = await adapter.embed_texts(chunk_texts)

        # ── 8. Simpan chunk + embedding ke PostgreSQL ───────────────────
        for i, (chunk, embedding) in enumerate(zip(chunks, embeddings)):
            chunk_id = uuid.uuid4()

            # Simpan chunk
            db_chunk = DocumentChunk(
                id=chunk_id,
                document_id=doc.id,
                chunk_index=chunk.chunk_index,
                page_number=chunk.page_number,
                text=chunk.text,
                token_count=chunk.token_count,
                embedding_model=adapter.model_name,
            )
            db.add(db_chunk)
            await db.flush()  # dapatkan ID

            # Simpan embedding via raw SQL (pgvector type)
            embedding_str = "[" + ",".join(str(v) for v in embedding) + "]"
            await db.execute(
                text("""
                    INSERT INTO document_embeddings
                        (id, chunk_id, embedding_model, embedding_dimension, embedding, created_at)
                    VALUES
                        (:id, :chunk_id, :model, :dim, CAST(:embedding AS vector), :now)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "chunk_id": str(chunk_id),
                    "model": adapter.model_name,
                    "dim": adapter.dimension,
                    "embedding": embedding_str,
                    "now": datetime.now(timezone.utc),
                }
            )

        # ── 9. Tandai selesai ───────────────────────────────────────────
        doc.ingest_status = "completed"
        job.status = "completed"
        job.finished_at = datetime.now(timezone.utc)
        await db.commit()

        logger.info(
            "Dokumen %s selesai diproses: %d chunk, %d halaman",
            doc.original_filename, len(chunks), extraction.total_pages,
        )
        return True

    except Exception as e:
        await db.rollback()
        error_code = type(e).__name__.upper()
        error_summary = str(e)[:500]
        logger.error("Gagal proses dokumen: %s — %s", error_code, error_summary)

        # Update status gagal menggunakan raw SQL untuk menghindari ORM lazy load
        try:
            await db.execute(
                text("UPDATE ingestion_jobs SET status='failed', error_code=:ec, error_summary=:es, finished_at=:now WHERE id=:id"),
                {"ec": error_code[:128], "es": error_summary[:512], "now": datetime.now(timezone.utc), "id": str(job.id)}
            )
            await db.execute(
                text("UPDATE documents SET ingest_status='failed' WHERE id=:id"),
                {"id": str(job.document_id)}
            )
            await db.commit()
        except Exception as db_err:
            logger.error("Gagal update status failed: %s", db_err)

        return False


async def _mark_job_failed(
    job: IngestionJob,
    error_code: str,
    db: AsyncSession,
    error_summary: str = "",
) -> None:
    job.status = "failed"
    job.error_code = error_code[:128]
    job.error_summary = error_summary[:512] if error_summary else error_code
    job.finished_at = datetime.now(timezone.utc)
    await db.commit()
