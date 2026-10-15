"""
Agent Policy — menentukan strategi retrieval dan apakah perlu iterasi ulang.
Untuk MVP: kebijakan sederhana berbasis threshold relevance dan jumlah sumber.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# Batas iterasi agent
MAX_ITERATIONS = 3
# Minimum similarity score untuk dianggap relevan
MIN_RELEVANCE_SCORE = 0.3
# Minimum jumlah sumber untuk dianggap cukup
MIN_SOURCES_COUNT = 1


@dataclass
class PolicyDecision:
    should_answer: bool          # apakah langsung jawab
    should_retry_retrieval: bool # apakah perlu retrieval ulang
    should_rephrase_query: bool  # apakah query perlu diparafrase
    reason: str
    refined_query: Optional[str] = None


def evaluate_retrieval(
    original_query: str,
    sources: list,
    iteration: int = 0,
) -> PolicyDecision:
    """
    Evaluasi hasil retrieval dan tentukan langkah berikutnya.

    Rules:
    1. Jika sumber cukup dan relevan → jawab langsung
    2. Jika sumber tidak ada dan belum pernah retry → retry dengan query yang diperluas
    3. Jika sudah melebihi batas iterasi → jawab bahwa info tidak ditemukan
    4. Jika sumber ada tapi relevance rendah → coba rephrase query
    """
    if iteration >= MAX_ITERATIONS:
        return PolicyDecision(
            should_answer=True,
            should_retry_retrieval=False,
            should_rephrase_query=False,
            reason="Batas iterasi tercapai",
        )

    if not sources:
        if iteration == 0:
            # Belum pernah retry — coba dengan query yang diperluas
            return PolicyDecision(
                should_answer=False,
                should_retry_retrieval=True,
                should_rephrase_query=True,
                reason="Tidak ada sumber ditemukan, coba query alternatif",
                refined_query=_expand_query(original_query),
            )
        else:
            # Sudah retry tapi masih kosong → tidak ada info
            return PolicyDecision(
                should_answer=True,
                should_retry_retrieval=False,
                should_rephrase_query=False,
                reason="Tidak ada informasi relevan di dokumen setelah retry",
            )

    # Ada sumber — cek kualitasnya
    avg_score = sum(s.score for s in sources) / len(sources)
    high_quality = [s for s in sources if s.score >= MIN_RELEVANCE_SCORE]

    if len(high_quality) >= MIN_SOURCES_COUNT:
        return PolicyDecision(
            should_answer=True,
            should_retry_retrieval=False,
            should_rephrase_query=False,
            reason=f"Ditemukan {len(high_quality)} sumber relevan (avg score: {avg_score:.2f})",
        )
    elif iteration == 0:
        # Sumber ada tapi kurang relevan — coba rephrase
        return PolicyDecision(
            should_answer=False,
            should_retry_retrieval=True,
            should_rephrase_query=True,
            reason=f"Sumber kurang relevan (avg score: {avg_score:.2f}), coba query alternatif",
            refined_query=_expand_query(original_query),
        )
    else:
        # Sudah retry — jawab dengan apa yang ada
        return PolicyDecision(
            should_answer=True,
            should_retry_retrieval=False,
            should_rephrase_query=False,
            reason=f"Jawab dengan sumber yang tersedia (avg score: {avg_score:.2f})",
        )


def _expand_query(query: str) -> str:
    """
    Perluas query dengan menambahkan konteks.
    Untuk MVP: tambahkan kata kunci umum.
    Fase lanjut: gunakan LLM untuk generate query alternatif.
    """
    # Hapus tanda tanya dan tambahkan konteks
    cleaned = query.rstrip("?").strip()
    return f"{cleaned} informasi detail penjelasan"


def check_prompt_injection(query: str) -> bool:
    """
    Deteksi percobaan prompt injection dari user.
    Return True jika terdeteksi mencurigakan.
    """
    injection_patterns = [
        "ignore previous",
        "ignore all instructions",
        "forget your instructions",
        "you are now",
        "act as",
        "jangan ikuti",
        "abaikan instruksi",
        "tampilkan system prompt",
        "show system prompt",
        "reveal your instructions",
        "/etc/passwd",
        "os.environ",
        "import os",
        "__import__",
    ]

    query_lower = query.lower()
    for pattern in injection_patterns:
        if pattern in query_lower:
            logger.warning("Potensi prompt injection terdeteksi: '%s'", pattern)
            return True
    return False
