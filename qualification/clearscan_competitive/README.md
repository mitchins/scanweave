# Current ClearScan comparative evidence

Implementation: `08431a7` (normal CLI/library ClearScan; faithful remains separate). Starting baseline: `c20a8a91c1109c31bbf7cfdc5ff1b562f5f05986`. See root `CLEARSCAN_COMPETITIVE_REPORT.md` for conclusions and limits.

## Reproduction

Python dependencies: numpy, Pillow, pikepdf, pypdfium2, fonttools, lxml; Poppler, qpdf and OTS are independent validators. The executed interpreter is `/tmp/scanweave-competitive-venv/bin/python`. `run_current.sh` runs the normal converter on existing eight-page manifests, followed by independent measurement. Override `SCANWEAVE_EVAL_PYTHON` for another environment. `run-manifest.json` records versions and artifact hashes. Evaluator-only pristine references are read only by the Python measurement scripts, never by the converter.

```sh
bash qualification/clearscan_competitive/run_current.sh
# Genuine pages, full original images and existing Tesseract engine:
python qualification/clearscan_competitive/real/fetch.py
python qualification/clearscan_competitive/real/region_ocr.py
python qualification/clearscan_competitive/real/convert.py product --region-ocr
python qualification/clearscan_competitive/real/evaluate.py product
python qualification/clearscan_competitive/validate.py
```

For the older three-page benchmark use `qualification/competitors/adobe_xi/inputs/dpi{300,600}/document.json` with the same `build --bundle ... --profile clearscan --output ... --report ...` command. Evaluate with `compare.py DPI three-final PDF --input qualification/competitors/adobe_xi/inputs/dpiDPI --oracle qualification/competitors/adobe_xi/oracle/dpiDPI`. Frozen Adobe files are in `three300/adobe.pdf` and `three600/adobe.pdf`.

## Adobe reference

`reference-runner.sh` is the isolated Wine/XTEST runner, not converter source. It uses Acrobat XI Pro11.0.20, Wine9.0 and dedicated Xvfb109. Normal UI settings captured through public control APIs: English(US), ClearScan, Downsample To600dpi. Adobe nevertheless emitted150dpi reduced backgrounds. `reference_ui.c` reads normal UI strings; it does not inspect executable internals, memory or proprietary program resources. It is optional evidence capture, not needed for conversion.

```sh
DISPLAY=:109 WINEPREFIX=/home/mitch/.wine-acrobat-xi \
  /usr/bin/time -v -o qualification/clearscan_competitive/300/adobe-repeat-time.txt \
  bash qualification/clearscan_competitive/reference-runner.sh \
  qualification/clearscan_competitive/300/source.pdf \
  qualification/clearscan_competitive/300/adobe-repeat.pdf clearscan
```

Repeat for600. Original300 accepted run was manually completed after reproducible UI selection/confirmation failures; the clean repeat's97.91s is the measured timing. The two300 outputs have different bytes but identical32 rendered pages, extracted text and font/raster/content payload sizes. No Adobe font program is used by ScanWeave. Only resulting public PDF objects are measured.

`source.pdf` embeds exact grayscale source samples with lossless Flate; `inputs.json` binds source PNG hashes. Lossless assembly uses `qualification/competitors/adobe_xi/lossless_pdf.py` `write_image_only_pdf(paths, output, dpi, (432,216))`, with the eight manifest pages in order. `run-manifest.json` independently verifies decoded samples and page dimensions.

## Measurement contract

Poppler uses integer physical DPI. PDFium exact-size scale is `math.nextafter(dpi/72,0)` to avoid a floating-point ceil from1800 to1801pixels; the ordinary `dpi/72` diagnostic is also preserved. Earlier fractional-DPI Poppler controls shifted vector text by1pixel and are excluded from headline scores; evidence remains under `pre-grid-correction/` and `poppler-vector-control.json`. No glyph is independently resized to an oracle bbox. Primary scores isolate552 nonspace glyph instances; legacy padded windows, shape-alignment diagnostics, counter/ink-width/centroid measures and both renderer outputs remain separate.

`stages.py` distinguishes actual target occurrence populations from unique witness populations. S1/S2 placed diagnostics use inferred construction geometry. Nominal S3 uses a72pt canvas to avoid small-page ceil changing raster phase. Do not subtract means from different populations as an additive causal decomposition.

`ownership_audit.py` renders a PDF with text objects removed and compares actual retained raster at each emitted vector occurrence. Encoded bytes are classified by whole image resources: residual background or native mixed fallback/artwork/unknown. Compressed bytes cannot honestly be divided among individual glyph pixels.

`identity.py` checks448 instances of six confusable characters per resolution. It is a bounded evaluator, not proof of arbitrary real-document correctness. `geometry.py` includes threshold-sensitive counters and a perimeter-based width proxy, not a direct stem-width measurement. Native text, supplied OCR and known source Unicode are distinguished.

Failed contour/background alternatives remain locally preserved; `scorecard.json` records their hashes/negative outcomes. They are not alternative product modes. Representative negative input/outputs and reviewer findings are versioned. Full intermediate renders can be regenerated from the preserved commands where source patches exist; not every discarded trial has an independently frozen source revision.

The actual qualified searchable-raster candidate can be exported without a new product mode:

```sh
cargo run --release -p scanweave-io --example export_raster_baseline -- qualification/experiments/m1g/fixture/dpi300/input/document.json qualification/clearscan_competitive/300/searchable-raster.pdf
```

Repeat with600. This example calls the normal document converter and writes its existing `raster_baseline_pdf_bytes`; it contains no separate reconstruction or PDF implementation. Exported byte lengths are checked against the candidates reported by the ordinary CLI. Full-resolution multi-panel renders are reproducible; compact `*-preview.png` panels and800% glyph crops are committed for inspection.
