#!/usr/bin/env python3
"""M0 baseline measurements (WP-F): B0 searchable raster vs B2 reconstruction
vs source, byte breakdowns, ratios, and bounded external-baseline attempts.

Usage: qualification/.venv/bin/python qualification/measure.py
Writes qualification/measurements.json. Bounded M0 scope: no advantage claimed.
"""
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
PROBE = os.path.join(ROOT, "target", "debug", "m0-font-pdf")
FIXTURES = os.path.join(HERE, "fixtures", "probe")
WORK = os.path.join(ROOT, "work", "m0-measure")
from tools_env import qpdf_bin, qpdf_env, version  # noqa: E402


def QPDF() -> str:
    return qpdf_bin()

sys.path.insert(0, os.path.join(HERE, ".venv", "lib", "python3.12", "site-packages"))
import pypdfium2 as pdfium  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

PAGES = [
    "p01_latin",
    "p02_wronglabel",
    "p03_kana",
    "p04_ligature",
    "p05_colour",
    "p06_degraded",
    "p07_sharedcid",
]

EXPECTED = {
    "p01_latin": "868a",
    "p02_wronglabel": "6",
    "p03_kana": "ガ",
    "p04_ligature": "fi𝐀",
    "p05_colour": "8",
    "p06_degraded": "8",
    "p07_sharedcid": "86818",
}


def sh(cmd, env=None):
    return subprocess.run(cmd, capture_output=True, text=True, env=env)


def run_external(cmd, out_path, env=None, label="") -> None:
    """Run an external baseline command FAIL-CLOSED: prior outputs are removed
    first (no stale reuse) and a missing/failed artifact aborts with a precise
    reason instead of being silently skipped or implicitly reported as smaller."""
    if os.path.exists(out_path):
        os.remove(out_path)
    r = sh(cmd, env=env)
    if r.returncode != 0 or not os.path.exists(out_path):
        raise RuntimeError(
            f"external baseline {label} failed (rc={r.returncode}) or produced no output: "
            f"{(r.stdout + r.stderr).strip()[-300:]}"
        )


def extract_pdfium(pdf):
    doc = pdfium.PdfDocument(pdf)
    t = doc[0].get_textpage().get_text_bounded()
    doc.close()
    return t


def render_gray(pdf, scale=300 / 72.0):
    doc = pdfium.PdfDocument(pdf)
    pil = doc[0].render(scale=scale).to_pil().convert("L")
    doc.close()
    return np.asarray(pil)


