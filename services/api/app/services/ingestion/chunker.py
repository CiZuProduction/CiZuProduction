"""
Chunking teks menjadi potongan-potongan kecil dengan overlap.
Mempertahankan metadata halaman asal.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from app.services.ingestion.extractor import PageContent

logger = logging.getLogger(__name__)


@dataclass
class TextChunk:
    chunk_index: int
    text: str
    page_number: int | None
    token_count: int | None = None


def chunk_pages(
    pages: list[PageContent],
    chunk_size: int = 800,
    chunk_overlap: int = 120,
) -> list[TextChunk]:
    """
    Potong teks dari semua halaman menjadi chunk dengan overlap.

    Strategi:
    1. Pisahkan teks per halaman, pertahankan nomor halaman.
    2. Potong tiap halaman menjadi chunk berdasarkan karakter.
    3. Chunk overlap memastikan konteks tidak hilang di batas chunk.
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size harus > 0")
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap harus < chunk_size")

    chunks: list[TextChunk] = []
    chunk_index = 0

    for page in pages:
        text = page.text.strip()
        if not text:
            continue

        # Pecah per paragraf dulu untuk mempertahankan batas semantik
        paragraphs = _split_paragraphs(text)
        current = ""

        for para in paragraphs:
            # Jika satu paragraf lebih besar dari chunk_size, potong paksa
            if len(para) > chunk_size:
                # Simpan current dulu jika ada
                if current.strip():
                    chunks.append(TextChunk(
                        chunk_index=chunk_index,
                        text=current.strip(),
                        page_number=page.page_number,
                        token_count=_estimate_tokens(current),
                    ))
                    chunk_index += 1
                    current = ""

                # Potong paragraf panjang
                for sub in _hard_split(para, chunk_size, chunk_overlap):
                    chunks.append(TextChunk(
                        chunk_index=chunk_index,
                        text=sub.strip(),
                        page_number=page.page_number,
                        token_count=_estimate_tokens(sub),
                    ))
                    chunk_index += 1
                continue

            # Cek apakah menambahkan paragraf ini melebihi chunk_size
            candidate = (current + "\n\n" + para).strip() if current else para
            if len(candidate) > chunk_size and current.strip():
                # Simpan chunk saat ini
                chunks.append(TextChunk(
                    chunk_index=chunk_index,
                    text=current.strip(),
                    page_number=page.page_number,
                    token_count=_estimate_tokens(current),
                ))
                chunk_index += 1
                # Mulai chunk baru dengan overlap dari akhir chunk sebelumnya
                overlap_text = _get_overlap(current, chunk_overlap)
                current = (overlap_text + "\n\n" + para).strip() if overlap_text else para
            else:
                current = candidate

        # Simpan sisa teks halaman
        if current.strip():
            chunks.append(TextChunk(
                chunk_index=chunk_index,
                text=current.strip(),
                page_number=page.page_number,
                token_count=_estimate_tokens(current),
            ))
            chunk_index += 1

    logger.debug("Chunking selesai: %d chunk dari %d halaman", len(chunks), len(pages))
    return chunks


def _split_paragraphs(text: str) -> list[str]:
    """Pisahkan teks berdasarkan baris kosong (paragraf)."""
    import re
    parts = re.split(r"\n\s*\n", text)
    return [p.strip() for p in parts if p.strip()]


def _hard_split(text: str, size: int, overlap: int) -> list[str]:
    """Potong teks paksa berdasarkan ukuran karakter."""
    results = []
    start = 0
    while start < len(text):
        end = start + size
        results.append(text[start:end])
        start = end - overlap
    return results


def _get_overlap(text: str, overlap_size: int) -> str:
    """Ambil bagian akhir teks sebagai overlap untuk chunk berikutnya."""
    if len(text) <= overlap_size:
        return text
    # Coba potong di batas kata
    overlap = text[-overlap_size:]
    space_idx = overlap.find(" ")
    if space_idx > 0:
        return overlap[space_idx:].strip()
    return overlap


def _estimate_tokens(text: str) -> int:
    """Estimasi kasar jumlah token (1 token ≈ 4 karakter untuk teks Indonesia/Inggris)."""
    return max(1, len(text) // 4)
