# Matched current Adobe XI comparison

Starting ScanWeave HEAD: `c20a8a91c1109c31bbf7cfdc5ff1b562f5f05986`. The authoritative document manifests reference eight pages, each 432 × 216 pt; extra fixture pages 08–11 are excluded. Identical source samples are assembled losslessly into `qualification/clearscan_competitive/{300,600}/source.pdf` for Adobe. Normal ScanWeave `build --bundle … --profile clearscan` consumes those exact images and the existing OCR bundle. Oracle images are evaluator-only.

Acrobat XI Pro 11.0.20, Wine 9.0 (Ubuntu), ClearScan output style, all pages. The runner needed repairs for a landscape selection miss and a settings-confirmation race. A shared display was also receiving unrelated application windows; accepted runs use dedicated Xvfb `:109`. Image-only and Searchable Image attempts were rejected, not counted as ClearScan. Accepted 300 DPI output contains embedded CID Type 0C font programs and reduced 150 DPI background images plus retained 300 DPI regions. The known producer string alone was insufficient verification.

Full same-instance and per-family results are in `qualification/clearscan_competitive/{300,600}/{source,adobe,previous}/metrics.json`. Each includes default-DPI and source-controlled resolution measurements, Poppler and PDFium independently, exact stream accounting, extraction and the ten best/worst families. Commands are encoded in the run scripts and CLI time logs.

## Rendering control

Rendering a completely untouched full-page scan at `-r 300` introduces sampling error in Poppler. PDFium's `scale=300/72` rounds the page to 1801 × 901 rather than 1800 × 900. At `299.99999`, both source-only renders reproduce the original samples exactly. However, Poppler then quantizes small placed raster patches differently; this is independently reproduced in `patch_sampling_probe.json` and `review.json`. Consequently both settings are retained, and an unrendered source-to-pristine score must not be interpreted as an equal-renderer baseline for an emitted PDF. Translation-only alignment scores are diagnostic, never replacements for physical-position scores.

The earlier fallback `8` has byte-exact encoded samples and a mathematically correct placement. PDFium's controlled render is exact inside its native patch; Poppler's is not. The discrepancy is not proof of missing source pixels or a wrong vector glyph.

Final tables and current implementation results are recorded in `CLEARSCAN_COMPETITIVE_REPORT.md` after the engineering reruns.

## Frozen starting-output measurements

The source column below is the image-only PDF; ScanWeave also reports qualified searchable-raster candidates of 4,210,178 B and 16,320,387 B.

| DPI | Source PDF B | Adobe PDF B | ScanWeave PDF B | Adobe font B | ScanWeave font B | Adobe raster B | ScanWeave raster B |
|---|---:|---:|---:|---:|---:|---:|---:|
| 300 | 4,124,819 | 37,100 | 1,093,038 | 5,963 | 35,332 | 17,411 | 917,473 |
| 600 | 16,263,472 | 50,779 | 889,147 | 5,880 | 52,464 | 30,036 | 754,225 |

At the source-controlled resolution, PDFium glyph-window IoU is 0.86728 Adobe versus 0.83911 ScanWeave at 300 DPI, and 0.86617 versus 0.86252 at 600 DPI. Poppler differs markedly: 0.63657 versus 0.66816 at 300 DPI; 0.74632 versus 0.69057 at 600 DPI. These reproduce the historical padded-window metric, including whitespace records; glyph isolation and stage diagnostics in the final report distinguish their limitations. Native-DPI results are preserved separately rather than averaged across renderers.
