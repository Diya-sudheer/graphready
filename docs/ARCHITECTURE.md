# GraphReady — System Architecture

## 1. Design principles

1. **Mapping-ready, not mapped.** The system's contract ends at artifacts a human can review: normalized tables, semantic annotations with confidence, and YARRRML skeletons. It never asserts triples.
2. **Every stage is a replaceable module** with a typed input/output contract. OCR engines, layout models, and embedding models are swappable via config.
3. **Everything is traceable.** Every extracted value carries provenance (document → page → region → stage → model version → confidence).
4. **Confidence is a first-class output.** Each stage emits calibrated confidence; the quality report aggregates it so the human knows *where to look*.
5. **Local-first.** The MVP runs offline on a laptop. Cloud models plug in behind the same interfaces, opt-in per stage.
6. **Human corrections are training data.** The validation UI writes corrections back to a feedback store that drives active learning.

## 2. High-level architecture

```
┌────────────────────────────────────────────────────────────────────────┐
│                            Ingestion Layer                              │
│  file watcher / CLI / FastAPI upload → DocumentRecord (SQLite)          │
│  ► Stage 01: type detection (signature + text-layer + image classifier) │
└───────────────┬────────────────────────────────────────────────────────┘
                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Perception Layer (visual)                        │
│  ► Stage 02: OCR (PaddleOCR | pluggable cloud)                          │
│  ► Stage 03: layout analysis (Docling / DocLayNet models)               │
│  ► Stage 04: table structure (TableFormer | pdfplumber | openpyxl)      │
│  ► Stage 05: figure/infographic text (crop + OCR + caption pairing)     │
│  ► Stage 06: reading-order reconstruction                               │
│  output: DocumentGraph — typed regions, text, tables, order, provenance │
└───────────────┬────────────────────────────────────────────────────────┘
                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                        Understanding Layer (semantic)                   │
│  ► Stage 07: cleaning & normalization (units, dates, headers, tidy)     │
│  ► Stage 08: semantic schema detection (column-type classifier)         │
│  ► Stage 09: entity candidates (GLiNER + gazetteers)                    │
│  ► Stage 10: relationship candidates (column pairs, co-occurrence)      │
│  ► Stage 11: ontology concept suggestion (bi-encoder + FAISS + rerank)  │
│  output: AnnotatedDataset — tables + semantic annotations + confidence  │
└───────────────┬────────────────────────────────────────────────────────┘
                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         Mapping-Prep Layer                              │
│  ► Stage 12: mapping-ready CSV generation                               │
│  ► Stage 13: YARRRML template suggestion                                │
│  ► Stage 15: quality & confidence report                                │
│  output: Mapping-Ready Package (csv + annotations.json + yarrrml + html)│
└───────────────┬────────────────────────────────────────────────────────┘
                ▼
┌────────────────────────────────────────────────────────────────────────┐
│                      Human-in-the-Loop Layer                            │
│  ► Stage 14: Streamlit validation UI (accept / edit / reject)           │
│  corrections → feedback store → active learning → model fine-tuning     │
└────────────────────────────────────────────────────────────────────────┘
```

### Agentic orchestration

The pipeline is driven by an **orchestrator agent** (`core/orchestrator.py`) rather than a fixed linear runner. Agency means *decisions about tools*, never LLM freeform extraction:

1. **route** — detect the document type (Stage 01)
2. **select** — pick the cheapest engine that handles it (CSV → pandas; PDF/scan/image/xlsx → Docling)
3. **inspect** — read the engine's confidence report
4. **escalate** — on low OCR confidence for scans/images, retry with a stronger backend (Chandra VLM-OCR, opt-in GPU); if none is installed, flag the package for priority human review
5. **accept** — write the Mapping-Ready Package

Every decision is recorded in an **AgentTrace** shipped inside the package (`document.json`), so agentic behavior stays fully auditable. The policy is deterministic rules today; the interface allows a learned or LLM policy later (the "multi-agent document processing" evolution path) without touching any stage code. Understanding-layer stages (07–11) attach to the same controller as they land.

## 3. Core data model

