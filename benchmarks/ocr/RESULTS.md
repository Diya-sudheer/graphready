# OCR engine benchmark results

Document: `Project_2.pdf` — ground truth from the PDF text layer.
Conditions simulate scan degradation. Metrics: order-insensitive word
precision/recall/F1, plus order-sensitive CER/WER (jiwer).

| engine | condition | precision | recall | F1 | CER | WER | s/page |
|---|---|---|---|---|---|---|---|
| rapidocr | clean_300dpi | 0.984 | 0.980 | 0.982 | 0.003 | 0.021 | 1.6 |
| easyocr | clean_300dpi | 0.981 | 0.976 | 0.978 | 0.040 | 0.071 | 10.8 |
| rapidocr | fax_150dpi | 0.974 | 0.956 | 0.965 | 0.005 | 0.044 | 1.2 |
| easyocr | fax_150dpi | 0.967 | 0.944 | 0.955 | 0.067 | 0.116 | 5.1 |
| rapidocr | poor_100dpi_blur | 0.973 | 0.969 | 0.971 | 0.017 | 0.032 | 0.9 |
| easyocr | poor_100dpi_blur | 0.785 | 0.733 | 0.758 | 0.106 | 0.306 | 3.6 |
| rapidocr | awful_100dpi_jpeg20 | 0.966 | 0.929 | 0.947 | 0.039 | 0.075 | 0.8 |
| easyocr | awful_100dpi_jpeg20 | 0.457 | 0.423 | 0.439 | 0.229 | 0.625 | 3.8 |

## Takeaways (2026-07-02, 3 pages, CPU)

1. **RapidOCR wins every condition** on F1 *and* is 4–7× faster — it stays the
   pipeline default with measured justification, not vibes.
2. **Degradation is the differentiator.** On clean renders the engines are
   nearly tied (F1 0.982 vs 0.978); on heavily degraded input EasyOCR collapses
   (F1 0.439) while RapidOCR holds (0.947). Benchmarking only on clean data
   would have hidden this completely — the same argument behind the planned
   NoisyTab benchmark for semantic typing.
3. **CER tells the same story earlier:** EasyOCR's character errors are 13×
   RapidOCR's even on clean input (0.040 vs 0.003), foreshadowing the collapse.
4. **Escalation threshold implication:** RapidOCR F1 only drops below 0.95 at
   the `awful` condition — the orchestrator's low-confidence escalation
   (→ Chandra) is worth triggering only for genuinely bad scans.

Caveats: one document, English, machine-rendered degradation (not real scanner
noise), 3 pages. Next: add Tesseract + Chandra adapters, more documents, real
scanned ground truth (FUNSD/SROIE).

Reproduce: `python benchmarks/ocr/benchmark_ocr.py --pdf <digital.pdf>`
