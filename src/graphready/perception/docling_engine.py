"""Docling-based perception engine (stages 02-06 in one backend).

Docling bundles a DocLayNet-trained layout model, TableFormer for table
structure, OCR for scanned pages, and reading-order reconstruction.
This is the default engine for PDFs, images, DOCX, and XLSX.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from graphready.core.model import DocType, QualityReport
from graphready.perception.base import PerceptionResult


@lru_cache(maxsize=2)
def _converter(do_ocr: bool):
    """Build a Docling converter; model weights load lazily on first use.

    OCR is a routing decision, not a constant: digital PDFs have a text layer,
    so running OCR on them wastes minutes and can only add errors.
    """
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions
    from docling.document_converter import DocumentConverter, PdfFormatOption

    opts = PdfPipelineOptions(do_ocr=do_ocr)
    return DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=opts),
            InputFormat.IMAGE: PdfFormatOption(pipeline_options=opts),
        }
    )


class DoclingEngine:
    name = "docling"

    _SUPPORTED = {
        DocType.PDF_DIGITAL,
        DocType.PDF_SCANNED,
        DocType.IMAGE,
        DocType.DOCX,
        DocType.SPREADSHEET,
    }

    def supports(self, doc_type: DocType) -> bool:
        return doc_type in self._SUPPORTED

    def parse(self, path: Path, doc_type: DocType) -> PerceptionResult:
        do_ocr = doc_type in (DocType.PDF_SCANNED, DocType.IMAGE)
        result = _converter(do_ocr).convert(str(path))
        doc = result.document

        text = doc.export_to_markdown()

        tables = []
        for table in getattr(doc, "tables", []):
            try:
                tables.append(table.export_to_dataframe(doc))
            except TypeError:  # older docling: no doc argument
                tables.append(table.export_to_dataframe())

        quality = self._quality_from(result, doc, text, len(tables))
        return PerceptionResult(
            text=text,
            tables=tables,
            quality=quality,
            backend=self.name,
            raw_export=doc.export_to_dict(),
        )

    @staticmethod
    def _quality_from(result, doc, text: str, n_tables: int) -> QualityReport:
        q = QualityReport(
            n_pages=len(getattr(doc, "pages", []) or []),
            n_tables=n_tables,
            n_text_chars=len(text),
        )
        # Docling >= 2.28 attaches a ConfidenceReport; read it defensively so the
        # engine still works on versions without one (fields stay None = "unknown").
        conf = getattr(result, "confidence", None)
        if conf is not None:
            q.overall_confidence = _score(conf, "mean_score")
            q.layout_confidence = _score(conf, "layout_score")
            q.ocr_confidence = _score(conf, "ocr_score")
            q.table_confidence = _score(conf, "table_score")
        if not text.strip():
            q.warnings.append("no text extracted")
        return q


def _score(conf, attr: str) -> float | None:
    value = getattr(conf, attr, None)
    if value is None:
        return None
    try:
        value = float(value)
    except (TypeError, ValueError):
        return None
    # Docling reports NaN when a scorer did not run on this document
    return None if value != value else value
