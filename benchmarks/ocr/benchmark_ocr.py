"""OCR engine comparison benchmark.

Ground truth comes for free: digital PDFs carry a text layer. We render their
pages to images at several degradation levels (simulating scan quality), run
each OCR engine on the images, and score the output against the text layer.

Metrics per (engine, condition):
  - CER / WER          — character/word error rate (order-sensitive, jiwer)
  - word P / R / F1    — bag-of-words precision/recall (order-insensitive,
                         fairer when engines disagree only on reading order)
  - seconds/page       — wall-clock speed

Usage:
    python benchmarks/ocr/benchmark_ocr.py --pdf path/to/digital.pdf --pages 3

Extending: subclass OcrAdapter, add to ADAPTERS. Tesseract/PaddleOCR/Chandra
slot in the same way.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import jiwer
import numpy as np
from PIL import Image, ImageFilter

# ---------------------------------------------------------------- conditions


@dataclass
class Condition:
    name: str
    scale: float  # pdfium render scale (1.0 ~ 72 dpi)
    blur: float = 0.0  # gaussian radius
    jpeg_q: int | None = None  # re-encode quality, None = lossless

    def apply(self, page) -> Image.Image:
        img = page.render(scale=self.scale).to_pil().convert("RGB")
        if self.blur:
            img = img.filter(ImageFilter.GaussianBlur(self.blur))
        if self.jpeg_q is not None:
            buf = io.BytesIO()
            img.save(buf, "JPEG", quality=self.jpeg_q)
            img = Image.open(buf).convert("RGB")
        return img


CONDITIONS = [
    Condition("clean_300dpi", scale=300 / 72),
    Condition("fax_150dpi", scale=150 / 72),
    Condition("poor_100dpi_blur", scale=100 / 72, blur=1.0),
    Condition("awful_100dpi_jpeg20", scale=100 / 72, blur=0.8, jpeg_q=20),
]

# ------------------------------------------------------------------ adapters


class OcrAdapter:
    name = "base"

    def read(self, img: Image.Image) -> str:  # pragma: no cover - interface
        raise NotImplementedError


class RapidOcrAdapter(OcrAdapter):
    """RapidOCR (PP-OCR models on onnxruntime) — Docling's default OCR."""

    name = "rapidocr"

    def __init__(self):
        from rapidocr import RapidOCR

        self.engine = RapidOCR()

    def read(self, img: Image.Image) -> str:
        result = self.engine(np.array(img))
        texts = getattr(result, "txts", None)
        if texts is None:  # older tuple API: (list[[box, text, conf]], elapse)
            items = result[0] or []
            texts = [it[1] for it in items]
        return " ".join(texts or [])


class EasyOcrAdapter(OcrAdapter):
    """EasyOCR (CRAFT detector + CRNN recognizer, PyTorch)."""

    name = "easyocr"

    def __init__(self):
        import easyocr

        self.engine = easyocr.Reader(["en"], verbose=False)

    def read(self, img: Image.Image) -> str:
        return " ".join(self.engine.readtext(np.array(img), detail=0))


ADAPTERS = [RapidOcrAdapter, EasyOcrAdapter]

# ------------------------------------------------------------------- scoring

_norm_ws = re.compile(r"\s+")


def normalize(text: str) -> str:
    """Lowercase, collapse whitespace, strip punctuation glued to words."""
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    return _norm_ws.sub(" ", text).strip()


def word_prf(truth: str, hyp: str) -> tuple[float, float, float]:
    """Order-insensitive bag-of-words precision/recall/F1."""
    t, h = Counter(truth.split()), Counter(hyp.split())
    overlap = sum((t & h).values())
    p = overlap / max(sum(h.values()), 1)
    r = overlap / max(sum(t.values()), 1)
    f1 = 2 * p * r / max(p + r, 1e-9)
    return p, r, f1


def score(truth: str, hyp: str) -> dict:
    truth_n, hyp_n = normalize(truth), normalize(hyp)
    p, r, f1 = word_prf(truth_n, hyp_n)
    return {
        "cer": round(jiwer.cer(truth_n, hyp_n or " "), 4),
        "wer": round(jiwer.wer(truth_n, hyp_n or " "), 4),
        "precision": round(p, 4),
        "recall": round(r, 4),
        "f1": round(f1, 4),
    }


# -------------------------------------------------------------------- runner


def run(pdf_path: Path, n_pages: int, out_dir: Path) -> dict:
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(str(pdf_path))
    n_pages = min(n_pages, len(pdf))

    truths = []
    for i in range(n_pages):
        tp = pdf[i].get_textpage()
        truths.append(tp.get_text_bounded())
        tp.close()

    adapters = []
    for cls in ADAPTERS:
        try:
            adapters.append(cls())
        except Exception as e:  # engine not installed — skip, don't fail
            print(f"[skip] {cls.name}: {e}")

    results = []
    for cond in CONDITIONS:
        images = [cond.apply(pdf[i]) for i in range(n_pages)]
        for adapter in adapters:
            t0 = time.perf_counter()
            hyps = [adapter.read(img) for img in images]
            elapsed = time.perf_counter() - t0
            agg = score(" ".join(truths), " ".join(hyps))
            agg.update(
                engine=adapter.name,
                condition=cond.name,
                sec_per_page=round(elapsed / n_pages, 2),
                n_pages=n_pages,
            )
            results.append(agg)
            print(
                f"{adapter.name:10s} {cond.name:22s} "
                f"F1={agg['f1']:.3f} CER={agg['cer']:.3f} "
                f"{agg['sec_per_page']:.1f}s/page"
            )
    pdf.close()

    payload = {"pdf": str(pdf_path), "results": results}
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "results.json").write_text(json.dumps(payload, indent=2))
    write_markdown(payload, out_dir / "RESULTS.md")
    return payload


def write_markdown(payload: dict, path: Path) -> None:
    lines = [
        "# OCR engine benchmark results",
        "",
        f"Document: `{Path(payload['pdf']).name}` — ground truth from the PDF text layer.",
        "Conditions simulate scan degradation. Metrics: order-insensitive word",
        "precision/recall/F1, plus order-sensitive CER/WER (jiwer).",
        "",
        "| engine | condition | precision | recall | F1 | CER | WER | s/page |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for r in payload["results"]:
        lines.append(
            f"| {r['engine']} | {r['condition']} | {r['precision']:.3f} "
            f"| {r['recall']:.3f} | {r['f1']:.3f} | {r['cer']:.3f} "
            f"| {r['wer']:.3f} | {r['sec_per_page']:.1f} |"
        )
    lines += [
        "",
        "Reproduce: `python benchmarks/ocr/benchmark_ocr.py --pdf <digital.pdf>`",
        "",
    ]
    path.write_text("\n".join(lines), encoding="utf-8")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True, type=Path)
    ap.add_argument("--pages", type=int, default=3)
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = ap.parse_args()
    run(args.pdf, args.pages, args.out)
