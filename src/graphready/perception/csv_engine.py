"""CSV/TSV perception engine.

Plain delimited files need no ML — pandas parses them exactly. Routing them
here instead of through Docling is itself an orchestrator decision (cheapest
capable tool wins).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from graphready.core.model import DocType, QualityReport
from graphready.perception.base import PerceptionResult


class CsvEngine:
    name = "pandas-csv"

    def supports(self, doc_type: DocType) -> bool:
        return doc_type is DocType.CSV

    def parse(self, path: Path, doc_type: DocType) -> PerceptionResult:
        sep = "\t" if path.suffix.lower() == ".tsv" else ","
        df = pd.read_csv(path, sep=sep)
        quality = QualityReport(
            overall_confidence=1.0,  # exact parse, no perception uncertainty
            n_pages=1,
            n_tables=1,
            n_text_chars=0,
        )
        return PerceptionResult(text="", tables=[df], quality=quality, backend=self.name)
