# Issue 37: compact source-raster challenger

**Verdict: HOLD.** The bounded candidate reduces the lossless penalty but remains 3,747,703 bytes (46.2%) above main. Historical page 2 fails the local detail check and retains exact pixels. Historical page 5 and receipts page 4 use compact JPEG; both show softening and their image OCR differs from source. Independent visual review by Claude and the hosted Sonar quality gate remain outstanding. This is not a recommendation to merge or promote the mode.

## Design and limits

The qualified #38 gate is unchanged: Rec.709 ink luminance exceeds paper luminance, and final visible vector occurrences are nonzero. Of ten suspect pages, only historical pages 2 and 5 and receipts page 4 route to searchable source raster. Existing source-exact baseline remains distinct from the new compact-source representation. The raster is made from canonical original RGB, without cleanup, ink suppression, or paper fill; routed text is invisible and document-wide reconstruction, donors, CIDs, segmentation and q3 are unchanged. The existing 200-DPI JPEG85 4:2:0 residual encoder, its eligibility and downsampling rules are reused. Encoding must save at least 5% against the exact patch. Encoder refusal or a failed fidelity check retains the #38 source-exact patch.

The experimental automatic check decodes and upsamples the compact result to source dimensions. It requires RGB mean absolute error ≤10, recall ≥0.98 for source-dark OCR-box pixels (source luminance <128, candidate <160), at least one such pixel, and rejects any OCR word box with ≥32 strongly coloured pixels (channel spread ≥45) whose local RGB MAE exceeds 16. These bounds were chosen from the three-page observations, not a held-out validation set: the prototype blurred coloured fine engraving on historical p2, while the measured p5 boxes remained below the local bound. The check does not establish character or artwork fidelity outside OCR boxes. It is a guard, not a substitute for independent visual review. Page reports distinguish `source_exact` and `clearscan_compact_lossy`, actual `raster_encoding`, and the compact decision; JPEG is never described as source-exact.

## Completed PDF sizes

| Document | A main (bytes) | B #38 exact (bytes) | C mixed challenger (bytes) |
|---|---:|---:|---:|
| historical | 2,246,646 | 13,762,217 | 5,994,232 |
| financial | 2,842,414 | 2,842,414 | 2,842,414 |
| mixed | 920,248 | 920,248 | 920,248 |
| receipts | 1,266,836 | 2,374,622 | 1,266,953 |
| forms | 831,974 | 831,974 | 831,974 |
| **Total** | **8,108,118** | **20,731,475** | **11,855,821** |

C saves 8,875,654 bytes versus B but is not close to A. Full-document SHA-256 values and all page image object metadata are in [bytes-final.json](bytes-final.json); A and B reference hashes were independently verified in [reference-hashes.json](reference-hashes.json). Image bytes below sum encoded image streams referenced by each page; they are not an allocation of shared PDF overhead.

