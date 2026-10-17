# M1-D5 bounded oracle qualification

## Disposition: CONTINUE RESEARCH

This run demonstrates donor-supported glyph repair in the existing controlled
12-page fixture, but does not qualify a restoration profile. The prior metrics
mixed source-raster masks with final-PDF renders. Those metrics are superseded by
the matched-render results in `dpi300/evaluation.json` and
`dpi600/evaluation.json`. The 300-DPI local fallback-render gap remains a real
output issue after correcting the evaluator.

No LOCKBOX was opened. No real-document scan corpus is present in the checkout;
SROIE, CORD, OCR-D and DIBCO adapters/data were not used. The installed-font
synthetic fixture is not a substitute for real-domain validation. `ocrmypdf`
and `recode_pdf` are not installed, so external searchable-raster/MRC comparisons
were unavailable.

## Experiment inventory and leakage boundary

The inherited development fixture has 12 pages each at 300 and 600 DPI and uses
DejaVu Serif plus Liberation Serif Italic. It includes damaged `e`, `a`, and `8`,
intact donor examples on sibling pages, a distinct italic style, a protected
financial string, and an OCR `e` labeled `c`. The evaluator has pristine pages;
the reconstruction call receives only the degraded RGB page and supplied OCR
geometry/text. No source outline is loaded by the reconstruction path.

The damage generator currently uses rectangular white knockouts. This provides
controlled positive/negative cases but does not meet the requested physical
realism standard. It cannot support photorealistic or generalization claims.
There are no independent document/font/degradation FIT and DEV cohorts, so the
current donor thresholds are not risk-calibrated. No acceptance-policy tuning
was done against LOCKBOX.

## Matched PDF comparison

A0 is the pristine raster PDF rendered by Poppler; A1 is the degraded searchable
raster PDF; A2 is faithful mode; A3 is the existing best-donor ClearScan
candidate. A4 evidence fusion is not implemented or run. A5 calibrated
acceptance is not implemented; under the current 0.98 automatic-selection
policy, the raster baseline is selected. Therefore the output does not yet
represent a candidate trained/calibrated according to this qualification
protocol.

Per-glyph values below are binarized IoU in the OCR box, with every PDF arm
rendered at the same resolution by Poppler. The direct scan comparison is kept
separate. These measurements show local glyph appearance, not a full-page
quality score.

| DPI | Glyph | Direct scan vs pristine raster | A1 vs A0 PDF | A2 faithful vs A0 | A2 vs A1 | A3 best donor vs A0 | A3 gain vs A1 |
|---:|:---:|---:|---:|---:|---:|---:|---:|
| 300 | `e` | .831 | .829 | .765 | .905 | .918 | +.090 |
| 300 | `a` | .836 | .833 | .674 | .786 | .931 | +.097 |
| 300 | `8` | .912 | .911 | .776 | .841 | .732 (raster fallback) | -.180 |
| 600 | `e` | .847 | .847 | .812 | .951 | .958 | +.111 |
| 600 | `a` | .829 | .831 | .810 | .966 | .967 | +.137 |
| 600 | `8` | .913 | .912 | .844 | .918 | .918 | +.006 |

Best-donor `e` and `a` repairs improve the final PDF appearance at both DPIs.
The 600-DPI `8` improvement is marginal. The existing faithful arm also scores
poorly against pristine and raster-baseline appearance in these glyph boxes.
This does not prove why that loss occurs, but it means faithful-mode
preservation is not qualified by this experiment. Keep faithful behavior
unchanged until that rendering path is independently fixed and verified.

There are zero observed false substitutions among the accepted damaged-glyph
cases and no mixed-style prototype groups in this small fixture. The protected
amount remains raster-owned; the visual `e` labeled `c` is not repaired. These
counts are not a sufficient estimate of false-substitution risk. Search text is
equal across the generated modes. PDFium search, qpdf, OTS and fontTools checks
pass on the recorded artifacts.

## Fallback-render anomaly

`diagnose_m1d5_fallback.py` compares the 300-DPI `8` using matching page
coordinates and records the embedded image bytes and PDF transform. The local
fallback XObject is byte-for-byte the source crop `[316,47,351,99]`; the
diagnostic binds page 1 `/Im0` to its 35x52 image object and adjacent `cm`/`Do`
operation, which maps it to `[75.84,11.28,84.24,23.76]` points. Thus the
previous raw-source-vs-PDF comparison was indeed an evaluator mismatch, but it
does not explain the remaining difference between local patch output and the
whole-page raster baseline:

- Raw scan vs pristine raster IoU: `.912`.
- A1 whole-page raster PDF vs A0: `.911`.
- ClearScan local-patch PDF vs A0: `.732`.
- Under PDFium, A1 vs A0 is `.913`, while ClearScan is `.768`.
- Translating the rendered patch up one output pixel, for diagnosis only,
  raises IoU to `.822`; original placement remains the scored result.

The crop, resource binding and affine values are correct, while local-XObject
rendering does not match whole-page raster sampling in either Poppler or
PDFium. This implicates an interaction between local-patch placement and the
renderers, but the root cause is unconfirmed. The issue remains unresolved and
blocks profile promotion. The diagnostic translation is not applied to
production output.

PDFium also differs from Poppler in nominal glyph IoU; details are retained in
the JSON files. A cross-renderer vector appearance claim is not made.

## PDF size and coverage

| DPI | ClearScan A3 | A1 raster baseline | Delta (A1 - A3) | Embedded font | Vector text-ink coverage |
|---:|---:|---:|---:|---:|---:|
| 300 | 104,188 B | 72,591 B | -31,597 B | 7,116 B | 2.23% |
| 600 | 173,180 B | 143,927 B | -29,253 B | 10,920 B | 3.98% |

No repeated intact occurrences pass the existing unchanged-text reuse gate
(0.98 source-mask IoU): 33 candidates are rejected at each DPI. Compression
therefore fails, and forced A3 output is larger than A1. In normal automatic
selection, the raster candidate avoids emitting this larger reconstruction.

## Reproduction

```sh
cargo test -p m0-font-pdf --test m1d_document -- --nocapture
qualification/.venv/bin/python qualification/evaluate_m1d_document.py
qualification/.venv/bin/python qualification/diagnose_m1d5_fallback.py
cargo test --workspace
qualification/checks.py --out /tmp/m1d5-checks.json
```

The prior E0-E7 suite passed. The inherited P01-P08 visual/transport failures
remain recorded separately and are not attributed to this change. There is no
real-domain result, physical degradation validation, calibrated A5 policy,
evidence-fusion arm, qualified faithful arm, or compression benefit. These
open items prevent promotion; continue only with a patch-rendering correction,
independent FIT/DEV corpus, realistic degradation calibration, and risk/coverage
validation before any LOCKBOX request.
