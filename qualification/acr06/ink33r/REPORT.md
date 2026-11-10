# Issue 33 — remeasurement after the #37 polarity fix

**Research recommendation: no automatic recolouring change is warranted on this evidence.** The strongest surviving edge mismatch is on financial mixed lines; it is not a universal property of all documents. Any owner-authorised follow-up should first demonstrate source-faithful, legible characters and improvements on paired, held-out lines at reading size, including historical print, without forcing black or compromising counters, punctuation or extraction. This study changes no product code. Independent review by Claude is pending.

## Baseline and scope

Main `ab7dfba96561595e7c587d8033954ed1ec235a20` was built with `cargo build --release --locked -p scanweave-cli` and converted at `--dpi 300 --profile clearscan --glyph-sharing off`. All five completed PDFs match the frozen #39 C-prime outputs. [provenance.json](provenance.json) includes the input, Adobe XI, old and corrected PDF hashes. All 32 pages have identical parsed OCR text and boxes in the old and new reports; raw hOCR hashes differ, while the parsed text and boxes used for these measurements match ([OCR provenance](ocr-provenance.json)).

| Document | Corrected PDF SHA-256 | Bytes |
|---|---|---:|
| historical | `68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b` | 2,247,390 |
| financial | `96e3b89df58f3e33629300faebf2b3cde81065437b49f1695c24361b10f472bd` | 2,842,414 |
| mixed | `a7efc67a2d331b756aade6a490328d2690343c43523c5284ae8db25937246f9a` | 920,248 |
| receipts | `82c00d2131a69f8c20ad4a078f011e15473f2c7ac25a059933162155f1068b34` | 1,266,953 |
| forms | `75dfda81cef2a5857328ede7dd76279d72e65a838fb6d352b7f6ea6673d383ff` | 831,974 |

## Method and limits