| Page | Inverted | Visible occurrences before route | C route | Image bytes A | Image bytes B | Image bytes C |
|---|---|---:|---|---:|---:|---:|
| historical 1 | true | 0 | not_raster_baseline | 451,336 | 451,336 | 451,336 |
| historical 2 | true | 22 | source_exact | 306,274 | 4,053,348 | 4,053,348 |
| historical 3 | true | 0 | not_raster_baseline | 252,220 | 252,220 | 252,220 |
| historical 4 | true | 0 | not_raster_baseline | 629,404 | 629,404 | 629,404 |
| historical 5 | true | 36 | clearscan_compact_lossy | 558,993 | 8,327,288 | 559,403 |
| financial 1 | false | 281 | not_raster_baseline | 168,983 | 168,983 | 168,983 |
| financial 2 | false | 197 | not_raster_baseline | 118,923 | 118,923 | 118,923 |
| financial 3 | false | 244 | not_raster_baseline | 154,805 | 154,805 | 154,805 |
| financial 4 | false | 345 | not_raster_baseline | 159,351 | 159,351 | 159,351 |
| financial 5 | false | 182 | not_raster_baseline | 141,195 | 141,195 | 141,195 |
| financial 6 | false | 207 | not_raster_baseline | 160,726 | 160,726 | 160,726 |
| financial 7 | false | 235 | not_raster_baseline | 144,818 | 144,818 | 144,818 |
| financial 8 | false | 437 | not_raster_baseline | 189,804 | 189,804 | 189,804 |
| financial 9 | false | 329 | not_raster_baseline | 151,487 | 151,487 | 151,487 |
| financial 10 | false | 280 | not_raster_baseline | 131,041 | 131,041 | 131,041 |
| financial 11 | false | 420 | not_raster_baseline | 167,809 | 167,809 | 167,809 |
| financial 12 | false | 215 | not_raster_baseline | 115,613 | 115,613 | 115,613 |
| financial 13 | false | 345 | not_raster_baseline | 170,890 | 170,890 | 170,890 |
| mixed 1 | false | 482 | not_raster_baseline | 253,560 | 253,560 | 253,560 |
| mixed 2 | false | 784 | not_raster_baseline | 256,604 | 256,604 | 256,604 |
| receipts 1 | false | 0 | not_raster_baseline | 83,699 | 83,699 | 83,699 |
| receipts 2 | false | 12 | not_raster_baseline | 66,397 | 66,397 | 66,397 |
| receipts 3 | false | 28 | not_raster_baseline | 168,476 | 168,476 | 168,476 |
| receipts 4 | true | 7 | clearscan_compact_lossy | 122,528 | 1,230,205 | 122,638 |
| receipts 5 | false | 7 | not_raster_baseline | 48,912 | 48,912 | 48,912 |
| receipts 6 | true | 0 | not_raster_baseline | 485,445 | 485,445 | 485,445 |
| receipts 7 | true | 0 | not_raster_baseline | 60,807 | 60,807 | 60,807 |
| receipts 8 | true | 0 | not_raster_baseline | 58,362 | 58,362 | 58,362 |
| receipts 9 | true | 0 | not_raster_baseline | 59,408 | 59,408 | 59,408 |
| receipts 10 | false | 28 | not_raster_baseline | 71,595 | 71,595 | 71,595 |
| forms 1 | false | 297 | not_raster_baseline | 386,679 | 386,679 | 386,679 |
| forms 2 | false | 207 | not_raster_baseline | 351,145 | 351,145 | 351,145 |

## Source fidelity and visual evidence

Metrics compare the completed C PDF rendered at 300 DPI with the source at matched geometry. Dark-pixel recall is within OCR boxes, thresholded as described above. SSIM and MAE are source comparisons, not claims of exact JPEG samples.

| Page | C representation | RGB MAE | SSIM | OCR-box dark-pixel recall |
|---|---|---:|---:|---:|
| historical 2 | source exact | 0.0000 | 1.000000 | 1.000000 |
| historical 5 | lossy JPEG | 4.5376 | 0.937604 | 0.999996 |
| receipts 4 | lossy JPEG | 2.0648 | 0.965346 | 0.999944 |

The earlier all-compact trial blurred coloured engraving on historical p2; [this enlarged source/prototype comparison](/data/coding/scanweave/qualification/acr06/local/ink37c/detail-07-word.png) shows why C rejects it and uses B. The p5 [stamp detail](/data/coding/scanweave/qualification/acr06/local/ink37c/stamp-detail.png) illustrates residual smoothing outside the automatic word-box guarantee. Per-word measurements are in [word-fidelity.json](word-fidelity.json); source edge comparisons are in [edges.json](edges.json). Thresholds were calibrated on these measurements, so they are not independent evidence of general safety.

The [final panel index](panel-final-index.json) records locations and SHA-256 hashes for all 65 known damaged glyphs (22, 36 and 7), named words Chicken, Nos, quod, ingenui and ad, and all three whole pages. The [four-column panels](/data/coding/scanweave/qualification/acr06/local/ink37c/panels-final/) show source / A / B / C at reading-size approximation, 300 DPI and 4× nearest-neighbour enlargement for crops. Reading-size crops were rescaled from the 300-DPI render; separate full-page 96-DPI renderer comparisons were run. These panels were examined during engineering; Claude has not independently reviewed them.

