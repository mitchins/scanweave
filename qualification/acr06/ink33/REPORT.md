# Issue 33 — ink tone and character consistency study

Research only; product code was not changed. Recommendation: **no change warranted on this evidence**. Word-level source-colour substitution is a useful research hypothesis but is not safe to adopt as measured: on historical mixed lines it moved 42 of 44 matched vector characters closer to source tone, yet moved two farther away, increased the median magnitude of the vector–raster gap, and lowered median whole-line SSIM. On receipts it moved 24 of 42 farther away. Correct character restoration and historical appearance remain mandatory; no black-forcing or other implementation is authorised by this study.

## Inputs and reproducibility

All five source, Adobe XI, Archive MRC reference, ScanWeave and counterfactual PDFs are hashed in [provenance.json](provenance.json). Main was `9655fccc1b9e2ce479dd95d06b5f48ea2bfc0e6d`, built with `cargo build --release --locked -p scanweave-cli`; generated at 300 DPI with `--profile clearscan --glyph-sharing off`. Historical, financial, mixed and receipts fresh PDFs match the saved baselines byte-for-byte. Forms does not: the old baseline SHA-256 is `1aa7b517618cf129b976d26aa7dd781e838bac79e96380e14b7ad74f2d0c0639`, and fresh main is `75dfda81cef2a5857328ede7dd76279d72e65a838fb6d352b7f6ea6673d383ff`. Both decompressed forms page content streams match, but the cause of the container-level hash difference was not resolved; all forms analysis uses fresh main and its OCR report. Archive MRC is hashed as reference only, not included in measurements.

## Mechanism

At main, `crates/scanweave-io/src/mask.rs:21–90` estimates paper from four 6×6 corners, classifies foreground using absolute luminance distance >60, and takes the per-channel median of page-wide foreground as `ink`. `convert.rs:793` runs segmentation and `convert.rs:1941` passes `seg.ink`; `page_pdf.rs:619–659` sets one RGB fill before page text runs. `page_pdf.rs:570–597` paints image patches separately; raster-retained details are carried in those image samples and do not receive the vector fill. Raster recomposition/encoding can still alter samples, so pixel identity is not presumed. Text render mode 3 is invisible; mode 0 is filled.

The PDF graphics-state audit ([script](operator_audit.py), [data](operator-audit.json)) tracks `g`, `rg`, `k`, `cs`, `sc`, `scn`, `Tr`, and `q/Q` at every show operator. No page invoked Form XObjects. Each ScanWeave page with visible text has exactly one visible fill. Historical page 2 uses RGB approximately (236,217,172); its paper rectangle is (1,1,1). This is consistent with the absolute-difference segmentation mechanism on dark corners, not proof of the source ink for a given glyph. Three historical pages contain no visible ScanWeave text shows and cannot provide mixed lines.

## Method and limitations

PDFium rendered source, ScanWeave, Adobe XI and each edited PDF at 300 DPI. Tesseract hOCR symbol and word boxes from the actual ScanWeave run provide a common coordinate frame. Visible ScanWeave PDFium text objects are greedily matched one-to-one to character boxes using intersection/union after requiring at least 35% of object area and 12% of character area in common. An unmatched OCR character intersecting a visible object by at least 12% is excluded as ambiguous; remaining characters are treated as raster-retained. This is an operational classification, not ground-truth ownership. Unmatched objects and overlapping/tiny/OCR-error boxes can cause missed mixed lines or residual misclassification; no claim is made that the detected counts exhaust all true mixed lines. Mixed-line counts and exclusions are below. The analysis compares the same source OCR boxes in all methods; Adobe can recognize or replace a different character, so the comparison does not establish recognition correctness.

Adobe may deskew: its page render and object boxes are registered to the source by ORB feature matches and RANSAC affine fitting; matrices, inlier counts and residuals are in `prepare-*.json`. Adobe renders are resampled bilinearly, which can alter edge and tone measurements. Other renders use the unshifted source coordinate system. PDFium supplies object geometry and Poppler checks extraction; the panels show registered Adobe. No visual registration can guarantee character-perfect matching on every box.
Across 32 pages, 32 used affine feature registration and 0 used translation fallback. Median across pages of the inlier median residual was 0.86 px, and the largest page inlier p90 residual was 3.19 px at 300 DPI. These are feature residuals, not per-character ground truth.

