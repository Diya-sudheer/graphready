"""GraphReady live demo (Gradio, deployable to Hugging Face Spaces).

Upload a document (PDF / image / CSV / XLSX) or pick a sample. The orchestrator
agent routes it through the perception pipeline; you get the agent's decision
trace, quality report, extracted tables, and text — the Mapping-Ready Package,
live.

Run locally:   python demo/app.py
Deploy:        push this folder as a Gradio Space (see demo/README.md)
"""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import gradio as gr
import pandas as pd

# Allow running without installing, from either layout:
#   repo:  demo/app.py  with  ../src/graphready
#   Space: app.py       with   ./src/graphready
_here = Path(__file__).resolve().parent
_repo = next(
    (root for root in (_here, _here.parent) if (root / "src" / "graphready").exists()),
    _here,
)
sys.path.insert(0, str(_repo / "src"))

from graphready.core.orchestrator import Orchestrator  # noqa: E402

SAMPLES_DIR = _repo / "data" / "samples"
MAX_PAGES_NOTE = (
    "Free-tier CPU: a multi-page PDF takes ~30–60 s. "
    "The agent trace below shows every routing decision the pipeline made."
)


def process(file: str | None) -> tuple[str, str, pd.DataFrame | None, str]:
    if not file:
        return "Upload a document first.", "", None, ""

    out_root = Path(tempfile.mkdtemp(prefix="graphready_"))
    try:
        result = Orchestrator(out_root=out_root).process(file)
    except Exception as e:
        return f"❌ {type(e).__name__}: {e}", "", None, ""

    record = result.record
    q = record.quality

    trace_lines = [
        f"[{d.decision}] → {d.chosen}\n    reason: {d.reason}"
        for d in record.trace.decisions
    ]
    trace = "\n".join(trace_lines)

    conf = f"{q.overall_confidence:.3f}" if q.overall_confidence is not None else "n/a"
    quality = (
        f"**Type:** `{record.doc_type.value}` · "
        f"**Pages:** {q.n_pages} · **Tables:** {q.n_tables} · "
        f"**Chars:** {q.n_text_chars:,} · **Confidence:** {conf}"
    )
    if q.warnings:
        quality += "\n\n⚠️ " + " · ".join(q.warnings)

    first_table = None
    csvs = sorted((result.path / "tables").glob("*.csv"))
    if csvs:
        first_table = pd.read_csv(csvs[0])
        quality += f"\n\nShowing table 1 of {len(csvs)}."

    text_md = ""
    text_file = result.path / "text.md"
    if text_file.exists():
        text_md = text_file.read_text(encoding="utf-8")
        if len(text_md) > 6000:
            text_md = text_md[:6000] + "\n\n… *(truncated for display)*"

    return quality, trace, first_table, text_md


def sample_paths() -> list[str]:
    if not SAMPLES_DIR.exists():
        return []
    return [str(p) for p in sorted(SAMPLES_DIR.iterdir()) if p.suffix.lower() in
            {".pdf", ".png", ".jpg", ".jpeg", ".csv", ".xlsx"}]


with gr.Blocks(title="GraphReady — documents → mapping-ready data") as demo:
    gr.Markdown(
        "# GraphReady\n"
        "**Heterogeneous documents → mapping-ready data for Knowledge Graph "
        "construction.** An orchestrator agent routes your document through "
        "layout analysis, table extraction, and OCR — and shows you every "
        "decision it made, with confidence scores. "
        "[Source & docs](https://github.com/Diya-sudheer/graphready)\n\n"
        f"*{MAX_PAGES_NOTE}*"
    )
    with gr.Row():
        with gr.Column(scale=1):
            file_in = gr.File(
                label="Document (PDF, PNG/JPG, CSV, XLSX)", type="filepath"
            )
            samples = sample_paths()
            if samples:
                gr.Examples(examples=[[s] for s in samples], inputs=[file_in])
            btn = gr.Button("Process", variant="primary")
        with gr.Column(scale=2):
            quality_out = gr.Markdown(label="Quality report")
            trace_out = gr.Textbox(
                label="Agent trace (route → select → inspect → accept)",
                lines=6,
                interactive=False,
            )
    table_out = gr.Dataframe(label="Extracted table (first)", interactive=False)
    text_out = gr.Markdown(label="Extracted text (reading order)")

    btn.click(process, inputs=[file_in], outputs=[quality_out, trace_out, table_out, text_out])

if __name__ == "__main__":
    demo.launch()
