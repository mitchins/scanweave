#!/usr/bin/env python3
"""Build M1-B document fixtures: 2-, 4- and 10-page hash-verified bundles
composing the already-qualified single-page fixtures (same rasters and OCR the
M0/M1-A gates measure, so document results are traceable to page results).

Produced under qualification/fixtures/documents/:
  doc4_invoice/     the four p10_multipage pages as one document (mixed line:
                    page1 carries the raster-fallback numeral "Page 1 of 4")
  doc4_repeat/      four identical statement pages (font-sharing test)
  doc4_mixed/       statement + noisy + decorative + statement (mixed
                    dispositions: vector, full-raster fallback, artwork)
  doc10_mixed/      10 pages: statement, invoice, receipt-style, kana ...
  doc2_min/         2-page minimal bundle (order + dimensions)

Each bundle directory holds the copied page rasters, the normalized
<page>.ocr.json files, and document.json (bundle contract: per-page
source/OCR sha256 pairing).
"""
import hashlib
import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIX = ROOT / "qualification" / "fixtures"
PROBE = FIX / "probe"
DOCS = FIX / "documents"


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def emit(doc_dir: Path, page_id: str, src_png: Path, src_ocr: Path) -> dict:
    dst_png = doc_dir / f"{page_id}.png"
    dst_ocr = doc_dir / f"{page_id}.ocr.json"
    shutil.copy(src_png, dst_png)
    # the OCR page's own page_id must equal the bundle page id (pairing rule);
    # only that field is rewritten, all spans/boxes are the source fixture's
    doc = json.loads(src_ocr.read_text())
    doc["page_id"] = page_id
    dst_ocr.write_text(json.dumps(doc, indent=2) + "\n")
    return {"page_id": page_id, "png": dst_png, "ocr": dst_ocr}


def bundle(doc_dir: Path, document_id: str, pages: list[dict]) -> None:
    sources = [
        {
            "source_id": f"src{i:03d}",
            "asset_path": p["png"].name,
            "file_sha256": sha256_file(p["png"]),
            "kind": "image",
        }
        for i, p in enumerate(pages)
    ]
    doc = {
        "schema_version": "1.0",
        "document_id": document_id,
        "sources": sources,
        "pages": [
            {
                "page_id": p["page_id"],
                "source_id": f"src{i:03d}",
                "source_page_index": 0,
                "ocr_page_path": p["ocr"].name,
                "ocr_page_sha256": sha256_file(p["ocr"]),
            }
            for i, p in enumerate(pages)
        ],
    }
    (doc_dir / "document.json").write_text(json.dumps(doc, indent=2) + "\n")


def build(name: str, document_id: str, specs: list[tuple[str, Path, Path]]) -> Path:
    doc_dir = DOCS / name
    if doc_dir.exists():
        shutil.rmtree(doc_dir)
    doc_dir.mkdir(parents=True)
    pages = [emit(doc_dir, pid, png, ocr) for pid, png, ocr in specs]
    bundle(doc_dir, document_id, pages)
    print(f"{name}: {len(pages)} pages -> {doc_dir.relative_to(ROOT)}")
    return doc_dir


def p(name: str) -> tuple[Path, Path]:
    d = PROBE / name
    png = d / f"{name}.png"
    ocr = d / f"{name}.ocr.json"
    assert png.exists() and ocr.exists(), (png, ocr)
    return png, ocr


def p10(n: int) -> tuple[Path, Path]:
    d = PROBE / "p10_multipage" / f"page{n}"
    stem = f"p10_page{n}"
    png = d / f"{stem}.png"
    ocr = d / f"{stem}.ocr.json"
    assert png.exists() and ocr.exists(), (png, ocr)
    return png, ocr


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    stmt = p("p16_statement")
    noisy = p("p14_noisy")
    deco = p("p15_decorative")
    kana = p("p03_kana")

    build("doc2_min", "doc2-min", [("page1", *stmt), ("page2", *noisy)])
    build("doc4_invoice", "doc4-invoice",
          [("page1", *p10(1)), ("page2", *p10(2)), ("page3", *p10(3)), ("page4", *p10(4))])
    build("doc4_repeat", "doc4-repeat",
          [("page1", *stmt), ("page2", *stmt), ("page3", *stmt), ("page4", *stmt)])
    build("doc4_mixed", "doc4-mixed",
          [("page1", *stmt), ("page2", *noisy), ("page3", *deco), ("page4", *stmt)])
    build("doc10_mixed", "doc10-mixed",
          [("p01", *stmt), ("p02", *p10(1)), ("p03", *noisy), ("p04", *stmt),
           ("p05", *deco), ("p06", *stmt), ("p07", *p10(2)), ("p08", *kana),
           ("p09", *noisy), ("p10", *stmt)])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
