# Supplemental independent review — known-outline control

## Matched-population result

I compared the 300 DPI evaluator-only `oracle-assembly.pdf` against exactly the 515 `id`s recorded as emitted vector occurrences in `300/final/stages/stage-errors.json`. All 515 accepted IDs occur exactly once in `300/oracle-assembly.json`; there are no missing or extra accepted IDs in this comparison. Crops use each truth glyph box with the existing 5 px isolation inset and the same 170 threshold, and render with PDFium at `nextafter(300/72, 0)`.

| Same 515 accepted occurrences | Mean isolated IoU to PIL pristine | Mean source IoU |
|---|---:|---:|
| Source scan | 0.94443 | — |
| Final ScanWeave PDF | 0.91626 | — |
| Known-outline oracle PDF | 0.83966 | — |

Thus the approximately 0.84 oracle number is not caused by averaging in fallback-only glyphs. It applies to the same accepted set and remains materially below both source (about 0.105) and final ScanWeave output (about 0.077).

Per-character oracle/source means show broad variation: `e` 0.774/0.948, `8` 0.830/0.947, `a` 0.816/0.942, `g` 0.847/0.948, `6` 0.846/0.945, `0` 0.914/0.950, `;` 0.878/0.953, `?` 0.799/0.939. Punctuation and kana sample counts are small. A local ±4 pixel translation search raises the matched aggregate only from 0.8397 to 0.8656 (mean selected offset 0 px horizontally, +0.43 px vertically), so a one-pixel origin correction explains part but not most of the gap.

## What the control proves and does not prove

`oracle_assembly.py` maps the exact visible accepted spans to their known Unicode characters, copies/decomposes the corresponding source TrueType outlines into the already embedded font, and substitutes the fixture's known nominal positions and baselines. This is a valid evaluator-only control for the combination of its font-program rewrite, positioning recipe, PDF assembly, PDFium rendering, and PIL-generated bitmap target. It is not a clean test of the reconstruction algorithm alone.

The generator and oracle script both use Pillow/FreeType text metrics for nominal advances, and the oracle script uses the nominal source font design outline. But the oracle rewrites each outline through `TTGlyphPen` without carrying the source glyph's hinting bytecode; it also leaves the synthetic embedded font's global hinting tables in place. The pristine bitmap was produced by Pillow/FreeType at a fixed pixel size with the source font's rasterization behavior. At this small print size the unhinted PDF vector and hinted Pillow bitmap can differ substantially even when design outline identity is correct. This is the leading confound requested for the control, and the 0.84 score must not be described as evidence that the source design outline is geometrically wrong.

An isolated first `e` has matching thresholded bounds between truth and oracle render, yet its isolated IoU is only 0.746; translating its crop by one pixel vertically raises it to 0.839. This is compatible with edge coverage/hinting differences plus a small phase effect, not a missing or wrong character. The broader per-character deficits persist beyond such translation.

The existing S3 nominal-witness measure is a different population/control: it rasterizes the already embedded reconstructed prototype at each page's witness geometry, then scores against the witness's pristine crop. Its 300 DPI mean 0.947 therefore shows that the current traced outlines can reproduce their source-like witness raster reasonably well under the measured renderer; it does not validate the known-outline injection, because it neither uses the source design outlines nor the generator's actual target positions. Do not use S3 to claim that the oracle control should score near 1.

## Recommendation for interpreting the oracle arm

Keep the current result as a bounded PDF-assembly and nominal-placement diagnostic. For a causal design-outline control, add a separate renderer-matched pristine reference: place the original source fonts (including their own font-wide hinting tables and glyph instructions) into a PDF using the same physical-size matrices and source baseline, then render with the same PDFium version/scale. Alternatively compare unhinted design-outline geometry in font coordinates before rasterization. Report the PIL bitmap score as a rasterizer-inclusive result. Do not use the present 0.84 score alone to assign the remaining competitive gap to placement, outlines, or ScanWeave reconstruction.

## Follow-up: full original-font program control

To remove the missing-font-program concern, `source_font_control.py` creates a second evaluator-only arm from the current 300 DPI final PDF. It preserves the complete source TTF bytes (including `fpgm`, `prep`, and `cvt ` tables), adds separate Latin and kana CID font resources, maps existing 2-byte CIDs through the retained ToUnicode map to original source GIDs, sets `/W` widths and descriptor ascent/descent/cap height/bounds in 1000/upem units, and substitutes the fixture's known nominal character positions. The ordinary ScanWeave font resource remains in place for invisible OCR CIDs; ActualText, page images, paint colors, and page geometry remain from the input PDF. The exact source-font byte hashes embedded in the output match their licensed fixture files.

Reproduce with:

```sh
/tmp/scanweave-competitive-venv/bin/python qualification/clearscan_competitive/source_font_control.py 300 qualification/clearscan_competitive/300/clearscan.pdf
/tmp/scanweave-competitive-venv/bin/python qualification/clearscan_competitive/measure_source_font_control.py
```

The generated eight-page PDF is 6,642,247 B, SHA-256 `e9775086f98ad5969db871a688b6e0fd3789ae859598e229120fd77face655fc`. `pdfinfo` reports 8 pages at 432 × 216 pt; Poppler lists embedded CID TrueType resources; pikepdf opens and parses it; Poppler 24.02.0 and PDFium 156.0.8076.0 both render it and both extract the supplied OCR after whitespace normalization. `qpdf` CLI is unavailable in this environment, so no separate qpdf --check result is claimed. Measurements and per-occurrence records are in `300/source-font-control/metrics.json`; PNGs for both renderers are preserved there.

On the **same 515 accepted occurrences**, source-font control means are 0.8581 Poppler / 0.8282 PDFium, compared with source 0.9444 and current final ScanWeave 0.9443 / 0.9163. The earlier outline-injection control measured 0.8397 PDFium on this set. Restoring full original font programs did not close the gap; the source-font PDF control is slightly lower by this thresholded metric. This rules out dropped per-glyph hinting bytecode as the explanation for the earlier low score (the source files have no per-glyph instruction programs, but the full global hint tables are present in this arm). It does not rule out different behavior between PIL's FreeType bitmap rasterization and Poppler/PDFium's PDF font rasterization, nor establish that the current ScanWeave outline is closer in design geometry. It establishes that the original licensed design outlines, in this PDF placement/rasterization path, do not reproduce the PIL pristine bitmap as closely as the current trace-derived output does.

The input OCR extraction remains correct, so this font substitution did not alter semantic text transport. Keep this as an evaluator-only control. Do not treat its lower raster IoU as proof the source font's design is wrong or as a competitive win on typographic quality; it is a direct demonstration that bitmap-relative scores mix outline geometry with font rasterizer and positioning behavior. Future design-outline claims need a renderer-matched reference or vector-space contour comparison alongside bitmap IoU.
