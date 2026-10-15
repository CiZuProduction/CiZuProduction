"""
Agentic RAG Service — Fase 5.
Orkestrasi: query → policy evaluation → retrieval → (retry jika perlu) → LLM → answer.
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass, field
from typing import Optional

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.services.agent.policy import (
    MAX_ITERATIONS,
    check_prompt_injection,
    evaluate_retrieval,
)

logger = logging.getLogger(__name__)


@dataclass
class RetrievedSource:
    document_id: str
    chunk_id: str
    text: str
    page: Optional[int]
    score: float
    document_name: str = ""


@dataclass
class RAGAnswer:
    answer: str
    sources: list[RetrievedSource] = field(default_factory=list)
    status: str = "completed"
    iterations: int = 0


class RagService:
    """
    Agentic RAG dengan policy evaluation dan retry logic.

    Alur:
    1. Validasi query (prompt injection check)
    2. Embed query
    3. Retrieve dari PGVector
    4. Evaluasi policy → retry jika diperlukan
    5. Build context
    6. Panggil LLM
    7. Return jawaban + sumber
    """

    def __init__(self, db: AsyncSession, user_id: uuid.UUID) -> None:
        self.db = db
        self.user_id = user_id

    async def answer(self, question: str, conversation_id: uuid.UUID) -> RAGAnswer:
        request_id = str(uuid.uuid4())[:8]

        logger.info(
            "Agentic RAG [%s]: user=%s question_len=%d",
            request_id, self.user_id, len(question),
        )

        # ── 1. Prompt injection check ───────────────────────────────────
        if check_prompt_injection(question):
            return RAGAnswer(
                answer="Maaf, pertanyaan mengandung pola yang tidak diizinkan.",
                status="rejected",
            )

        # ── 2. Embed query ──────────────────────────────────────────────
        try:
            from app.services.ingestion.embedder import get_embedding_adapter
            adapter = get_embedding_adapter()
            embeddings = await adapter.embed_texts([question])
            query_embedding = embeddings[0]
        except Exception as e:
            logger.error("[%s] Gagal embed query: %s", request_id, e)
            return RAGAnswer(
                answer="Maaf, layanan embedding sedang tidak tersedia.",
                status="failed",
            )

        # ── 3. Agentic retrieval loop ───────────────────────────────────
        sources: list[RetrievedSource] = []
        current_query = question
        current_embedding = query_embedding
        iteration = 0

        while iteration < MAX_ITERATIONS:
            try:
                sources = await self._retrieve(current_embedding)
            except Exception as e:
                logger.error("[%s] Gagal retrieve iter=%d: %s", request_id, iteration, e)
                break

            # Evaluasi apakah sumber sudah cukup
            decision = evaluate_retrieval(
                original_query=question,
                sources=sources,
                iteration=iteration,
            )

            logger.info(
                "[%s] Policy iter=%d: sources=%d decision=%s reason='%s'",
                request_id, iteration, len(sources),
                "answer" if decision.should_answer else "retry",
                decision.reason,
            )

            if decision.should_answer:
                break

            # Retry dengan query yang direfine
            if decision.should_retry_retrieval and decision.refined_query:
                logger.info(
                    "[%s] Retry dengan query: '%s'",
                    request_id, decision.refined_query,
                )
                try:
                    refined_embeddings = await adapter.embed_texts([decision.refined_query])
                    current_embedding = refined_embeddings[0]
                    current_query = decision.refined_query
                except Exception as e:
                    logger.error("[%s] Gagal embed refined query: %s", request_id, e)
                    break

            iteration += 1

        # ── 4. Handle no sources ────────────────────────────────────────
        if not sources:
            return RAGAnswer(
                answer=(
                    "Saya tidak menemukan informasi yang relevan "
                    "di dokumen yang tersedia untuk menjawab pertanyaan ini. "
                    "Pastikan dokumen yang relevan sudah diupload."
                ),
                sources=[],
                status="no_sources",
                iterations=iteration,
            )

        # ── 5. Build context ────────────────────────────────────────────
        context = self._build_context(sources)

        # ── 6. Panggil LLM ──────────────────────────────────────────────
        try:
            from app.services.llm_service import generate_answer
            answer_text = await generate_answer(
                question=question,
                context=context,
            )
        except Exception as e:
            logger.error("[%s] Gagal panggil LLM: %s", request_id, e)
            return RAGAnswer(
                answer="Maaf, layanan AI sedang tidak tersedia. Coba lagi sesaat.",
                sources=sources,
                status="failed",
                iterations=iteration,
            )

        logger.info(
            "[%s] Selesai: iter=%d sources=%d answer_len=%d",
            request_id, iteration, len(sources), len(answer_text),
        )

        return RAGAnswer(
            answer=answer_text,
            sources=sources,
            status="completed",
            iterations=iteration,
        )

    async def _retrieve(self, query_embedding: list[float]) -> list[RetrievedSource]:
        """Cari chunk paling relevan menggunakan cosine similarity di PGVector."""
        embedding_str = "[" + ",".join(str(v) for v in query_embedding) + "]"
        top_k = settings.retrieval_top_k

        result = await self.db.execute(
            text("""
                SELECT
                    dc.id as chunk_id,
                    dc.text,
                    dc.page_number,
                    d.id as document_id,
                    d.original_filename,
                    1 - (de.embedding <=> CAST(:query_vec AS vector)) as similarity
                FROM document_embeddings de
                JOIN document_chunks dc ON dc.id = de.chunk_id
                JOIN documents d ON d.id = dc.document_id
                WHERE
                    d.owner_id = :user_id
                    AND d.ingest_status = 'completed'
                ORDER BY de.embedding <=> CAST(:query_vec AS vector)
                LIMIT :top_k
            """),
            {
                "query_vec": embedding_str,
                "user_id": str(self.user_id),
                "top_k": top_k,
            },
        )

        rows = result.fetchall()
        sources = []
        for row in rows:
            if row.similarity < 0.3:
                continue
            sources.append(RetrievedSource(
                chunk_id=str(row.chunk_id),
                text=row.text,
                page=row.page_number,
                document_id=str(row.document_id),
                document_name=row.original_filename,
                score=float(row.similarity),
            ))

        return sources

    def _build_context(self, sources: list[RetrievedSource]) -> str:
        """Susun teks konteks dari chunk yang ditemukan."""
        MAX_CONTEXT_CHARS = 12000
        context_parts = []
        total_chars = 0

        for i, src in enumerate(sources):
            page_info = f" (hal. {src.page})" if src.page else ""
            header = f"[Sumber {i+1}: {src.document_name}{page_info}]"
            chunk_text = f"{header}\n{src.text}"

            if total_chars + len(chunk_text) > MAX_CONTEXT_CHARS:
                break

            context_parts.append(chunk_text)
            total_chars += len(chunk_text)

        return "\n\n---\n\n".join(context_parts)
