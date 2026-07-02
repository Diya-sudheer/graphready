# GraphReady — Annotated Research Survey

Literature grounding the design (emphasis on 2023–2025; foundational earlier work included where the field still builds on it). Each entry: problem → method → strengths/weaknesses → how it feeds GraphReady.

> Written from knowledge up to early 2026; verify exact venues/versions when citing. arXiv IDs given where stable.

---

## A. Document parsing toolkits & layout understanding

### A1. Docling (IBM Research, 2024) — arXiv:2408.09869
- **Problem:** No permissively licensed, production-quality open toolkit converting PDFs into structured representations.
- **Method:** Pipeline combining a DocLayNet-trained layout detector, TableFormer for table structure, OCR integration, and reading-order heuristics; outputs a unified `DoclingDocument`.
- **Strengths:** Runs locally on CPU, actively maintained, strong table handling, MIT license. **Weaknesses:** infographics/charts are largely out of scope; limited handwriting; reading order is heuristic.
- **Use here:** The perception-layer backbone (Stages 03–04, 06). GraphReady adds what Docling lacks: type routing, infographic path, semantic layers, HITL.

### A2. DocLayNet (Pfitzmann et al., KDD 2022)
- **Problem:** Layout datasets (PubLayNet) were biased to scientific papers; models failed on business docs.
- **Method:** 80k+ manually annotated pages across 6 document categories, 11 region classes; human double-annotation to quantify ambiguity.
- **Strengths:** diversity, honest inter-annotator analysis. **Weaknesses:** still print-centric; no infographics class granularity.
- **Use here:** Training/eval distribution for layout; its class taxonomy is our `Region.class` vocabulary.

### A3. LayoutLMv3 (Huang et al., ACM MM 2022)
- **Problem:** Unified pretraining for text+layout+image in document understanding.
- **Method:** Multimodal transformer, masked text + masked image + word-patch alignment pretraining; SOTA on FUNSD/CORD/DocVQA-era benchmarks.
- **Strengths:** one encoder for many doc tasks. **Weaknesses:** needs OCR upstream; page-level (long docs awkward); fine-tuning-hungry.
- **Use here:** Candidate encoder for the *advanced* form/key-value extraction stage; not in MVP (Docling + GLiNER cover MVP needs more cheaply).

### A4. LayoutReader (Wang et al., EMNLP 2021)
- **Problem:** Reading-order reconstruction treated as heuristic XY-cuts fails on multi-column/complex layouts.
- **Method:** seq2seq over layout tokens trained on ReadingBank (500k pages from DOCX ground truth).
- **Strengths:** learned ordering clearly beats geometric rules. **Weaknesses:** word-level (slow); domain shift on scans.
- **Use here:** Stage 06's drop-in learned upgrade; our Kendall-τ eval hook exists precisely so this swap is measurable.

## B. OCR & OCR-free document reading

### B5. GOT-OCR 2.0 (Wei et al., 2024) — arXiv:2409.01704
- **Problem:** Fragmented OCR: separate models for text, formulas, tables, charts.
- **Method:** 580M-param unified end-to-end "general OCR theory" model (vision encoder + lightweight decoder) reading text/formula/chart into structured formats.
- **Strengths:** one model, many artifact types, small enough for local GPU. **Weaknesses:** English/Chinese-centric; hallucination risk typical of generative OCR; weaker on degraded scans than pipeline OCR.
- **Use here:** Candidate alternative OCR backend; its chart→data ability is interesting for the infographic path (Stage 05) as a local option before reaching for cloud VLMs.

### B6. Nougat (Blecher et al., Meta, 2023) — arXiv:2308.13418
- **Problem:** Scientific PDFs → structured markup (math, tables) lossy with classic OCR.
- **Method:** Swin encoder + mBART decoder, image-to-markdown, trained on arXiv pairs.
- **Strengths:** excellent on academic PDFs, handles math. **Weaknesses:** hallucinates on out-of-domain docs; repetition failure mode; academic-only.
- **Use here:** The "research paper pipeline" evolution path swaps Nougat in as a perception backend for scientific profiles.

### B7. Donut (Kim et al., ECCV 2022)
- **Problem:** OCR error propagation in document understanding pipelines.
- **Method:** OCR-free encoder-decoder mapping page pixels directly to structured JSON (classification, parsing, VQA).
- **Strengths:** proved end-to-end viability; robust to OCR-hostile layouts. **Weaknesses:** fixed output schemas; needs per-task fine-tuning; weak on dense long documents.
- **Use here:** Conceptual: our receipt/form profile could fine-tune Donut. Also a warning: end-to-end models give **no provenance** — a key reason GraphReady stays pipeline-based (values must trace to pixels for the validation UI).

## C. Table understanding & semantic table interpretation