For each usable box, luminance is 0–255 Rec. 709-weighted RGB. Local background is the 85th percentile; ink candidates are at least 10 units darker; core is the median of the darkest 30% of those candidates. Boxes without at least three candidates or 10 units contrast are excluded for that method. Coverage is the fraction below the midpoint of that method’s own core and background; it is a contrast-normalised stroke-density proxy, not a direct stroke-width measurement. Edge width is 0.8×contrast divided by the median gradient magnitude at pixels between 10% and 90% of the estimated transition: a gradient-width proxy in 300-DPI pixels, not a traced edge-rise distance. Outline roughness is `(4-neighbour perimeter − perimeter after σ=0.65 px Gaussian mask smoothing) / smoothed perimeter`; it is a pixel-scale shape/roughness proxy, not a pure measure of typographic smoothness. Small boxes, thresholding, OCR overlap, nearby marks, resampling and different glyph shapes affect these measures. The measurements use the composite page image: a box assigned to a vector object can also contain retained raster ink or a neighbour, so its core need not be the vector fill alone. A whole-line grayscale SSIM compares the source and output in the OCR line box padded by two pixels, with data range 255. Higher SSIM is more similar, but registration and paper changes also affect it.

Each line’s dispersion is the interquartile range (IQR) of character core tones. The vector−raster gap is the difference of the two class medians; negative means vector is darker. For source and Adobe, the same classes refer to ScanWeave ownership, not their own ownership. Tables give the 10th/50th/90th percentiles across mixed lines, except character error, which is pooled across usable characters on mixed lines. Word-run results include every usable OCR word on mixed lines; mixed-word gaps require both classes within the word. Raw per-character files are split into chunks of at most 500, and per-line/word records are in `metrics-<document>-<page>.json`.

| Document | Detected mixed lines | Mixed words | Matched visible objects / all | Ambiguous symbols excluded | SW / Adobe overlap coverage |
|---|---:|---:|---:|---:|---:|
| historical | 24 | 25 | 44/58 | 3 | 4.0% / 95.8% |
| financial | 298 | 1 | 3611/3717 | 128 | 43.0% / 99.5% |
| mixed | 62 | 0 | 809/1266 | 70 | 30.0% / 99.2% |
| receipts | 13 | 1 | 57/82 | 3 | 29.0% / 95.9% |
| forms | 48 | 5 | 504/504 | 202 | 24.6% / 94.1% |

Coverage is the fraction of measured characters on mixed lines classified as ScanWeave vector or intersecting any Adobe visible text-object box. Adobe box intersection can overcount: it is not a pixel mask or ground-truth vector character count. The historical sample has only 44 confidently matched vector characters. Counts are not independent samples; lines and characters within a document are correlated.

## Results by document

### Historical

| Output | Line tone IQR | Line vector−raster gap | Character absolute tone error | Line SSIM | Word tone IQR | Mixed-word gap |
|---|---:|---:|---:|---:|---:|---:|
| Source | 4.1/5.6/7.7 | -6.3/-0.7/5.0 | 0.0/0.0/0.0 | 1.000/1.000/1.000 | 1.3/3.3/6.7 | -4.8/0.2/4.8 |
| ScanWeave | 4.4/5.7/13.4 | -6.6/-2.2/3.7 | 3.6/6.1/10.9 | 0.916/0.948/0.952 | 1.3/3.4/8.2 | -6.5/-1.5/3.1 |
| Adobe XI | 0.0/0.0/0.0 | 0.0/0.0/0.0 | 1.0/5.1/10.5 | 0.734/0.797/0.818 | 0.0/0.0/0.0 | 0.0/0.0/0.0 |
| A: line | 4.5/6.1/15.0 | -12.2/-5.9/-2.5 | 3.2/6.0/10.6 | 0.913/0.940/0.949 | 1.2/3.6/8.7 | -13.2/-5.4/-2.5 |
| B: word | 4.5/6.1/15.0 | -13.1/-7.0/-2.4 | 3.2/6.0/10.6 | 0.913/0.940/0.949 | 1.3/3.6/8.6 | -12.6/-5.9/-3.0 |
| C: Adobe transfer | 4.3/5.7/13.0 | -4.4/-2.5/-0.7 | 3.5/6.0/10.9 | 0.914/0.940/0.949 | 1.2/3.4/8.2 | -6.2/-1.5/1.8 |

All cells are p10/p50/p90; tone units are 0–255. A dash means insufficient usable observations. Word IQR includes single-class words on mixed lines; the mixed-word gap has the much smaller sample above.

