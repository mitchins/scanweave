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
QPDF = os.path.join(ROOT, "tools", "dist", "bin", "qpdf")

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
    env = dict(os.environ, LD_LIBRARY_PATH=os.path.join(ROOT, "tools", "dist", "lib"))
    out = {"pages": {}, "external_baselines": {}}

    # --- Bounded external baseline attempts (record, never fake) ---
    ia = sh(["which", "ia-pdf-tools"])
    ocrmypdf = sh(["which", "ocrmypdf"])
    tess = sh(["which", "tesseract"])
    out["external_baselines"] = {
        "internetarchive_pdftools": {
            "status": "BLOCKED",
            "reason": "not installed; build requires leptonica + AGPL toolchain; "
            "session has no root (sudo requires password); bounded attempt not continued — "
            "recorded per plan as PROVISIONAL contributor",
        },
        "ocrmypdf": {
            "status": "BLOCKED",
            "reason": f"binary present: {bool(ocrmypdf.stdout.strip())}; requires tesseract "
            f"(present: {bool(tess.stdout.strip())}) and pip deps; apt blocked (no root)",
        },
        "note": "no compression comparison against external MRC in M0; ratios below are "
        "utility-internal (B2 vs B0 vs source) per QUALIFICATION §3 denominators",
    }

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
        q = sh([QPDF, "--check", b0], env=env)
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