We reran the [original #33 method](../ink33/REPORT.md) using the same 300-DPI PDFium renders, source OCR boxes, ORB/RANSAC Adobe registration, overlap thresholds and greedy one-to-one visible-object matching. Unmatched boxes overlapping a visible object are excluded as ambiguous; remaining boxes are classified raster. The classification is operational, not a ground-truth ownership mask. A box can contain neighbouring or raster ink, so its tone is not necessarily the vector fill alone. Adobe images are affine-registered with bilinear resampling; this affects their edge and SSIM measurements. OCR and registration errors, overlapping boxes, thresholding and different glyph shapes limit interpretation.

Luminance is Rec.709 on 0–255 RGB. In each character box the background is its 85th percentile; the ink core is the median of the darkest 30% of pixels at least 10 units darker. Line or word dispersion is the IQR of character core tones; vector−raster gap is the difference between class medians on the same mixed line. Character error is absolute difference from the source core. Coverage is contrast-normalised dark-pixel fraction. Edge width is a gradient-based 10–90% transition proxy in 300-DPI pixels; roughness is a threshold-mask perimeter proxy. Line SSIM compares padded source and rendered line boxes. The results are not physical stroke widths and cannot alone establish recognition correctness.

The original mixed-line calculations are retained. To measure pages with no vectors, the copied script also records every usable line and word, without changing the classification or metric definitions. Old all-line records were reconstructed from frozen old character files; all 445 old mixed lines reproduced their original tone, gap, SSIM and edge metrics exactly ([check](old-reconstruction-check.json)). Mixed-line cohorts change after routing; the 420 surviving paired lines have **zero metric changes** for source, ScanWeave and Adobe, with 25 old-only and zero new-only lines ([paired-lines.json](paired-lines.json)).

## What #37 changed

The prior historical sample of 24 mixed lines came entirely from pages 2 and 5. Their 22 and 36 paper-coloured visible glyphs are now suppressed; all five historical pages have no visible vector text, so the new mixed-line sample is empty. Receipts page 4 loses seven wrong-colour visible glyphs and its one mixed line; its remaining sample is 12 rather than 13 lines. These changes are not a change in the tone of surviving vectors. The other 29 pages retain their previous output, as established by the #39 three-renderer checks ([PDFium](../ink37c/cprime/render-pdfium.json), [Poppler](../ink37c/cprime/render-poppler.json), [MuPDF](../ink37c/cprime/render-mupdf.json)). Old historical mixed-line medians and recolouring results based on those paper-region glyphs must not be treated as evidence for ordinary ink policy.

| Document | Mixed lines old → new | Mixed words old → new | Visible objects old → new by page |
|---|---:|---:|---|
| historical | 24 → 0 | 25 → 0 | 1:0→0, 2:22→0, 3:0→0, 4:0→0, 5:36→0 |
| financial | 298 → 298 | 1 → 1 | 1:281→281, 2:197→197, 3:244→244, 4:345→345, 5:182→182, 6:207→207, 7:235→235, 8:437→437, 9:329→329, 10:280→280, 11:420→420, 12:215→215, 13:345→345 |
| mixed | 62 → 62 | 0 → 0 | 1:482→482, 2:784→784 |
| receipts | 13 → 12 | 1 → 1 | 1:0→0, 2:12→12, 3:28→28, 4:7→0, 5:7→7, 6:0→0, 7:0→0, 8:0→0, 9:0→0, 10:28→28 |
| forms | 48 → 48 | 5 → 5 | 1:297→297, 2:207→207 |

### All usable lines and words

Cells show old → new medians, calculated over all usable OCR lines or words rather than just mixed lines. Tone and error are luminance units; SSIM is dimensionless. Source, ScanWeave and Adobe use the same boxes. The character count differs by three on historical because three formerly ambiguous overlapping boxes are now usable; other document populations have identical counts. Whole-page medians can hide the 65 local character defects. Full p10/p50/p90, signed errors, coverage, edge and roughness distributions and sample sizes are in the `old-all-summary-*` and `all-summary-*` JSON files.

| Document / output | Lines old/new | Line IQR | Word IQR | Character absolute tone error | Line SSIM |
|---|---:|---:|---:|---:|---:|
| historical / source | 109/109 | 5.7 → 5.7 | 3.4 → 3.4 | 0.0 → 0.0 | 1.000 → 1.000 |
| historical / scanweave | 109/109 | 6.6 → 6.6 | 3.7 → 3.7 | 5.7 → 5.7 | 0.949 → 0.950 |
| historical / adobe | 109/109 | 0.0 → 0.0 | 0.0 → 0.0 | 6.5 → 6.5 | 0.811 → 0.811 |
| financial / source | 677/677 | 4.5 → 4.5 | 3.2 → 3.2 | 0.0 → 0.0 | 1.000 → 1.000 |
| financial / scanweave | 677/677 | 1.8 → 1.8 | 0.0 → 0.0 | 10.4 → 10.4 | 0.932 → 0.932 |
| financial / adobe | 677/677 | 0.0 → 0.0 | 0.0 → 0.0 | 9.0 → 9.0 | 0.854 → 0.854 |
| mixed / source | 84/84 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 1.000 → 1.000 |
| mixed / scanweave | 84/84 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.943 → 0.943 |
| mixed / adobe | 84/84 | 1.0 → 1.0 | 0.4 → 0.4 | 9.0 → 9.0 | 0.834 → 0.834 |
| receipts / source | 77/77 | 7.9 → 7.9 | 4.7 → 4.7 | 0.0 → 0.0 | 1.000 → 1.000 |
| receipts / scanweave | 77/77 | 8.2 → 8.2 | 4.4 → 4.4 | 3.4 → 3.4 | 0.972 → 0.972 |
| receipts / adobe | 77/77 | 2.8 → 2.8 | 0.0 → 0.0 | 6.5 → 6.5 | 0.905 → 0.905 |
| forms / source | 156/156 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 1.000 → 1.000 |
| forms / scanweave | 156/156 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 1.000 → 1.000 |
| forms / adobe | 156/156 | 3.0 → 3.0 | 0.5 → 0.5 | 12.0 → 12.0 | 0.877 → 0.877 |

### Original mixed-line comparison

Cells below are old → new medians on each run’s mixed-line cohort, so changes in receipts reflect the removed page-4 line. The source and Adobe classes are defined by ScanWeave ownership for comparability. A dash means no usable mixed lines; it does not mean the numerical gap is zero. Full distributions, word-level and per-character errors are in [comparison.json](comparison.json), `summary-*.json`, and the page-level records.

| Document / output | Line IQR | Word IQR | Vector−raster tone | Absolute character error | Line SSIM |
|---|---:|---:|---:|---:|---:|
| historical / source | 5.6 → — | 3.3 → — | -0.7 → — | 0.0 → — | 1.000 → — |
| historical / scanweave | 5.7 → — | 3.4 → — | -2.2 → — | 6.1 → — | 0.948 → — |
| historical / adobe | 0.0 → — | 0.0 → — | 0.0 → — | 5.1 → — | 0.797 → — |
| financial / source | 6.8 → 6.8 | 3.5 → 3.5 | 0.9 → 0.9 | 0.0 → 0.0 | 1.000 → 1.000 |
| financial / scanweave | 4.7 → 4.7 | 0.4 → 0.4 | 4.0 → 4.0 | 10.7 → 10.7 | 0.943 → 0.943 |
| financial / adobe | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 9.1 → 9.1 | 0.873 → 0.873 |
| mixed / source | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 1.000 → 1.000 |
| mixed / scanweave | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.946 → 0.946 |
| mixed / adobe | 1.0 → 1.0 | 0.3 → 0.3 | 0.0 → 0.0 | 9.0 → 9.0 | 0.825 → 0.825 |
| receipts / source | 8.7 → 7.6 | 4.9 → 4.7 | -6.8 → -7.1 | 0.0 → 0.0 | 1.000 → 1.000 |
| receipts / scanweave | 6.6 → 6.5 | 4.7 → 4.6 | -6.3 → -6.6 | 5.4 → 5.1 | 0.966 → 0.968 |
| receipts / adobe | 2.0 → 2.0 | 0.0 → 0.0 | -2.0 → -4.9 | 7.3 → 7.0 | 0.895 → 0.897 |
| forms / source | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 1.000 → 1.000 |
| forms / scanweave | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.0 → 0.0 | 0.987 → 0.987 |
| forms / adobe | 2.0 → 2.0 | 0.0 → 0.0 | 0.0 → 0.0 | 7.0 → 7.0 | 0.884 → 0.884 |

## Edge softness and coverage on remaining mixed lines

Vector and raster widths are medians of the per-line class medians. The paired difference is the median of each line’s vector-minus-raster width, so it need not equal the difference between those two medians. The 96-DPI column is the 300-DPI proxy multiplied by 96/300, not an independently measured display edge. Negative means the vector proxy is narrower. Coverage and roughness have the same line/class definitions; distributions for all three outputs are in [comparison.json](comparison.json).

| Document | Lines | ScanWeave vector / raster edge px at 300 DPI | Paired edge difference px at 300 / scaled to 96 DPI | Vector / raster coverage | Vector / raster roughness |
|---|---:|---:|---:|---:|---:|
| historical | 0 | — / — | — / — | — / — | — / — |
| financial | 298 | 1.538 / 2.256 | -0.739 / -0.237 | 0.369 / 0.358 | 0.000 / 0.000 |
| mixed | 62 | 1.565 / 1.600 | -0.202 / -0.065 | 0.398 / 0.398 | 0.000 / 0.000 |
| receipts | 12 | 2.777 / 2.612 | 0.098 / 0.032 | 0.406 / 0.422 | 0.000 / 0.000 |
| forms | 48 | 1.589 / 1.589 | 0.000 / 0.000 | 0.507 / 0.439 | 0.000 / 0.000 |

Financial retains a consistent narrower-vector proxy: the paired median is −0.739 pixels at 300 DPI (p10–p90 −0.880 to −0.630), compared with a nearly zero source class gap. Mixed has a smaller paired median (−0.202) with a wide spread; receipts reverses sign at the median (+0.098), and forms is 0. Historical has no remaining mixed lines. Thus the earlier financial “cutout”/soft-raster observation remains supported; a uniform gap across the corpus does not.

In the [financial and mixed panels](/data/coding/scanweave/qualification/acr06/local/ink33r/panels/sheet-13.png), edge and weight differences are clearer enlarged than at reading size. At the requested reading size the financial difference can be subtle; this unblinded panel review does **not establish a consistently material reading-size defect**, and a scaled proxy is not a visibility threshold. The [receipts and forms panels](/data/coding/scanweave/qualification/acr06/local/ink33r/panels/sheet-14.png) likewise do not establish a general sharpening need. The [historical references](/data/coding/scanweave/qualification/acr06/local/ink33r/panels/sheet-15.png) are explicitly raster-only, not mixed-line evidence.

## Visible fill and source-local paper audit

The original graphics-state audit follows fill colour spaces, `Tr` and `q/Q` through every text show ([operator-audit.json](operator-audit.json)); there were no unhandled Form XObjects. For each page, source-local paper is the median of the 85th-percentile luminances in its OCR word boxes. This is evidence around text, not a global paper estimate. We also compare each PDFium visible object against the 85th percentile of its own source box expanded by two pixels ([fill-local.json](fill-local.json)). None of 21 visible page fills is above its measured page-local paper, and none of 5,562 visible objects exceeds its own local proxy. Two no-visible-text receipts pages have no usable OCR-word paper evidence. This test flags luminance, not every possible colour or shape defect.

| Page | Visible fill RGB (0–255); show count | Local paper luminance | Above paper? |
|---|---|---:|---|
| historical 1 | none | 234.0 | n/a |
| historical 2 | none | 229.9 | n/a |
| historical 3 | none | 182.0 | n/a |
| historical 4 | none | 175.2 | n/a |
| historical 5 | none | 204.0 | n/a |
| financial 1 | (49, 32, 16) × 281 | 198.1 | no |
| financial 2 | (50, 33, 17) × 197 | 198.8 | no |
| financial 3 | (46, 30, 15) × 244 | 196.9 | no |
| financial 4 | (60, 44, 24) × 345 | 197.3 | no |
| financial 5 | (54, 39, 21) × 182 | 197.1 | no |
| financial 6 | (50, 36, 24) × 207 | 197.6 | no |
| financial 7 | (57, 42, 26) × 235 | 197.9 | no |
| financial 8 | (56, 40, 20) × 437 | 200.0 | no |
| financial 9 | (68, 51, 27) × 329 | 198.2 | no |
| financial 10 | (56, 39, 22) × 280 | 197.0 | no |
| financial 11 | (55, 39, 20) × 420 | 200.9 | no |
| financial 12 | (60, 43, 21) × 215 | 198.9 | no |
| financial 13 | (51, 36, 22) × 345 | 199.0 | no |
| mixed 1 | (133, 127, 111) × 482 | 217.2 | no |
| mixed 2 | (0, 0, 0) × 784 | 255.0 | no |
| receipts 1 | none | — | n/a |
| receipts 2 | (58, 62, 56) × 12 | 146.8 | no |
| receipts 3 | (56, 57, 52) × 28 | 161.4 | no |
| receipts 4 | none | 173.0 | n/a |
| receipts 5 | (123, 106, 100) × 7 | 203.8 | no |
| receipts 6 | none | 161.2 | n/a |
| receipts 7 | none | — | n/a |
| receipts 8 | none | 215.5 | n/a |
| receipts 9 | none | 142.4 | n/a |
| receipts 10 | (94, 77, 71) × 28 | 217.0 | no |
| forms 1 | (0, 0, 0) × 297 | 255.0 | no |
| forms 2 | (19, 19, 19) × 207 | 255.0 | no |

## Adobe XI and offline counterfactuals

Adobe visible fills and their OCR spatial associations are recorded in [operator-audit.json](operator-audit.json), `adobe-policy-*.json` and per-page `adobe-objects-*`. Adobe has varying fills and is not ground truth for colour or shape; its registered line SSIM is lower than ScanWeave’s median on these measured cohorts.

| Document | Adobe visible objects | OCR words with multiple observed fills / mapped words | Fill vs source-core Pearson / Spearman (n) |
|---|---:|---:|---:|
| historical | 1030 | 27 / 690 | 0.88 / 0.90 (987) |
| financial | 2140 | 7 / 1894 | 0.62 / 0.70 (2013) |
| mixed | 1111 | 0 / 711 | 0.99 / 0.84 (786) |
| receipts | 270 | 1 / 108 | 0.96 / 0.88 (123) |
| forms | 1061 | 10 / 793 | 0.37 / 0.26 (1006) |

Overlap matching and registration can misassign words and colours; those correlations do not establish Adobe’s sampling algorithm.

A substitutes a source line-core median for each visible show; B uses the word-core median; C transfers the nearest observed Adobe fill on the line. These are offline PDF content-stream counterfactuals, not product changes and not a reconstruction of Adobe’s internal policy. Historical has no visible vectors, so the three colour edits are no-ops there and cannot test the old historical recolouring conclusion. The table compares matched vector characters on corrected-baseline mixed lines against source core tone. It does not establish character correctness or a safe colour rule.

| Document / experiment | Paired vectors | Closer to source | Farther | Unchanged |
|---|---:|---:|---:|---:|
| historical / A | 0 | 0 | 0 | 0 |
| historical / B | 0 | 0 | 0 | 0 |
| historical / C | 0 | 0 | 0 | 0 |
| financial / A | 2699 | 2205 | 494 | 0 |
| financial / B | 2699 | 2443 | 256 | 0 |
| financial / C | 2699 | 2257 | 442 | 0 |
| mixed / A | 755 | 393 | 72 | 290 |
| mixed / B | 755 | 406 | 59 | 290 |
| mixed / C | 755 | 413 | 310 | 32 |
| receipts / A | 35 | 8 | 27 | 0 |
| receipts / B | 35 | 10 | 24 | 1 |
| receipts / C | 35 | 2 | 32 | 1 |
| forms / A | 498 | 201 | 4 | 293 |
| forms / B | 498 | 203 | 2 | 293 |
| forms / C | 498 | 195 | 254 | 49 |

On financial, word substitution moves 256 of 2,699 paired vectors farther from source; on receipts it moves 24 of 35 farther. The median financial vector−raster gap changes from about +4 to −8.4 luminance units under B. Neither a mean improvement nor Adobe similarity justifies automatic recolouring. All A/B/C PDFs retain identical `pdftotext` output; [edit-validation.json](edit-validation.json) verifies the only content-stream edits are RGB fill insertions around visible shows.

## Panels, artifacts and reproducibility

The [panel index](panel-index.json) records all selected line IDs, boxes, selection reasons and SHA-256 hashes. It includes the 40 largest absolute gaps, 10 seeded random remaining mixed lines (seed 33033), document extremes and a median-gap line per document with a mixed line, plus five historical raster-only references. Sheets show source / ScanWeave / registered Adobe at 96-DPI reading-size approximation and 4× that size; panels are unblinded and are not a controlled perceptual study. Full per-character observations are committed in [character-index.json](character-index.json) and `characters/`; full per-line/word observations are in `all-lines-*` and `metrics-*`.

Scripts are copied from #33 where possible; adaptations are recorded verbatim in [script-diffs.json](script-diffs.json). `build_corpus.sh` and `run_pipeline.sh` record the commands; `provenance.py`, `ocr_provenance.py`, `old_all.py`, `old_summary.py`, `compare.py`, `paired_lines.py`, `fill_local.py`, `edge_differences.py` and `export_chars.py` add the new checks; `finalize.sh` runs them. [validation.json](validation.json) records the hash, classification, fill and extraction checks. Run Python with `qualification/.venv/bin/python -I`. Large PDFs, renders, counterfactuals and panels remain in `qualification/acr06/local/ink33r/`; no product changes or release actions were made. Independent review by Claude remains outstanding.