| Output | Vector coverage within box | Raster coverage within box | Vector edge width, px | Raster edge width, px | Vector roughness | Raster roughness |
|---|---:|---:|---:|---:|---:|---:|
| Source | 0.423/0.476/0.576 | 0.389/0.429/0.453 | 2.00/2.45/2.96 | 2.02/2.50/2.61 | 0.000/0.000/0.027 | 0.000/0.000/0.000 |
| ScanWeave | 0.406/0.462/0.556 | 0.395/0.436/0.466 | 2.21/2.43/2.84 | 2.38/2.64/2.72 | 0.000/0.003/0.030 | 0.000/0.000/0.000 |
| Adobe XI | 0.425/0.493/0.582 | 0.397/0.441/0.464 | 1.69/1.81/2.18 | 1.75/1.81/1.86 | 0.000/0.000/0.006 | 0.000/0.000/0.000 |
| A: line | 0.472/0.586/0.720 | 0.395/0.436/0.468 | 2.41/2.72/3.73 | 2.38/2.64/2.73 | 0.000/0.000/0.017 | 0.000/0.000/0.000 |
| B: word | 0.472/0.587/0.720 | 0.395/0.436/0.468 | 2.42/2.79/3.91 | 2.38/2.64/2.73 | 0.000/0.000/0.017 | 0.000/0.000/0.000 |
| C: Adobe transfer | 0.473/0.593/0.724 | 0.395/0.436/0.468 | 2.26/2.61/3.69 | 2.38/2.64/2.73 | 0.000/0.000/0.009 | 0.000/0.000/0.000 |

These are p10/p50/p90 of the per-line class medians, using the same ScanWeave-derived vector/raster grouping for every output. Roughness is a threshold-mask perimeter proxy; zero does not imply a mathematically smooth contour.

- A: of 44 paired vector characters, 37 moved closer to source, 7 farther, and 0 had unchanged absolute error; 15 ended >1 luminance unit darker than source and 23 >1 lighter. Signed change p10/p50/p90: -8.6/-4.7/-0.4.
- B: of 44 paired vector characters, 42 moved closer to source, 2 farther, and 0 had unchanged absolute error; 15 ended >1 luminance unit darker than source and 14 >1 lighter. Signed change p10/p50/p90: -10.1/-5.2/-2.4.
- C: of 44 paired vector characters, 22 moved closer to source, 21 farther, and 1 had unchanged absolute error; 1 ended >1 luminance unit darker than source and 39 >1 lighter. Signed change p10/p50/p90: -4.7/-0.0/2.6.

### Financial

| Output | Line tone IQR | Line vector−raster gap | Character absolute tone error | Line SSIM | Word tone IQR | Mixed-word gap |
|---|---:|---:|---:|---:|---:|---:|
| Source | 3.9/6.8/10.0 | -5.2/0.9/8.5 | 0.0/0.0/0.0 | 1.000/1.000/1.000 | 1.0/3.5/7.1 | 11.1/11.1/11.1 |
| ScanWeave | 0.0/4.7/10.6 | -1.9/4.0/10.7 | 3.7/10.7/18.9 | 0.922/0.943/0.973 | 0.0/0.4/8.2 | 0.0/0.0/0.0 |
| Adobe XI | 0.0/0.0/5.8 | 0.0/0.0/4.2 | 2.4/9.1/16.6 | 0.804/0.873/0.941 | 0.0/0.0/1.0 | 6.5/6.5/6.5 |
| A: line | 1.0/8.9/14.0 | -14.4/-9.0/-4.3 | 1.3/7.0/15.2 | 0.922/0.943/0.972 | 0.0/0.4/8.2 | 0.0/0.0/0.0 |
| B: word | 3.6/8.6/15.4 | -16.4/-8.4/0.4 | 0.4/5.8/14.9 | 0.922/0.943/0.973 | 0.0/0.4/8.2 | 0.0/0.0/0.0 |
| C: Adobe transfer | 0.1/4.1/8.9 | -5.0/-0.1/6.0 | 2.9/9.1/16.6 | 0.922/0.943/0.973 | 0.0/0.4/8.2 | 0.0/0.0/0.0 |

All cells are p10/p50/p90; tone units are 0–255. A dash means insufficient usable observations. Word IQR includes single-class words on mixed lines; the mixed-word gap has the much smaller sample above.

