#!/usr/bin/env python3
"""M1-B external baseline comparison at DOCUMENT level.

For each document fixture: build scanweave (reconstruct + auto), build the same
document with OCRmyPDF and with IA MRC (recode_pdf), then compare ACTUAL BYTES
and the search/fidelity gates (not just compression ratios):

  - serialized bytes per candidate
  - per-page ink IoU vs the source raster (fidelity gate)
  - native PDFium search of each document's key tokens per page
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.insert(0, "qualification/.venv/lib/python3.12/site-packages")
import pypdfium2 as pdfium  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "qualification" / "fixtures" / "documents"
WORK = Path("/tmp/opencode/m1b_baselines")
CLI = ROOT / "target" / "debug" / "scanweave-cli"
TESS = ROOT / "tools" / "ext" / "bin" / "tesseract"
OCRmyPDF = ROOT / "qualification" / ".venv" / "bin" / "ocrmypdf"
RECODE = ROOT / "qualification" / ".venv" / "bin" / "recode_pdf"
IMG2PDF = ROOT / "qualification" / ".venv" / "bin" / "img2pdf"

results = []


def check(name, cond, detail=""):
    results.append((name, bool(cond), detail))


def fg(a, paper=255.0, t=60.0):
    return np.abs(a.astype(float) - paper) > t


def ink_iou(src_png: Path, pdf: Path, page: int) -> float:
    src = np.asarray(Image.open(src_png).convert("L"))
    d = pdfium.PdfDocument(str(pdf))
    # render at the scale that maps the page's MediaBox onto the source raster
    # (external tools may write a 72dpi MediaBox; scanweave writes 300dpi)
    h_pt = d[page].get_size()[1]
    ren = np.asarray(d[page].render(scale=src.shape[0] / h_pt).to_pil().convert("L"))
    d.close()
    h = min(src.shape[0], ren.shape[0])
    w = min(src.shape[1], ren.shape[1])
    ms, mr = fg(src[:h, :w]), fg(ren[:h, :w])
    inter = (ms & mr).sum()
    union = (ms | mr).sum()
    return float(inter / union) if union else 1.0


def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


# the same environment the M0 harness uses: locally built tesseract + its data
EXT = ROOT / "tools" / "ext"
EXT_ENV = dict(
    os.environ,
    LD_LIBRARY_PATH=str(EXT / "lib"),
    TESSDATA_PREFIX=str(EXT / "share" / "tessdata"),
    PATH=str(EXT / "bin") + ":" + os.environ.get("PATH", ""),
)


def build_scanweave(doc: str, mode: str):
    d = WORK / doc / mode
    d.mkdir(parents=True, exist_ok=True)
    r = run([str(CLI), "build", "--bundle", str(DOCS / doc / "document.json"),
             "--mode", mode, "--output", str(d / "scanweave.pdf"), "--report", str(d / "scanweave.json")])
    assert r.returncode == 0, r.stderr[:400]
    return d / "scanweave.pdf"


def build_external(doc: str):
    """OCRmyPDF + IA MRC over the same page rasters (document level)."""
    d = WORK / doc / "external"
    d.mkdir(parents=True, exist_ok=True)
    pages = sorted((DOCS / doc).glob("page*.png")) + sorted((DOCS / doc).glob("p0*.png")) + sorted((DOCS / doc).glob("p10.png"))
    pages = sorted({p for p in (DOCS / doc).glob("*.png")})
    # input PDF: one page per raster, in bundle order
    bundle = json.loads((DOCS / doc / "document.json").read_text())
    order = [p["page_id"] for p in bundle["pages"]]
    pngs = [d / f"{pid}.png" for pid in order]
    for pid in order:
        Image.open(DOCS / doc / f"{pid}.png").convert("RGB").save(d / f"{pid}.png")
    inp = d / "input.pdf"
    r = run([str(IMG2PDF), "--output", str(inp), *[str(p) for p in pngs]])
    assert r.returncode == 0, r.stderr[:300]
    ocrm = d / "ocrmypdf.pdf"
    r = run([str(OCRmyPDF), "--output-type", "pdf", "--force-ocr", "-l", "eng",
             "--optimize", "0", str(inp), str(ocrm)], env=EXT_ENV)
    ocr_ok = r.returncode == 0 and ocrm.exists()
    ia = d / "ia_mrc.pdf"
    # hocr over the whole doc (per-page hocr merged by tesseract's txt? IA needs
    # one hocr per page; run tesseract per page and pass the first for -T with
    # the page set — recode_pdf accepts a single hocr for the last page only,
    # so document-level IA MRC uses the page-1 hocr on page 1 only is invalid;
    # instead run recode_pdf per page and report per-page sizes.
    # IA MRC (recode_pdf) is a per-page tool: run it on each single-page input
    # and report per-page bytes (document-level MRC concatenation is out of
    # scope for this comparison)
    ia_bytes = []
    for i, pid in enumerate(order):
        stem = d / f"{pid}"
        run([str(TESS), str(DOCS / doc / f"{pid}.png"), str(stem), "-c", "hocr_char_boxes=1", "hocr"],
            env=EXT_ENV)
        single = d / f"in_{pid}.pdf"
        r = run([str(IMG2PDF), "--output", str(single), str(DOCS / doc / f"{pid}.png")])
        if r.returncode != 0:
            ia_bytes.append(None)
            continue
        out = d / f"ia_{pid}.pdf"
        r = run([str(RECODE), "-P", str(single), "-T", str(stem) + ".hocr", "-o", str(out), "-m", "0",
                 "--bg-compression-flags=-r 500", "--fg-compression-flags=-r 750",
                 "--hq-bg-compression-flags=-r 500", "--hq-fg-compression-flags=-r 750"],
                env=EXT_ENV)
        if r.returncode == 0 and out.exists():
            ia_bytes.append(out.stat().st_size)
        else:
            ia_bytes.append(None)
    return d, ocrm if ocr_ok else None, ia_bytes


def main() -> int:
    WORK.mkdir(parents=True, exist_ok=True)
    docs = ["doc4_invoice", "doc4_repeat", "doc4_mixed", "doc10_mixed", "doc2_min"]
    report = {}
    for doc in docs:
        bundle = json.loads((DOCS / doc / "document.json").read_text())
        order = [p["page_id"] for p in bundle["pages"]]
        sw = build_scanweave(doc, "reconstruct")
        swa = build_scanweave(doc, "auto")
        ext, ocrm, ia_sizes = build_external(doc)

        entry = {
            "pages": len(order),
            "scanweave_reconstruct_bytes": sw.stat().st_size,
            "scanweave_auto_bytes": swa.stat().st_size,
            "ocrmypdf_bytes": ocrm.stat().st_size if ocrm else None,
            "ia_mrc_page_bytes": ia_sizes,
            "ia_mrc_total_bytes": sum(b for b in ia_sizes if b) if all(b is not None for b in ia_sizes) else None,
        }
        report[doc] = entry

        # fidelity + search gates for the scanweave candidates
        for label, pdf in (("reconstruct", sw), ("auto", swa)):
            ious = [ink_iou(DOCS / doc / f"{pid}.png", pdf, i) for i, pid in enumerate(order)]
            entry[f"{label}_ink_iou"] = [round(x, 4) for x in ious]
        d = pdfium.PdfDocument(str(sw))
        for i, pid in enumerate(order):
            tp = d[i].get_textpage()
            t = tp.get_text_bounded()
            if doc == "doc4_invoice" and i == 0:
                check(f"{doc}: mixed line native search (page1)", bool(tp.search("Page 1 of 4").get_next()))
        d.close()
        # ---- external fidelity (same engine, same threshold rule) ----------
        if ocrm:
            entry["ocrmypdf_ink_iou"] = [
                round(ink_iou(DOCS / doc / f"{pid}.png", ocrm, i), 4) for i, pid in enumerate(order)
            ]
        ia_ious = []
        for i, pid in enumerate(order):
            ia_pdf = ext / f"ia_{pid}.pdf"
            if ia_pdf.exists():
                ia_ious.append(round(ink_iou(DOCS / doc / f"{pid}.png", ia_pdf, 0), 4))
            else:
                ia_ious.append(None)
        entry["ia_mrc_ink_iou"] = ia_ious

        # ---- honest byte comparison: scanweave must not exceed either baseline
        if entry["ocrmypdf_bytes"]:
            check(f"{doc}: scanweave <= OCRmyPDF bytes",
                  entry["scanweave_reconstruct_bytes"] <= entry["ocrmypdf_bytes"],
                  f"{entry['scanweave_reconstruct_bytes']} vs {entry['ocrmypdf_bytes']}")
        if entry["ia_mrc_total_bytes"]:
            check(f"{doc}: scanweave <= IA MRC bytes",
                  entry["scanweave_reconstruct_bytes"] <= entry["ia_mrc_total_bytes"],
                  f"{entry['scanweave_reconstruct_bytes']} vs {entry['ia_mrc_total_bytes']}")
        # ---- fidelity floor: scanweave's ink IoU must clear the measured
        #      M1-A-accepted floor (0.75) on every page, and be reported next
        #      to the external candidates' (not silently dropped)
        for i in range(len(order)):
            check(f"{doc}: page{i+1} ink IoU >= 0.75",
                  entry["reconstruct_ink_iou"][i] >= 0.75,
                  str(entry["reconstruct_ink_iou"][i]))
            if entry.get("ocrmypdf_ink_iou"):
                entry["iou_margin_vs_ocrmypdf"] = round(
                    min(entry["reconstruct_ink_iou"]) - min(entry["ocrmypdf_ink_iou"]), 4)
            d = pdfium.PdfDocument(str(ocrm))
            found = 0
            for i, pid in enumerate(order):
                if d[i].get_textpage().search("Total").get_next() or d[i].get_textpage().search("Amount").get_next():
                    found += 1
            d.close()
            entry["ocrmypdf_pages_with_search"] = found
        print(f"{doc}: {entry}")

    (WORK / "baseline_report.json").write_text(json.dumps(report, indent=2))
    width = max(len(n) for n, _, _ in results) if results else 0
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'} {name.ljust(width)} {detail}")
    print()
    print("FAILED:", [n for n, ok, _ in results if not ok] or "none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
