#!/usr/bin/env python3
"""M1-B N1 experiments: mixed visible/invisible line search in PDFium + Poppler.

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
        "BT /F1 11 Tf",
        "/Span <</ActualText <FEFF0050006100670065002000310020006F006600200034002E> >> BDC",
        "1 0 0 1 72 700 Tm (Page) Tj",
        "3 Tr",
        "1 0 0 1 116 700 Tm (1) Tj",
        "0 Tr",
        "1 0 0 1 130 700 Tm (of) Tj",
        "1 0 0 1 190 700 Tm (4.) Tj",
        "EMC",
        "ET",
    ]
    return ("\n".join(c)).encode()


def content_v2() -> bytes:
    # line-level ActualText, but the owner run is visible (control for V1)
    c = [
        "BT /F1 11 Tf",
        "/Span <</ActualText <FEFF0050006100670065002000310020006F006600200034002E> >> BDC",
        "1 0 0 1 72 700 Tm (Page) Tj",
        "1 0 0 1 116 700 Tm (1) Tj",
        "1 0 0 1 130 700 Tm (of) Tj",
        "1 0 0 1 190 700 Tm (4.) Tj",
        "EMC",
        "ET",
    ]
    return ("\n".join(c)).encode()


def content_v3() -> bytes:
    c = []
    for t, x in ((b"Page", 72), (b"1", 116), (b"of", 130), (b"4.", 190)):
        c.append(f"BT /F1 11 Tf 1 0 0 1 {x} 700 Tm ({t.decode()}) Tj ET")
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
    with tempfile.TemporaryDirectory(dir="/tmp/opencode") as td:
        workdir = Path(td)
        results = []
        for name, content in (
            ("V0_shipped", content_v0()),
            ("V1_line_actualtext", content_v1()),
            ("V2_line_actualtext_visible_owner", content_v2()),
            ("V3_plain_visible", content_v3()),
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