| Output | Vector coverage within box | Raster coverage within box | Vector edge width, px | Raster edge width, px | Vector roughness | Raster roughness |
|---|---:|---:|---:|---:|---:|---:|
| Source | 0.307/0.355/0.433 | 0.299/0.348/0.404 | 1.57/1.61/1.72 | 1.57/1.61/1.68 | 0.000/0.000/0.010 | 0.000/0.000/0.008 |
| ScanWeave | 0.323/0.369/0.444 | 0.314/0.358/0.407 | 1.39/1.54/1.60 | 2.19/2.26/2.34 | 0.000/0.000/0.005 | 0.000/0.000/0.008 |
| Adobe XI | 0.319/0.363/0.432 | 0.313/0.359/0.404 | 1.74/1.86/2.03 | 1.75/1.85/2.01 | 0.000/0.000/0.000 | 0.000/0.000/0.000 |
| A: line | 0.323/0.369/0.443 | 0.314/0.358/0.407 | 1.38/1.53/1.60 | 2.19/2.26/2.34 | 0.000/0.000/0.006 | 0.000/0.000/0.008 |
| B: word | 0.323/0.369/0.444 | 0.314/0.358/0.407 | 1.39/1.53/1.60 | 2.19/2.26/2.34 | 0.000/0.000/0.005 | 0.000/0.000/0.008 |
| C: Adobe transfer | 0.323/0.369/0.444 | 0.314/0.358/0.407 | 1.38/1.54/1.60 | 2.19/2.26/2.34 | 0.000/0.000/0.005 | 0.000/0.000/0.008 |

These are p10/p50/p90 of the per-line class medians, using the same ScanWeave-derived vector/raster grouping for every output. Roughness is a threshold-mask perimeter proxy; zero does not imply a mathematically smooth contour.

- A: of 2699 paired vector characters, 2205 moved closer to source, 494 farther, and 0 had unchanged absolute error; 1245 ended >1 luminance unit darker than source and 1017 >1 lighter. Signed change p10/p50/p90: -17.3/-13.6/-9.0.
- B: of 2699 paired vector characters, 2443 moved closer to source, 256 farther, and 0 had unchanged absolute error; 872 ended >1 luminance unit darker than source and 890 >1 lighter. Signed change p10/p50/p90: -19.7/-12.5/-5.0.
- C: of 2699 paired vector characters, 2257 moved closer to source, 442 farther, and 0 had unchanged absolute error; 174 ended >1 luminance unit darker than source and 2407 >1 lighter. Signed change p10/p50/p90: -9.4/-3.4/0.8.

### Mixed

| Output | Line tone IQR | Line vector−raster gap | Character absolute tone error | Line SSIM | Word tone IQR | Mixed-word gap |
|---|---:|---:|---:|---:|---:|---:|
| Source | 0.0/0.0/12.0 | -1.7/0.0/2.6 | 0.0/0.0/0.0 | 1.000/1.000/1.000 | 0.0/0.0/8.9 | — |
| ScanWeave | 0.0/0.0/13.7 | 0.0/0.0/14.3 | 0.0/0.0/15.2 | 0.908/0.946/0.962 | 0.0/0.0/5.9 | — |
| Adobe XI | 0.0/1.0/1.7 | -0.5/0.0/1.0 | 2.0/9.0/15.0 | 0.783/0.825/0.866 | 0.0/0.3/1.2 | — |
| A: line | 0.0/0.0/6.8 | -4.9/0.0/0.0 | 0.0/0.0/7.0 | 0.908/0.947/0.963 | 0.0/0.0/5.9 | — |
| B: word | 0.0/0.0/9.2 | -5.2/0.0/0.0 | 0.0/0.0/6.1 | 0.908/0.947/0.962 | 0.0/0.0/5.9 | — |
| C: Adobe transfer | 0.0/0.0/8.0 | -1.2/3.5/13.0 | 0.0/0.7/10.4 | 0.908/0.947/0.963 | 0.0/0.0/5.9 | — |

All cells are p10/p50/p90; tone units are 0–255. A dash means insufficient usable observations. Word IQR includes single-class words on mixed lines; the mixed-word gap has the much smaller sample above.

| Output | Vector coverage within box | Raster coverage within box | Vector edge width, px | Raster edge width, px | Vector roughness | Raster roughness |
|---|---:|---:|---:|---:|---:|---:|
| Source | 0.368/0.390/0.424 | 0.365/0.394/0.406 | 1.39/1.50/2.89 | 1.42/1.51/2.92 | 0.000/0.000/0.015 | 0.000/0.000/0.014 |
| ScanWeave | 0.368/0.398/0.472 | 0.366/0.398/0.415 | 1.40/1.56/2.37 | 1.50/1.60/3.01 | 0.000/0.000/0.016 | 0.000/0.000/0.000 |
| Adobe XI | 0.389/0.416/0.450 | 0.379/0.412/0.437 | 1.58/1.68/2.22 | 1.61/1.68/2.14 | 0.000/0.000/0.000 | 0.000/0.000/0.000 |
| A: line | 0.366/0.395/0.472 | 0.366/0.398/0.415 | 1.40/1.56/2.21 | 1.50/1.60/3.01 | 0.000/0.000/0.013 | 0.000/0.000/0.000 |
| B: word | 0.366/0.395/0.472 | 0.366/0.398/0.415 | 1.40/1.56/2.24 | 1.50/1.60/3.01 | 0.000/0.000/0.013 | 0.000/0.000/0.000 |
| C: Adobe transfer | 0.366/0.395/0.472 | 0.366/0.398/0.415 | 1.39/1.56/2.24 | 1.50/1.60/3.01 | 0.000/0.000/0.013 | 0.000/0.000/0.000 |

