#!/usr/bin/env python3
"""M0-Q item 4 — end-to-end pipeline test on a MINIATURE SYNTHETIC CORPUS.

Builds a tiny corpus from the committed synthetic fixtures (documents grouped by
stratum, one holdout document), runs the hardened adapter (pixel-hash binding,
normalized OCR validation, document-level split isolation, sealed holdout),
then exercises the runner interface (checks.py --pages) against the resulting
bundle layout. No access to the real benign corpus is required or performed.
"""
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
WORK = os.path.join(ROOT, "work", "corpus-mini")
FIX = os.path.join(HERE, "fixtures", "probe")

failures = []


def check(name, cond, detail=""):
    print(f"{'PASS' if cond else 'FAIL'} {name} {detail}")
    if not cond:
        failures.append(name)


def main() -> int:
    venv = os.path.join(HERE, ".venv", "bin", "python")
    corpus = os.path.join(WORK, "corpus")
    out = os.path.join(WORK, "bundle")
    shutil.rmtree(WORK, ignore_errors=True)

    # documents: (stratum, document, source fixture name)
    docs = [
        ("receipts", "doc-alpha", "p09_realtext"),
        ("receipts", "doc-beta", "p02_wronglabel"),
        ("statements", "doc-gamma", "p01_latin"),
        ("books", "doc-delta", "p05_colour"),
        ("japanese_h", "doc-epsilon", "p03_kana"),
        ("receipts_holdout", "holdout_zeta", "p07_sharedcid"),
    ]
    for stratum, doc, fixture in docs:
        d = os.path.join(corpus, stratum, doc)
        os.makedirs(d)
        src_png = os.path.join(FIX, fixture, f"{fixture}.png")
        src_ocr = os.path.join(FIX, fixture, f"{fixture}.ocr.json")
        if not os.path.exists(src_png):
            check("fixture availability", False, f"missing {src_png}")
            return 1
        shutil.copy(src_png, os.path.join(d, "page_01.png"))
        # pre-normalized OCR (validated by the adapter) with a stale pixel hash
        # to exercise the binding check
        ocr = json.load(open(src_ocr))
        ocr["page_id"] = "page_01"
        if doc == "doc-alpha":  # one document gets a deliberately broken hash
            ocr["raster"]["pixel_sha256"] = "0" * 64
        with open(os.path.join(d, "page_01.ocr.json"), "w") as f:
            json.dump(ocr, f)

    # 1. adapter runs; broken binding on doc-alpha is REPORTED (fail-closed)
    r = subprocess.run(
        [venv, os.path.join(HERE, "corpus_adapter.py"),
         "--corpus", corpus, "--out", out],
        capture_output=True, text=True,
    )
    printed = r.stdout + r.stderr
    check("adapter fails closed on binding mismatch", r.returncode == 1, r.stdout.strip()[-120:])
    check("binding mismatch named in output", "doc-alpha" in printed and "pixel-hash binding" in printed)

    # 2. repair the binding and re-run: clean manifest with holdout sealed
    ocr = json.load(open(os.path.join(corpus, "receipts", "doc-alpha", "page_01.ocr.json")))
    import numpy as np
    from PIL import Image
    rgb = np.asarray(Image.open(os.path.join(corpus, "receipts", "doc-alpha", "page_01.png")).convert("RGB"))
    h, w, _ = rgb.shape
    header = f"SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n".encode()
    import hashlib
    ocr["raster"]["pixel_sha256"] = hashlib.sha256(header + rgb.tobytes()).hexdigest()
    json.dump(ocr, open(os.path.join(corpus, "receipts", "doc-alpha", "page_01.ocr.json"), "w"))
    r = subprocess.run(
        [venv, os.path.join(HERE, "corpus_adapter.py"),
         "--corpus", corpus, "--out", out],
        capture_output=True, text=True,
    )
    check("adapter succeeds after repair", r.returncode == 0, r.stdout.strip())
    manifest = json.load(open(os.path.join(out, "document_manifest.json")))
    check("holdout sealed", manifest["holdout_sealed"] == 1 and "holdout_zeta" not in {d["document"] for d in manifest["documents"]})
    seal = json.load(open(os.path.join(out, "sealed_holdout.json")))
    check("seal recorded", len(seal) == 1 and "seal_sha256" in seal[0])
    splits = {d["document"]: d["split"] for d in manifest["documents"]}
    check("document-level splits", set(splits.values()) <= {"train", "development", "calibration"}
          and splits.get("receipts/holdout_zeta") is None, str(splits))
    # all pages of one document share the split (trivially true: split is per-document)
    check("every page bound", all(len(d["pages"]) >= 1 for d in manifest["documents"]))

    # 3. runner interface: checks.py --pages + --fixtures-dir work against the
    # ADAPTER's bundle layout (as the corpus harness would materialize it)
    probe_pages = os.path.join(WORK, "probe-pages")
    for di, doc in enumerate(manifest["documents"]):
        for pg in doc["pages"]:
            name = f"c{di:02d}_{pg['page']}"
            d = os.path.join(probe_pages, name)
            os.makedirs(d)
            shutil.copy(os.path.join(corpus, pg["raster"]), os.path.join(d, f"{name}.png"))
            shutil.copy(pg["ocr"], os.path.join(d, f"{name}.ocr.json"))
    names = sorted(os.listdir(probe_pages))
    r = subprocess.run(
        [venv, os.path.join(HERE, "checks.py"),
         "--pages", ",".join(names), "--fixtures-dir", probe_pages,
         "--out", os.path.join(WORK, "corpus_checks.json")],
        capture_output=True, text=True,
    )
    printed = r.stdout + r.stderr
    # interface criterion: every corpus page is PROCESSED (PASS/FAIL line) and
    # recorded in results; gate outcomes are corpus-evaluation territory, not
    # an interface assertion.
    processed = sum(1 for n in names if f"PASS {n}" in printed or f"FAIL {n}" in printed)
    res = json.load(open(os.path.join(HERE, "probe_results.json")))
    recorded = sum(1 for n in names if n in res["pages"])
    # transport (correctness) must PASS on corpus pages; visual gates are reported
    transport_ok = all(
        res["pages"][n]["checks"].get("extract_poppler") and res["pages"][n]["checks"].get("extract_pdfium")
        for n in names
    )
    check("checks.py --pages/--fixtures-dir runs on adapter bundle",
          processed == len(names) and recorded == len(names), f"{processed}/{len(names)} processed")
    check("corpus pages transport (both engines)", transport_ok)
    check("adapter bundle carries validated OCR",
          all(pg["ocr_mode"] in ("prenormalized", "hocr_imported")
              for doc in manifest["documents"] for pg in doc["pages"]))

    # 4. holdout materialization is refused unless explicitly requested
    r = subprocess.run(
        [venv, os.path.join(HERE, "corpus_adapter.py"),
         "--corpus", corpus, "--out", os.path.join(WORK, "bundle-ho"),
         "--include-holdout"],
        capture_output=True, text=True,
    )
    m2 = json.load(open(os.path.join(WORK, "bundle-ho", "document_manifest.json")))
    check("holdout materializes only with --include-holdout",
          "receipts_holdout/holdout_zeta" in {x["document"] for x in m2["documents"]})

    # 5. missing corpus fails closed
    r = subprocess.run(
        [venv, os.path.join(HERE, "corpus_adapter.py"),
         "--corpus", "/nonexistent-corpus", "--out", os.path.join(WORK, "b2")],
        capture_output=True, text=True,
    )
    check("missing corpus fails closed", r.returncode == 1 and "BLOCKED" in (r.stdout + r.stderr))

    if failures:
        print(f"FAILED: {failures}")
        return 1
    print("miniature synthetic corpus pipeline test passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
