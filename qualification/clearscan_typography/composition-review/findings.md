# S4 → S5 paired-pixel diagnosis (300 DPI)

## Scope and method

This is a read-only diagnosis of the existing matched 300 DPI artifacts. The script does not regenerate canonical PDFs or modify converter code. It loads the frozen S4 vector-only, S5 final, and raster-only PDFs; renders all three with PDFium at `nextafter(300/72, 0)`; and independently renders S4/S5 with integer-DPI Poppler (`pdftoppm -r 300`). It compares all 515 nonspace emitted occurrences in truth-bbox crops inset by 5 px, using the benchmark's `<170` dark threshold. Each S4→S5 threshold change is also checked against the pristine oracle, original scan samples, and raster-only render. Inputs and SHA-256 hashes are in `paired-pixels.json`.

Run from the repository root:

```sh
/tmp/scanweave-competitive-venv/bin/python qualification/clearscan_typography/composition-review/paired_pixels.py
```

## Findings

The PDFium paired score reproduces the frozen stage result: S4 mean IoU is `0.93455`, S5 is `0.91626`, and the mean delta is `-0.01829` over 515 emitted occurrences. The change is entirely one-directional at the threshold: there are 3,778 S4-light/S5-dark samples and no S4-dark/S5-light samples. Only 195 of those new dark samples overlap pristine dark pixels; 107 overlap source pixels already below 170.

This is strongly renderer-dependent. On Poppler's integer-DPI render the same 515 crops score `0.94430` for both S4 and S5, with zero threshold crossings, despite 195,250 grayscale samples changing. Thus the PDFium score loss is not evidence that S5 drops glyph strokes or that the vector outlines move. It is a threshold crossing at antialiased edges under a different page background/rendering combination.

The changed PDFium samples have the signature of ordinary antialiased text composited over the raster paper layer. At the newly dark samples, mean S4 gray is `170.91`, mean S5 gray is `167.48`, and mean raster-only gray is `248.11`. The elementary alpha-over-background prediction `S4 × raster_only / 255` has mean absolute error `1.23` gray levels at these samples. The raster-only layer itself contributes zero samples below 170 in these crops. The substrate is near-white, not dark residual glyph ink; its small gray offset moves borderline vector edge samples across the strict threshold.

The largest losses are on pages 2 and 5 (DejaVu Serif): page 2 averages `−0.05494` over 66 crops and page 5 `−0.04755` over 67. Their 2,345 new dark samples include 31 pristine-dark pixels; the mean raster-only gray at those new-dark positions is `249.71`, and the alpha-over-background prediction has mean absolute error `1.24`. The worst examples are repeated `;`, `?`, `0`, `g`, `8`, and `6` occurrences. This is not uniquely an italic-punctuation issue.

On the requested italic pages 6–7 (Liberation Serif Italic), the paired mean delta is only `−0.00371` across 107 crops. They have 218 new dark samples, 50 pristine-dark, and 13 source-dark; mean S4/S5/raster-only intensities at those new-dark pixels are `175.50` / `165.59` / `239.42`, and the alpha-over-background model MAE is `0.88`. The larger individual losses are italic `6` (page 6, `−0.09074`), `g` (`−0.08096`), `0` (`−0.05184`), and semicolon on page 7 (`−0.04131`). Their pixel deltas have the same edge-compositing signature. A few of the changed edge pixels correspond to pristine ink; most are threshold-darkened outside the oracle's `<170` mask.

The tested crops are inset from the pristine glyph bounding boxes, so broad adjacent-character contamination is not the explanation. Nor does the raster-only control show dark text reappearing over the vectors. Instead, the PDFium threshold penalizes vector antialias samples after they are composited over a slightly gray, retained paper sample, while Poppler's threshold metric does not.

## Recommendation

Do not change the compositor or whiten glyph rectangles based on this result. Doing so would remove legitimate local paper texture to improve a renderer- and threshold-sensitive metric. Keep the S4→S5 result as a renderer-specific diagnostic, and report glyph geometry separately from final-page appearance. If a future product requirement demands invariant glyph edge appearance across paper texture, evaluate a tightly bounded, alpha-aware background neutralization under the actual emitted glyph coverage, with the surrounding page untouched; this experiment does not establish that as a beneficial product change.

No reconstruction or converter code was edited. `paired_pixels.py`, `paired-pixels.json`, `crops.png`, and this report are the only artifacts created for this review.
