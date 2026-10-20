# Design-space contour review

## Scope and binding

This is an evaluator-only comparison of source-font and embedded ScanWeave TrueType design outlines. It uses the generator's nominal placement, the original licensed source fonts, and the actual embedded CID-to-GID mappings and text matrices recovered by `audit.py`. No Adobe outline parser or product code was used to compute the geometry metrics.

The full-population comparison covers 515 emitted occurrences at 300 DPI. The source-font control PDF has SHA-256 `e9775086f98ad5969db871a688b6e0fd3789ae859598e229120fd77face655fc` (recorded in the JSON). The geometry-scored final PDF is preserved as `300/source-gate-trial/final.pdf`, SHA-256 `f2ec4e0425869eaba5a3bc4ec41ec583b0e9342ce3990abf6236e3e45e515aa5`. The subsequent private semantic-owner glyph changed the final PDF hash to `4ec9b5ea1520eb364a6f232af51ca8f4b60f6db6aedd86d8b27bbdbb846110ce`; `geometry-binding.json` confirms all 515 painted 300-DPI visible outlines and placements are identical across these files. The source-control/previous/fit measurements are in `design-geometry-control-previous-fit.json`; the final candidate measurements are in `design-geometry-300-final.json`. The bounded paired stem-width samples are in `design-geometry-300-final-representative.json` (final) and `design-geometry-300-representative.json` (previous).

The original-font control uses the full licensed source programs and their original outlines, not contours reconstructed from raster samples. Across 514 identity-matched instances, source-to-control symmetric boundary Chamfer is effectively zero: mean `7.07e-7 px`, median `6.73e-7 px`, and aggregate boundary p95 `6.32e-6 px`. Mean absolute signed-area bias is `3.44e-13`. One apparent control instance was excluded and recorded: page 7 `p07s0000` has oracle text `e`, while its retained OCR CID maps to original italic-font GID/name `c`. That is a source-control text-code mismatch, not a contour error.

## Full-population design geometry

All three ScanWeave arms contain 515 occurrences and no geometry extraction failures.

| Arm | Mean symmetric Chamfer | p95 boundary distance (mean of per-occurrence p95s) | Mean absolute signed-area bias | Mean translation-only improvement |
|---|---:|---:|---:|---:|
| Previous outline | 0.3899 px | 0.9133 px | 10.35% | 0.0797 px |
| Coverage-fit trial | 0.3659 px | 0.8942 px | 3.23% | 0.0787 px |
| Guarded final | 0.3690 px | 0.8986 px | 4.33% | 0.0796 px |

The coverage-fit trial is the strongest of these three on the aggregate boundary metric. The final guarded build is close but slightly worse than that trial, consistent with the fidelity guard retaining some old outlines. Both improve meaningfully over the previous outline in area calibration and mean boundary distance. The final must not be described as matching pristine vector geometry: its mean symmetric boundary error remains about `0.37 px`; sampled characters commonly range around `0.25–0.45 px`.

Per-character area calibration improves strongly on the coverage-fit trial for `6` (mean absolute bias `8.90%` to `0.69%`), `8` (`11.32%` to `2.49%`), and comma (`16.81%` to `7.26%`). Boundary distance improves more modestly. The grayscale fit therefore appears to improve contour size/stroke coverage more than it recovers the exact source curve geometry.

The translation-only diagnostic tests fixed `dx,dy` shifts on a 0.5 px grid within ±1 px, without scale or box fitting. Its mean gain is about `0.08 px` for all arms. This indicates a smaller placement component in addition to contour-shape error; the fitting change does not resolve placement. The diagnostic is not folded into the primary score.

## Representative stem-width sample

To keep cross-section evaluation bounded, the script scores at most five instances each of `e`, `6`, `8`, `g`, punctuation, italic `a`, and available kana. The representative set is 43 instances per arm. A source interval is included only when its width is `0.7–6 px` and its left/right edges vary by less than `0.25 px` across ±`0.25 px` vertically. At the same y, the nearest overlapping embedded interval is matched by center; unmatched intervals are reported separately.

The source-font control has 6,316 intervals, zero missing intervals, and mean absolute width error below `1e-12 px`, confirming the interval pairing/control. In the paired previous versus guarded-final sample, the previous has 6,029 matched intervals and 287 unmatched; the final has 6,060 matched and 256 unmatched. Mean signed width error falls from `+0.423 px` to `+0.218 px` (embedded minus source), and mean absolute error falls from `0.539 px` to `0.433 px`. The positive bias remains: reconstructed strokes tend to be thicker. The simple center-based matcher and unmatched intervals make this diagnostic descriptive, not a complete stem-quality metric. By character in the final sample, mean absolute error is `0.33 px` for `8`, `0.45 px` for `e`, `0.52 px` for `6`, and `0.62–0.70 px` for the four two-instance kana groups. The sample is too small to generalize those kana values.

## Method limits

- Curves are flattened at maximum nominal spacing `0.18 px`; nearest-point distances and scanline interval matching are sampled approximations.
- Source placement uses the fixture generator's exact nominal x, baseline, and size; these values intentionally use the generator-compatible Pillow metrics. No independent bbox rescaling is applied.
- Embedded placement uses each PDF's actual MediaBox, text matrix, CID-to-GID mapping, and embedded font program.
- Hinting, antialiasing, and renderer snapping are deliberately excluded. Those are raster-space effects and would confound the requested design-contour measurement.
- The source-font control has one identity mismatch as detailed above. Control statistics exclude it; ScanWeave arms are not filtered for glyph mismatch.
- The stem-width cross-sections are a narrow diagnostic, not evidence about all strokes, cursive transitions, or diagonal/curved stems.

## Code review notes

The changed ClearScan path is gated by `policy.profile == "clearscan"`. Faithful dispatches to the existing `trace_shape`; ClearScan's fitter uses no OCR label or source font program, and `grayscale_fit_never_uses_the_ocr_label` checks this property. Candidate geometry must pass the existing `0.90` local ink-IoU gate, the topology check, and—when an unreplaced local sharing that exact shape key exists—a source-preservation floor no lower than the baseline's acceptance. The latter is a sound bounded guard for the observed real-page regressions.

The follow-up semantic-owner change is also ClearScan-only. Hidden characters use separate CIDs bound to one stable frame; the document font union deduplicates and remaps it normally. All515 visible300DPI outline hashes, text matrices and boxes remain unchanged. An initial200-unit frame caused positional Poppler layout sorting errors despite correct raw extraction; that trial is superseded. The completed full-em frame was independently rechecked: all eight300DPI pages have matching normalized raw/layout text in supplied OCR order, and receipt cord00 has identical423-character native PDFium/Poppler text. See [owner-frame-review.md](owner-frame-review.md) for exact final hashes and the completed checks.

The offset implementation's normal signs and fixed crop frame are covered by tests for zero-offset equivalence, outer inset/counter expansion, and topology validity. The remaining geometric caution is that `contour_topology::valid` rejects intersections and outside holes but does not explicitly reject one disconnected outer component wholly contained inside another without edge crossings. The unchanged component count and source IoU gate reduce the risk, but an explicit outer-component containment check would make the topology contract complete if nested/disjoint component failures are observed.

No blocking correctness issue was found in the current candidate scoring, normal direction, construction-frame conversion, or faithful-mode isolation. The main quality limitation supported by these measurements is residual contour bias/shape error, especially in thin strokes and kana; avoid presenting the modest raster score changes as pristine-outline parity.
