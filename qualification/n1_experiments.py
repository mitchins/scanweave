#!/usr/bin/env python3
"""M1-B N1 mechanism experiments: mixed visible/invisible line search.

SCOPE (stated honestly): these variants isolate PDF-LEVEL mechanisms — mark
granularity, rendering mode, inline-vs-last emission, baseline placement — on
a synthetic one-line page with a Type1 font. They do NOT reproduce the real
failure: the real page uses a CID font whose owner CID references the empty
placeholder glyph at the span's box height, and the real-page A/B is the
discriminating evidence (M1-A build at 650dafa: native search False, owner
label appended after the page's last line; M1-B build: native search True with
pixel-identical rendering — asserted permanently by
test_m1b_paint_fidelity.py).

Builds a one-line page reproducing the p10 page1 failure geometry: three
VISIBLE text runs ("Page", "of", "4.") plus one RASTER-FALLBACK span ("1")
whose owner text can only ride the text layer invisibly, and compares four
mark-content strategies:

  V0  M1-A shipped: per-span /ActualText on the visible runs; the fallback
      owner as a bare invisible run emitted last in content order.
  V1  LINE-level /ActualText enclosing every run of the line (visible + owner)
      in reading order; ActualText carries the OCR line text verbatim (with
      the OCR's own separators — no invented whitespace).
  V2  line-level /ActualText where the owner run is drawn VISIBLE at the span
      position (glyph-substituted label; tests whether visibility alone fixes
      ordering even with a single owner run inside one line mark).
  V3  unified visible runs only (no ActualText, ordinary per-run ToUnicode
      text) — control: the exact text the extractors would see if the label
      were a normal visible span.

Each variant is checked with:
  - PDFium native search (FPDFText_FindStart) for "Page 1 of 4"
  - PDFium bounded extraction
  - Poppler pdftotext extraction
"""
import subprocess
import sys
import tempfile
from pathlib import Path

PAGE_TEXT_START = 'BT /F1 11 Tf'
PAGE_LABEL = '1 0 0 1 72 700 Tm (Page) Tj'
PAGE_NUMBER_ONE = '1 0 0 1 116 700 Tm (1) Tj'
PAGE_OF = '1 0 0 1 130 700 Tm (of) Tj'
PAGE_COUNT = '1 0 0 1 190 700 Tm (4.) Tj'


sys.path.insert(0, "qualification/.venv/lib/python3.12/site-packages")
import pypdfium2 as pdfium  # noqa: E402

Q = "Page 1 of 4"


def content_v0() -> bytes:
    c = []
    c.append("BT /F1 11 Tf 1 0 0 1 72 700 Tm (Page) Tj ET")
    c.append("BT /F1 11 Tf 1 0 0 1 130 700 Tm (of) Tj ET")
    c.append("BT /F1 11 Tf 1 0 0 1 190 700 Tm (4.) Tj ET")
    # fallback owner: invisible, last in content order (M1-A shipped shape)
    c.append("BT /F1 11 Tf 3 Tr 1 0 0 1 116 700 Tm (1) Tj ET")
    return ("\n".join(c)).encode()


def content_v1() -> bytes:
    # one line-level ActualText enclosing all runs, in reading order
    c = [
        PAGE_TEXT_START,
        "/Span <</ActualText <FEFF0050006100670065002000310020006F006600200034002E> >> BDC",
        PAGE_LABEL,
        "3 Tr",
        PAGE_NUMBER_ONE,
        "0 Tr",
        PAGE_OF,
        PAGE_COUNT,
        "EMC",
        "ET",
    ]
    return ("\n".join(c)).encode()


def content_v2() -> bytes:
    # line-level ActualText, but the owner run is visible (control for V1)
    c = [
        PAGE_TEXT_START,
        "/Span <</ActualText <FEFF0050006100670065002000310020006F006600200034002E> >> BDC",
        PAGE_LABEL,
        PAGE_NUMBER_ONE,
        PAGE_OF,
        PAGE_COUNT,
        "EMC",
        "ET",
    ]
    return ("\n".join(c)).encode()


def content_v3() -> bytes:
    c = []
    for t, x in ((b"Page", 72), (b"1", 116), (b"of", 130), (b"4.", 190)):
        c.append(f"BT /F1 11 Tf 1 0 0 1 {x} 700 Tm ({t.decode()}) Tj ET")
    return ("\n".join(c)).encode()


def _mark(text: str) -> str:
    """per-span /ActualText mark, as the shipped assembler emits for every span"""
    utf16 = "".join(f"{ord(c):04X}" for c in text)
    return f"/Span <</ActualText <FEFF{utf16}>> >> BDC"


