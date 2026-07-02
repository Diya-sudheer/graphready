# GraphReady — Development Roadmap

Four phases, each ending in something runnable and demo-able. Suggested GitHub milestones map 1:1 to phases; issues per milestone are listed as checklists.

---

## Phase 0 — Foundations (Milestone `v0.1-skeleton`, ~2 weeks)

Goal: repo you could show someone on day 14 — clean structure, CI, one document flowing end to end through *stub* stages.

- [ ] Package skeleton, `pyproject.toml`, ruff + pytest + GitHub Actions CI
- [ ] Core data model: `DocumentRecord`, `Page`, `Region`, `Table`, provenance fields (pydantic)
- [ ] Stage-runner DAG with typed artifact passing; artifacts serialized to a package folder
- [ ] SQLite registry + CLI: `graphready process <file>` (stages may be stubs)
- [ ] 10-document sample set (mixed types) committed under `data/samples/`
- [ ] Golden-file test: sample doc → package folder snapshot

## Phase 1 — MVP: perception + mapping-ready output (Milestone `v0.2-mvp`, ~6 weeks)

Goal: **the honest demo** — real PDF/scan/xlsx in, mapping-ready package out, reviewed in the UI. 100% local.

**Perception**
- [ ] Stage 01: type detection (deterministic tier; classifier tier can be heuristic-only in MVP)
- [ ] Stage 02: PaddleOCR backend behind `OcrEngine` interface
- [ ] Stages 03/04/06 via Docling (layout, TableFormer tables, reading order)
- [ ] Stage 04b: xlsx/csv path with multi-row-header flattening and merged-cell unrolling
- [ ] Stage 05 (basic): figure crop + OCR + nearest-caption pairing

**Understanding & mapping-prep**
- [ ] Stage 07: unicode/number/date/unit normalization; wide→long tidy reshaping
- [ ] Stage 08 (baseline): column typing with gradient-boosted trees on Sherlock-style features, trained on VizNet subset
- [ ] Stage 09: GLiNER with a general-domain label profile
- [ ] Stage 11 (baseline): schema.org term index in FAISS + bi-encoder retrieval (no re-ranker yet)
- [ ] Stage 12: mapping-ready CSV + `annotations.json`
- [ ] Stage 13: YARRRML skeleton generation; CI job runs yarrrml-parser + Morph-KGC on outputs
- [ ] Stage 15 (basic): quality report with raw (uncalibrated) confidences

**HITL**
- [ ] Stage 14: Streamlit review app — column suggestions, accept/edit/reject, provenance image panel
- [ ] Feedback store schema

**Definition of done:** a scanned annual-report page and a messy Excel file both produce packages whose YARRRML executes under Morph-KGC after ≤ 5 human corrections in the UI.

## Phase 2 — Real ML depth (Milestone `v0.3-ml`, ~8 weeks)

Goal: the components that make this *your* ML project, not glue code.

- [ ] Stage 01 learned classifier (MobileNetV3/ViT-tiny fine-tune on RVL-CDIP subset + collected infographics)
- [ ] Stage 08 v2: DoDuo-style serialized-table transformer; train on GitTables; **evaluate on extraction-noised tables** (our noise-injection harness — see EVALUATION.md)
- [ ] Stage 10: relationship candidates (header-pair embeddings vs property labels, functional-dependency analysis, datatype/range compatibility)
- [ ] Stage 11 v2: cross-encoder re-ranker; SemTab harness with CTA/CEA/CPA metrics
- [ ] Stage 15 v2: temperature scaling / isotonic calibration per stage, ECE reporting, end-to-end mapping-readiness score
- [ ] Active learning loop: uncertainty×diversity sampler ordering the review queue; retraining script; model registry (versioned weights + config hash in provenance)
- [ ] Cross-document entity clustering (HDBSCAN over embeddings) for candidate deduplication
- [ ] FastAPI service + Docker compose (api, ui)

## Phase 3 — Research & flagship polish (Milestone `v1.0`, ~8+ weeks)

- [ ] **NoisyTab benchmark** (working name): SemTab-style CTA/CPA ground truth over *OCR/layout-extracted* tables — built by running our perception layer over public PDFs with hand-verified annotations; release dataset + leaderboard script
- [ ] GNN experiment: column-graph (GraphSAGE/GAT) joint CTA+CPA vs per-column baseline — ablation writeup
- [ ] Reading-order learned model (LayoutReader-style) vs XY-cut ablation on Kendall-τ
- [ ] DePlot-style chart→table local model for infographics; optional cloud-VLM fallback behind config flag
- [ ] Human-effort study: time-to-validated-mapping with vs without suggestions/active learning (even n=5 users is compelling in a README)
- [ ] Docs site (mkdocs-material), demo GIFs/video, architecture diagrams, `medical.yaml` demo profile
- [ ] Optional: Neo4j preview loader (load *validated* mappings' output for visual inspection — still not auto-KG)

---

## Feature tiers

**MVP (Phase 1):** local pipeline for digital PDFs, scans, images, xlsx/csv; baseline typing/NER/concept suggestion; YARRRML skeletons; validation UI; quality report.

**Advanced (Phases 2–3):** trained document classifier; table-transformer column typing robust to extraction noise; relation candidates; re-ranked ontology matching; calibrated confidence; active learning; entity clustering; GNN CTA/CPA; chart→table; API + Docker; benchmark release.

## Research contributions (thesis-grade)

1. **Task + benchmark: "mapping-readiness."** Define and metricize the doc→mapping-ready task; release the NoisyTab benchmark. (No public benchmark evaluates semantic table interpretation under realistic extraction noise.)
2. **Robust semantic typing under extraction noise.** Quantify clean-table model degradation (Sherlock/DoDuo) on OCR'd tables; show noise-aware training closes the gap.
3. **Composed confidence calibration.** How per-stage calibrated confidences aggregate into trustworthy end-to-end scores across a multi-stage pipeline — barely studied.
4. **Active learning for mapping validation.** Measure human-effort reduction (corrections-to-convergence) from uncertainty×diversity queue ordering.
5. **GNN-based joint CTA/CPA on column graphs** vs independent per-column prediction.

## Publication opportunities

| Venue type | Fit |
|---|---|
| ISWC / ESWC (resource & in-use tracks) | NoisyTab benchmark; the system paper; SemTab challenge participation with the Stage 11 stack |
| ICDAR / DAS | perception-layer contributions, noise-injection harness |
| K-CAP / EKAW / Semantic Web Journal | human-in-the-loop mapping methodology |
| TPDL / JCDL, or workshops (DL4KG, Text2KG, HITLAIA) | early results; Text2KG is a near-perfect topical match |

## What makes this portfolio-flagship material

- A **defensible thesis** (human-reviewed mapping > auto-KG) argued against named related work (Docs2KG, GraphRAG), not just a feature list
- Your **own trained models** with ablations and honest error analysis — visibly not an LLM wrapper
- A **released benchmark** — the single highest-leverage artifact for research credibility
- End-to-end engineering: typed pipeline, provenance, calibration, CI that executes generated mappings, Docker, HITL UI
- Clear evolution story to enterprise/medical/GraphRAG uses — shows architectural thinking, not just a script