These are p10/p50/p90 of the per-line class medians, using the same ScanWeave-derived vector/raster grouping for every output. Roughness is a threshold-mask perimeter proxy; zero does not imply a mathematically smooth contour.

- A: of 755 paired vector characters, 393 moved closer to source, 72 farther, and 290 had unchanged absolute error; 213 ended >1 luminance unit darker than source and 202 >1 lighter. Signed change p10/p50/p90: -18.8/-14.6/0.0.
- B: of 755 paired vector characters, 406 moved closer to source, 59 farther, and 290 had unchanged absolute error; 158 ended >1 luminance unit darker than source and 170 >1 lighter. Signed change p10/p50/p90: -20.9/-11.0/0.0.
- C: of 755 paired vector characters, 413 moved closer to source, 310 farther, and 32 had unchanged absolute error; 125 ended >1 luminance unit darker than source and 545 >1 lighter. Signed change p10/p50/p90: -13.1/-11.6/13.0.

### Receipts

| Output | Line tone IQR | Line vector−raster gap | Character absolute tone error | Line SSIM | Word tone IQR | Mixed-word gap |
|---|---:|---:|---:|---:|---:|---:|
| Source | 5.3/8.7/16.9 | -16.9/-6.8/7.0 | 0.0/0.0/0.0 | 1.000/1.000/1.000 | 1.5/4.9/7.8 | -16.0/-16.0/-16.0 |
| ScanWeave | 2.1/6.6/14.2 | -17.5/-6.3/2.2 | 1.0/5.4/21.4 | 0.940/0.966/0.978 | 1.4/4.7/8.0 | -14.0/-14.0/-14.0 |
| Adobe XI | 0.0/2.0/13.4 | -23.7/-2.0/0.8 | 2.0/7.3/23.1 | 0.874/0.895/0.927 | 0.0/0.0/1.6 | 0.0/0.0/0.0 |
| A: line | 4.3/6.2/14.6 | -13.9/-4.4/-0.7 | 1.0/5.1/15.8 | 0.947/0.962/0.976 | 1.4/4.3/6.5 | -12.0/-12.0/-12.0 |
| B: word | 2.6/6.2/14.0 | -18.1/-5.1/1.2 | 1.0/5.3/13.2 | 0.947/0.966/0.977 | 1.4/4.3/6.4 | -10.3/-10.3/-10.3 |
| C: Adobe transfer | 1.3/6.2/14.0 | -16.8/-4.0/4.7 | 1.0/5.5/16.1 | 0.945/0.966/0.977 | 1.4/4.3/6.4 | -10.9/-10.9/-10.9 |

All cells are p10/p50/p90; tone units are 0–255. A dash means insufficient usable observations. Word IQR includes single-class words on mixed lines; the mixed-word gap has the much smaller sample above.

| Output | Vector coverage within box | Raster coverage within box | Vector edge width, px | Raster edge width, px | Vector roughness | Raster roughness |
|---|---:|---:|---:|---:|---:|---:|
| Source | 0.292/0.380/0.544 | 0.357/0.387/0.526 | 1.76/2.40/3.27 | 1.77/2.30/3.15 | 0.000/0.000/0.017 | 0.000/0.000/0.011 |
| ScanWeave | 0.367/0.425/0.613 | 0.398/0.420/0.541 | 1.96/2.88/3.60 | 2.11/2.57/3.11 | 0.000/0.000/0.010 | 0.000/0.000/0.006 |
| Adobe XI | 0.345/0.432/0.579 | 0.345/0.411/0.553 | 1.77/1.92/2.06 | 1.81/1.87/2.00 | 0.000/0.000/0.009 | 0.000/0.000/0.000 |
| A: line | 0.260/0.433/0.591 | 0.398/0.420/0.541 | 1.88/2.70/3.14 | 2.11/2.57/3.11 | 0.000/0.000/0.019 | 0.000/0.000/0.006 |
| B: word | 0.264/0.402/0.587 | 0.398/0.420/0.541 | 1.91/2.68/3.37 | 2.11/2.57/3.11 | 0.000/0.000/0.018 | 0.000/0.000/0.006 |
| C: Adobe transfer | 0.270/0.415/0.587 | 0.398/0.420/0.541 | 1.95/2.63/3.34 | 2.11/2.57/3.11 | 0.000/0.000/0.018 | 0.000/0.000/0.006 |

