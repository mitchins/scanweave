# Real-document convergence evidence

Product implementation: `5998611`, `13288a8`; report: `../../CLEARSCAN_REAL_DOCUMENT_REPORT.md`.

## Reproduce

Use the existing licensed development inputs and attribution from `../pdf_packaging/` (CORD, OCR-D, financial/form/mixed sources). Do not open the sealed holdout. Python scripts require the same pikepdf, Pillow, NumPy, pypdfium2 and fontTools environment as the packaging suite; Poppler, Tesseract and GNU time must be installed. Validation uses `../tools_env.py` for qpdf/OTS.

```sh
cargo build --release
python3 qualification/real_convergence/run.py --groups
python3 qualification/real_convergence/run.py
python3 qualification/real_convergence/measure.py
python3 qualification/real_convergence/outline_inventory.py
python3 qualification/real_convergence/render_comparisons.py
python3 qualification/real_convergence/synthetic.py
python3 qualification/real_convergence/verify_synthetic.py
python3 qualification/real_convergence/package_results.py
```

`SCANWEAVE_BIN` can override `target/release/scanweave`. `run.py` skips completed run records; use a new evidence directory or remove only the intended generated run record to repeat a case. The command used for ordinary conversion is simply:

```sh
scanweave qualification/pdf_packaging/groups/forms-input.pdf output.pdf
```

The CLI runs Tesseract internally. No manually prepared bundle is needed.

## Inspect

- `outputs/scan-linn.pdf`: full real page with increased reconstruction coverage.
- `outputs/cord-05.pdf`: zero-vector page retained efficiently and searchably.
- `outputs/nara-form-01.pdf`: five previously skipped vector digits restored.
- `300/final.pdf`, `600/final.pdf`: established synthetic regression outputs.
- `comparisons/*normal*` and `*300*`: source/previous/new/Adobe context (manifest identifies ordering).
- `comparisons/restored-form-digits.png`: source/before/fixed, actual missing-paint correction.
- `inspection/history-02-words.png`: rejected local segmentation/coverage attempt, not the delivered output.

`scorecard.json/csv` contains all 35 complete-document arm records. `page-results.json/csv` contains 32 per-page records; document byte columns are not per-page byte allocations. `measurements.json` retains every native-resource histogram, byte count, filter, timing and renderer deviation. `outline-inventory.json` counts actual painted CID/GIDs independently of report proposals. `run-manifest.json` hashes representative, complete local and frozen comparator PDFs.

Complete collection PDFs and huge raw sidecars remain ignored under `collections/`; their hashes and commands are retained. Small representative PDFs and selected renders are committed. Existing source/competitor assets remain at their prior paths with their original attribution. No external artifact host is implied.

## Controls and limitations

`diagnose.py`: one-pass original funnel. `ocr_controls.py`: PSM3/6/11 controls. `audit_samples.py`: decoded native samples. `workflow_controls.py`: JPEG pass-through plus complex-geometry fallback. `runtime_control.py`: isolated no-vector recomposition ablation (requires its recorded control binaries/build). `grouping_control.py`: restored paint with unchanged fonts/images/text. The latter controls reference preserved local paths; their recorded JSONs are evidence, not a new public converter mode.

Rust logs retain inherited failures separately; `e0-e7-p01-p08.json` retains inherited visual/native failures. Real scans have no pristine-font ground truth. Source-relative pixels, OCR annotation queries and manual appearance observations remain separate measurements.
