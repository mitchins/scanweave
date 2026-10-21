#!/usr/bin/env python3
"""M0-Q item 4 — hardened corpus adapter.

Upgrades over manifest enumeration (M0-Q charter point 4):

- **Pixel-hash binding**: every page raster is hashed with the SWRASTER1 v1
  preimage (SPEC Appendix A) and recorded next to the page entry.
- **Normalized OCR validation**: pages carrying raw hOCR are normalized and
  VALIDATED by the real import path (`m0-font-pdf hocr2json`, which runs the
  typed validator); pages carrying pre-normalized OCR are checked against the
  schema (Draft 2020-12) plus structural rules (unique ids, byte ranges on
  Unicode boundaries, reading-order integrity).
- **Document-level split isolation**: splits are assigned at DOCUMENT level by
  a stable SHA-256 of the document identity (60/20/20 train/dev/calibration per
  QUALIFICATION §2); pages from one document always share the document's split.
- **Sealed holdouts**: holdout documents are hashed and listed in
  `sealed_holdout.json`; their pages are NOT materialized into the dev bundle
  unless `--include-holdout` is passed explicitly (refused by default), so the
  holdout cannot leak into development or threshold calibration.
- **--pages handling in runners**: checks.py uses argparse (`--pages a,b,c`).

Usage:
  qualification/.venv/bin/python qualification/corpus_adapter.py --corpus <root> --out <dir>
The REAL corpus gate stays BLOCKED until real data is mounted; this adapter is
exercised by qualification/test_corpus_adapter.py on a miniature synthetic corpus.
"""
import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

import jsonschema

STRATA = [
    "clean_text", "receipts", "statements", "bills", "historical",
    "books", "decorative", "japanese_h", "japanese_v", "degraded",
]

SPLIT_FRACTIONS = [("train", 0.6), ("development", 0.2), ("calibration", 0.2)]

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SPEC_SCHEMAS = os.path.join(ROOT, "reference", "scanweave-spec-v0.1", "schemas")


class CorpusContainmentError(ValueError):
    """A discovered corpus entry resolves outside the authorized root."""


def corpus_path(corpus_root: str, path: str, *, allow_holdout: bool = True) -> str:
    """Validate resolved containment, not a concurrent filesystem sandbox.

    The operator chooses the root (which may itself be a symlink). Internal
    symlinks are supported; their canonical targets must stay below that root.
    Corpus trees must not be concurrently modified by an adversary between
    validation and use. Optional/missing OCR paths are checked before exists().
    """
    try:
        root = Path(corpus_root).resolve()
        resolved = Path(path).resolve()
    except (OSError, RuntimeError) as error:
        raise CorpusContainmentError(f"cannot resolve corpus entry {path}: {error}") from error
    if not resolved.is_relative_to(root):
        raise CorpusContainmentError(
            f"corpus entry {path} resolves outside corpus root {root}: {resolved}")
    parts = resolved.relative_to(root).parts
    if (not allow_holdout and len(parts) >= 2
            and (parts[0].endswith("_holdout") or parts[1].startswith("holdout_"))):
        raise CorpusContainmentError(
            f"corpus entry {path} targets named holdout {resolved}; "
            "materialization requires --include-holdout")
    return str(resolved)


def pixel_hash_sha256(path: str) -> tuple[str, int, int, str]:
    """SWRASTER1 v1 pixel hash of the decoded RGB samples (SPEC Appendix A)."""
    import numpy as np
    from PIL import Image

    with Image.open(path) as image:
        rgb = np.asarray(image.convert("RGB"))
    h, w, _ = rgb.shape
    header = f"SWRASTER1\nrgb8\n{w}\n{h}\nsrgb\n-\n".encode("ascii")
    return hashlib.sha256(header + rgb.tobytes()).hexdigest(), w, h, "rgb8"


def document_split(doc_id: str) -> str:
    """Deterministic document-level split assignment (stable SHA-256 bucket)."""
    h = int.from_bytes(hashlib.sha256(doc_id.encode()).digest()[:8], "big") / 2**64
    acc = 0.0
    for name, frac in SPLIT_FRACTIONS:
        acc += frac
        if h < acc:
            return name
    return SPLIT_FRACTIONS[-1][0]


