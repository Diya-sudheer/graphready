"""Core data model: everything the pipeline produces hangs off these types.

Every artifact carries provenance — which stage, which backend, what confidence —
so the validation UI can trace any value back to its source.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class DocType(str, Enum):
    PDF_DIGITAL = "pdf_digital"
    PDF_SCANNED = "pdf_scanned"
    IMAGE = "image"
    SPREADSHEET = "spreadsheet"
    CSV = "csv"
    DOCX = "docx"
    UNKNOWN = "unknown"


class Provenance(BaseModel):
    """Who produced a value, from where, and how sure they were."""

    stage: str
    backend: str
    model_version: str | None = None
    confidence: float | None = None  # calibrated later; raw for now
    page: int | None = None
    bbox: tuple[float, float, float, float] | None = None


class TableArtifact(BaseModel):
    """One extracted table, ready to become a mapping-ready CSV."""

    table_id: str
    n_rows: int
    n_cols: int
    columns: list[str]
    csv_path: str | None = None  # relative to package root once written
    provenance: Provenance


class Decision(BaseModel):
    """One routing/escalation decision made by the orchestrator agent."""

    at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    decision: str  # e.g. "route", "select_engine", "escalate", "accept"
    reason: str
    chosen: str


class AgentTrace(BaseModel):
    """Full record of what the orchestrator decided and why.

    This is the auditability contract: agentic behavior with zero mystery.
    """

    decisions: list[Decision] = Field(default_factory=list)

    def record(self, decision: str, reason: str, chosen: str) -> None:
        self.decisions.append(Decision(decision=decision, reason=reason, chosen=chosen))


class QualityReport(BaseModel):
    """Per-document extraction quality; feeds the human review queue ordering."""

    overall_confidence: float | None = None  # None = backend reported nothing
    layout_confidence: float | None = None
    ocr_confidence: float | None = None
    table_confidence: float | None = None
    n_pages: int = 0
    n_tables: int = 0
    n_text_chars: int = 0
    warnings: list[str] = Field(default_factory=list)


class DocumentRecord(BaseModel):
    """Top-level record for one processed document."""

    doc_id: str
    source_path: str
    sha256: str
    doc_type: DocType
    processed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    tables: list[TableArtifact] = Field(default_factory=list)
    quality: QualityReport = Field(default_factory=QualityReport)
    trace: AgentTrace = Field(default_factory=AgentTrace)
    extra: dict[str, Any] = Field(default_factory=dict)


class PackageResult(BaseModel):
    """Pointer to a written Mapping-Ready Package on disk."""

    package_dir: str
    record: DocumentRecord

    @property
    def path(self) -> Path:
        return Path(self.package_dir)
