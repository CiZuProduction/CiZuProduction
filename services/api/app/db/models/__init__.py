# Ekspor semua model agar Alembic dapat mendeteksi perubahan schema
from app.db.models.audit import AuditLog
from app.db.models.conversation import Conversation, Message, MessageSource
from app.db.models.document import (
    Document,
    DocumentChunk,
    DocumentEmbedding,
    IngestionJob,
)
from app.db.models.user import User

__all__ = [
    "User",
    "Document",
    "DocumentChunk",
    "DocumentEmbedding",
    "IngestionJob",
    "Conversation",
    "Message",
    "MessageSource",
    "AuditLog",
]
