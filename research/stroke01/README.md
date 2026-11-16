# STROKE-01 crop experiment

No converter integration. Run with the pinned environment and native dev source images prepared under `$B/stroke01/native/`:

```sh
export B=/data/coding/scanweave/work/books01
export TMPDIR="$B/tmp" OPENBLAS_NUM_THREADS=1
/data/coding/scanweave/qualification/.venv/bin/python -I -B research/stroke01/prototype.py
/data/coding/scanweave/qualification/.venv/bin/python -I -B research/stroke01/test_prototype.py
/data/coding/scanweave/qualification/.venv/bin/python -I -B research/stroke01/summarize.py
```

Native images are the single Flate image extracted with `pdfimages -f 1 -l 1 -png <dev-source.pdf> "$B/stroke01/native/<page>"`. Inputs, crop boxes, output location, known local font paths and random seed are in `prototype.py`. A fresh machine must have those exact fonts (hashes in results summary). The baseline and competitor panel inputs are existing aligned BOOKS-01 renders. All generated images and raw synthetic cases stay under `$B`; the committed summary contains aggregate scores and page-level numerical diagnostics, no image or OCR/GT text.

`decline` is a hand-set, uncalibrated contrast/noise heuristic, not a calibrated probability of correctness. The code computes proposed outputs even on declined cases for diagnostic scoring; a real caller would keep the original raster. There is no page-boundary or illustration classifier, and the skeleton-width geometry model does not guarantee topology. The baseline column reconstructs the existing global foreground mask, not the complete baseline PDF renderer. Results are a bounded negative PoC, not a controlled comparison of full implementations of the cited papers.
