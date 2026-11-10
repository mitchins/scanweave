# HVC-41B: bounded historical recovery pilots

**HOLD: no validated historical vector was emitted.** The frozen source-polarity rule admitted zero regions containing the 275 page-1 proposals, and zero of the measured page-3 and page-4 proposal regions. The retained [completed historical PDF](/data/coding/scanweave/qualification/acr06/local/hvc41b/final/historical.pdf) is byte-identical to #39, has zero visible text objects and preserves its extraction and source appearance. Verified new vector coverage is **0%** on each pilot page. This is a failed, over-conservative admission experiment, not evidence that historical text is unrecoverable. No production change, default change, PR or merge is recommended.

The original whole-PDF CLI was inadvertently started at the beginning of this task; that CLI invokes Tesseract. It was stopped as soon as the code path was identified, and its output was discarded. It may have performed OCR before being stopped. All reported experiments subsequently replayed frozen hOCR; source PDF, raster pixel and hOCR SHA-256 values were checked by the replay path. The control replay additionally placed a failing Tesseract stub first in PATH; it was never invoked. This initial mistake violated the instruction not to run new OCR.

## Frozen method and scope

The pre-pilot [frozen rules](FROZEN_RULES.md) require each OCR symbol box in a region to pass dark-pixel fraction, contrast, surrounding-paper and independent interior-paper agreement tests. Every box must pass. Glyph checks were fixed in advance at mask IoU ≥0.90, fill-luminance error ≤15, zero external ink removal and no paint beyond the one-pixel-expanded box. No threshold was relaxed. The OCR-local reference and segmentation-mask overlap remain imperfect, particularly on historical print; they cannot independently establish that a glyph represents the correct character.

The page-border definition is a component bbox touching at least two page edges and spanning at least 80% of both dimensions. Only this component receives the four-pixel Euclidean proximity refinement after the existing bbox filter. Other artwork bboxes, suspect units and protected regions remain in force. The switch applies only when the experimental interior estimator changes the page; the corner-only check consequently leaves planning unchanged by construction, and is not evidence that an unconditional exemption is safe. Donor collection continues to use the original planner. All experimental behaviours use `SCANWEAVE_HVC41B_` switches on research commit `9635f2f`. The frozen hOCR replay is an input-replay switch, not a reconstruction change.

**Important limitation:** the frozen admission rule is evaluated offline and is not integrated as a live per-region product or research emission gate. The interior and border runs are contained diagnostics, not candidate PDFs. No proposal can be emitted based on the offline screen. The original baseline is retained when no proposals are admitted. This also avoids the diagnostic semantic changes; it does not solve semantics for any future mixed raster/vector implementation.

## Pilot outcomes and failure classes

| Historical page | Proposal census | Admitted | Actual isolated pre-font paths | Verified emitted | Verified new source-ink coverage |
|---|---:|---:|---:|---:|---:|
| 1 | 275 | 0 | 275 | 0 | 0% |
| 3 | 170 | 0 | 139 | 0 | 0% |
| 4 | 113 | 0 | 81 | 0 | 0% |

Page 1 starts from exactly 275 existing pre-containment proposals. All 275 fail region admission: each proposal belongs to a region with at least one symbol box outside the 5–45% dark-fraction bound; 273 also have a box below the 70% surround bound. Failures overlap. The page-1 region rule admits zero; no glyph reaches an independent rendered-font or visual acceptance test. [Page 1 ledger](ledger-01.json) records the reasons and an indexed panel for each proposal. This satisfies the stop condition without relaxing the rule. The rule’s zero admission across the controls as well as the historical pilots is a sign of low usefulness, not proof that those regions are unsafe.

The isolated path diagnostic renders the product’s exported **pre-font-quantization** `shape.path` on blank tiles, rather than the final embedded font glyph in a completed candidate page. It is useful for separating hypotheses but is not a valid final font-glyph IoU, placement test or independent character review. The IoU is against the OCR-local reference restricted to the unit bbox; neighboring characters, imperfect OCR and rasterization alignment can contaminate it. No source raster is cleaned or deleted in these diagnostic tiles.

| Page | Isolated paths | Median proxy IoU | Proxy IoU ≥0.90 | Global fill ΔL median / within 15 | Proxy pixels beyond expanded bbox |
|---|---:|---:|---:|---:|---:|
| 1 | 275 | 0.465 | 2 | 12.8 / 170 | 0 paths |
| 3 | 139 | 0.510 | 7 | 49.4 / 0 | 0 paths |
| 4 | 81 | 0.683 | 3 | 20.3 / 19 | 0 paths |

Page 1 therefore has 273 of 275 isolated pre-font path proxies below the frozen IoU bound; the global colour differs from the per-unit source sample by more than 15 on 105. These are diagnostic classifications, not final-glyph failures. All 275 fail the earlier region gate; none is emitted. No residual-removal check was exercised because the retained candidate removes no additional raster ink. The zero outside-box count is a tile-path proxy, not a final-font placement certification.