### C8. TableFormer (Nassar et al., CVPR 2022)
- **Problem:** Table structure recognition (spans, multi-line cells) from images.
- **Method:** transformer decoding table structure as a tag sequence + cell-bbox regression; trained on PubTables-1M/FinTabNet-class data.
- **Strengths:** handles spans well; ships inside Docling. **Weaknesses:** long/dense tables; borderless tables on noisy scans.
- **Use here:** Stage 04 image-table backbone; its cell confidences propagate into our quality report.

### C9. Sherlock (Hulsebos et al., KDD 2019) & DoDuo (Suhara et al., SIGMOD 2022)
- **Problem:** Semantic column typing — what does this column *mean*?
- **Method:** Sherlock: 1,588 hand-crafted features per column → deep classifier over 78 types. DoDuo: pretrained transformer over serialized tables, jointly predicting column types + column-pair relations, using table context.
- **Strengths:** DoDuo shows context matters (whole-table signal); both trainable locally. **Weaknesses:** fixed type vocabularies; trained on *clean web tables* — degrades on OCR'd/messy tables (this gap is a GraphReady research contribution).
- **Use here:** Blueprint for Stage 08 — our own classifier is Sherlock-style features + DoDuo-style context, retrained/evaluated on *extraction-noised* tables.

### C10. TURL (Deng et al., VLDB 2020)
- **Problem:** General-purpose representation learning for relational web tables.
- **Method:** structure-aware transformer with masked-entity pretraining on 570k Wikipedia tables; fine-tunes to CTA/CEA/CPA-style tasks.
- **Strengths:** established table representation learning as a field. **Weaknesses:** entity-linked Wikipedia bias; KB-dependent.
- **Use here:** Pretraining recipe if we train our own table encoder (advanced phase).

### C11. SemTab Challenge (ISWC, 2019–2025, ongoing)
- **Problem:** Benchmarking table-to-KG matching: CTA (column→class), CEA (cell→entity), CPA (column-pair→property).
- **Method:** Annual shared task; top systems blend lexical matching, embeddings, and lately LLM re-ranking; datasets from Wikidata/DBpedia + "hard" synthetic noise rounds.
- **Strengths:** exactly our Stage 11 task definition, with public ground truth. **Weaknesses:** tables are born-digital; noise is synthetic, not OCR-realistic.
- **Use here:** Primary benchmark family for ontology suggestion; our proposed contribution — a SemTab-style benchmark over *extracted* (OCR/layout-noised) tables — directly extends it.

## D. Information extraction & NER

### D12. GLiNER (Zaratiana et al., NAACL 2024)
- **Problem:** Zero-shot NER without LLM-scale cost.
- **Method:** Small bidirectional transformer matching span embeddings against natural-language label embeddings — any label set at inference time.
- **Strengths:** ~300MB, CPU-viable, arbitrary schemas per domain profile. **Weaknesses:** long-document context limits; nested-entity quirks; label-phrasing sensitivity.
- **Use here:** Stage 09 backbone. Domain profiles are literally GLiNER label-set configs. Label-phrasing sensitivity is measurable in our eval harness (nice ablation for a thesis).

### D13. SPIRES / OntoGPT (Caufield et al., Bioinformatics 2024)
- **Problem:** Ontology-grounded structured extraction from text.
- **Method:** Recursive LLM prompting against a declared LinkML schema, grounding outputs to ontology IDs.
- **Strengths:** schema-first extraction, grounded outputs. **Weaknesses:** pure LLM wrapper — costly, unvalidated confidence, hallucination-prone.
- **Use here:** Design contrast we cite: GraphReady achieves grounding via retrieval + classifiers with calibrated confidence, using LLMs only as opt-in verifiers.

## E. KG construction, GraphRAG & semantic mapping

### E14. GraphRAG: From Local to Global (Edge et al., Microsoft, 2024) — arXiv:2404.16130
- **Problem:** RAG fails on global, corpus-level questions.
- **Method:** LLM-extracted entity/relation graph → community detection (Leiden) → hierarchical community summaries used at query time.
- **Strengths:** demonstrated value of graph-shaped preprocessing for QA. **Weaknesses:** indexing cost is enormous (LLM over every chunk); extraction quality unaudited; text-only (no tables/scans).
- **Use here:** Defines our "GraphRAG preprocessing engine" evolution path: GraphReady's entity/relation candidates over *documents GraphRAG can't read* (scans, tables, infographics) are exactly the missing indexing input — with confidence and provenance GraphRAG lacks.

### E15. LightRAG (Guo et al., 2024) — arXiv:2410.05779
- **Problem:** GraphRAG's cost and rigid index updates.
- **Method:** dual-level (entity/theme) retrieval over an incrementally updatable graph index.
- **Strengths:** cheap incremental updates — relevant to our per-document package model. **Weaknesses:** still LLM-extraction-dependent; evaluation contested.
- **Use here:** Incremental-index thinking informs how packages update the ontology-suggestion index without full rebuilds.

