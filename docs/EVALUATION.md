# GraphReady — Evaluation Plan

Every stage gets its own harness under `benchmarks/`; the pipeline gets end-to-end metrics. Numbers go in the README — measured, versioned, reproducible (`graphready evaluate --stage <name>`).

## Per-stage metrics & datasets

| Stage | Metric(s) | Benchmark data |
|---|---|---|
| 01 Type detection | accuracy, macro-F1, confusion matrix | RVL-CDIP (16 classes, subset), self-labeled infographic/table-photo set |
| 02 OCR | CER, WER (token-level) | FUNSD, SROIE, self-scanned samples at varied DPI |
| 03 Layout | mAP@0.5:0.95 per region class | DocLayNet test split |
| 04 Tables | **TEDS** and TEDS-struct | PubTables-1M test, FinTabNet (hard financial tables) |
| 05 Figures/infographics | text-extraction recall vs annotation; chart→table cell F1 | InfographicsVQA images (re-annotated for extraction), ChartQA charts |
| 06 Reading order | Kendall's τ, BLEU over token order | ReadingBank sample, hand-ordered scans |
| 07 Normalization | field-level accuracy (dates/units/numbers) vs gold | self-built gold set from samples (freeze it — regression suite) |
| 08 Column typing | macro/weighted F1; **clean vs noised gap** | VizNet/Sherlock 78 types, GitTables; + our noise-injected variants |
| 09 Entities | span P/R/F1 (relaxed + strict) | FUNSD entities, CoNLL-style sets per domain profile |
| 10 Relations | candidate precision@k, recall of gold predicates | SemTab CPA ground truth; annotated sample docs |
| 11 Ontology suggestion | **CTA/CEA/CPA accuracy, Hit@1/5, MRR** (SemTab protocol) | SemTab rounds (2019–2024); NoisyTab (ours, Phase 3) |
| 15 Confidence | **ECE**, reliability diagrams; selective-prediction risk-coverage curves | held-out validated packages |

## End-to-end metrics (the ones that matter)

1. **Mapping executability:** % of generated YARRRML skeletons that parse (yarrrml-parser) and execute (Morph-KGC) on their CSVs — enforced ≥ threshold in CI.
2. **Corrections-to-valid-mapping (CTVM):** median human edits in the validation UI until the expert accepts the mapping. Primary HITL metric; the active-learning claim is "AL ordering reduces CTVM by X%".
3. **Annotation coverage:** % of columns/cells with a suggestion above confidence threshold (report jointly with precision — coverage alone is gameable).
4. **Time-to-validated-mapping:** wall-clock user study metric (Phase 3, n≥5 users, with/without suggestions).
5. **Provenance completeness:** % of output values traceable to a source region (target: 100%; regression-tested).

## The noise-injection harness (core research tooling)

To measure "semantic typing under extraction noise" we corrupt clean benchmark tables with *realistic* perception errors, parameterized by severity:

- OCR character confusions sampled from our own PaddleOCR error distribution (confusion matrix harvested from Stage 02 eval)
- Cell merge/split errors mimicking TableFormer failure modes
- Header loss / multi-row header flattening errors
- Column truncation and reading-order swaps

This gives paired clean/noised versions of VizNet/GitTables/SemTab — the substrate for research contribution #2 and the NoisyTab benchmark.

## Baselines to compare against

- Stage 08: majority-class, header-string fuzzy match, Sherlock features + logistic regression, our GBT, our transformer
- Stage 11: exact label match, BM25 over ontology labels, bi-encoder, bi-encoder + cross-encoder, (optional) LLM re-ranker — the ablation table practically writes the thesis chapter
- End-to-end contrast: Docs2KG-style LLM auto-extraction on the same documents, judged on schema consistency + hallucination rate vs our human-validated output

## Reporting discipline

- Every README number links to the benchmark script + config hash + model version that produced it
- Confidence intervals via bootstrap over documents (not rows — rows within a doc are correlated)
- A `RESULTS.md` changelog: date, commit, metric deltas — reviewers and hiring managers love visible measurement culture
