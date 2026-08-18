# GraphReady

**An OCR engine benchmark under scan degradation — and an analysis of why the document → knowledge-graph task can't currently be evaluated end to end.**

This started as an attempt to build a pipeline turning messy documents into mapping-ready data for knowledge graph construction. Working on knowledge graphs in practice changed the question. The hard part is not building the stages — it is **knowing whether they work**, and for the semantic half of this problem there is no ground truth and no benchmark. Rather than ship unfalsifiable claims, this repository was cut back to the parts that are actually true: one measured benchmark, one working perception prototype, and the analysis that came out of it.

**[OCR benchmark results](benchmarks/ocr/RESULTS.md)** · **[Live demo](https://huggingface.co/spaces/Diya1704/graphready)** · [Literature survey](docs/RESEARCH.md)

---

## 1. Result: OCR engine choice under degradation

RapidOCR vs EasyOCR, four simulated scan-degradation conditions, order-insensitive word P/R/F1 plus CER/WER (jiwer). Ground truth from the PDF text layer.

| engine | condition | F1 | CER | s/page |
|---|---|---|---|---|
| rapidocr | clean_300dpi | **0.982** | 0.003 | 1.6 |
| easyocr | clean_300dpi | 0.978 | 0.040 | 10.8 |
| rapidocr | poor_100dpi_blur | **0.971** | 0.017 | 0.9 |
| easyocr | poor_100dpi_blur | 0.758 | 0.106 | 3.6 |
| rapidocr | awful_100dpi_jpeg20 | **0.947** | 0.039 | 0.8 |
| easyocr | awful_100dpi_jpeg20 | 0.439 | 0.229 | 3.8 |

**Findings:**

1. **Degradation is the differentiator.** On clean renders the engines are nearly tied (0.982 vs 0.978). On heavily degraded input EasyOCR collapses (0.439) while RapidOCR holds (0.947) — at 4–7× the speed. **Benchmarking only on clean data would have hidden this completely.**
2. **CER predicts collapse before word-F1 does.** EasyOCR's character error rate is 13× RapidOCR's even on clean input (0.040 vs 0.003) — a cheap early-warning signal usable for routing.
3. **Escalation threshold.** RapidOCR only drops below F1 0.95 at the worst condition, so escalating to a heavier backend is worth triggering only for genuinely bad scans.

**Scope:** one document, 3 pages, English, machine-simulated degradation (not real scanner noise), two engines, CPU. This justifies a default engine choice; it does not characterize OCR performance in general. Full table and caveats: [benchmarks/ocr/RESULTS.md](benchmarks/ocr/RESULTS.md).

```bash
python benchmarks/ocr/benchmark_ocr.py --pdf <digital.pdf>
```

---

## 2. Analysis: why the semantic half can't be evaluated

Knowledge graph construction pipelines assume clean, structured input. Real organizations have scanned reports, infographic-heavy PDFs, spreadsheets with merged headers, photographed tables. The gap between *"pile of documents"* and *"data an RML mapping can consume"* is where most KG projects actually die — so that gap is worth attacking.

The obstacle is evaluation, not implementation:

- **The perception half is measurable.** Type detection, layout, table structure and OCR have mature models *and public benchmarks with ground truth* (DocLayNet, PubTables-1M, FUNSD, SROIE). Building a working perception path was mostly integration.
- **The semantic half is not.** Column semantic typing, entity and relation candidates, ontology suggestion — there is **no ground truth for this task**. [SemTab](https://sem-tab-challenge.github.io/) provides gold data for parts of table→KG matching (CTA/CPA/CEA), but it **assumes already-clean tables** — precisely the assumption that makes the real problem hard. No public benchmark covers "messy real-world document → mapping-ready output".

Without such a benchmark, any end-to-end accuracy claim is unfalsifiable. **So none is made here.** That is the main conclusion of this work, and the reason the understanding layer was never built rather than built-and-guessed-at.

**What a defensible evaluation would need:**

1. **SHACL structural validation first** — verifies well-formedness of output without requiring semantic ground truth. Cheapest honest signal.
2. **A small gold-annotated set** — ~50–100 documents annotated for column semantics and target ontology terms, with a second annotator and reported inter-annotator agreement. Small and real beats large and self-labeled.
3. **Reuse SemTab only where it legitimately applies** — the clean-table portion, stated as such.
4. **Degradation-aware benchmarking throughout**, per finding #1 above.
5. **A human-effort study** for any end-to-end claim — corrections-to-valid-mapping, time-to-first-valid-mapping — rather than pretending to measure automated accuracy.

A deliberate scope decision, unchanged from the start: fully automatic KG construction is brittle and unauditable. The human expert belongs in the loop, which is also why *human correction effort* is the honest end-to-end metric.

---

## 3. Prototype (perception layer only)

A working confidence-driven orchestrator that detects document type, routes to an extraction engine, runs Docling perception (layout + TableFormer + OCR), and emits extracted tables with a quality report, provenance, and an auditable `AgentTrace` of every routing decision.

```bash
pip install -e .
graphready process ./inbox/report.pdf --out ./packages/report/
```

**This produces extracted tables and a quality report. It does not produce semantic annotations or RML/YARRRML mappings** — those stages were never built, for the reason in §2.

Runs locally. Cloud VLM escalation (Chandra) sits behind a strict interface, off by default.
Stack: Python 3.11+ · Docling · RapidOCR · pandas · Gradio.

---

## Limitations

- **No end-to-end evaluation exists**, by design — see §2.
- **The understanding layer is not implemented** (semantic typing, entities, relations, ontology suggestion, YARRRML generation).
- **The OCR benchmark is narrow** — one document, simulated degradation, two engines.
- **Confidence scores are uncalibrated** — no temperature scaling or isotonic fitting was done, so they are not probabilities.
- **The demo shows the perception layer only.**

## Research grounding

Model and decomposition choices are grounded in 2022–2025 literature on Document AI, table structure recognition, semantic table interpretation (SemTab), GraphRAG preprocessing, and human-in-the-loop ML. Annotated survey: [docs/RESEARCH.md](docs/RESEARCH.md).

## License

[MIT](LICENSE)
