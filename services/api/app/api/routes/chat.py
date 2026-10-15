"""
Endpoint chat: kirim pertanyaan, daftar percakapan, detail, hapus.
"""
import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import Pagination, require_authenticated_user
from app.core.rate_limit import limiter, LIMIT_CHAT
from app.db.models.conversation import Conversation, Message, MessageSource
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ConversationDetail,
    ConversationSummary,
    MessageOut,
    SourceItem,
)
from app.services.audit_service import AuditEvent, log_event
from app.services.rag_service import RagService

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
@limiter.limit(LIMIT_CHAT)
async def send_chat(
    request: Request,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> ChatResponse:
    """
    Terima pertanyaan, jalankan Agentic RAG, simpan hasil, kembalikan jawaban+sumber.
    """
    # Dapatkan atau buat conversation
    conv: Conversation | None = None
    if payload.conversation_id:
        conv = await _get_conv_or_404(db, payload.conversation_id, current_user)

    if conv is None:
        conv = Conversation(owner_id=current_user.id, title=payload.question[:80])
        db.add(conv)
        await db.flush()

    # Simpan pesan user
    user_msg = Message(
        conversation_id=conv.id,
        role="user",
        content=payload.question,
    )
    db.add(user_msg)
    await db.flush()

    # Panggil RAG service
    rag = RagService(db=db, user_id=current_user.id)
    try:
        rag_result = await rag.answer(question=payload.question, conversation_id=conv.id)
    except Exception as exc:
        logger.error("RAG error untuk user=%s: %s", current_user.id, str(exc))
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Layanan AI sementara tidak tersedia. Coba lagi sesaat.",
        )

    # Simpan pesan assistant
    assistant_msg = Message(
        conversation_id=conv.id,
        role="assistant",
        content=rag_result.answer,
        usage_metadata={"status": rag_result.status},
    )
    db.add(assistant_msg)
    await db.flush()

    # Simpan sumber
    sources_out: list[SourceItem] = []
    for src in rag_result.sources:
        ms = MessageSource(
            message_id=assistant_msg.id,
            chunk_id=uuid.UUID(src.chunk_id),
            document_id=uuid.UUID(src.document_id),
            document_name=src.document_name,  # nama file asli
            page_number=src.page,
            relevance_score=src.score,
        )
        db.add(ms)
        sources_out.append(
            SourceItem(
                document_id=uuid.UUID(src.document_id),
                document_name=src.document_name,
                page=src.page,
                chunk_id=uuid.UUID(src.chunk_id),
                relevance_score=src.score,
            )
        )

    logger.info(
        "Chat selesai: conv=%s user=%s status=%s sources=%d",
        conv.id, current_user.id, rag_result.status, len(sources_out),
    )

    return ChatResponse(
        conversation_id=conv.id,
        message_id=assistant_msg.id,
        answer=rag_result.answer,
        sources=sources_out,
        status=rag_result.status,
    )


@router.get("/conversations", response_model=list[ConversationSummary])
async def list_conversations(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
    pagination: Pagination = Depends(),
) -> list[ConversationSummary]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.owner_id == current_user.id)
        .order_by(Conversation.updated_at.desc())
        .offset(pagination.offset)
        .limit(pagination.page_size)
    )
    convs = result.scalars().all()
    # Build manual — hindari lazy load
    return [
        ConversationSummary(
            id=str(c.id),
            title=c.title,
            created_at=c.created_at.isoformat(),
            updated_at=c.updated_at.isoformat(),
        )
        for c in convs
    ]


@router.get("/conversations/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> ConversationDetail:
    conv = await _get_conv_or_404(db, conversation_id, current_user)

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conv.id)
        .options(selectinload(Message.sources))
        .order_by(Message.created_at)
    )
    messages = result.scalars().all()

    # Build response manual — hindari lazy load ORM di luar greenlet
    messages_out = []
    for m in messages:
        sources_out = []
        for s in m.sources:
            sources_out.append(SourceItem(
                document_id=s.document_id,
                document_name=s.document_name,
                page=s.page_number,
                chunk_id=s.chunk_id if s.chunk_id else uuid.uuid4(),
                relevance_score=s.relevance_score,
            ))
        messages_out.append(MessageOut(
            id=str(m.id),
            role=m.role,
            content=m.content,
            created_at=m.created_at.isoformat(),
            sources=sources_out,
        ))

    return ConversationDetail(
        id=str(conv.id),
        title=conv.title,
        created_at=conv.created_at.isoformat(),
        updated_at=conv.updated_at.isoformat(),
        messages=messages_out,
    )


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
) -> None:
    conv = await _get_conv_or_404(db, conversation_id, current_user)
    await db.delete(conv)
    await log_event(
        db,
        event_type=AuditEvent.CONVERSATION_DELETE,
        user_id=current_user.id,
        target_type="conversation",
        target_id=str(conversation_id),
    )
    logger.info("Conversation dihapus: conv=%s user=%s", conversation_id, current_user.id)


async def _get_conv_or_404(
    db: AsyncSession, conversation_id: uuid.UUID, current_user: User
) -> Conversation:
    result = await db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conv = result.scalar_one_or_none()
    if conv is None or conv.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Percakapan tidak ditemukan")
    return conv