### E16. Docs2KG (Sun et al., 2024) — arXiv:2406.02962
- **Problem:** Unified KG construction from heterogeneous unstructured docs (email, web, PDF, Excel).
- **Method:** Docling/markdown-style parsing + LLM-driven schema and triple extraction into a unified dual (layout+semantic) graph.
- **Strengths:** closest published system to our scope; validates the heterogeneous-input framing. **Weaknesses:** auto-generates the KG (no human mapping step), LLM-heavy, no calibrated confidence, no mapping-language output.
- **Use here:** Primary "related work" contrast: GraphReady's thesis is that stopping at *mapping-ready + human review* yields more trustworthy KGs than Docs2KG-style end-to-end automation. An empirical comparison is a publishable study.

### E17. RML / YARRRML ecosystem (Dimou et al., LDOW 2014; Heyvaert et al., ESWC 2018; RML W3C CG spec 2023–2025)
- **Problem:** Declarative, reusable mappings from heterogeneous data to RDF.
- **Method:** RML extends R2RML beyond relational sources; YARRRML is its human-writable YAML syntax; tooling: RMLMapper, Morph-KGC, yarrrml-parser.
- **Strengths:** W3C-community standard; mappings are auditable artifacts — exactly the human-review contract we target. **Weaknesses:** authoring is tedious and expert-only — *the pain GraphReady reduces*; limited native handling of messy sources (which is our job upstream).
- **Use here:** Stage 13's output format; Morph-KGC/RMLMapper in CI to guarantee suggested mappings actually execute.

### E18. LLMs for KG construction — survey line (e.g. Zhu et al. 2023/2024, "LLMs for KG construction and reasoning"; Pan et al., TKDE 2024 "Unifying LLMs and KGs")
- **Problem:** Mapping the landscape of LLM-based KG building.
- **Method:** Surveys of extraction, completion, and reasoning approaches.
- **Consistent findings:** LLMs are strong extractors but weak at schema consistency, calibration, and provenance — reviewers repeatedly flag the missing human-validation layer.
- **Use here:** Literature-backed justification for GraphReady's core bet (human-reviewed mapping > automatic KG generation).

## F. Charts, infographics & multimodal documents

### F19. ChartQA / DePlot / MatCha line (Masry et al. 2022; Liu et al., ACL 2023) and UniChart (Masry et al., EMNLP 2023)
- **Problem:** Extracting data and answering questions from charts.
- **Method:** DePlot: chart→linearized table, then reason over the table; MatCha/UniChart: chart-specialized pretraining of pix2struct-style models.
- **Strengths:** chart→table is precisely our "mapping-ready" philosophy applied to figures. **Weaknesses:** synthetic-chart bias; brittle on real infographics with decorative elements.
- **Use here:** Stage 05 advanced path: DePlot-style chart→table as a local model, cloud VLM only as fallback.

### F20. InfographicsVQA (Mathew et al., WACV 2022) + DocVQA family
- **Problem:** QA over infographics requiring joint text/layout/graphic reasoning.
- **Strengths:** the standard held-out testbed for infographic understanding. **Weaknesses:** QA format doesn't directly measure extraction completeness.
- **Use here:** Source of realistic infographic evaluation material for Stage 05 (we evaluate extraction coverage, not QA).

## G. Human-in-the-loop, active learning & calibration

### G21. Active learning surveys & practice (Settles 2009 foundational; modern: Zhan et al. 2022; ALANNO/argilla-style tooling 2023–2024)
- **Problem:** Minimizing human labeling effort.
- **Method:** uncertainty, diversity (core-set), and hybrid acquisition; batch-mode AL for annotation UIs.
- **Use here:** The review-queue sampler (uncertainty × embedding-diversity) and the retraining loop; measuring *annotation-effort reduction* is one of our headline evaluation metrics.

### G22. Calibration of modern neural networks (Guo et al., ICML 2017) + selective prediction line (2023–2024 works on calibrated IE)
- **Problem:** Neural confidence scores are systematically overconfident.
- **Method:** temperature scaling, isotonic regression; ECE as the metric; selective prediction (abstain below threshold).
- **Use here:** Stage 15 verbatim. A *pipeline-level* study — how per-stage calibrated confidences compose into end-to-end mapping-readiness confidence — is largely unexplored and a genuine research contribution.

---

## Synthesis: the gap GraphReady occupies

| Existing work | What it gives | What it lacks for KG prep |
|---|---|---|
| Docling, GOT-OCR, TableFormer | perception (layout, tables, text) | no semantics, no mapping output |
| Sherlock/DoDuo, SemTab systems | semantic typing on **clean** tables | breaks on extraction noise; no provenance |
| Docs2KG, GraphRAG, SPIRES | end-to-end LLM extraction | no human mapping step, no calibration, costly |
| RML/YARRRML tooling | auditable mapping execution | assumes clean input; tedious authoring |

**GraphReady = the missing middle:** perception-grade extraction + semantic annotation with calibrated confidence + human-reviewed declarative mapping — and a benchmark that measures exactly that (see EVALUATION.md and the research-contribution list in ROADMAP.md).