For page 4, one 1,757,958-pixel component qualifies as page border. Interior-only planning produces zero pre-containment occurrences; the narrower border-only diagnostic produces 81. It also changes 60 existing recorded reconstruction decisions relative to interior-only, so it violates the requirement to preserve those decisions. All measured proposal regions fail frozen admission; the #39 page is retained. Page 3’s corresponding diagnostic produces 139 pre-containment outlines, versus zero without the border refinement.

For page 3, the global fill is RGB `[45,44,44]`. The source-owned text-mask sample, excluding artwork, gives page ink `[107,91,83]` over 23,889 sampled pixels. On the same 139 isolated paths, global-versus-per-unit source-sample median ΔL is 49.4 and none is within 15; the page-ink versus per-unit sample median is 3.0 and all 139 are within 15. The page ink is measured from these same samples, so this is not a held-out validation. Median shape-proxy IoU is 0.510, with 7/139 at least 0.90. Both colour and shape merit further examination; neither is established as correct in the final font. The [colour panel index](colour-panel-index.json) links source and identical isolated paths painted in global, page and local colours. No recolouring was made in product code.

The [panel index](panel-index.json) hashes 558 source / #39 / retained-candidate panels at reading size and 4×, covering every proposal in the union of the previous and narrower pilot sets. [Page 3 ledger](ledger-03.json), [page 4 ledger](ledger-04.json), and `p*-shape-colour.json` hold the outcomes and proxy metrics. All final candidate panels show the unchanged baseline because every proposal was rejected.

## Semantics, donors and controls

Identical frozen hOCR hashes establish that the contained probe extraction changes did not require new OCR. On historical p1, the baseline has 190 text-show operations while both diagnostics have 388; the `/ActualText` sequence is unchanged but the ToUnicode resource hash changes. The post-planning fallback still assembles occurrences and invisible owners from the changed segmentation, so a span can be split into more text shows even in invisible mode. This accounts for the changed grouping and is consistent with the extractor differences; a fully isolated causal proof and a mixed-vector semantic repair were not completed. The diagnostic also changes downstream donor decisions: baseline → interior changes 62 shared-symbol decisions on p1, and interior → border changes 273 on p3 and 60 on p4. See [semantic structures](semantic-structure.json), [extraction comparison](semantics-probes.json), and [donor comparison](donor-comparison.json).

The retained candidate avoids those changes by preserving the original full PDF bytes, including `/ActualText`, CID/ToUnicode mappings, and all source and donor behaviour. PDFium and Poppler extraction match on all five historical pages; PDFium searches for `Bacharias`, `Geift`, and the p4 extracted word succeed on both baseline and candidate. PDFium finds zero visible text objects on the five pages. These checks do not constitute a fix for semantics if vectors are later emitted. qpdf and OTS pass ([candidate checks](candidate-check.json), [PDF validation](pdf-check.json)).

All 26 frozen controls had zero regions passing the offline frozen rule ([control admission](control-admission.json)). With the corner estimator, paired baseline/border-switch PDFs were byte-identical for all 26 controls and the Tesseract-failing stub was not invoked. The only full interior-plus-border control run stopped at its second control, black border: PDFium changed 37,833 pixels at 96 DPI and 368,818 at 300 DPI; Poppler extraction changed while PDFium extraction did not. Poppler’s whitespace-token multiset was unchanged, but ordering and line grouping differed. The remaining 24 controls were not run in this stopped pilot. The visual changes were not certified safe or characterized as source damage. This stop is independent of the offline rule, which has not been integrated into the diagnostic PDF path ([stop record](interior-control-replay.json)).

The retained candidate was rendered at 96 and 300 DPI in [PDFium](render-pdfium.json), [Poppler](render-poppler.json), and [MuPDF](render-mupdf.json), with PNG hashes. Since it is byte-identical to baseline, matching renderer output and search results follow for identical renderer settings; no independent source-fidelity claim is made from that equality. No new visible glyphs were emitted.

## Corpus, border components, bytes and cost

With all reconstruction switches off and only frozen-hOCR replay enabled, all five whole-document SHA-256 hashes match `ab7dfba`. The corner-estimator run with the border research switch and trace export also matches all five PDFs byte for byte. Literal all-switches-off CLI execution would invoke prohibited OCR, so the input-replay switch was necessary for this verification. [Corpus results](corpus-results.json) give all hashes, per-page counters, and image-resource byte sums. Image bytes are raw encoded image streams referenced by each page and may be shared; they are not isolated-page PDF sizes. Per-page elapsed times are recorded; RSS is process-level only.