The load-bearing abstraction is the **DocumentGraph** — an in-memory (and JSON-serializable) typed graph:

```python
DocumentRecord      # id, source path, sha256, detected type, status
  └── Page          # page number, image ref, dimensions
        └── Region  # bbox, class (text|title|table|figure|caption|header|footer),
                    # reading-order index, confidence
              ├── TextBlock   # text, OCR confidence per token
              ├── Table       # cells[row][col], spans, header rows, TEDS-ready structure
              └── Figure      # crop ref, extracted text, paired caption

AnnotatedDataset    # produced by understanding layer
  └── TableArtifact # tidy dataframe + per-column:
        ├── SemanticType        # e.g. person_name, date, currency (+ confidence)
        ├── OntologySuggestions # ranked concept IRIs (+ scores, source ontology)
        ├── EntityCandidates    # spans → candidate entity class
        └── RelationCandidates  # (col_a, col_b, suggested predicate, confidence)
```

Everything hangs off this model; stages only read/write these types. Provenance is a field on every node, never an afterthought.

## 4. Stage details and model choices

### Stage 01 — Document type detection
- **Tier 1 (deterministic):** file extension + magic bytes; for PDFs, text-layer coverage ratio (chars per page area) separates digital from scanned.
- **Tier 2 (learned):** a fine-tuned MobileNetV3/ViT-tiny classifier on first-page renders distinguishes `document_scan | infographic | table_photo | form | chart`. Trained on RVL-CDIP subsets + self-collected samples.
- **Why not an LLM:** this is a cheap, fast, offline classification problem — a 10 MB model at >95% accuracy beats a VLM call.

### Stage 02 — OCR
- **Local default:** Docling's integrated OCR path for scans; PaddleOCR as alternative backend.
- **Escalation backend:** **Chandra** (Datalab, 2025) — a VLM-based OCR model, markedly stronger on handwriting, degraded scans, and complex tables; needs a GPU (~8 GB VRAM), so the orchestrator invokes it only when the default engine reports low confidence.
- **Interface:** `PerceptionEngine.parse(path) -> PerceptionResult(text, tables, quality)` — cloud backends (Azure Document Intelligence, Google Document AI) implement the same interface, enabled per-config.
- Confidence scores are retained and propagate into the quality report; they are what the orchestrator's escalation policy reads.

### Stage 03 — Layout analysis
- **Docling** as the backbone: its layout model is trained on DocLayNet (11 region classes, 80k pages) and ships with table/figure/caption detection and reading order.
- LayoutParser + Detectron2 kept as an alternative backend for experimentation (the module interface makes this a config switch).

### Stage 04 — Table extraction
- Digital PDFs: pdfplumber/camelot lattice+stream.
- Scanned/image tables: **TableFormer** (via Docling) for structure recognition (row/col spans), OCR text injected into the predicted grid.
- Spreadsheets: openpyxl + a **header-detection heuristic stack** (merged-cell unrolling, multi-row header flattening, unit-row detection) — messy Excel is a first-class citizen, not an edge case.

### Stage 05 — Figures & infographics
- Figure regions from layout → crop → OCR → cluster text fragments spatially (DBSCAN on positions) → pair with nearest caption region.
- Infographics get the type-specific path: detected as such in Stage 01, processed with denser OCR + fragment clustering; **optional** cloud VLM assist for chart-value extraction (clearly flagged as cloud in provenance).

