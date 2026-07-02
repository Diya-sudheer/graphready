"""Fast tests: routing and CSV path (no ML models needed)."""

import pandas as pd

from graphready.core.model import DocType
from graphready.core.orchestrator import Orchestrator
from graphready.ingest.detect import detect_doc_type


def test_detect_by_extension(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("a,b\n1,2\n")
    doc_type, reason = detect_doc_type(f)
    assert doc_type is DocType.CSV
    assert ".csv" in reason


def test_detect_unknown(tmp_path):
    f = tmp_path / "mystery.xyz"
    f.write_text("?")
    assert detect_doc_type(f)[0] is DocType.UNKNOWN


def test_csv_end_to_end(tmp_path):
    src = tmp_path / "patients.csv"
    src.write_text("name,dob,diagnosis\nAda,1990-01-01,flu\nGrace,1985-06-06,cold\n")

    result = Orchestrator(out_root=tmp_path / "packages").process(src)

    # package artifacts exist
    assert (result.path / "document.json").exists()
    df = pd.read_csv(result.path / "tables" / "table_00.csv")
    assert list(df.columns) == ["name", "dob", "diagnosis"]
    assert len(df) == 2

    # agent trace recorded route -> select -> accept
    decisions = [d.decision for d in result.record.trace.decisions]
    assert decisions == ["route", "select_engine", "accept"]
    assert result.record.trace.decisions[1].chosen == "pandas-csv"