These are p10/p50/p90 of the per-line class medians, using the same ScanWeave-derived vector/raster grouping for every output. Roughness is a threshold-mask perimeter proxy; zero does not imply a mathematically smooth contour.

- A: of 42 paired vector characters, 15 moved closer to source, 27 farther, and 0 had unchanged absolute error; 13 ended >1 luminance unit darker than source and 29 >1 lighter. Signed change p10/p50/p90: -73.5/0.6/5.5.
- B: of 42 paired vector characters, 17 moved closer to source, 24 farther, and 1 had unchanged absolute error; 7 ended >1 luminance unit darker than source and 30 >1 lighter. Signed change p10/p50/p90: -69.3/1.3/4.3.
- C: of 42 paired vector characters, 9 moved closer to source, 32 farther, and 1 had unchanged absolute error; 3 ended >1 luminance unit darker than source and 38 >1 lighter. Signed change p10/p50/p90: -63.9/1.9/14.8.

### Forms

| Output | Line tone IQR | Line vector−raster gap | Character absolute tone error | Line SSIM | Word tone IQR | Mixed-word gap |
|---|---:|---:|---:|---:|---:|---:|
| Source | 0.0/0.0/0.0 | 0.0/0.0/0.0 | 0.0/0.0/0.0 | 1.000/1.000/1.000 | 0.0/0.0/0.0 | 0.0/0.0/20.4 |
| ScanWeave | 0.0/0.0/5.7 | 0.0/0.0/19.0 | 0.0/0.0/19.0 | 0.964/0.987/0.998 | 0.0/0.0/0.0 | 0.0/0.0/0.0 |
| Adobe XI | 0.0/2.0/7.0 | -4.6/0.0/3.3 | 0.0/7.0/25.0 | 0.750/0.884/0.953 | 0.0/0.0/4.0 | -23.6/0.0/27.0 |
| A: line | 0.0/0.0/0.0 | 0.0/0.0/0.0 | 0.0/0.0/0.0 | 0.964/0.987/0.998 | 0.0/0.0/0.0 | 0.0/0.0/0.0 |
| B: word | 0.0/0.0/0.0 | 0.0/0.0/0.0 | 0.0/0.0/0.0 | 0.964/0.987/0.998 | 0.0/0.0/0.0 | 0.0/0.0/0.0 |
| C: Adobe transfer | 0.0/0.0/9.9 | 0.0/6.5/17.3 | 0.0/0.0/9.0 | 0.965/0.987/0.998 | 0.0/0.0/0.0 | 1.0/3.0/10.0 |

All cells are p10/p50/p90; tone units are 0–255. A dash means insufficient usable observations. Word IQR includes single-class words on mixed lines; the mixed-word gap has the much smaller sample above.

| Output | Vector coverage within box | Raster coverage within box | Vector edge width, px | Raster edge width, px | Vector roughness | Raster roughness |
|---|---:|---:|---:|---:|---:|---:|
| Source | 0.358/0.485/0.597 | 0.297/0.439/0.580 | 1.42/1.58/1.60 | 1.52/1.59/1.60 | 0.000/0.000/0.005 | 0.000/0.000/0.000 |
| ScanWeave | 0.357/0.507/0.613 | 0.297/0.439/0.580 | 1.41/1.59/1.60 | 1.52/1.59/1.60 | 0.000/0.000/0.007 | 0.000/0.000/0.000 |
| Adobe XI | 0.349/0.485/0.601 | 0.306/0.449/0.589 | 1.50/1.59/1.68 | 1.54/1.60/1.66 | 0.000/0.000/0.003 | 0.000/0.000/0.000 |
| A: line | 0.357/0.507/0.613 | 0.297/0.439/0.580 | 1.40/1.59/1.60 | 1.52/1.59/1.60 | 0.000/0.000/0.007 | 0.000/0.000/0.000 |
| B: word | 0.357/0.507/0.613 | 0.297/0.439/0.580 | 1.40/1.59/1.60 | 1.52/1.59/1.60 | 0.000/0.000/0.007 | 0.000/0.000/0.000 |
| C: Adobe transfer | 0.357/0.507/0.613 | 0.297/0.439/0.580 | 1.41/1.59/1.60 | 1.52/1.59/1.60 | 0.000/0.000/0.007 | 0.000/0.000/0.000 |