def main() -> int:
    os.makedirs(WORK, exist_ok=True)
    env = qpdf_env()
    out = {"pages": {}, "external_baselines": {}}

    # --- External baselines: executed with the pinned source-built tools ---
    # (M0-Q repair B4: this section previously hard-coded BLOCKED; the tools are
    # now built and the runs are real. Settings recorded per QUALIFICATION §3.)
    ext = os.path.join(ROOT, "tools", "ext")
    venv_bin = os.path.join(HERE, ".venv", "bin")
    tess_bin = os.path.join(ext, "bin", "tesseract")
    recode = os.path.join(venv_bin, "recode_pdf")
    ocrmypdf_bin = os.path.join(venv_bin, "ocrmypdf")
    ext_env = dict(
        os.environ,
        LD_LIBRARY_PATH=os.path.join(ext, "lib"),
        TESSDATA_PREFIX=os.path.join(ext, "share", "tessdata"),
        PATH=os.path.join(ext, "bin") + ":" + os.environ.get("PATH", ""),
    )
    out["external_baselines"] = {
        "tesseract": sh([tess_bin, "--version"], env=ext_env).stdout.splitlines()[:1],
        "ocrmypdf": sh([ocrmypdf_bin, "--version"], env=ext_env).stdout.strip(),
        "ia_recode_pdf": "archive-pdf-tools 1.5.7 @ 8fe8b5b7 + recorded PyMuPDF compat shim (see LEDGER.md)",
    }

    # --- Real-page external comparison (p09: real tesseract OCR text page) ---
    p09_dir = os.path.join(FIXTURES, "p09_realtext")
    if os.path.isdir(p09_dir):
        d = os.path.join(WORK, "p09_realtext")
        os.makedirs(d, exist_ok=True)
        r = sh([PROBE, "build", "--page", p09_dir, "--out", d])
        p09 = {"probe_rc": r.returncode}
        png = os.path.join(p09_dir, "p09_realtext.png")
        p09["source_png"] = os.path.getsize(png)
        for label, f in (("B2", "out.pdf"), ("B0", "b0_raster.pdf")):
            p09[label] = os.path.getsize(os.path.join(d, f))
        # external: make a 1-page PDF input, run ocrmypdf + ia recode_pdf
        from PIL import Image as PILImage
        PILImage.open(png).convert("RGB").save(os.path.join(d, "input.pdf"), "PDF", resolution=300.0)
        hocr = os.path.join(d, "tess.hocr")
        sh([tess_bin, png, hocr[:-5], "-c", "hocr_char_boxes=1", "hocr"], env=ext_env)
        q = sh([ocrmypdf_bin, "--output-type", "pdf", "--force-ocr", "-l", "eng",
                "--optimize", "0", os.path.join(d, "input.pdf"), os.path.join(d, "ocrm.pdf")],
               env=ext_env)
        p09["ocrmypdf_bytes"] = os.path.getsize(os.path.join(d, "ocrm.pdf")) if q.returncode == 0 else None
        q = sh([recode, "-P", os.path.join(d, "input.pdf"), "-T", hocr,
                "-o", os.path.join(d, "ia.pdf"), "-m", "0",
                "--bg-compression-flags=-r", "500", "--fg-compression-flags=-r", "750",
                "--hq-bg-compression-flags=-r", "500", "--hq-fg-compression-flags=-r", "750"],
               env=ext_env)
        # recode_pdf needs the flags as separate argv items; rerun with sh instead
        if q.returncode != 0 or not os.path.exists(os.path.join(d, "ia.pdf")):
            q = sh(
                [recode, "-P", os.path.join(d, "input.pdf"), "-T", hocr,
                 "-o", os.path.join(d, "ia.pdf"), "-m", "0",
                 "--bg-compression-flags=-r 500", "--fg-compression-flags=-r 750",
                 "--hq-bg-compression-flags=-r 500", "--hq-fg-compression-flags=-r 750"],
                env=ext_env,
            )
        p09["ia_mrc_bytes"] = os.path.getsize(os.path.join(d, "ia.pdf")) if os.path.exists(os.path.join(d, "ia.pdf")) else None
        # fidelity: ink IoU for every candidate (same threshold rule)
        src_gray = np.asarray(PILImage.open(png).convert("L"))
        def _fg(a, p=255.0, t=60.0):
            return np.abs(a.astype(float) - p) > t
        ms = _fg(src_gray)
        doc0 = pdfium.PdfDocument(os.path.join(d, "out.pdf"))
        ren0 = np.asarray(doc0[0].render(scale=300 / 72.0).to_pil().convert("L"))[: src_gray.shape[0], : src_gray.shape[1]]
        mr0 = _fg(ren0)
        p09["B2_ink_iou"] = round(float((ms & mr0).sum() / (ms | mr0).sum()), 4)
        # marked-content balance (BDC==EMC) as committed evidence — qpdf cannot
        # check pairing, so the harness records it structurally
        import subprocess as _sp
        env_q = qpdf_env()
        qdf = os.path.join(d, "out.qdf.pdf")
        _sp.run([QPDF(),
                 "--qdf", "--object-streams=disable", os.path.join(d, "out.pdf"), qdf],
                capture_output=True, env=env_q)
        raw = open(qdf, "rb").read() if os.path.exists(qdf) else b""
        bdc, emc = raw.count(b"BDC" + bytes([10])), raw.count(b"EMC" + bytes([10]))
        p09["marked_content_balanced"] = (bdc == emc) and bdc > 0
        p09["marked_content"] = {"bdc": bdc, "emc": emc}
        for label, f in (("ia_mrc", "ia.pdf"), ("ocrmypdf", "ocrm.pdf")):
            fp = os.path.join(d, f)
            if os.path.exists(fp):
                dd = pdfium.PdfDocument(fp)
                rr = np.asarray(dd[0].render(scale=300 / 72.0).to_pil().convert("L"))[: src_gray.shape[0], : src_gray.shape[1]]
                mrr = _fg(rr)
                p09[f"{label}_ink_iou"] = round(float((ms & mrr).sum() / (ms | mrr).sum()), 4)
        out["pages"]["p09_realtext"] = p09
        print("p09_realtext:", {k: v for k, v in p09.items() if k != "probe_rc"})

    # --- Repeated-text 4-page document (p10): per-page sums + externals ---
    p10_dir = os.path.join(FIXTURES, "p10_multipage")
    if os.path.isdir(p10_dir):
        p10 = {"pages": {}, "totals": {}}
        tot = {"src": 0, "B0": 0, "B2": 0, "ocrmypdf": 0, "ia_mrc": 0}
        for n in range(1, 5):
            d = os.path.join(WORK, f"p10_page{n}")
            os.makedirs(d, exist_ok=True)
            png = os.path.join(p10_dir, f"p10_page{n}.png")
            sh([PROBE, "build", "--page", os.path.join(p10_dir, f"page{n}"), "--out", d])
            ipdf = os.path.join(d, "input.pdf")
            PILImage.open(png).convert("RGB").save(ipdf, "PDF", resolution=300.0)
            hocr = os.path.join(d, "tess.hocr")
            sh([tess_bin, png, hocr[:-5], "-c", "hocr_char_boxes=1", "hocr"], env=ext_env)
            run_external([ocrmypdf_bin, "--output-type", "pdf", "--force-ocr", "-l", "eng",
                          "--optimize", "0", ipdf, os.path.join(d, "ocrm.pdf")],
                         os.path.join(d, "ocrm.pdf"), ext_env, "ocrmypdf")
            run_external([recode, "-P", ipdf, "-T", hocr, "-o", os.path.join(d, "ia.pdf"), "-m", "0",
                          "--bg-compression-flags=-r 500", "--fg-compression-flags=-r 750",
                          "--hq-bg-compression-flags=-r 500", "--hq-fg-compression-flags=-r 750"],
                         os.path.join(d, "ia.pdf"), ext_env, "ia recode_pdf")
            row = {
                "src": os.path.getsize(png),
                "B0": os.path.getsize(os.path.join(d, "b0_raster.pdf")),
                "B2": os.path.getsize(os.path.join(d, "out.pdf")),
                "ocrmypdf": os.path.getsize(os.path.join(d, "ocrm.pdf")),
                "ia_mrc": os.path.getsize(os.path.join(d, "ia.pdf")),
            }
            p10["pages"][n] = row
            for k in tot:
                tot[k] += row[k]
        p10["totals"] = tot
        p10["totals"]["B2_vs_ocrmypdf"] = round(tot["B2"] / tot["ocrmypdf"], 4) if tot["ocrmypdf"] else None
        p10["totals"]["B2_vs_ia_mrc"] = round(tot["B2"] / tot["ia_mrc"], 4) if tot["ia_mrc"] else None
        p10["totals"]["B2_vs_B0"] = round(tot["B2"] / tot["B0"], 4) if tot["B0"] else None
        out["pages"]["p10_multipage"] = p10
        print("p10_multipage totals:", p10["totals"])

    for name in PAGES:
        page_dir = os.path.join(FIXTURES, name)
        out_dir = os.path.join(WORK, name)
        os.makedirs(out_dir, exist_ok=True)
        r = sh([PROBE, "build", "--page", page_dir, "--out", out_dir])
        if r.returncode != 0:
            out["pages"][name] = {"error": r.stderr[:200]}
            continue

        src_png = os.path.join(page_dir, f"{name}.png")
        b2 = os.path.join(out_dir, "out.pdf")
        b0 = os.path.join(out_dir, "b0_raster.pdf")

        sizes = {
            "source_png": os.path.getsize(src_png),
            "B0_searchable_raster": os.path.getsize(b0),
            "B2_reconstructed": os.path.getsize(b2),
            "font": os.path.getsize(os.path.join(out_dir, "out.ttf")),
        }
        sizes["source_ratio_B2"] = round(sizes["B2_reconstructed"] / sizes["source_png"], 4)
        sizes["baseline_ratio_B2"] = round(
            sizes["B2_reconstructed"] / sizes["B0_searchable_raster"], 4
        )
        sizes["baseline_ratio_B0"] = 1.0

        page = {"sizes": sizes}

        # B0 verification: structural + transport + render-neutrality
        q = sh([QPDF(), "--check", b0], env=env)
        text = extract_pdfium(b0).replace("\n", "").replace("\r", "").replace(" ", "")
        exp = EXPECTED[name]
        # render neutrality: invisible text must paint nothing — B0 render must be
        # pixel-identical to the text-less twin rendered by the SAME engine.
        # (Comparing against the raw PNG would test the renderer's image
        # smoothing, not our file; cairo smooths even 1:1 images.)
        b0_notext = os.path.join(out_dir, "b0_notext.pdf")
        ren_text = render_gray(b0)
        ren_notext = render_gray(b0_notext)
        identical = bool((ren_text == ren_notext).all())
        diff_px = int((ren_text != ren_notext).sum())

        # transport: multiset of code points (extractor line grouping may differ
        # from span order; content equality is the M0 gate for B0)
        ok_chars = sorted(text) == sorted(exp)
        page["B0_checks"] = {
            "qpdf": q.returncode == 0,
            "transport_chars": ok_chars,
            "transport_got": text,
            "render_neutral": identical,
            "render_diff_px": diff_px,
        }

        # byte breakdown: writer instrumentation, emitted by the probe itself
        bd_path = os.path.join(out_dir, "breakdown.json")
        if os.path.exists(bd_path):
            page["byte_breakdown"] = json.load(open(bd_path))
        out["pages"][name] = page
        print(f"{name}: B0={sizes['B0_searchable_raster']}B B2={sizes['B2_reconstructed']}B "
              f"src={sizes['source_png']}B baseline_ratio_B2={sizes['baseline_ratio_B2']} "
              f"B0(chars={page['B0_checks']['transport_chars']}, neutral={page['B0_checks']['render_neutral']}, qpdf={page['B0_checks']['qpdf']})")

    with open(os.path.join(HERE, "measurements.json"), "w") as f:
        json.dump(out, f, indent=1)
    print("written qualification/measurements.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
