"""Chandra escalation engine (opt-in, GPU).

Chandra (Datalab, 2025) is a vision-language OCR model that is markedly stronger
than pipeline OCR on handwriting, degraded scans, and complex tables. It is the
orchestrator's escalation target when Docling reports low OCR confidence on a
scanned document.

Not enabled by default: it needs several GB of VRAM and a separate install
(`pip install chandra-ocr`). The class exists so the escalation path is real
code with a real contract; `available()` gates whether the orchestrator may
choose it.
"""

from __future__ import annotations

from pathlib import Path

from graphready.core.model import DocType
from graphready.perception.base import PerceptionResult


class ChandraEngine:
    name = "chandra"

    _SUPPORTED = {DocType.PDF_SCANNED, DocType.IMAGE}

    @staticmethod
    def available() -> bool:
        try:
            import chandra  # noqa: F401
        except ImportError:
            return False
        return True

    def supports(self, doc_type: DocType) -> bool:
        return doc_type in self._SUPPORTED

    def parse(self, path: Path, doc_type: DocType) -> PerceptionResult:
        if not self.available():
            raise RuntimeError(
                "Chandra is not installed. Install with: pip install chandra-ocr "
                "(requires a GPU with ~8GB VRAM; see configs/default.yaml)."
            )
        raise NotImplementedError(
            "Chandra integration is Phase 2 (see docs/ROADMAP.md): "
            "page render -> chandra.generate -> markdown + tables."
        )
