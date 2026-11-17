# STROKE-02 research

Crop-only experiment; no converter integration or improved ScanWeave PDF was produced. Generated PDFs, rendered images, diagnostic data and progress stay in `/data/coding/scanweave/work/books01/stroke02/`. Set `TMPDIR` to its `tmp/` subdirectory. Inputs are the two authorized dev source PDFs, BOOKS-01 dev `runs.json`/selected hOCR and existing comparator PDFs. OCR boxes are used for geometry only; they are not shape templates. The full-page benchmark and holdout are not run.

With the existing `/data/coding/scanweave/qualification/.venv/bin/python`, in order:

```
export TMPDIR=/data/coding/scanweave/work/books01/stroke02/tmp OPENBLAS_NUM_THREADS=1
python -I -B research/stroke02/diagnose.py
python -I -B research/stroke02/psf_fit.py
python -I -B research/stroke02/crop_fit.py
python -I -B research/stroke02/compare_metrics.py
python -I -B research/stroke02/ambiguity.py
python -I -B research/stroke02/ink_mass.py
python -I -B research/stroke02/synthetic_physics.py
python -I -B research/stroke02/final_panels.py
python -I -B research/stroke02/summarize.py
python -I -B research/stroke02/test_crop_fit.py
```

The source images are made with `pdfimages -f 1 -l 1 -png` from the dev source PDFs into `$B/stroke02/native/<page>-000.png`; `pdfimages` was Poppler 24.02.0. Python 3.12.3, NumPy 2.5.4, SciPy 1.18.1, scikit-image 0.26.0, Pillow 13.0.0, pypdfium2 5.14.0, and PDFium 156.0.8076.0 were used; see STROKE-01's `results-summary.json` for system-font hashes. PNG/PDF outputs and OCR stay local. Candidate crop PDFs embed source pixels and have no text layer, so they cannot measure real PDF text, size benefit or displacement. PDFium reference images are rendered at actual 1× and 2×, with accepted BOOKS-01 affine registration for competitors (bicubic alignment at the rendered resolution).

The uncertainty gate and the region crops are exploratory, not production safeguards or independent tests. `pdf_rescan_linear_rgb_rmse` reprojects a rendered crop PDF through a single-colour, locally estimated background and Gaussian blur, using the same OCR-group window; unchanged raster at boundaries may be blurred again. A low score is not proof of source glyph correctness.

## Corrected local-PSF continuation

After preparing the existing native images and OCR inputs, run `joint_fit.py`, `counter_test.py`, `oracle_calibration.py`, `joint_render.py`, `fair_compare.py`, then `summarize_calibrated.py` and `final_panels.py` with the same isolated Python and `TMPDIR`. The old `results-joint.json` records the superseded pre-correction experiment; its within-MAD rejection and five-hypothesis veto must not be used. The current comparative numbers are in `results-calibrated.json`. Synthetic oracle noise and JPEG are assumptions, not measured scanner parameters; PDF contour-coordinate round trips are covered by `test_joint.py`.