def content_v4_off_baseline() -> bytes:
    """M1-A geometry: the owner run sits on the OCR POLYGON-BOX bottom, which
    is ~1pt BELOW the visible line's glyph-ink baseline (as on the real page:
    span box [143,299,161,341] → y_bot = page_h - 341*dpi-scale while the
    visible glyph baseline sits at the ink bottom). Invisible run, emitted last
    — exactly the M1-A content shape."""
    c = [PAGE_TEXT_START]
    c.append(_mark("Page"))
    c.append(PAGE_LABEL)
    c.append("EMC")
    c.append(_mark("of"))
    c.append(PAGE_OF)
    c.append("EMC")
    c.append(_mark("4."))
    c.append(PAGE_COUNT)
    c.append("EMC")
    # owner: invisible, emitted LAST, on the polygon-box baseline (1pt below
    # the visible line) — the M1-A content shape
    c.append(_mark("1"))
    c.append("3 Tr")
    c.append("1 0 0 1 116 699 Tm (1) Tj")
    c.append("0 Tr")
    c.append("EMC")
    c.append("ET")
    return ("\n".join(c)).encode()


def content_v5_ink_baseline() -> bytes:
    """Shipped M1-B geometry: owner run invisible, INLINE in reading order, on
    the span's traced INK baseline (exactly the visible line's baseline)."""
    c = [PAGE_TEXT_START]
    c.append(_mark("Page"))
    c.append(PAGE_LABEL)
    c.append("EMC")
    # owner: invisible, INLINE in reading order, on the line's baseline
    c.append(_mark("1"))
    c.append("3 Tr")
    c.append(PAGE_NUMBER_ONE)
    c.append("0 Tr")
    c.append("EMC")
    c.append(_mark("of"))
    c.append(PAGE_OF)
    c.append("EMC")
    c.append(_mark("4."))
    c.append(PAGE_COUNT)
    c.append("EMC")
    c.append("ET")
    return ("\n".join(c)).encode()


def build_pdf(content: bytes) -> bytes:
    objs = []
    objs.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objs.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")
    objs.append(
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
        b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>"
    )
    objs.append(b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream")
    objs.append(
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
    )
    out = bytearray(b"%PDF-1.7\n")
    offsets = []
    for i, body in enumerate(objs, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + body + b"\nendobj\n"
    xref = len(out)
    out += f"xref\n0 {len(objs)+1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objs)+1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n"
    ).encode()
    return bytes(out)


def evaluate(name: str, content: bytes, workdir: Path) -> dict:
    pdf = workdir / f"{name}.pdf"
    pdf.write_bytes(build_pdf(content))
    d = pdfium.PdfDocument(str(pdf))
    tp = d[0].get_textpage()
    text = tp.get_text_bounded()
    native = bool(tp.search(Q).get_next())
    found = Q in text
    d.close()
    poppler = subprocess.run(
        ["pdftotext", str(pdf), "-"], capture_output=True, text=True
    ).stdout.strip()
    return {
        "variant": name,
        "pdfium_native": native,
        "pdfium_contains": found,
        "pdfium_text": text.replace("\r", "\\r").replace("\n", "\\n"),
        "poppler_contains": Q in poppler,
        "poppler_text": poppler.replace("\n", "\\n"),
    }


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="scanweave-n1-") as td:
        workdir = Path(td)
        results = []
        for name, content in (
            ("V0_m1a_geometry_off_baseline", content_v4_off_baseline()),
            ("V1_line_actualtext", content_v1()),
            ("V2_line_actualtext_visible_owner", content_v2()),
            ("V3_plain_visible", content_v3()),
            ("V4_m1b_shipped_ink_baseline", content_v5_ink_baseline()),
        ):
            results.append(evaluate(name, content, workdir))
    width = max(len(r["variant"]) for r in results)
    print(f"{'variant'.ljust(width)} | pdfium native | pdfium contains | poppler contains")
    for r in results:
        print(
            f"{r['variant'].ljust(width)} | "
            f"{'PASS' if r['pdfium_native'] else 'FAIL':^13} | "
            f"{'PASS' if r['pdfium_contains'] else 'FAIL':^15} | "
            f"{'PASS' if r['poppler_contains'] else 'FAIL'}"
        )
    print()
    for r in results:
        print(f"{r['variant']}:")
        print(f"  pdfium : {r['pdfium_text']}")
        print(f"  poppler: {r['poppler_text']}")
    winners = [r["variant"] for r in results if r["pdfium_native"] and r["poppler_contains"]]
    print()
    print("variants passing native search + poppler:", winners or "NONE")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
