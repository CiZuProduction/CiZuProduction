"""
Ekstraksi teks dari file PDF dan gambar.
- PDF dengan teks: gunakan pypdf
- PDF scan / gambar: tandai needs_review (PaddleOCR opsional, berat di CPU)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class PageContent:
    page_number: int      # 1-indexed
    text: str
    is_ocr: bool = False


@dataclass
class ExtractionResult:
    pages: list[PageContent] = field(default_factory=list)
    total_pages: int = 0
    needs_ocr: bool = False
    error: str | None = None

    @property
    def full_text(self) -> str:
        return "\n\n".join(p.text for p in self.pages if p.text.strip())

    @property
    def has_text(self) -> bool:
        return any(p.text.strip() for p in self.pages)


def extract_pdf(file_path: Path) -> ExtractionResult:
    """
    Ekstrak teks dari PDF menggunakan pypdf.
    Jika halaman tidak mengandung teks (kemungkinan scan),
    tandai needs_ocr = True.
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        return ExtractionResult(error="pypdf tidak terinstall")

    try:
        reader = PdfReader(str(file_path))
        total = len(reader.pages)
        pages: list[PageContent] = []
        empty_pages = 0

        for i, page in enumerate(reader.pages):
            try:
                text = page.extract_text() or ""
                text = _normalize_text(text)
            except Exception as e:
                logger.warning("Gagal ekstrak halaman %d: %s", i + 1, e)
                text = ""

            if not text.strip():
                empty_pages += 1

            pages.append(PageContent(
                page_number=i + 1,
                text=text,
                is_ocr=False,
            ))

        # Jika lebih dari 50% halaman kosong → kemungkinan PDF scan
        needs_ocr = empty_pages > max(1, total * 0.5)

        logger.info(
            "PDF ekstrak selesai: %s halaman=%d kosong=%d needs_ocr=%s",
            file_path.name, total, empty_pages, needs_ocr,
        )

        return ExtractionResult(
            pages=pages,
            total_pages=total,
            needs_ocr=needs_ocr,
        )

    except Exception as e:
        logger.error("Gagal baca PDF %s: %s", file_path.name, e)
        return ExtractionResult(error=f"PDF_READ_ERROR: {type(e).__name__}")


def extract_image(file_path: Path) -> ExtractionResult:
    """
    Untuk file gambar (PNG/JPG), tandai needs_ocr.
    OCR aktual akan dilakukan jika PaddleOCR tersedia.
    """
    return ExtractionResult(
        pages=[PageContent(page_number=1, text="", is_ocr=False)],
        total_pages=1,
        needs_ocr=True,
    )


def extract_file(file_path: Path, mime_type: str) -> ExtractionResult:
    """Entry point — pilih extractor berdasarkan tipe file."""
    suffix = file_path.suffix.lower()

    if suffix == ".pdf" or "pdf" in mime_type:
        return extract_pdf(file_path)
    elif suffix in {".png", ".jpg", ".jpeg"} or "image" in mime_type:
        return extract_image(file_path)
    else:
        return ExtractionResult(error=f"UNSUPPORTED_TYPE: {suffix}")


def _normalize_text(text: str) -> str:
    """Bersihkan whitespace berlebih tanpa menghilangkan makna."""
    import re
    # Normalisasi baris baru berlebih (max 2 berturut-turut)
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Hilangkan spasi di awal/akhir tiap baris
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()
