"""Mapping-Ready Package writer (stage 12; stages 13/15 grow here).

Package layout on disk — human-inspectable by design:

    <package>/
    ├── tables/table_00.csv ...   # extracted tables
    ├── text.md                   # full text in reading order
    ├── document.json             # record: type, quality, provenance, agent trace
    └── raw_export.json           # backend-native structured export (full provenance)
"""

from __future__ import annotations

import json
from pathlib import Path

from graphready.core.model import DocumentRecord, PackageResult, Provenance, TableArtifact
from graphready.perception.base import PerceptionResult


def write_package(
    record: DocumentRecord, result: PerceptionResult, package_dir: Path
) -> PackageResult:
    package_dir.mkdir(parents=True, exist_ok=True)
    tables_dir = package_dir / "tables"
    tables_dir.mkdir(exist_ok=True)

    for i, df in enumerate(result.tables):
        rel = f"tables/table_{i:02d}.csv"
        df.to_csv(package_dir / rel, index=False)
        record.tables.append(
            TableArtifact(
                table_id=f"{record.doc_id}-t{i:02d}",
                n_rows=len(df),
                n_cols=df.shape[1],
                columns=[str(c) for c in df.columns],
                csv_path=rel,
                provenance=Provenance(
                    stage="perception",
                    backend=result.backend,
                    confidence=result.quality.table_confidence,
                ),
            )
        )

    if result.text:
        (package_dir / "text.md").write_text(result.text, encoding="utf-8")

    if result.raw_export is not None:
        with open(package_dir / "raw_export.json", "w", encoding="utf-8") as f:
            json.dump(result.raw_export, f, ensure_ascii=False, default=str)

    (package_dir / "document.json").write_text(
        record.model_dump_json(indent=2), encoding="utf-8"
    )
    return PackageResult(package_dir=str(package_dir), record=record)
