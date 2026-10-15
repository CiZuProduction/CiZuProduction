"""
Pydantic schemas untuk chat dan conversation.
"""
import uuid
from datetime import datetime

from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4096)
    conversation_id: uuid.UUID | None = None


class SourceItem(BaseModel):
    document_id: uuid.UUID
    document_name: str
    page: int | None
    chunk_id: uuid.UUID
    relevance_score: float | None = None


class ChatResponse(BaseModel):
    conversation_id: uuid.UUID
    message_id: uuid.UUID
    answer: str
    sources: list[SourceItem]
    status: str  # completed | failed | no_sources


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    content: str
    created_at: datetime
    sources: list[SourceItem] = []

    model_config = {"from_attributes": True}


class ConversationSummary(BaseModel):
    id: uuid.UUID
    title: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ConversationDetail(ConversationSummary):
    messages: list[MessageOut] = []