| Document | Baseline / default / corner PDF bytes | Baseline elapsed / peak KiB | Default replay elapsed / peak KiB | Corner switch elapsed / peak KiB |
|---|---:|---:|---:|---:|
| historical | 2,247,390 / 2,247,390 / 2,247,390 | 1:09.10 / 733,820 | 0:59.23 / 733,920 | 1:06.83 / 747,036 |
| receipts | 1,266,953 / 1,266,953 / 1,266,953 | 0:34.03 / 538,276 | 0:24.18 / 556,688 | 0:27.33 / 561,116 |
| financial | 2,842,414 / 2,842,414 / 2,842,414 | 8:14.45 / 1,469,956 | 7:32.23 / 1,958,700 | 7:21.02 / 1,958,484 |
| mixed | 920,248 / 920,248 / 920,248 | 1:47.36 / 364,140 | 1:49.71 / 448,428 | 1:44.92 / 448,248 |
| forms | 831,974 / 831,974 / 831,974 | 0:41.68 / 442,784 | 0:38.52 / 467,316 | 0:40.26 / 479,440 |

The 32-page baseline, default replay and corner-switch corpus totals are each 8,108,979 bytes. The contained historical diagnostics are larger: interior-only 2,273,051 bytes, 2:15.78 and 774,852 KiB peak; border-only 2,358,053 bytes, 5:41.97 and 733,396 KiB peak, versus 2,247,390 baseline. They are not qualified candidates and their cost is not a compression result. Times were measured in separate runs under changing load.

| Page | Baseline / corner disposition | Corner inverted | Corner border components | Encoded page-image resource bytes |
|---|---|---|---:|---:|
| historical 1 | reconstruct / reconstruct | True | 0 | 451,336 |
| historical 2 | raster_baseline_compact / raster_baseline_compact | True | 0 | 306,608 |
| historical 3 | reconstruct / reconstruct | True | 0 | 252,220 |
| historical 4 | reconstruct / reconstruct | True | 0 | 629,404 |
| historical 5 | raster_baseline_compact / raster_baseline_compact | True | 0 | 559,403 |
| receipts 1 | reconstruct / reconstruct | False | 0 | 83,699 |
| receipts 2 | reconstruct / reconstruct | False | 0 | 66,397 |
| receipts 3 | reconstruct / reconstruct | False | 0 | 168,476 |
| receipts 4 | raster_baseline_compact / raster_baseline_compact | True | 0 | 122,638 |
| receipts 5 | reconstruct / reconstruct | False | 0 | 48,912 |
| receipts 6 | reconstruct / reconstruct | True | 0 | 485,445 |
| receipts 7 | reconstruct / reconstruct | True | 1 | 60,807 |
| receipts 8 | reconstruct / reconstruct | True | 0 | 58,362 |
| receipts 9 | reconstruct / reconstruct | True | 1 | 59,408 |
| receipts 10 | reconstruct / reconstruct | False | 0 | 71,595 |
| financial 1 | reconstruct / reconstruct | False | 0 | 168,983 |
| financial 2 | reconstruct / reconstruct | False | 0 | 118,923 |
| financial 3 | reconstruct / reconstruct | False | 0 | 154,805 |
| financial 4 | reconstruct / reconstruct | False | 0 | 159,351 |
| financial 5 | reconstruct / reconstruct | False | 0 | 141,195 |
| financial 6 | reconstruct / reconstruct | False | 0 | 160,726 |
| financial 7 | reconstruct / reconstruct | False | 0 | 144,818 |
| financial 8 | reconstruct / reconstruct | False | 0 | 189,804 |
| financial 9 | reconstruct / reconstruct | False | 0 | 151,487 |
| financial 10 | reconstruct / reconstruct | False | 0 | 131,041 |
| financial 11 | reconstruct / reconstruct | False | 0 | 167,809 |
| financial 12 | reconstruct / reconstruct | False | 0 | 115,613 |
| financial 13 | reconstruct / reconstruct | False | 0 | 170,890 |
| mixed 1 | reconstruct / reconstruct | False | 0 | 253,560 |
| mixed 2 | reconstruct / reconstruct | False | 0 | 256,604 |
| forms 1 | reconstruct / reconstruct | False | 0 | 386,679 |
| forms 2 | reconstruct / reconstruct | False | 0 | 351,145 |

On corner segmentation, the only qualifying components in the 32 pages occur on receipts 7 and 9 (one each); none of the 26 controls has one. On interior segmentation, historical pages 3, 4 and 5 each have one. The switch is intentionally inoperative on corner-estimator pages, so identical bytes do not prove that an ungated pixel-contact rule would be safe. All 26 per-control byte sizes, wall times, peak RSS and component counts are in [control results](control-results.json).

Library tests passed 92/92 with Tesseract blocked, including the frozen border and distance tests. Full product CI was not run, and no live region-admission implementation, completed PDF with verified vectors, held-out glyph review, full interior-control run or product qualification exists. Independent review by Claude is outstanding. The next work, if authorized, must first design and independently validate an admission rule that admits real historical text, preserve baseline semantics and donor choices, and verify actual emitted font glyphs without deleting neighboring source ink; this report does not authorize tuning the frozen pilot.
