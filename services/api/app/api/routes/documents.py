"""
Endpoint dokumen: upload, list, detail, delete, reprocess.
"""
import hashlib
import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import Pagination, require_authenticated_user
from app.core.config import settings
from app.core.rate_limit import limiter, LIMIT_UPLOAD
from app.db.models.document import Document, IngestionJob
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.document import DocumentListResponse, DocumentOut, DocumentUploadResponse
from app.services.audit_service import AuditEvent, log_event
from app.services.storage_service import get_storage_service

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/documents", tags=["documents"])


def _validate_upload(file: UploadFile, content: bytes) -> None:
    """Validasi ekstensi dan ukuran file."""
    filename = file.filename or ""
    ext = Path(filename).suffix.lstrip(".").lower()
    if ext not in settings.allowed_extensions_set:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Ekstensi .{ext} tidak diizinkan",
        )
    if len(content) > settings.max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Ukuran file melebihi batas {settings.max_upload_size_mb} MB",
        )


@router.post(
    "",
    response_model=DocumentUploadResponse,
    status_code=status.HTTP_202_ACCEPTED,
)
@limiter.limit(LIMIT_UPLOAD)
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> DocumentUploadResponse:
    """Upload dokumen baru. File dienkripsi saat disimpan. Ingest dijalankan asinkron."""
    content = await file.read()
    _validate_upload(file, content)

    checksum = hashlib.sha256(content).hexdigest()
    internal_name = f"{uuid.uuid4().hex}_{checksum[:8]}"

    # Simpan file dengan enkripsi AES-256-GCM jika ENCRYPTION_KEY tersedia
    storage = get_storage_service()
    try:
        storage_path = await storage.save(content, internal_name)
    except Exception as e:
        logger.error("Gagal menyimpan file: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Gagal menyimpan file. Coba lagi.",
        )

    doc = Document(
        owner_id=current_user.id,
        original_filename=file.filename or "unknown",
        internal_filename=internal_name,
        storage_path=str(storage_path),
        file_size_bytes=len(content),
        mime_type=file.content_type or "application/octet-stream",
        checksum_sha256=checksum,
        ingest_status="queued",
    )
    db.add(doc)
    await db.flush()

    job = IngestionJob(document_id=doc.id, status="queued")
    db.add(job)
    await db.commit()
    await db.refresh(doc)

    logger.info(
        "Dokumen diunggah: doc_id=%s user=%s encrypted=%s",
        doc.id, current_user.id, storage.encryption_enabled,
    )
    await log_event(
        db,
        event_type=AuditEvent.DOCUMENT_UPLOAD,
        user_id=current_user.id,
        target_type="document",
        target_id=str(doc.id),
        extra={
            "filename": doc.original_filename,
            "size_bytes": doc.file_size_bytes,
            "mime_type": doc.mime_type,
            "encrypted": storage.encryption_enabled,
        },
        ip_address=request.client.host if request.client else None,
    )
    return DocumentUploadResponse(
        document_id=doc.id,
        original_filename=doc.original_filename,
        ingest_status=doc.ingest_status,
        message="Dokumen berhasil diunggah dan masuk antrian proses.",
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
    pagination: Pagination = Depends(),
) -> DocumentListResponse:
    """Daftar dokumen milik pengguna (atau semua jika admin)."""
    base_q = select(Document)
    if current_user.role != "admin":
        base_q = base_q.where(Document.owner_id == current_user.id)

    count_result = await db.execute(select(func.count()).select_from(base_q.subquery()))
    total = count_result.scalar_one()

    result = await db.execute(
        base_q.order_by(Document.created_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    docs = result.scalars().all()

    return DocumentListResponse(
        items=[DocumentOut.model_validate(d) for d in docs],
        total=total,
        page=pagination.page,
        page_size=pagination.page_size,
    )


@router.get("/{document_id}", response_model=DocumentOut)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> DocumentOut:
    """Detail dokumen. Hanya pemilik atau admin yang dapat mengakses."""
    doc = await _get_doc_or_404(db, document_id, current_user)
    return DocumentOut.model_validate(doc)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> None:
    """Hapus dokumen dan data terkait (chunks, embeddings, jobs)."""
    doc = await _get_doc_or_404(db, document_id, current_user)

    # Hapus file fisik secara aman (overwrite sebelum delete)
    storage = get_storage_service()
    await storage.delete(Path(doc.storage_path))

    await db.delete(doc)
    await log_event(
        db,
        event_type=AuditEvent.DOCUMENT_DELETE,
        user_id=current_user.id,
        target_type="document",
        target_id=str(document_id),
        extra={"filename": doc.original_filename},
    )
    logger.info("Dokumen dihapus: doc_id=%s user=%s", document_id, current_user.id)


@router.post("/{document_id}/reprocess", status_code=status.HTTP_202_ACCEPTED)
async def reprocess_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> dict:
    """Antri ulang proses ingest untuk dokumen yang gagal."""
    doc = await _get_doc_or_404(db, document_id, current_user)
    if doc.ingest_status not in {"failed", "needs_review"}:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Hanya dokumen dengan status failed/needs_review yang dapat diproses ulang",
        )
    doc.ingest_status = "queued"
    job = IngestionJob(document_id=doc.id, status="queued")
    db.add(job)
    logger.info("Reprocess diminta: doc_id=%s user=%s", document_id, current_user.id)
    return {"message": "Dokumen masuk antrian proses ulang."}


async def _get_doc_or_404(
    db: AsyncSession, document_id: uuid.UUID, current_user: User
) -> Document:
    result = await db.execute(select(Document).where(Document.id == document_id))
    doc = result.scalar_one_or_none()
    if doc is None or (doc.owner_id != current_user.id and current_user.role != "admin"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Dokumen tidak ditemukan",
        )
    return doc