Image OCR is supporting evidence only: source vs C token sequence ratios are 1.000 on historical p2, 0.568 on p5, and 0.773 on receipts p4. Source and B agree at 1.000. Tesseract itself is imperfect on the historical source, but the changes on C are a reason for HOLD, not proof of a particular missing glyph. Counts and outputs: [ocr-final.json](ocr-final.json). No claim that the automatic metric guarantees every counter, fade, punctuation mark or artwork feature is preserved.

## Unaffected pages, text and validity

Across all 29 unaffected pages, B and C have zero changed rendered pixels at both 96 and 300 DPI in PDFium, Poppler and MuPDF. Their content streams and referenced image/font/ToUnicode resources are byte-identical; historical p2 also matches B. Financial, mixed and forms are whole-PDF byte-identical across A, B and C. Render data: [PDFium](render-pdfium.json), [Poppler](render-poppler.json), [MuPDF](render-mupdf.json); resource comparisons: [resources-final.json](resources-final.json). Document metadata and full-PDF serialization can differ where an image changes.

PDFium and Poppler extraction and PDFium searches match B on every page; all routed pages have zero visible text-show operations and retain invisible text. See [semantics-final.json](semantics-final.json) and [text-modes-final.json](text-modes-final.json). Donor decisions, semantic owners, counts and polarity reports match B before routing ([donors.json](donors.json)). All five C PDFs pass qpdf; all five distinct embedded fonts pass OTS ([pdf-checks-final.json](pdf-checks-final.json)). All five faithful-mode PDFs and the explicit source-exact single-page baseline are byte-identical to #38. A receipts q3/glyph-sharing run keeps all ten page content streams identical to B; the routed image alone changes.

## Original-image passthrough

The three canonical input image streams are Flate, not eligible source JPEGs; verified original stream passthrough would be larger than #38 recompression. Source / B encoded bytes: historical p2 5,031,652 / 4,053,348; historical p5 10,186,745 / 8,327,288; receipts p4 1,752,418 / 1,230,205. Identity checks were not weakened. See [passthrough.json](passthrough.json).

## Runtime and peak RSS

Measurements use `/usr/bin/time -v` on complete corpus document conversions. Jobs ran concurrently and timings are observational, not a controlled benchmark.

| Document | A elapsed / peak RSS KiB | B elapsed / peak RSS KiB | C elapsed / peak RSS KiB |
|---|---:|---:|---:|
| historical | mm:ss or m:ss): 1:34.05 / 724,216 | mm:ss or m:ss): 1:07.94 / 714,072 | mm:ss or m:ss): 1:12.95 / 746,664 |
| financial | mm:ss or m:ss): 7:58.15 / 1,468,252 | mm:ss or m:ss): 8:09.15 / 1,470,588 | mm:ss or m:ss): 7:52.87 / 1,471,020 |
| mixed | mm:ss or m:ss): 1:59.92 / 362,220 | mm:ss or m:ss): 1:49.12 / 362,196 | mm:ss or m:ss): 1:48.56 / 363,628 |
| receipts | mm:ss or m:ss): 0:30.15 / 542,572 | mm:ss or m:ss): 0:27.79 / 547,336 | mm:ss or m:ss): 0:28.93 / 536,680 |
| forms | mm:ss or m:ss): 1:01.76 / 437,580 | mm:ss or m:ss): 0:45.77 / 442,196 | mm:ss or m:ss): 0:42.14 / 438,176 |

## Checks and outstanding review

Focused tests exercise compact routing, normal/faithful behavior, encoder ineligibility, lost-ink and coloured-detail rejection, report fidelity, and mixed documents. `cargo test --workspace --locked`, the requested Clippy command and all 20 Python CI gates passed. The local LLVM changed-line calculation is 201/216 (93.1%); it is an approximation, not SonarCloud’s quality gate; see [coverage-new.json](coverage-new.json). Hosted Sonar was not run: no scanner/token is available and the workflow is triggered by a PR or main push; no PR was opened per instruction. Claude’s independent code, glyph, mappings and size review remains pending.

The three compact routes and the seven suspect zero-vector pages follow #38 routing. No new estimator, segmentation, donor selection, q3, or compression project was introduced. The lossless option remains the safe reference.

Product branch commit: `062803b`. Per-page decisions, luminances and fidelity fields: [page-decisions.json](page-decisions.json).
