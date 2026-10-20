# ClearScan typography evidence

Normal product path: `--profile clearscan`. Implementation commits: `53b949f`, `ec7bcdc`, `6495218`. Baseline: `903580f` (code ancestor `08431a7`). No separate reconstruction mode is used.

Start with `300/final.pdf`, `300/final-native-page00.png`, and `300/final-serif-800pct.png`. `CLEARSCAN_TYPOGRAPHY_REPORT.md` at repository root explains the measured gains and limitations.

## Reproduce

From the repository root, using the existing measurement environment:

```sh
cargo build --release -p scanweave-cli
/tmp/scanweave-competitive-venv/bin/python qualification/clearscan_typography/run.py --dpi 300 600 --real --measure
/tmp/scanweave-competitive-venv/bin/python qualification/clearscan_typography/validate.py
/tmp/scanweave-competitive-venv/bin/python qualification/clearscan_typography/semantic_audit.py
/tmp/scanweave-competitive-venv/bin/python qualification/clearscan_typography/ownership_audit.py
/tmp/scanweave-competitive-venv/bin/python qualification/clearscan_typography/real/owner_regression.py
```

The converter receives only the degraded page images and supplied OCR in `qualification/experiments/m1g/fixture/dpi{300,600}/input/document.json`. Oracle images/fonts are opened only by the evaluators. `run-manifest.json` and `run.py` retain the normal converter commands; real-page `runs.json` includes exact argv. Frozen Adobe and previous ScanWeave PDFs are provided for identical scans. Adobe output hashes are verified against the original competitive run manifest; Acrobat need not be rerun to reproduce the comparisons.

Python dependencies: NumPy, Pillow, pikepdf, pypdfium2, fontTools. Poppler, qpdf and OTS are also used; qpdf/OTS paths come from the existing `qualification/tools_env.py`. Exact versions/hashes are in `run-manifest.json`. Rust uses the existing Cargo.lock. Full reports are archived as deterministic `.json.gz`; the converter regenerates ordinary `.json` files. To inspect an archived report, use Python `gzip.open`, or `gzip -dc FILE.json.gz > FILE.json` before invoking helpers which expect JSON.

## Measurement contracts

- Same 552 non-space glyph instances, fixed physical positions; no candidate-specific resizing. Both integer-DPI Poppler and exact-size PDFium (`nextafter(dpi/72,0)`) are reported independently. Ordinary-scale PDFium is a separate rounding diagnostic.
- `stages.py` uses unique witnesses for S1–S3 and emitted occurrences for S0/S4/S5. These are not an additive error budget. S4/S5 are paired.
- `design_geometry.py` is evaluator-only. It compares original design outlines with actual embedded glyphs/CID maps/text matrices. Its source-font control validates geometry independently of Pillow/Poppler/PDFium rasterization. Use `--arms previous final --representative` for bounded cross-section diagnostics. Full original-font control contains one inherited OCR code mismatch, explicitly excluded only from the control.
- `geometry-binding.json` binds the earlier complete geometry review to final visible outline hashes and placement matrices. One additional private glyph serves invisible text; it is not a reconstructed source-font identity.
- `compare.py`, `audit.py`, `geometry.py`, `identity.py`, `examples.py`, `native.py`, `context.py` reuse the earlier qualification utilities. Encoded mixed-content raster bytes are not allocated to arbitrary semantic classes by pixel area.
- Failed methods retain actual PDFs, metrics and source snapshots/patches. Their outputs are never selected by a public product flag.

## Real inputs and licences

Reuse the exact ten CORD and five OCR-D pages and existing OCR from `qualification/clearscan_competitive/real/`. Licence/attribution and download manifests remain there: `ATTRIBUTION.md`, `cord_license.txt`, `ocrd-LICENSE.md`, `downloads.json`, `region-ocr-manifest.json`. Full page images are retained for composition. No pristine typography is asserted for these scans. Nominal 300 DPI is a conversion geometry setting, not a claim about their original capture resolution.
