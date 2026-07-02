---
title: GraphReady
emoji: 🗺️
colorFrom: blue
colorTo: green
sdk: gradio
sdk_version: "5.0.0"
app_file: app.py
pinned: false
license: mit
short_description: Documents → mapping-ready data for KG construction
---

# GraphReady — live demo

Upload a PDF, image, CSV, or XLSX. The orchestrator agent routes it through the
perception pipeline (layout analysis, TableFormer table extraction, OCR when —
and only when — the document is a scan) and returns the Mapping-Ready Package:
extracted tables, text in reading order, a quality report, and the full agent
decision trace.

Source, architecture, and benchmarks: https://github.com/Diya-sudheer/graphready

## Deploying this Space

1. Create a Space at huggingface.co/new-space (SDK: Gradio, CPU basic).
2. Push the contents of this `demo/` folder plus the `src/` tree, or use
   `scripts/deploy_space.py` from the repo root.
3. First build takes ~10 minutes (model weights download once and are cached).