These are p10/p50/p90 of the per-line class medians, using the same ScanWeave-derived vector/raster grouping for every output. Roughness is a threshold-mask perimeter proxy; zero does not imply a mathematically smooth contour.

- A: of 498 paired vector characters, 201 moved closer to source, 4 farther, and 293 had unchanged absolute error; 5 ended >1 luminance unit darker than source and 8 >1 lighter. Signed change p10/p50/p90: -19.0/0.0/0.0.
- B: of 498 paired vector characters, 203 moved closer to source, 2 farther, and 293 had unchanged absolute error; 3 ended >1 luminance unit darker than source and 10 >1 lighter. Signed change p10/p50/p90: -19.0/0.0/0.0.
- C: of 498 paired vector characters, 195 moved closer to source, 254 farther, and 49 had unchanged absolute error; 4 ended >1 luminance unit darker than source and 399 >1 lighter. Signed change p10/p50/p90: -10.0/1.0/9.0.

## Adobe XI policy and shape comparison

The exact content-stream fill spaces and `Tr` modes are in `operator-audit.json`, and the individual PDFium text objects, resolved RGBA, decoded text, geometry, and matched OCR line/word are in `adobe-objects-<document>-<page>.json`. Raw `g`/`rg`/`k`/`sc`/`scn` and `cs` are retained in the operator audit; object RGBA is PDFium’s resolved colour. The text shows in this corpus use DeviceRGB or DeviceGray and modes 0 or 3; mode 3 shows are invisible. Historical visible Adobe shows are not pure black; mixed and forms include both black and nonblack shows. The visible fills vary within pages, so neither universal black nor a single page colour describes Adobe’s output.

| Document | Visible text objects | Mapped objects / all | OCR words with >1 observed fill / mapped visible words | Single-character visible objects | Adobe fill vs source core, Pearson / Spearman (n) |
|---|---:|---:|---:|---:|---:|
| historical | 1030 | 1043/1085 | 27/690 | 148 | 0.88 / 0.90 (987) |
| financial | 2140 | 2023/2151 | 7/1894 | 22 | 0.62 / 0.70 (2013) |
| mixed | 1111 | 787/1117 | 0/711 | 42 | 0.99 / 0.84 (786) |
| receipts | 270 | 132/306 | 1/108 | 21 | 0.96 / 0.88 (123) |
| forms | 1061 | 1117/1175 | 10/793 | 64 | 0.37 / 0.26 (1006) |

Objects often contain several characters and some contain one; some OCR word boxes receive multiple fills. Since word/line matching is spatial and boxes may overlap, those cases do not prove deliberate within-word colour changes. Conversely the PDF cannot reveal Adobe’s internal sampler or prove a single per-word/per-glyph rule. The positive correlations compare resolved Adobe object fill luminance with one overlapping source OCR character core; shared page background, unmatched objects and registration errors confound them. They are consistent with local colour adaptation, not proof that the value was sampled from source. Adobe’s outline, weight and coverage comparisons are the roughness, density, edge and overlap-coverage proxies above, not an assumption that Adobe’s shape or colour policy is known.

## Offline colour-only counterfactuals

A replaces each visible ScanWeave show fill with the median of the per-character source core RGB values on its matched OCR line; B uses the matched word. C transfers the nearest observed Adobe fill on the same matched line (nearest page object as fallback). C is an **Adobe-output spatial proxy**, not Adobe’s unknown actual algorithm. For 1:1 character matches, line/word comes from the character; remaining objects use the nearest OCR word, recorded as `target_method` in the local maps. The per-page number of confidently matched objects and changed shows is in `prepare-*.json`. No per-pixel raster or glyph geometry is edited.

`validate_edits.py` checks every original page content instruction remains in order and the only additions are pairs of `rg` around visible shows; page MediaBox, CropBox and rotation are unchanged. [edit-validation.json](edit-validation.json) records counts. `pdftotext -enc UTF-8` output is byte-identical to the selected ScanWeave PDF for A, B and C on all five documents. This checks extraction preservation, not OCR correctness. Signed/absolute per-character tone errors, line SSIM, line dispersion, run dispersion, coverage, edge and roughness are reported above and in JSON. Because some historical vector characters move farther from the source and others cross from light to dark, the counterfactuals do **not** establish a no-drift guarantee. No implementation should be inferred from this offline edit.

## Contact sheets

[panel-index.json](panel-index.json) contains 56 indexed line strips: the 40 largest absolute measured vector−raster gaps, 10 reproducibly random remaining mixed lines (seed 33033), and extras for document worst lines and historical page coverage. Pages without a mixed historical line use a nonmixed OCR line. Each sheet shows source, ScanWeave, registered Adobe, A, B and C side by side at 96-DPI reading size and 3× that size. The large PNGs are in the local research directory:

- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-01.png` — SHA-256 `b4690ffd107550e9f3d73a792682810f25af693e5fd62a9dc2073243c888c741`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-02.png` — SHA-256 `5860f4dcd67ae6527cac69e6c14d5ec674d8a33597e9817b3f8e53f2c72ded4b`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-03.png` — SHA-256 `381631558cd46c5ce12dbbd5473c94bbc3ae26ea0643fd2564d035da129f11d0`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-04.png` — SHA-256 `578c435d3cffd94069696813851250a569461614675279669aa7512a65e8f627`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-05.png` — SHA-256 `2e0abc96f0b844e0b5b19948e3a3515df7b04e11953a12c906eb234a33004020`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-06.png` — SHA-256 `c5cfcb76c3bf06a0148259f3bd756fc43f5579b7795f6655173494efdacf7c5b`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-07.png` — SHA-256 `80a06b7c9c3b9e067327760966c0d35686ff3de78d4e8e6952d1930ff297265c`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-08.png` — SHA-256 `5ff5b4c02d7b0b893daa6abccbe8dbd932a9794173c7018ae1b2c37da9cf8d6a`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-09.png` — SHA-256 `ce35efb3f38168c54af53fcd54fa91f90d4a1a642950cf47168af0cfdc7e5df8`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-10.png` — SHA-256 `240fa5f69387832dfc806ad25f845ec88b4109a73b6038246b878a8c84999eeb`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-11.png` — SHA-256 `66cfc70bd4608a76934f1663c265ae662bd8c4e3a8042043510ea6f84f340252`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-12.png` — SHA-256 `48387347e85c495dbde4882df316a6b9d4987e6e4f8731092e55a9e53ae24f60`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-13.png` — SHA-256 `ee3661d4ccf8d98a0e6527f32ba51853c81016280842bbfb9e2f6922756c88a8`
- `/data/coding/scanweave/qualification/acr06/local/ink33/panels/sheet-14.png` — SHA-256 `b8499db133de7d12c50c223ea27c4a3602055b133cfee8a9cdd28929fbabd6f5`

## Evidence and reproduction

Run the scripts with `qualification/.venv/bin/python -I` from the repository root. `prepare.py` makes the maps, registered renders and edited PDFs; `measure.py` writes line, word and per-character data and performs extraction checks; `adobe_policy.py` enumerates Adobe text objects; `operator_audit.py` tracks graphics operators; `validate_edits.py` verifies the edits; `panels.py` makes contact sheets and the index; `provenance.py` records hashes; and `make_report.py` compiles this report. Large assets and per-page matching maps are under `qualification/acr06/local/ink33/`; evidence JSON and scripts are alongside this report. No evidence has been committed.

## Independent review (Claude), 2026-11-09

**Verdict: the recommendation is superseded. Re-assess #33 after #37 is fixed.**

- **The main "pale vector letter" effect on historical and receipts pages is a defect, not a tone policy.**
  - `mask.rs` estimates paper from the four page corners.
  - On 10 of 32 pages (all historical pages, and receipts 4, 6, 7, 8 and 9) the corners are dark: a scan border, a binding shadow or a tabletop.
  - On those pages the text "ink" estimate becomes the real paper colour. The operator audit in this study shows text fills lighter than the paper fill on every one of those pages.
  - 65 visible glyphs are drawn this way: historical p2 (22), historical p5 (36) and receipts p4 (7). On receipts p4, "Chicken" renders as near-white outlines.
  - This is tracked in #37 (title and root cause corrected).
- **Historical and receipts results are contaminated.** Their tone gaps and the line/word counterfactuals measure this inversion, not ScanWeave's intended ink policy. Financial, mixed and forms have correct polarity, so their results stand.
- **Where polarity is correct, a single page-level fill is not the dominant problem.** On financial, per-line and per-word recolouring overshoots: the vector−raster gap goes from +4.0 to about −9. The larger difference there is edge softness. Raster-retained characters measure 2.26 px edge width against 1.61 px in the source, consistent with the ~200-DPI background resampling. Vector glyphs measure 1.54 px.
- **Adobe XI** varies its text fill within pages. Its line SSIM against the source is lower than ScanWeave's on every document, so copying its colour policy is not a goal in itself.
- **Raw data:** per-character records (3.6 MB) were moved to `local/ink33/raw-chars/` to keep the commit small. Summaries and per-line metrics remain here.
