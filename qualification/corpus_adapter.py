#!/usr/bin/env python3
"""M0-Q corpus adapter — turns a mounted benign corpus into probe page bundles.

BLOCKED until the operator mounts the corpus. Expected layout:

  <corpus-root>/
    <stratum>/<document>/page_NN.png|.tif|.jpg   (300-dpi-equivalent scans)
    <stratum>/<document>/page_NN.hocr            (tesseract hOCR, char boxes preferred)

Strata (QUALIFICATION §2): clean_text, receipts, statements, bills, historical,
books, decorative, japanese_h, japanese_v, degraded.

Document-level split isolation: the adapter emits document_manifest.json grouping by
document; split assignment stays with the qualification runner (60/20/20 per
QUALIFICATION §2). Holdout documents are marked and NEVER copied into dev bundles.

Usage (after mount):
  qualification/.venv/bin/python qualification/corpus_adapter.py --corpus <root> --out qualification/fixtures/corpus
Every page is bound via SWRASTER1 pixel-hash + file hash; hOCR is imported through the
same validator as all fixtures (typed layer + JSON-Schema layer apply unchanged).
"""
import argparse
import json
import os
import sys

STRATA = [
    "clean_text", "receipts", "statements", "bills", "historical",
    "books", "decorative", "japanese_h", "japanese_v", "degraded",
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpi", type=float, default=300.0)
    args = ap.parse_args()

    if not os.path.isdir(args.corpus):
        print(f"BLOCKED: corpus root {args.corpus} is not mounted")
        return 1

    manifest = {"documents": [], "strata_found": []}
    n_pages = 0
    for stratum in STRATA:
        sdir = os.path.join(args.corpus, stratum)
        if not os.path.isdir(sdir):
            continue
        manifest["strata_found"].append(stratum)
        for doc in sorted(os.listdir(sdir)):
            ddir = os.path.join(sdir, doc)
            if not os.path.isdir(ddir):
                continue
            pages = []
            for f in sorted(os.listdir(ddir)):
                if f.endswith((".png", ".tif", ".tiff", ".jpg")):
                    base = os.path.splitext(f)[0]
                    hocr = os.path.join(ddir, base + ".hocr")
                    pages.append(
                        {
                            "image": os.path.join(ddir, f),
                            "hocr": hocr if os.path.exists(hocr) else None,
                        }
                    )
            if pages:
                manifest["documents"].append(
                    {"stratum": stratum, "document": doc, "pages": pages}
                )
                n_pages += len(pages)

    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "document_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    print(
        f"manifest written: {len(manifest['documents'])} documents, {n_pages} pages, "
        f"strata={manifest['strata_found']}"
    )
    if len(manifest["documents"]) == 0:
        print("BLOCKED: no documents found under the expected strata layout")
        return 1
    print("NEXT: run tesseract -c hocr_char_boxes=1 hocr per page (missing .hocr), then")
    print("      probes/m0-font-pdf hocr2json per page, then checks.py/measure.py --pages.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
