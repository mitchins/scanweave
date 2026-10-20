# Smooth ClearScan contours

Start with `../../../CLEARSCAN_CONTOUR_REPORT.md` (remove the space), or open `600/final.pdf` for the strongest full-document output. `300/final.pdf` is the lower-resolution matched output. `previous.pdf` freezes 4bff482; `adobe.pdf` is the same-input frozen Acrobat XI comparator.

`serif`, `italic`, `punctuation` and `kana` comparison PNGs show source, pristine, Adobe, previous, final, vector-only and raster-only rows, at 100%, 300%, 800% and 1600%. Actual vector-only/raster-only PDFs are under each DPI's `final/` directory. Full zoom render hashes and dimensions are in `zoom-renders.json`; selected full-page renders are committed.

Run `python qualification/clearscan_contours/run.py --measure --zooms --repeat` from the repository root after building the release CLI. Use the existing qualification Python environment with Pillow, NumPy, FontTools, pikepdf and pypdfium2 plus Poppler, qpdf and OTS. The runner hydrates archived JSON automatically. Commands for geometry and real inputs are in the report. `run-manifest.json` binds original scan/OCR inputs separately from evaluator-only pristine references. No pristine font is a converter input.

Large JSON records are archived losslessly as `.json.gz`; `archives.json` records original and archive hashes. Rejected trial PDFs remain local; `trial-results.json` preserves their measured results and hashes. These controls are not additional product modes.

Real derivatives retain source licensing and attribution in `real/ATTRIBUTION.md`, `cord_license.txt` and `ocrd-LICENSE.md`. No pristine truth exists for those pages.