### Stage 06 — Reading order
- Default: Docling's built-in ordering; fallback: recursive XY-cut.
- Evaluation hook (Kendall's τ against annotated order) so a learned model (LayoutReader-style) can be dropped in later as a research extension.

### Stage 07 — Cleaning & normalization
- Unicode/whitespace repair, de-hyphenation across line breaks, locale-aware number parsing.
- **Units:** `pint`-based detection and canonicalization (`"12 kg"` → value 12, unit `kg`, QUDT-ready).
- **Dates:** dateutil + format inference per column, canonical ISO 8601.
- **Tidy reshaping:** wide→long detection for crosstab tables (year columns, repeated measure groups) — critical for RML, which wants one row per statement subject.

### Stage 08 — Semantic schema detection *(a core original-ML component)*
- A **column semantic-type classifier** in the Sherlock/DoDuo tradition:
  - Features: character/word distributions, value statistics, regex-bank hits, header embedding, sample-value embeddings (SentenceTransformers), column-context (neighboring headers).
  - Model: gradient-boosted trees baseline → small transformer over serialized column (DoDuo-style) as the advanced version.
  - Trained on VizNet/Sherlock's 78 types + GitTables schema.org types; fine-tuned on domain data via the active-learning loop.
- This is deliberately **your own trainable model** — the centerpiece for the thesis/portfolio narrative.

### Stage 09 — Entity candidates
- **GLiNER** (zero-shot span NER) with a configurable label set per domain profile (e.g. medical: drug, dose, condition; general: person, org, location).
- Gazetteer matcher (pyahocorasick) for known vocabularies loaded from the target ontology's labels.
- Output is *candidates with confidence*, never asserted entities.

### Stage 10 — Relationship candidates
- **Table-native relations:** for each column pair (a, b) in a table, score candidate predicates using: header-pair embedding similarity to ontology property labels, key/functional-dependency analysis (does a→b look functional?), datatype compatibility with property range.
- **Text relations (lightweight):** sentence-level co-occurrence of entity candidates + dependency-path patterns (spaCy) → candidate (subject_type, predicate_hint, object_type).
- **Research extension:** a GNN (GraphSAGE/GAT) over the column graph (nodes = columns with embedding features; edges = same-table adjacency, FD edges, similarity edges) to jointly predict column concepts and pairwise predicates — this is where SemTab-style CTA/CPA becomes a graph learning problem.

### Stage 11 — Ontology concept suggestion
- Ontology terms (classes + properties from schema.org, DBpedia, or a user-supplied OWL/SKOS file) are indexed: label + synonyms + definition → SentenceTransformers embedding → **FAISS**.
- Query = column header + sampled values + semantic type; retrieve top-k; **cross-encoder re-ranker** (ms-marco-MiniLM) for the final ranking.
- Output: ranked IRI suggestions with scores, per column (CTA), per column-pair (CPA), per cell-entity where applicable (CEA) — deliberately aligned with SemTab task definitions so public benchmarks apply directly.

### Stage 12–13 — Mapping-ready CSV + YARRRML suggestion
- CSVs: tidy, normalized, stable column IDs, sidecar `annotations.json`.
- YARRRML generator: subject template inferred from detected key column, predicate-object maps from accepted/top concept suggestions, datatypes from normalization stage. Every suggested line carries a `# confidence: 0.87 (model: xyz@v3)` comment — the human sees exactly what to trust.
- Validated against `yarrrml-parser` + RMLMapper in CI (round-trip: suggested mapping must at least parse and run on the CSV).

### Stage 14 — Human validation UI
- Streamlit app over the package: table view with per-column suggestion dropdowns (top-k concepts), accept/edit/reject, region-image side panel for provenance (click a value → see the source pixels).
- Every decision → `feedback.sqlite` with full context (features, model version, chosen vs rejected).

### Stage 15 — Confidence & quality reporting
- Per-stage raw scores → **calibration** (temperature scaling for neural stages, isotonic regression for heuristic scores) fitted on held-out validated packages, reported with ECE.
- End-to-end **mapping-readiness score** per table: weighted aggregation of extraction, normalization, and annotation confidence — the headline number in `quality_report.html`.

### Active learning loop (cross-cutting)
- Sampler ranks unvalidated columns/entities by (uncertainty × diversity via embedding clustering) and puts them first in the review queue.
- Periodic retraining job fine-tunes the column-type classifier and re-fits calibrators on accumulated feedback; model registry keeps versions so provenance stays honest.

## 5. Local vs cloud

| Concern | Local (default) | Cloud (opt-in) |
|---|---|---|
| OCR | PaddleOCR | Azure Document Intelligence / Google Document AI for degraded scans |
| Layout/tables | Docling (DocLayNet + TableFormer) | — |
| NER | GLiNER | — |
| Embeddings | all-MiniLM-L6-v2 / bge-small (SentenceTransformers) | larger embedding APIs if corpus is huge |
| Infographic value extraction | OCR + clustering (best-effort) | Claude vision for chart→data (flagged in provenance) |
| Relation verification | rule + embedding scores | LLM-as-verifier on low-confidence candidates only |

Rule: cloud calls are (a) behind the same stage interface, (b) off by default, (c) recorded in provenance, (d) never required for the pipeline to complete.

## 6. Folder structure

```
graphready/
├── README.md
├── pyproject.toml
├── docker/                       # Dockerfile + compose (api, ui, worker)
├── configs/                      # YAML per-profile: models, ontologies, thresholds
│   ├── default.yaml
│   └── profiles/                 # e.g. medical.yaml, finance.yaml
├── docs/
│   ├── ARCHITECTURE.md
│   ├── RESEARCH.md
│   ├── ROADMAP.md
│   └── EVALUATION.md
├── src/graphready/
│   ├── core/                     # DocumentGraph, artifacts, provenance, stage runner
│   ├── ingest/                   # Stage 01: loaders + type detection
│   ├── ocr/                      # Stage 02: engine interface + Paddle/cloud backends
│   ├── layout/                   # Stage 03
│   ├── tables/                   # Stage 04: pdf/image/xlsx extractors, header repair
│   ├── figures/                  # Stage 05
│   ├── order/                    # Stage 06
│   ├── normalize/                # Stage 07: units, dates, tidy reshaping
│   ├── schema/                   # Stage 08: column-type classifier (train + infer)
│   ├── entities/                 # Stage 09
│   ├── relations/                # Stage 10 (+ GNN extension)
│   ├── ontology/                 # Stage 11: term indexing, FAISS, re-ranking
│   ├── mapping/                  # Stages 12–13: CSV packaging, YARRRML generation
│   ├── confidence/               # Stage 15: calibration, quality report
│   ├── feedback/                 # feedback store, active-learning sampler, retraining
│   ├── api/                      # FastAPI: upload, status, package download
│   ├── ui/                       # Streamlit validation app (Stage 14)
│   └── cli.py                    # `graphready process|review|export|evaluate`
├── tests/                        # unit + golden-file pipeline tests
├── benchmarks/                   # evaluation harnesses per stage (see EVALUATION.md)
├── scripts/                      # dataset download, model training, index building
└── data/                         # gitignored; samples/ kept for demos
```

## 7. Storage

- **SQLite** (MVP): document registry, stage results index, feedback store. Single-file, zero-ops, perfect for local.
- Artifacts on disk as JSON/CSV/parquet in per-document package folders (human-inspectable — a feature, not a shortcut).
- **PostgreSQL** swap-in for multi-user deployment (SQLAlchemy from day one so this is a connection-string change).
- FAISS index files per ontology profile; Chroma as alternative backend if metadata filtering becomes important.

## 8. Evolution paths

| Future system | What changes | What's already in place |
|---|---|---|
| Enterprise document intelligence | Postgres, S3/MinIO artifact store, auth, Prefect orchestration, worker pool | stage DAG, typed artifacts, Docker |
| Medical guideline processing | `medical.yaml` profile: SNOMED/UMLS ontology index, GLiNER medical labels, PHI-safe local-only enforcement | profile system, local-first design |
| Research paper pipeline | Nougat/GROBID backend in the perception layer, citation-graph artifacts | pluggable stage backends |
| Semantic ETL framework | scheduler + connectors (IMAP, SharePoint, watched folders) | ingestion interface |
| GraphRAG preprocessing | emit chunk+entity+relation artifacts in GraphRAG's expected shape; the KG-prep output *is* the GraphRAG index input | entity/relation candidate stages |
| Multi-agent document processing | wrap stages as tools; an orchestrating agent routes hard documents to specialist flows and the validation queue | clean stage contracts, confidence signals for routing |

The common thread: **stages with typed contracts + confidence + provenance** is exactly the substrate all six systems need. Nothing in the MVP has to be thrown away.
