# STROKE-01 crop experiment

Offline research only; it does not modify the converter. The initial `results-summary.json` preserves the first experiment. The corrected run writes a new `results-corrected.json` and keeps raw evidence under `$B/stroke01/corrected/`:

```sh
export B=/data/coding/scanweave/work/books01
export TMPDIR="$B/tmp" OPENBLAS_NUM_THREADS=1
/data/coding/scanweave/qualification/.venv/bin/python -I -B research/stroke01/prototype.py
/data/coding/scanweave/qualification/.venv/bin/python -I -B research/stroke01/shell_diagnostic.py
/data/coding/scanweave/qualification/.venv/bin/python -I -B research/stroke01/summarize.py
/data/coding/scanweave/qualification/.venv/bin/python -I -B research/stroke01/test_prototype.py
```

Native dev inputs are single Flate images extracted with `pdfimages -f 1 -l 1 -png <dev-source.pdf> "$B/stroke01/native/<page>"`. Fixed crop boxes, font paths, synthetic seed and outputs are in `prototype.py`; exact dependency versions and font hashes are in the results. The baseline and competitor panel inputs are existing aligned BOOKS-01 renders. Generated images and raw synthetic cases remain under `$B`; committed results contain aggregate scores and numerical page diagnostics, no images or OCR/GT text.

`local_model.py` estimates colour independently per proposed connected component from its strongest skeleton-centre samples, borrowing a nearby component if there are too few. A component-size bound excludes a single large blob; this is not a semantic illustration classifier and could miss fine details or accept parts of an illustration. The reported colour uncertainty is core-sample dispersion relative to contrast, not a calibrated confidence interval. Renderings preserve original pixels outside component support.

`calibration.py` chooses a crop-level SNR/uncertainty gate on two synthetic training fonts; the remaining italic font is held out from gate fitting. This font was present in the first experiment and aggregate model results were inspected during development, so it is not a fully independent test of model selection. Declined outputs retain original raster; the raw proposed masks are still scored for diagnosis. The synthetic table reports gate-accepted cases separately, rather than assigning an invented binary-mask score to the retained raster.

The energy method uses ICM, not exact graph-cut optimisation; geometry does not enforce topology. The baseline mask reconstructs the global threshold, not the complete ScanWeave PDF renderer. See the report for limitations, synthetic safety criteria and comparator panels.
