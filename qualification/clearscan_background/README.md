# ClearScan paper reconstruction

Start with [the engineering report](../../CLEARSCAN_BACKGROUND_REPORT.md) and [600 DPI output](600/final.pdf). The normal converter uses `--profile clearscan`; no new conversion profile exists.

## Reproduce

Build the release CLI, then run `python qualification/clearscan_background/run.py --repeat` from the repository root using the existing qualification Python environment. Dependencies: NumPy, Pillow, pikepdf, pypdfium2, FontTools, Poppler, qpdf and OTS. `--measure-only` skips conversion and remeasures saved outputs. `contour_trial.py`, `summarize.py` and `manifest.py` regenerate the isolated rejected-contour measurements, scorecard and hash manifest. The runner hydrates lossless JSON archives automatically.

## Artifacts

- `300/` and `600/`: same-input `previous.pdf`, `final.pdf`, frozen `adobe.pdf`, normal CLI reports/time logs, per-renderer metrics and source/pristine comparisons.
- `stage-a/`: A0 frozen page, A1 evaluator-only paired paper at native/150 DPI, A2 final ordinary converter. The replay asserts exact original-source reproduction. Fonts/text/placements stay fixed; native footprint geometry stays fixed in A0/A1.
- `background-context-*pct.png`: true physical crop showing paired paper, baseline/new/Adobe background-only, vector-only and final output. Zooms are 100%, 800%, 1600%; full page render selection also includes300%.
- `final/stages/S4-vector-only.pdf`, `final/raster-only.pdf`: complete layer diagnostics. Default/nextafter render differences remain independently recorded.
- `resources.json`: exact encoded stream accounting and native/mixed resource classes. Pixel meanings within mixed images are not converted into invented byte shares.
- `hard-negative/`: faint horizontal rule crossing actual glyphs, at both DPIs, including native pixel, final render and whole-raster patch-sampling controls.
- `contour-trial/` and `contour-300.pdf`: rejected 0.30px grayscale curve fit, isolated from background effects. This is an archived qualification result, not a product mode.
- `real/final/`: CORD-02 and OCR-D history-01 PDFs, full-page source/Poppler/PDFium comparisons, extraction/search/byte results. Their dataset licences and attribution remain applicable.

`run-manifest.json` separates converter inputs from evaluator-only original typography. `archives.json` binds raw and gzip hashes. Rejected candidate data remains locally preserved; committed trial data is clearly marked. The ordinary final300 conversion is byte-identical on repeat.
