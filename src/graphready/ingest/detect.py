"""Stage 01: document type detection.

Tier 1 (this module): deterministic — extension, magic bytes, and for PDFs the
text-layer coverage test (a "PDF" with no extractable text is a scan).
Tier 2 (Phase 2): learned image classifier for scan/infographic/table-photo/form.
"""

from __future__ import annotations

from pathlib import Path

from graphready.core.model import DocType

# Below this many extractable characters per page (averaged over sampled pages),
# a PDF is treated as scanned. Digital PDFs typically have 1000+ chars/page.
SCANNED_PDF_CHARS_PER_PAGE = 50

_EXTENSION_MAP = {
    ".csv": DocType.CSV,
    ".tsv": DocType.CSV,
    ".xlsx": DocType.SPREADSHEET,
    ".xlsm": DocType.SPREADSHEET,
    ".xls": DocType.SPREADSHEET,
    ".docx": DocType.DOCX,
    ".png": DocType.IMAGE,
    ".jpg": DocType.IMAGE,
    ".jpeg": DocType.IMAGE,
    ".tiff": DocType.IMAGE,
    ".tif": DocType.IMAGE,
    ".bmp": DocType.IMAGE,
    ".webp": DocType.IMAGE,
}


def detect_doc_type(path: str | Path, sample_pages: int = 3) -> tuple[DocType, str]:
    """Return (doc_type, reason). The reason string goes into the agent trace."""
    p = Path(path)
    ext = p.suffix.lower()

    if ext in _EXTENSION_MAP:
        return _EXTENSION_MAP[ext], f"extension {ext}"

    if ext == ".pdf":
        chars_per_page = _pdf_text_coverage(p, sample_pages)
        if chars_per_page < SCANNED_PDF_CHARS_PER_PAGE:
            return (
                DocType.PDF_SCANNED,
                f"text layer has {chars_per_page:.0f} chars/page "
                f"(< {SCANNED_PDF_CHARS_PER_PAGE}) over first {sample_pages} pages",
            )
        return DocType.PDF_DIGITAL, f"text layer has {chars_per_page:.0f} chars/page"

    return DocType.UNKNOWN, f"unrecognized extension {ext!r}"


def _pdf_text_coverage(path: Path, sample_pages: int) -> float:
    """Average extractable characters per page over the first `sample_pages` pages."""
    import pypdfium2 as pdfium  # docling dependency; imported lazily

    pdf = pdfium.PdfDocument(str(path))
    try:
        n = min(len(pdf), sample_pages)
        if n == 0:
            return 0.0
        total = 0
        for i in range(n):
            textpage = pdf[i].get_textpage()
            total += textpage.count_chars()
            textpage.close()
        return total / n
    finally:
        pdf.close()
