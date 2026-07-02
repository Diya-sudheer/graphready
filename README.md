# GraphReady

**Turning heterogeneous documents into mapping-ready data for Knowledge Graph construction.**

GraphReady is a document intelligence pipeline that ingests messy real-world documents — digital and scanned PDFs, images, infographics, spreadsheets, CSVs — and produces **clean, normalized, semantically annotated tables plus suggested RML/YARRRML mapping templates**, ready for a human expert to review and finalize.

> **Design principle:** GraphReady does *not* auto-generate a Knowledge Graph. Fully automatic KG construction is brittle and unauditable. Instead, GraphReady solves the harder, more practical upstream problem: getting heterogeneous documents into a state where declarative semantic mapping (RML/YARRRML) is *possible*, *fast*, and *trustworthy* — with the human expert kept in the loop where it matters.

---

## Why this problem?

Knowledge Graph construction pipelines assume clean, structured input (CSV, JSON, relational tables). Real organizations have scanned reports, infographic-heavy PDFs, Excel files with merged headers, and photographed tables. The gap between *"pile of documents"* and *"data an RML mapping can consume"* is where most KG projects actually die.

GraphReady fills that gap:

```
 heterogeneous docs  ──►  extraction & understanding  ──►  mapping-ready data  ──►  human-reviewed RML/YARRRML  ──►  KG (out of scope)
        │                        │                              │                          │
   PDFs, scans,           OCR, layout, tables,          normalized CSVs +           validation UI,
   images, xlsx,          reading order, figures        semantic annotations,       confidence report,
   infographics                                          YARRRML skeletons          active learning
```

## What it produces

For each input document, GraphReady emits a **Mapping-Ready Package**:

| Artifact | Description |
|---|---|
| `tables/*.csv` | Cleaned, normalized, tidy tables extracted from the document |
| `annotations.json` | Per-column semantic types, entity candidates, relationship candidates, ontology concept suggestions (with calibrated confidence) |
| `mapping.yarrrml.yml` | Auto-suggested YARRRML mapping skeleton — subject templates, predicate suggestions, datatype hints — for the human to edit |
| `quality_report.html` | OCR/layout/extraction confidence, coverage stats, flagged low-confidence regions |
| `provenance.json` | Every value traced back to page, region, and pipeline stage that produced it |

## Pipeline stages

1. **Document type detection** — file signatures + text-layer analysis + lightweight image classifier (digital PDF vs scan vs infographic vs table photo)
2. **OCR** — PaddleOCR locally; pluggable cloud backends for degraded scans
3. **Layout analysis** — DocLayNet-class layout detection via Docling
4. **Table extraction** — TableFormer (image tables) + pdfplumber (digital) + openpyxl (spreadsheets)
5. **Figure & infographic text extraction** — region cropping + OCR + caption pairing
6. **Reading-order reconstruction** — geometric + learned ordering
7. **Cleaning & normalization** — units, dates, encodings, header repair, tidy-data reshaping
8. **Semantic schema detection** — trainable column-type classifier (Sherlock/DoDuo-style)
9. **Entity candidate identification** — zero-shot NER (GLiNER) + gazetteers
10. **Relationship candidate identification** — column-pair semantics, co-occurrence, dependency patterns
11. **Ontology concept suggestion** — SentenceTransformers embeddings vs ontology term index in FAISS (SemTab-style CTA/CPA)
12. **Mapping-ready CSV generation**
13. **RML/YARRRML template suggestion**
14. **Human validation UI** — Streamlit review app; corrections feed active learning
15. **Quality & confidence reporting** — calibrated per-stage and end-to-end confidence

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the full design.

## ML components (not an LLM wrapper)

| Component | Model class | Runs |
|---|---|---|
| Layout detection | Vision transformer / CNN detector (DocLayNet-trained, via Docling) | local |
| Table structure recognition | TableFormer (im2seq transformer) | local |
| OCR | PaddleOCR (CNN+CTC / SVTR) | local |
| Document type classifier | Fine-tuned MobileNet/ViT-tiny + heuristics | local |
| Column semantic typing | **Own trainable classifier** — feature-based + embedding-based, trained on VizNet/GitTables/SemTab | local |
| Entity candidates | GLiNER (zero-shot span-based NER) | local |
| Ontology concept suggestion | SentenceTransformers bi-encoder + FAISS; cross-encoder re-ranker | local |
| Entity/schema clustering | HDBSCAN over embeddings (cross-document deduplication) | local |
| Confidence estimation | Temperature scaling / isotonic calibration per stage | local |
| Active learning | Uncertainty + diversity sampling from validation UI corrections | local |
| (Optional) Relation typing over column graphs | GNN (GraphSAGE/GAT) on table-column graphs | local |
| (Optional) Hard infographic parsing, relation verification | Cloud VLM/LLM (Claude) behind a strict interface — off by default | cloud, opt-in |

**The MVP runs 100% locally.** Cloud models are optional accelerators, never dependencies.

## Tech stack

Python 3.11+ · PyTorch · scikit-learn · SentenceTransformers · Docling · PaddleOCR · FAISS · spaCy/GLiNER · pandas · FastAPI · Streamlit · SQLite (→ PostgreSQL) · Docker · NetworkX (→ Neo4j, future)

## Quickstart (planned CLI)

```bash
pip install -e .
graphready process ./inbox/report.pdf --out ./packages/report/
graphready review --package ./packages/report/     # launches Streamlit validation UI
graphready export --package ./packages/report/ --format yarrrml
```

## Project status & roadmap

Currently in design phase. See [docs/ROADMAP.md](docs/ROADMAP.md) for the milestone plan (MVP → advanced features → research contributions) and [docs/EVALUATION.md](docs/EVALUATION.md) for metrics and benchmark datasets.

## Research

The design is grounded in 2022–2025 literature on Document AI, table understanding, semantic table interpretation (SemTab), GraphRAG preprocessing, and human-in-the-loop ML. Full annotated survey: [docs/RESEARCH.md](docs/RESEARCH.md).

## Scalability path

The modular stage/artifact architecture is designed to evolve into: enterprise document intelligence, medical guideline processing, research-paper pipelines, semantic ETL, GraphRAG preprocessing, and multi-agent document processing. See [docs/ARCHITECTURE.md § Evolution paths](docs/ARCHITECTURE.md#evolution-paths).

## License

MIT (planned).
