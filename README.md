# GraphReady

**An analysis of what actually stands between heterogeneous documents and Knowledge Graph construction — with a working perception-layer prototype and a measured OCR benchmark.**

> **What this repository is.** GraphReady began as an attempt to build a document → mapping-ready-data pipeline. Working on knowledge graphs in practice changed the question. The hard part turned out not to be *building* the stages, but *knowing whether they work at all*: for the semantic half of this problem there is **no ground truth and no end-to-end benchmark**. This repository is therefore published as an **analysis and prototype**, not as a finished tool — a study of the problem, a working perception layer, one rigorous component benchmark, and an honest account of what cannot yet be measured.

**[Live demo (perception layer)](https://huggingface.co/spaces/Diya1704/graphready)** · **[Showcase](https://diya-sudheer.github.io/graphready/)** · **[OCR benchmark results](benchmarks/ocr/RESULTS.md)** · [Evaluation plan](docs/EVALUATION.md) · [Research survey](docs/RESEARCH.md)

---

## Status at a glance

| | |
|---|---|
| **Built & runnable** | Document type detection · agentic engine routing · Docling perception (layout + TableFormer + OCR) for PDF/scan/image/xlsx · exact pandas path for CSV · Mapping-Ready Package output with quality report and full agent trace |
| **Measured** | OCR engine selection — [reproducible benchmark](benchmarks/ocr/RESULTS.md), 2 engines × 4 degradation conditions |
| **Designed, not built** | The entire understanding layer: semantic column typing, entity candidates, relation candidates, ontology suggestion, YARRRML generation, validation UI, active learning *(module directories exist as stubs)* |
| **Not validated** | **Any end-to-end claim.** There is no gold-standard dataset for "document → mapping-ready data", so pipeline output quality is currently **unmeasured**. See [Limitations](#limitations--evaluation-status). |

---

## The problem this analyses

Knowledge Graph construction pipelines assume clean, structured input (CSV, JSON, relational tables). Real organizations have scanned reports, infographic-heavy PDFs, Excel files with merged headers, and photographed tables. The gap between *"pile of documents"* and *"data an RML mapping can consume"* is where most KG projects actually die.

```
 heterogeneous docs  ──►  extraction & understanding  ──►  mapping-ready data  ──►  human-reviewed RML/YARRRML  ──►  KG
        │                        │                              │                          │
   PDFs, scans,           OCR, layout, tables,          normalized CSVs +           validation UI,
   images, xlsx,          reading order, figures        semantic annotations,       confidence report
   infographics                                          YARRRML skeletons
   [PROTOTYPED]              [PARTLY BUILT]                  [DESIGNED]                 [DESIGNED]
```

A deliberate scope decision, unchanged: GraphReady does **not** attempt to auto-generate a Knowledge Graph. Fully automatic KG construction is brittle and unauditable. The target is the upstream problem — getting documents into a state where declarative semantic mapping is *possible*, with a human expert in the loop.

---

## Findings

**1. Engine choice matters far more under degradation than on clean input.**
Benchmarking two OCR engines across four degradation conditions: on clean 300 dpi renders they are nearly tied (word-F1 0.982 vs 0.978), but on heavily degraded input EasyOCR collapses (F1 0.439) while RapidOCR holds (0.947) — at 4–7× the speed. **Benchmarking only on clean data would have hidden this entirely.** Full numbers and caveats: [benchmarks/ocr/RESULTS.md](benchmarks/ocr/RESULTS.md).

**2. Character error rate predicts collapse before word-F1 does.**
EasyOCR's CER is 13× RapidOCR's even on clean input (0.040 vs 0.003) — an early warning signal visible before the word-level metric degrades. Useful as a cheap routing signal.

**3. The perception layer is tractable; the understanding layer is where the real difficulty is.**
Type detection, layout analysis, table structure and OCR are supported by mature models and *public benchmarks with ground truth* (DocLayNet, PubTables-1M, FUNSD, SROIE). Building a working perception path was mostly integration work.

**4. The central finding: the semantic half of this problem cannot currently be honestly evaluated.**
Semantic column typing, entity/relation candidates and ontology suggestion have **no ground truth for this task**. [SemTab](https://sem-tab-challenge.github.io/) provides gold data for *parts* of table→KG matching (CTA/CPA/CEA) but assumes **already-clean tables** — precisely the assumption this project set out to remove. There is no public benchmark for "messy real-world document → mapping-ready output". Without one, any accuracy claim about the full pipeline would be unfalsifiable, which is why none is made here.

**5. Consequence for the design.** This is the argument for keeping the human in the loop, and for measuring *human correction effort* rather than pretending to measure automated accuracy. The honest metrics for the unbuilt layer are things like corrections-to-valid-mapping and time-to-first-valid-mapping — both requiring a user study that has not been run.

---

## What a defensible evaluation would require

Not yet done — recorded here so the gap is explicit rather than implied:

1. **Structural validation first.** SHACL constraints over generated output verify *well-formedness* without needing semantic ground truth. This is the cheapest honest signal and the natural next step.
2. **A small gold-annotated set.** ~50–100 documents annotated for column semantics and target ontology terms, with a second annotator and reported inter-annotator agreement. Small but real beats large and self-labeled.
3. **Reuse SemTab where it legitimately applies** — for the clean-table portion of the task only, stated as such.
4. **Degradation-aware benchmarking throughout**, following finding #1: evaluating only on clean data hides the failures that matter.
5. **A human-effort user study** for the end-to-end claim.

The full per-stage metric design lives in [docs/EVALUATION.md](docs/EVALUATION.md) — note that it is a **plan**, containing no executed results.

---

## Reference architecture (design study)

The 15-stage decomposition below is the *analysis output* — a map of the problem space grounded in 2022–2025 Document AI literature. Stages 1–7 are partly implemented; 8–15 are design only.

<details>
<summary>Full 15-stage decomposition</summary>

1. **Document type detection** — file signatures + text-layer analysis + lightweight image classifier ✅ *built*
2. **OCR** — Docling OCR path; pluggable engines ✅ *built, benchmarked*
3. **Layout analysis** — DocLayNet-class detection via Docling ✅ *built via Docling*
4. **Table extraction** — TableFormer (image) + pdfplumber (digital) + openpyxl (xlsx) ✅ *built via Docling*
5. **Figure & infographic text extraction** — region cropping + OCR + caption pairing ⚠️ *partial*
6. **Reading-order reconstruction** — geometric + learned ordering ⚠️ *via Docling*
7. **Cleaning & normalization** — units, dates, encodings, header repair, tidy reshaping ⚠️ *partial*
8. **Semantic schema detection** — trainable column-type classifier (Sherlock/DoDuo-style) ❌ *design only*
9. **Entity candidate identification** — zero-shot NER (GLiNER) + gazetteers ❌ *design only*
10. **Relationship candidate identification** — column-pair semantics, co-occurrence ❌ *design only*
11. **Ontology concept suggestion** — embeddings vs ontology index in FAISS (SemTab-style CTA/CPA) ❌ *design only*
12. **Mapping-ready CSV generation** ⚠️ *basic package output built*
13. **RML/YARRRML template suggestion** ❌ *design only*
14. **Human validation UI** — review app; corrections feed active learning ❌ *design only*
15. **Quality & confidence reporting** ⚠️ *basic report built; calibration design only*

</details>

Full design rationale: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) · Milestones: [docs/ROADMAP.md](docs/ROADMAP.md)

The **agentic orchestration** layer is real and is the most interesting built component: a confidence-driven controller that routes documents to engines, escalates weak extractions to stronger backends, and records every decision in an auditable `AgentTrace`.

---

## Running the prototype

```bash
pip install -e .
graphready process ./inbox/report.pdf --out ./packages/report/
```

Produces a Mapping-Ready Package: extracted tables, a quality report, provenance, and the agent trace. **Understanding-layer artifacts (`annotations.json`, `mapping.yarrrml.yml`) are not produced** — those stages are unbuilt.

Reproduce the OCR benchmark:

```bash
python benchmarks/ocr/benchmark_ocr.py --pdf <digital.pdf>
```

**Tech stack:** Python 3.11+ · PyTorch · Docling · RapidOCR · pandas · Gradio. The prototype runs 100% locally; cloud VLM escalation (Chandra) sits behind a strict interface and is off by default.

---

## Limitations & evaluation status

Stated plainly, because the alternative is overclaiming:

- **No end-to-end evaluation exists.** No accuracy, precision, or quality number is reported for the pipeline as a whole, because there is no ground truth to compute one against.
- **The understanding layer is not implemented.** Semantic typing, entities, relations, ontology suggestion, YARRRML generation, validation UI and active learning are design artifacts; their module directories are stubs.
- **The OCR benchmark is narrow.** One document, 3 pages, English, machine-simulated degradation rather than real scanner noise, 2 engines. It justifies a default engine choice; it does not characterize OCR performance in general.
- **`docs/EVALUATION.md` is a plan, not results.** It contains no executed numbers.
- **Confidence scores are uncalibrated.** The design calls for temperature scaling / isotonic calibration per stage; none has been fitted, so reported confidences are not probabilities.
- **The live demo shows the perception layer only.**
- **Scope:** even when complete, the output is intended for *human review*, not direct KG ingestion.

---

## Research grounding

The decomposition and model choices are grounded in 2022–2025 literature on Document AI, table structure recognition, semantic table interpretation (SemTab), GraphRAG preprocessing, and human-in-the-loop ML. Annotated survey: [docs/RESEARCH.md](docs/RESEARCH.md).

## License

[MIT](LICENSE)
