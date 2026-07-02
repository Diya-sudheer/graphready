"""Perception engine interface.

An engine turns a source file into text + tables + quality signals (stages 02-06).
Engines are interchangeable: the orchestrator picks one per document and may
escalate to a stronger one when confidence comes back low.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import pandas as pd

from graphready.core.model import DocType, QualityReport


@dataclass
class PerceptionResult:
    """What an engine extracted from one document."""

    text: str  # full document text in reading order (markdown)
    tables: list[pd.DataFrame] = field(default_factory=list)
    quality: QualityReport = field(default_factory=QualityReport)
    backend: str = "unknown"
    raw_export: dict | None = None  # backend-native structured export (provenance)


class PerceptionEngine(Protocol):
    name: str

    def supports(self, doc_type: DocType) -> bool: ...

    def parse(self, path: Path, doc_type: DocType) -> PerceptionResult: ...
