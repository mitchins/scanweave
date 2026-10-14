#!/usr/bin/env python3
"""M0-Q final correction A — PDF text search verification.

Required gate: 'Total', '1,234.56', 'INV-2026-0042' must succeed through
PDFium on the committed p09 fixture; both extractors must preserve intact
financial identifiers and recognizable OCR words without intra-word whitespace;
character transport stays exact and non-duplicated.

Also covers: decimal points, negative amounts (p08 '-42'), invoice references,
ligatures (p04 'fi'), kana (p03 'ガ'), supplementary-plane (p04 '𝐀'), and a
regression guard against the per-glyph-space defect ('T o t a l').

RED before the repair (recorded): raw PDFium extraction was
'Tota l a m o u nt d u e : 1 , 2 3 4 . 5 6 EU R...' and all three queries missed.

Run: qualification/.venv/bin/python qualification/test_text_search.py
"""
import json
import os
import subprocess
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FIX = os.path.join(HERE, "fixtures", "probe")
WORK = os.path.join(ROOT, "work", "m0-search")
PROBE = os.path.join(ROOT, "target", "debug", "m0-font-pdf")
QPDF = os.path.join(ROOT, "tools", "dist", "bin", "qpdf")

sys.path.insert(0, os.path.join(HERE, ".venv", "lib", "python3.12", "site-packages"))
import pypdfium2 as pdfium  # noqa: E402

failures = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        failures.append(name)


def build(page):
    """page = page stem; the probe requires --page <directory containing
    <stem>.png + <stem>.ocr.json>."""
    d = os.path.join(WORK, page.replace("/", "_"))
    os.makedirs(d, exist_ok=True)
    full = os.path.join(FIX, page)
    if os.path.isdir(full):
        srcdir = full          # page names its own directory; the probe pairs the
    else:                       # unique png/ocr.json inside it
        srcdir = os.path.dirname(full)
    r = subprocess.run([PROBE, "build", "--page", srcdir, "--out", d],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stderr[:300]
    return os.path.join(d, "out.pdf"), os.path.join(d, "b0_raster.pdf")


def pdfium_text(pdf):
    doc = pdfium.PdfDocument(pdf)
    t = doc[0].get_textpage().get_text_bounded()
    doc.close()
    return t


def poppler_text(pdf):
    return subprocess.run(["pdftotext", pdf, "-"], capture_output=True, text=True).stdout


def has_intra_word_spaces(text: str) -> bool:
    """The per-glyph-space defect signature: runs of >=3 single-character
    whitespace-separated tokens (e.g. 'T o t a l', '1 , 2 3 4')."""
    toks = text.split()
    run = 0
    for t in toks:
        if len(t) == 1 and not t.isspace():
            run += 1
            if run >= 3:
                return True
        else:
            run = 0
    return False


def main() -> int:
    os.makedirs(WORK, exist_ok=True)

    # ---- required gate: p09 search through PDFium ----
    b2, b0 = build("p09_realtext")
    pt = pdfium_text(b2)
    pt_b0 = pdfium_text(b0)
    qt = poppler_text(b2)
    for q in ("Total", "1,234.56", "INV-2026-0042"):
        check(f"pdfium B2 search {q!r}", q in pt)
        check(f"pdfium B0 search {q!r}", q in pt_b0)
        check(f"poppler B2 text {q!r}", q in qt)

    # intact words / no intra-word whitespace (both engines, B2 and B0)
    check("pdfium B2 no intra-word spaces", not has_intra_word_spaces(pt), repr(pt[:60]))
    check("pdfium B0 no intra-word spaces", not has_intra_word_spaces(pt_b0))
    check("poppler B2 no intra-word spaces", not has_intra_word_spaces(qt))

    # character transport remains exact and non-duplicated (supplementary)
    ocr = json.load(open(os.path.join(FIX, "p09_realtext", "p09_realtext.ocr.json")))
    expected = "".join(s["text"] for s in ocr["spans"])
    stripped = "".join(pt.split())
    check("pdfium B2 exact char transport", stripped == expected, f"{len(stripped)} chars")

    # ---- extended assertions: decimals, negatives, refs, ligatures, kana ----
    b2_08, _ = build("p08_symbols")
    t08 = pdfium_text(b2_08)
    check("p08 pdfium intact '1,234.56'", "1,234.56" in t08, repr(t08[:80]))
    check("p08 pdfium intact '-42'", "-42" in t08)
    check("p08 no intra-word spaces", not has_intra_word_spaces(t08))

    b2_04, _ = build("p04_ligature")
    t04 = pdfium_text(b2_04)
    check("p04 pdfium ligature 'fi'", "fi" in "".join(t04.split()))
    check("p04 pdfium supplementary U+1D400", "𝐀" in t04)

    b2_03, _ = build("p03_kana")
    t03 = pdfium_text(b2_03)
    check("p03 pdfium kana 'ガ' intact", "ガ" in t03)

    for n in range(1, 5):
        b2_10, b0_10 = build(f"p10_multipage/page{n}/p10_page{n}")
        t10 = pdfium_text(b2_10)
        check(f"p10 page{n} pdfium '1,234.56'", "1,234.56" in t10)
        check(f"p10 page{n} pdfium 'Page {n} of 4'", f"Page {n} of 4" in t10, repr(t10[:60]))

    # qpdf structural sanity on the repaired artifacts
    env = dict(os.environ, LD_LIBRARY_PATH=os.path.join(ROOT, "tools", "dist", "lib"))
    r = subprocess.run([QPDF, "--check", b2], capture_output=True, text=True, env=env)
    check("qpdf --check repaired p09", r.returncode == 0)

    if failures:
        print(f"\nFAILED: {failures}")
        return 1
    print("\nall PDF text-search assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
