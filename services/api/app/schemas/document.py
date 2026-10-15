"""
Pydantic schemas untuk dokumen.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel


class DocumentUploadResponse(BaseModel):
    document_id: uuid.UUID
    original_filename: str
    ingest_status: str
    message: str


class DocumentOut(BaseModel):
    id: uuid.UUID
    original_filename: str
    file_size_bytes: int
    mime_type: str
    ingest_status: str
    page_count: int | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DocumentListResponse(BaseModel):
    items: list[DocumentOut]
    total: int
    page: int
    page_size: int
