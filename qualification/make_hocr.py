#!/usr/bin/env python3
"""Emit W3C hOCR (HTML + RDFa) from a scanweave normalized ocr.json fixture.

The scanweave CLI's foreign-OCR entry point is hOCR. The M1-A fixtures were
produced with tesseract's JSON output, so this script re-encodes the same
word boxes and labels as hOCR without re-running OCR (deterministic).
"""
import json
import sys
from pathlib import Path
from xml.sax.saxutils import escape


def to_hocr(ocr_json: Path, out_path: Path) -> None:
    d = json.loads(ocr_json.read_text())
    w, h = d["canonical_image"]["width"], d["canonical_image"]["height"]
    words = []
    for s in d["spans"]:
        words.append((s["polygon"], s["text"]))
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"',
        '  "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">',
        '<html xmlns="http://www.w3.org/1999/xhtml">',
        '  <head><meta http-equiv="Content-Type" content="text/html; charset=utf-8"/>'
        '<title>ScanWeave M1-A fixture</title></head>',
        '  <body>',
        f'    <div class=\'ocr_page\' title=\'bbox 0 0 {w} {h}\'>',
        '      <div class=\'ocr_carea\'>',
    ]
    for poly, text in words:
        xs = [p[0] for p in poly]
        ys = [p[1] for p in poly]
        bbox = f'bbox {min(xs):.0f} {min(ys):.0f} {max(xs):.0f} {max(ys):.0f}'
        lines.append(
            f"        <span class='ocrx_word' title='{bbox}; x_wconf 95'>{escape(text)}</span>"
        )
    lines += ["      </div>", "    </div>", "  </body>", "</html>", ""]
    out_path.write_text("\n".join(lines))


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: make_hocr.py <input.ocr.json> <out.hocr>", file=sys.stderr)
        return 2
    to_hocr(Path(sys.argv[1]), Path(sys.argv[2]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
