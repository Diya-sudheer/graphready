"""The orchestrator agent.

Agency here means *decisions about tools*, not LLM freeform generation:

1. route      — detect the document type
2. select     — pick the cheapest engine that can handle it
3. inspect    — read the engine's confidence report
4. escalate   — on low confidence, retry with a stronger engine (if available)
5. accept     — write the package, or flag it for priority human review

Every decision is recorded in an AgentTrace and shipped inside the package, so
agentic behavior stays fully auditable. The policy is deterministic today; the
interface deliberately allows a learned or LLM policy later without touching
the stages themselves.
"""

from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

from graphready.core.model import AgentTrace, DocType, DocumentRecord, PackageResult
from graphready.ingest.detect import detect_doc_type
from graphready.mapping.package import write_package
from graphready.perception.base import PerceptionEngine, PerceptionResult
from graphready.perception.chandra_engine import ChandraEngine
from graphready.perception.csv_engine import CsvEngine
from graphready.perception.docling_engine import DoclingEngine

# Below this OCR confidence on a scanned document, the agent escalates (or, if no
# stronger engine is installed, flags the package for priority human review).
ESCALATION_THRESHOLD = 0.6


class Orchestrator:
    def __init__(self, out_root: Path | str = "packages"):
        self.out_root = Path(out_root)
        # Ordered cheapest-first; the escalation engine is separate.
        self.engines: list[PerceptionEngine] = [CsvEngine(), DoclingEngine()]
        self.escalation_engine = ChandraEngine()

    def process(self, path: str | Path) -> PackageResult:
        path = Path(path)
        trace = AgentTrace()

        # 1. route
        doc_type, reason = detect_doc_type(path)
        trace.record("route", reason, doc_type.value)
        if doc_type is DocType.UNKNOWN:
            raise ValueError(f"Unsupported document type for {path.name}: {reason}")

        # 2. select — first (cheapest) engine that supports the type
        engine = next((e for e in self.engines if e.supports(doc_type)), None)
        if engine is None:
            raise ValueError(f"No engine supports {doc_type.value}")
        trace.record("select_engine", f"cheapest engine supporting {doc_type.value}", engine.name)

        # 3. inspect
        result = engine.parse(path, doc_type)

        # 4. escalate if perception looks weak on a scan-like document
        result = self._maybe_escalate(path, doc_type, result, trace)

        # 5. accept and package
        record = DocumentRecord(
            doc_id=uuid.uuid4().hex[:12],
            source_path=str(path),
            sha256=_sha256(path),
            doc_type=doc_type,
            quality=result.quality,
            trace=trace,
        )
        trace.record(
            "accept",
            f"{result.quality.n_tables} tables, {result.quality.n_text_chars} chars, "
            f"overall confidence {result.quality.overall_confidence}",
            "write_package",
        )
        return write_package(record, result, self.out_root / path.stem)

    def _maybe_escalate(
        self,
        path: Path,
        doc_type: DocType,
        result: PerceptionResult,
        trace: AgentTrace,
    ) -> PerceptionResult:
        ocr_conf = result.quality.ocr_confidence
        weak = doc_type in (DocType.PDF_SCANNED, DocType.IMAGE) and (
            (ocr_conf is not None and ocr_conf < ESCALATION_THRESHOLD)
            or result.quality.n_text_chars == 0
        )
        if not weak:
            return result

        if self.escalation_engine.available() and self.escalation_engine.supports(doc_type):
            trace.record(
                "escalate",
                f"ocr confidence {ocr_conf} < {ESCALATION_THRESHOLD} on {doc_type.value}",
                self.escalation_engine.name,
            )
            return self.escalation_engine.parse(path, doc_type)

        trace.record(
            "flag_for_review",
            f"ocr confidence {ocr_conf} < {ESCALATION_THRESHOLD} on {doc_type.value}, "
            "no escalation engine installed",
            "priority_human_review",
        )
        result.quality.warnings.append("low OCR confidence — prioritized for human review")
        return result


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()
