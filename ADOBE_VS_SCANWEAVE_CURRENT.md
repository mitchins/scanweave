# Adobe XI versus current ScanWeave

Matched eight-page inputs: genuine300/600DPI, exact image samples and432×216pt pages. Starting ScanWeave`c20a8a91c1109c31bbf7cfdc5ff1b562f5f05986`; measured current implementation`08431a7`. Full engineering findings, stage attribution and real-document evidence are in [CLEARSCAN_COMPETITIVE_REPORT.md](CLEARSCAN_COMPETITIVE_REPORT.md).

Acrobat XI Pro11.0.20 /Wine9.0, dedicated Xvfb109. Verified normal UI: English(US), ClearScan, Downsample To600dpi. Actual reduced background images are150dpi. Visible embedded CID Type0C text and image/content inspection verify genuine reconstruction. Adobe output fonts were measured only; no Adobe font programs/resources were transferred into ScanWeave.

| DPI | Source PDF B | Adobe B | Previous ScanWeave B | New ScanWeave B | Adobe PDFium glyph IoU | Previous IoU | New IoU | Raw scan IoU |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 300 | 4,124,819 | 37,100 | 1,093,038 | 732,603 | 0.90255 | 0.89301 | 0.91080 | 0.94516 |
| 600 | 16,263,472 | 50,779 | 889,147 | 1,334,401 | 0.94155 | 0.93798 | 0.94272 | 0.97807 |

The source scan remains more accurate in aggregate than either reconstructed converter. New ScanWeave improves against the previous output on both exact-size renderers, strongly at300 and modestly at600;600 size grows50.1%. Do not read these results as aggregate recovery beyond the source or Adobe-level compression.

## Rendering and reproducibility

Primary results isolate552 nonspace instances at fixed physical positions. Poppler uses integer physical DPI; PDFium uses`nextafter(dpi/72,0)` to avoid floating-point ceil. Ordinary-scale PDFium, raw padded windows, shape-alignment diagnostics, original image-only renders and all renderer-specific records remain available. Earlier fractional-DPI Poppler results were invalidated by a1pixel vector phase shift and preserved under`pre-grid-correction/`. They are not headline results. The frozen source PDF has exact decoded samples, but Poppler rendering of even that image-only file introduces resampling.

The300 Adobe repeat differs37100→38295B, but all32rendered pages are pixel-identical, text agrees and raster/font/content payload sizes match. Other streams/overhead differ1195B. Valid repeated300 conversion97.91s;600 conversion98.82s. Shared-display interference and bounded landscape/dialog runner fixes are documented; invalid image-only/Searchable Image attempts are excluded.

## Evidence and commands

- [Run manifest and exact source-image verification](qualification/clearscan_competitive/run-manifest.json).
- [Reproduction commands, settings and measurement contracts](qualification/clearscan_competitive/README.md).
- [Machine-readable common scorecard](qualification/clearscan_competitive/scorecard.json).
- [300 DPI native/enlarged examples](qualification/clearscan_competitive/300/final-best-800pct.png) and [worst examples](qualification/clearscan_competitive/300/final-worst-800pct.png).
- [Independent implementation review](qualification/clearscan_competitive/final-review.md) and [known-font control review](qualification/clearscan_competitive/oracle-control-review.md).

The older frozen three-page benchmark is reported separately with same-input Adobe/current/previous results; it is never substituted for the eight-page comparison. Both Poppler and PDFium, OCR errors and visual identity diagnostics remain separate.