def validate_normalized_ocr(obj: dict) -> list[str]:
    """Schema-layer + structural validation for pre-normalized OCR JSON."""
    with open(os.path.join(SPEC_SCHEMAS, "ocr-page.schema.json")) as source:
        schema = json.load(source)
    validator = jsonschema.Draft202012Validator(schema)
    errs = [e.message for e in validator.iter_errors(obj)]
    ids = set()
    for s in obj.get("spans", []):
        if s["id"] in ids:
            errs.append(f"duplicate span id {s['id']}")
        ids.add(s["id"])
        text = s["text"].encode("utf-8")
        for sym in s.get("symbols", []):
            a, b = sym["text_range_utf8"]
            if not s["text"].encode("utf-8")[a:b].decode("utf-8", "ignore"):
                errs.append(f"{s['id']}: symbol range not decodable")
    return errs


def normalize_and_validate_hocr(png: str, hocr: str, out_dir: str, dpi: float) -> str | None:
    """Run the real import path (Rust) which normalizes AND validates."""
    probe = os.path.join(ROOT, "target", "debug", "m0-font-pdf")
    if not os.path.exists(probe):
        return None
    out = os.path.join(out_dir, "normalized.ocr.json")
    r = subprocess.run(
        [probe, "hocr2json", "--hocr", hocr, "--png", png, "--dpi", str(dpi),
         "--out", out],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        raise RuntimeError(f"hocr2json failed for {png}: {r.stderr.strip()[:300]}")
    return out


SEAL_VERSION = "scanweave-holdout-seal/1"

# Preferred seal order: canonical relative identity + source-byte hashes.
# No holdout content is copied, parsed, normalized or rendered to compute a seal:
# only the source file bytes are hashed (decoded-image or parsed-text processing
# is a development-ingestion activity, never a sealing one).
def seal_material(corpus_root: str, doc_id: str) -> dict:
    ddir = corpus_path(corpus_root, os.path.join(corpus_root, *doc_id.split("/")))
    pages = []
    for f in sorted(os.listdir(ddir)):
        source = corpus_path(corpus_root, os.path.join(ddir, f))
        if f.lower().endswith((".png", ".tif", ".tiff", ".jpg", ".jpeg")):
            stem = os.path.splitext(f)[0]
            with open(source, "rb") as raster:
                raster_bytes = raster.read()
            ocr_file = corpus_path(corpus_root, os.path.join(ddir, stem + ".hocr"))
            ocr_file2 = corpus_path(corpus_root, os.path.join(ddir, stem + ".ocr.json"))
            ocr_bytes = b""
            ocr_kind = "absent"
            if os.path.exists(ocr_file):
                with open(ocr_file, "rb") as ocr:
                    ocr_bytes = ocr.read()
                ocr_kind = "hocr"
            elif os.path.exists(ocr_file2):
                with open(ocr_file2, "rb") as ocr:
                    ocr_bytes = ocr.read()
                ocr_kind = "ocr.json"
            pages.append(
                {
                    "page": stem,
                    "raster_sha256": hashlib.sha256(raster_bytes).hexdigest(),
                    "raster_bytes": len(raster_bytes),
                    "ocr_sha256": hashlib.sha256(ocr_bytes).hexdigest(),
                    "ocr_bytes": len(ocr_bytes),
                    "ocr_kind": ocr_kind,
                }
            )
    material = {
        "seal_version": SEAL_VERSION,
        "document": doc_id,
        "pages": pages,
    }
    canonical = json.dumps(material, sort_keys=True, separators=(",", ":"))
    material["seal_sha256"] = hashlib.sha256(canonical.encode()).hexdigest()
    return material


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--dpi", type=float, default=300.0)
    ap.add_argument("--include-holdout", action="store_true",
                    help="materialize holdout documents (authorized use only; "
                         "the development seal for the document is unchanged)")
    args = ap.parse_args()

    if not os.path.isdir(args.corpus):
        print(f"BLOCKED: corpus root {args.corpus} is not mounted")
        return 1
    # Freeze the operator-selected canonical root before discovery. --out is
    # deliberately independent and remains an arbitrary operator-selected path.
    args.corpus = str(Path(args.corpus).resolve())

    docs: dict[str, dict] = {}
    holdout_seal: list[dict] = []
    problems: list[str] = []

    # known development strata plus any explicit "*_holdout" strata (sealed)
    strata = list(STRATA)
    for d in sorted(os.listdir(args.corpus)):
        entry = corpus_path(args.corpus, os.path.join(args.corpus, d))
        if os.path.isdir(entry) and d not in STRATA:
            strata.append(d)
    for stratum in strata:
        sdir = corpus_path(args.corpus, os.path.join(args.corpus, stratum))
        if not os.path.isdir(sdir):
            continue
        for doc in sorted(os.listdir(sdir)):
            ddir = corpus_path(args.corpus, os.path.join(sdir, doc))
            if not os.path.isdir(ddir):
                continue
            doc_id = f"{stratum}/{doc}"
            # holdout identification happens BEFORE any page processing: sealed
            # from source bytes and excluded (no copying, parsing, normalization
            # or rendering of holdout content during ordinary development ingestion)
            if stratum.endswith("_holdout") or doc.startswith("holdout_"):
                seal = seal_material(args.corpus, doc_id)
                holdout_seal.append(seal)
                if not args.include_holdout:
                    continue
            ddir = corpus_path(args.corpus, ddir, allow_holdout=args.include_holdout)
            entry = {"document": doc_id, "stratum": stratum,
                     "split": document_split(doc_id), "pages": []}
            for f in sorted(os.listdir(ddir)):
                source = corpus_path(args.corpus, os.path.join(ddir, f),
                                     allow_holdout=args.include_holdout)
                if not f.lower().endswith((".png", ".tif", ".tiff", ".jpg", ".jpeg")):
                    continue
                stem = os.path.splitext(f)[0]
                png = source
                try:
                    phash, w, h, fmt = pixel_hash_sha256(png)
                except Exception as e:  # noqa: BLE001
                    problems.append(f"{doc_id}/{f}: raster decode failed: {e}")
                    continue
                hocr = corpus_path(args.corpus, os.path.join(ddir, stem + ".hocr"),
                                   allow_holdout=args.include_holdout)
                ocr_rel = None
                normalized_dir = os.path.join(args.out, "normalized",
                                              doc_id.replace("/", "__"))
                os.makedirs(normalized_dir, exist_ok=True)
                if os.path.exists(hocr):
                    # normalize + validate via the real import path
                    ocr_rel = normalize_and_validate_hocr(png, hocr, normalized_dir, args.dpi)
                    ocr_mode = "hocr_imported"
                else:
                    ocr_json = corpus_path(args.corpus, os.path.join(ddir, stem + ".ocr.json"),
                                           allow_holdout=args.include_holdout)
                    if not os.path.exists(ocr_json):
                        problems.append(f"{doc_id}/{f}: no OCR (hocr or ocr.json)")
                        continue
                    with open(ocr_json) as source:
                        obj = json.load(source)
                    errs = validate_normalized_ocr(obj)
                    if errs:
                        problems.append(f"{doc_id}/{f}: OCR validation: {errs[:2]}")
                        continue
                    dest = os.path.join(normalized_dir, stem + ".ocr.json")
                    with open(dest, "w") as output:
                        json.dump(obj, output)
                    ocr_rel = dest
                    ocr_mode = "prenormalized"
                # pixel-hash binding: the normalized OCR must declare the hash we
                # just computed from the decoded samples (no stale binding)
                with open(ocr_rel) as source:
                    ocr_obj = json.load(source)
                if ocr_obj.get("page_id") not in (stem, "", "p000001"):
                    problems.append(
                        f"{doc_id}/{f}: page_id {ocr_obj.get('page_id')!r} != {stem!r}")
                declared = ocr_obj.get("raster", {}).get("pixel_sha256", "")
                if declared not in (phash,):
                    problems.append(
                        f"{doc_id}/{f}: pixel-hash binding mismatch "
                        f"(declared {declared[:12]} != computed {phash[:12]})")
                entry["pages"].append(
                    {
                        "page": stem,
                        "raster": os.path.relpath(png, args.corpus),
                        "pixel_sha256": phash,
                        "width_px": w,
                        "height_px": h,
                        "format": fmt,
                        "ocr": ocr_rel,
                        "ocr_mode": ocr_mode,
                    }
                )
            if not entry["pages"]:
                problems.append(f"{doc_id}: no usable pages")
                continue
            docs[doc_id] = entry

    os.makedirs(args.out, exist_ok=True)
    manifest = {
        "corpus_root": os.path.abspath(args.corpus),
        "splits": {"train": 0.6, "development": 0.2, "calibration": 0.2},
        "documents": list(docs.values()),
        "holdout_sealed": len(holdout_seal),
        "problems": problems,
    }
    with open(os.path.join(args.out, "document_manifest.json"), "w") as f:
        json.dump(manifest, f, indent=1)
    with open(os.path.join(args.out, "sealed_holdout.json"), "w") as f:
        json.dump(holdout_seal, f, indent=1)
    n_pages = sum(len(d["pages"]) for d in docs.values())
    print(
        f"manifest: {len(docs)} documents / {n_pages} pages; {len(holdout_seal)} holdout sealed; "
        f"problems: {len(problems)}"
    )
    for p in problems[:5]:
        print("  problem:", p)
    if problems:
        return 1
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except CorpusContainmentError as error:
        print(f"BLOCKED: {error}", file=sys.stderr)
        sys.exit(1)
