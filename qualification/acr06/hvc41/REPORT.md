# #41 feasibility: dark borders and historical vector coverage

**Finding: no safe candidate emerged among the tested estimators.** Dominant-interior segmentation recovers much more OCR-local dark-ink reference on historical pages, but fails frozen reverse-panel and small-receipt controls; the other tested alternatives also fail at least one control. On historical pages 3–5, corrected segmentation still leaves every owned unit in `ContactNonText`. On page 1, 275 pre-containment vector proposals overlap 26.8% of the independent reference ink, but this is a mask overlap, not verified glyph coverage. The required ≥10% correctly reconstructed, visually reviewed coverage has **not been demonstrated**. The research output keeps containment; do not ship or bypass it based on these data.

## Design and reference

Baseline is the existing `ab7dfba` 300-DPI ClearScan, glyph-sharing-off run. `baseline.py` re-verifies all five output SHA-256 hashes against #33r provenance; existing Adobe XI PDFs and registered renders are reused, never regenerated. The measurements cover all 32 corpus pages and 26 frozen #37 controls. `estimate.py` reproduces the current four-corner and absolute-luminance-distance foreground rule and compares dominant interior, supported bright mode, interior median and 128 px tile median. The latter four are offline measurements; only dominant interior was also instrumented through the real Rust pipeline. The switch is research-only and preserves/forces containment for any changed page with visible proposals; no unsafe vector PDF is emitted. The research code is on the branch named below; reproduction scripts are included.

The independent real-page proxy intersects OCR symbol boxes with pixels at least 30 luminance units darker than the local 85th-percentile background; assumed dark-on-light, based on these corpus scans, never on the tested page estimate. For controls the known polarity sets dark or light. OCR misses text and boxes can include rules, artwork or texture. Receipt 7 has no OCR reference and cannot be scored. Direct synthetic truth verifies source PNG/PDF hashes and checks exact known ink-colour core and exact paper pixels *inside accepted OCR boxes*: antialiasing, outside-box text and same-colour artwork are excluded or ambiguous. The photo proxy includes substantial texture (142,831 reference pixels versus 2,206 exact ink cores); its proxy recall cannot establish photo text recall. This is not ground-truth segmentation or a safety certification. Border occupancy and out-of-box pixels are proxies; rules and artwork cannot be separately quantified without annotated ground truth. Small-component/hole counts in JSON are similarly diagnostic, with overlapping OCR boxes possibly double-counted.

## Page-level failure decomposition

For the ten affected pages: `R/P` is reference-ink recall / reference-paper false admission, corner then dominant interior. `OCR` is symbol boxes; `units` is owned units after the interior experiment; `regions` counts those units by vector / contact-nontext / unsupported / fidelity. `pre→post` is proposed visible occurrences before containment → reported visible after. Adobe figures are visible-object counts and bounding-box overlap with reference ink, an **upper bound**, not Adobe glyph-mask coverage. p7 lacks a usable OCR reference.

| Page | Corner paper / ink RGB | OCR | Corner R/P | Interior R/P | Units; regions V/C/U/F | Pre→post | Adobe objects / bbox upper bound |
|---|---|---:|---:|---:|---:|---:|---:|
| historical 1 | [56, 53, 52] / [233, 216, 197] | 905 | 36.2%/100.0% | 82.4%/0.0% | 843; 275/218/318/32 | 275→0 | 226 / 62.6% |
| historical 2 | [1, 1, 1] / [236, 217, 172] | 574 | 44.6%/100.0% | 85.2%/0.0% | 608; 73/403/124/8 | 73→0 | 129 / 63.3% |
| historical 3 | [41, 40, 43] / [205, 186, 165] | 860 | 43.7%/100.0% | 90.0%/0.2% | 803; 0/803/0/0 | 0→0 | 280 / 94.8% |
| historical 4 | [39, 38, 40] / [200, 174, 147] | 404 | 24.3%/99.5% | 85.8%/0.6% | 343; 0/343/0/0 | 0→0 | 92 / 74.9% |
| historical 5 | [34, 33, 34] / [196, 192, 173] | 1486 | 32.4%/100.0% | 82.9%/0.0% | 1125; 0/1125/0/0 | 0→0 | 303 / 84.9% |
| receipts 4 | [166, 123, 88] / [203, 205, 204] | 56 | 33.0%/31.1% | 89.9%/17.3% | 85; 0/85/0/0 | 0→0 | 17 / 91.5% |
| receipts 6 | [152, 111, 57] / [224, 208, 193] | 160 | 0.1%/75.2% | 94.4%/14.4% | 45; 0/45/0/0 | 0→0 | 59 / 89.3% |
| receipts 7 | [29, 30, 14] / [191, 191, 172] | 0 | n/a/n/a | n/a/n/a | 0; 0/0/0/0 | 0→0 | 4 / n/a |
| receipts 8 | [14, 12, 13] / [210, 197, 190] | 17 | 51.6%/100.0% | 84.0%/0.2% | 40; 0/40/0/0 | 0→0 | 25 / 99.2% |
| receipts 9 | [77, 63, 38] / [154, 149, 131] | 110 | 0.3%/88.4% | 82.7%/0.0% | 95; 30/27/30/8 | 30→0 | 17 / 68.4% |

Historical interior segmentation still classifies 48–70% of the 5%-wide page border as foreground, demonstrating the distinction between finding ink and excluding borders. Receipt 7 has no boxes or owned units in this run. Main itself reports 22, 36 and 7 pre-containment occurrences on historical 2, historical 5 and receipts 4 respectively; the merged #37 fix suppresses those visible occurrences. The old masks selected light paper there, so main’s `text_ink_px` counters cannot be read as actual text-ink coverage.

## Baseline page inputs and stage counters

Reference RGB values are OCR-local medians and are not ground truth. Foreground is the original corner-based full-page foreground, so on inverted pages most is paper. `owned / traced / fidelity` are reported pipeline counters, not necessarily sequential glyph counts. Full donor, ownership, region and coverage records for all 32 pages are in [baseline-funnel.json](baseline-funnel.json). Source-safe visible coverage on these pages is not established by these counters; all have zero visible vector objects after containment.

| Page | Source px @ DPI | Local paper / ink RGB | Corner foreground px | Baseline owned / trace shapes / below fidelity | Baseline pre→post |
|---|---|---|---:|---:|---:|
| historical 1 | 1738×2355 @ 300 | [243, 234, 215] / [99, 80, 74] | 3,492,212 | 152 / 1 / 0 | 0→0 |
| historical 2 | 1116×1835 @ 300 | [244, 233, 179] / [74, 42, 22] | 1,721,353 | 237 / 153 / 106 | 22→0 |
| historical 3 | 1676×2287 @ 300 | [182, 169, 148] / [109, 94, 84] | 2,673,305 | 2 / 1 / 0 | 0→0 |
| historical 4 | 2319×3928 @ 300 | [195, 170, 143] / [81, 64, 45] | 6,857,458 | 165 / 1 / 0 | 0→0 |
| historical 5 | 1757×2440 @ 300 | [205, 204, 187] / [50, 49, 41] | 3,379,382 | 517 / 321 / 90 | 36→0 |
| receipts 4 | 1109×1479 @ 300 | [173, 169, 165] / [95, 92, 90] | 483,466 | 83 / 11 / 3 | 7→0 |
| receipts 6 | 2305×4096 @ 300 | [203, 185, 167] / [123, 103, 110] | 5,432,429 | 1 / 1 / 0 | 0→0 |
| receipts 7 | 865×1297 @ 300 | None / None | 973,909 | 0 / 1 / 0 | 0→0 |
| receipts 8 | 865×1297 @ 300 | [223, 211, 204] / [87, 72, 65] | 640,407 | 9 / 1 / 0 | 0→0 |
| receipts 9 | 865×1297 @ 300 | [143, 138, 121] / [88, 81, 67] | 716,511 | 47 / 1 / 0 | 0→0 |

## Estimator and control comparison

This diagnostic screen is **post hoc**, not a calibrated acceptance rule: less than 95% exact-colour ink-core recall or more than 5% exact-paper admission on any control is counted as a failure; when paper truth is unavailable only recall is evaluated. It cannot establish safety. Historical recall is the median across its five page-level OCR-local proxies.

| Estimator | Historical median reference recall | Screen failures / 26 | Illustrative failures |
|---|---:|---:|---|
| corner | 36.2% | 14 | black_border, receipt_table, reverse_panel, small_receipt, reverse_with_margin, midtone_table, reverse_panel-44, reverse_panel-72, reverse_panel-108, reverse_panel-160, dark_table-44, dark_table-72, dark_table-108, dark_table-160 |
| interior_mode | 85.2% | 2 | reverse_panel, small_receipt |
| bright_mode | 93.0% | 7 | reverse_panel, reverse_page-72, reverse_page-108, reverse_page-160, reverse_panel-72, reverse_panel-108, reverse_panel-160 |
| interior_median | 83.4% | 2 | reverse_panel, small_receipt |
| tile_median_128 | 81.6% | 3 | small_receipt, reverse_panel-160, dark_table-160 |

For example the base reverse-panel and small-receipt controls give dominant interior 0% exact-ink-core recall and 100% exact-paper admission. Bright mode fails the true reverse-page controls. Tiled median narrowly misses the screen on small receipt, reverse-panel-160 and dark-table-160. On the photographic control, pristine exact-core recall is essentially 100% for all estimators; no uniform exact paper reference exists there. These observations reject the tested general rules, not the possibility of a different estimator. Dark borders, coloured paper, table, reverse, binding shadow and photo results are in `reference-controls.json` and `estimator-measurements.json`.

## Reconstruction funnel and safety

`baseline-funnel.json` records OCR, ownership, region counts, donor decisions, reported trace/budget and fidelity counters for all 32 pages. `trial-funnel.json` gives the actual instrumented interior-mode pipeline for all historical and receipts pages, with per-layer overlap against source reference. `proposed-*.json` records every pre-containment occurrence: masks are **not** traced outlines and OCR labels are not correctness checks. Per-region pixel counts may overlap. Other estimators stop at segmentation because the frozen-control failures already meet the owner’s stop condition; their real donor/trace/geometry funnels were not run.

Historical p1: 905 OCR symbols; 843 owned units, of which 275 reach vector planning, 218 contact non-text, 318 unsupported and 32 fidelity-policy raster. The 275 pre-containment proposals overlap 55,975/208,768 = 26.8% of the proxy, and an exploratory post-hoc mask/fill screen retains 255 and 25.4%. Neither proves the glyph geometry, source character, placement, color or freedom from damage. Donor decisions among 843 occurrences include 597 without supported donor, 67 canonical reuse, 50 repaired and 12 rejected donor geometry; these categories describe the recorded stage, not independent summed gates. Reported trace statistics are not necessarily per-occurrence rejections. For p2, 608 owned units yield 73 proposals, 10.8% proxy overlap; 403 are contact non-text. On p3/p4/p5, respectively 803/343/1,125 owned units are all contact non-text and produce zero proposals. This region gate is a concrete independent obstacle to recovery even after this segmentation experiment. No glyph was asserted verified-safe; no ≥10% safe coverage claim is warranted.

The visual evidence contains source, corrected ScanWeave, pre-existing Adobe registered output, reference mask, corner mask, interior and tiled masks at page and line scale: [panel-index.json](panel-index.json). [control-panel-index.json](control-panel-index.json) covers selected controls (no Adobe column); [unit-panel-index.json](unit-panel-index.json) contains 40 selected p1/p2 mask examples, not a complete glyph correctness review. All indexes carry SHA-256, actual large PNGs are under `qualification/acr06/local/hvc41/panels/`. Inspection of historical p1/p2 and reverse-panel and small-receipt masks shows why paper/ink separation is not a complete glyph-shape validation. No Adobe, Wine or VM execution was used.

## Contained-output rendering and semantics

The contained experimental historical and receipts PDFs have zero changed pixels versus baseline on every page in PDFium, Poppler and MuPDF at 96 and 300 DPI ([PDFium](render-pdfium.json), [Poppler](render-poppler.json), [MuPDF](render-mupdf.json)). This only establishes the appearance of the contained outputs, not candidate vector quality. Poppler and PDFium extraction is not invariant: [semantics.json](semantics.json) records page-level comparisons. Historical p1 has token and order changes in both engines (PDFium has 4 baseline-only and 2 probe-only whitespace tokens; Poppler 78 and 2); historical p2 and p5 differ in ordering/segmentation, as do receipt p4 and p9. These raw token differences can arise from joined or split words and are not a definitive lost-word count, but the differences are real and unresolved. This probe is not suitable for release even apart from the control failures; no claim is made that it preserves OCR semantics.

The research switch substitutes interior paper only when its luminance exceeds the corner estimate by more than 60; the offline alternatives always report their own estimate. On normal receipts pages 1, 2, 3, 5 and 10 the switch retains the corner estimate, so their actual pipeline run is not the offline interior-mode counterfactual. On all ten inverted pages the experimental pipeline and offline dominant-interior RGB agree. Independent source and Adobe XI file hashes and corrected PDF hashes all matched prior provenance ([provenance.json](provenance.json)). The research-only Rust library suite passed 90 tests; this is instrumentation validation, not production qualification.

## ContactNonText decomposition

**Actual bottleneck: bounding-box contact with page-spanning artwork components.** With the interior estimator on historical pages 3–5, all 2,271 owned units are in regions whose bboxes overlap artwork bboxes. For 2,024 units there is no artwork pixel within four Euclidean pixels of any unit pixel in that region; 247 units are in regions with actual nearby artwork pixels. Suspect flags overlap those categories. On each of the three pages, the largest artwork component has a page-spanning bbox intersecting every text region, while **that component itself has zero unit-pixel contacts** within four pixels. Other components account for the real pixel contacts.

This diagnostic uses the same connected components, ownership, OCR, margins and estimators as the earlier run. The counterfactual replaces bbox intersection with a mask-pixel Euclidean distance of at most `CONTACT_MARGIN_PX = 4`, and retains the existing independent suspect and protected-region tests. It is behind `SCANWEAVE_HVC41_PIXEL_CONTACT` on research commit `4c9a6ca` only. Pages with pre-containment vectors are forced to source-raster containment, including in the corner run. No unverified glyphs are exposed. The focused proximity test passes, including boundary and diagonal distances.

For each text region, [per-page region JSON](contact/) records unit indexes, original planner disposition, bbox contacts with component IDs, pixel counts, bbox fill ratios and pixel-contact booleans, plus suspect unit symbols and boxes. The `suspect` test in `ownership.rs::unit_ink_exceeds_slots` compares the owned component ink bbox to its **original owning OCR slot** bbox expanded by six pixels: any side beyond that is suspect. The recorded slots may subsequently include absorbed slots. Protected regions retain priority. Standalone artwork entries are also included. [decomposition.json](contact/decomposition.json) lists the five largest artwork components per page; [panel index](contact/panel-index.json) hashes 20 source-overlay sheets showing the three largest masks and bboxes for each affected page and estimator.

The cells below are **units / union of source-reference ink pixels**. “BBox only” means at least one artwork bbox intersects, but no artwork pixel is within four pixels; “pixel” means at least one actual nearby artwork pixel; “suspect” is independent and can overlap either. Counts are region-level: an entire multi-unit region is counted if any of its units meets the condition. OCR-local ink is the proxy described above, not ground-truth characters; receipt 7 has no reference. The corner rows compare against the actual current estimator, not a polarity-adjusted estimate.

| Estimator / page | Bbox only: units / ref px | Pixel contact: units / ref px | Suspect: units / ref px |
|---|---:|---:|---:|
| interior historical 1 | 75 / 17,492 | 40 / 8,995 | 116 / 24,986 |
| interior historical 2 | 115 / 29,801 | 228 / 64,705 | 149 / 40,752 |
| interior historical 3 | 783 / 127,128 | 20 / 2,756 | 94 / 16,083 |
| interior historical 4 | 246 / 255,969 | 97 / 151,315 | 86 / 104,268 |
| interior historical 5 | 995 / 443,220 | 130 / 69,252 | 618 / 292,372 |
| interior receipts 4 | 76 / 6,927 | 9 / 897 | 8 / 1,352 |
| interior receipts 6 | 40 / 2,209 | 5 / 3 | 38 / 2,022 |
| interior receipts 7 | 0 / 0 | 0 / 0 | 0 / 0 |
| interior receipts 8 | 40 / 3,022 | 0 / 0 | 0 / 0 |
| interior receipts 9 | 1 / 3,364 | 5 / 1,836 | 27 / 15,619 |
| corner historical 1 | 0 / 0 | 152 / 2,265 | 0 / 0 |
| corner historical 2 | 1 / 1 | 1 / 90,462 | 1 / 90,462 |
| corner historical 3 | 0 / 0 | 2 / 125 | 0 / 0 |
| corner historical 4 | 5 / 108 | 160 / 21,815 | 16 / 6,252 |
| corner historical 5 | 13 / 1,002 | 6 / 182,914 | 22 / 184,346 |
| corner receipts 4 | 11 / 480 | 56 / 1,058 | 6 / 599 |
| corner receipts 6 | 0 / 0 | 1 / 2 | 0 / 0 |
| corner receipts 7 | 0 / 0 | 0 / 0 | 0 / 0 |
| corner receipts 8 | 0 / 0 | 9 / 197 | 0 / 0 |
| corner receipts 9 | 26 / 42 | 21 / 15 | 3 / 0 |

Largest interior artwork components on the three principal pages:

| Page | Component IDs | Bbox (source px) | Artwork pixels | Bbox fill | Units bbox-hit / actually nearby |
|---|---|---|---:|---:|---:|
| historical 3 | [1] | [0.0, 0.0, 1676.0, 2287.0] | 1,090,936 | 28.5% | 803 / 0 |
| historical 4 | [1] | [0.0, 0.0, 2319.0, 3928.0] | 1,757,958 | 19.3% | 343 / 0 |
| historical 5 | [1] | [0.0, 0.0, 1757.0, 2440.0] | 477,439 | 11.1% | 1125 / 0 |

The following funnel is the contained interior-mode counterfactual. `Vector` is the number of regions changed from bbox-contact raster to pixel-contact vector at the initial planning stage. Proposals are actual pre-containment visible occurrences after the other pipeline gates; “new” counts those within newly released regions. Reference overlap is the union of their owned source masks, not rendered outline coverage. The screen is post-hoc: source-mask reference precision ≥0.9, page-fill luminance within 25 of the unit’s reference-ink median, donor source-mask IoU ≥0.98, and prototype trace IoU ≥0.98 when reported. The donor IoU and trace-budget flags are proxies, not a complete independent geometry test; neither this screen nor OCR label verifies the emitted character. Full per-occurrence measurements are in [new-proposals.json](contact/new-proposals.json).

| Interior page | Newly vector regions / units | Pre-containment proposals: bbox → pixel | Newly proposed / proxy ink overlap | Screened / proxy ink overlap |
|---|---:|---:|---:|---:|
| historical 1 | 15 / 75 | 275 → 267 | 16 / 1.8% | 12 / 1.5% |
| historical 2 | 18 / 100 | 73 → 95 | 22 / 2.9% | 9 / 1.6% |
| historical 3 | 169 / 689 | 0 → 160 | 160 / 18.8% | 0 / 0.0% |
| historical 4 | 44 / 196 | 0 → 93 | 93 / 21.6% | 54 / 17.5% |
| historical 5 | 115 / 465 | 0 → 129 | 129 / 10.1% | 92 / 8.6% |
| receipts 4 | 12 / 68 | 0 → 61 | 61 / 63.5% | 11 / 19.3% |
| receipts 6 | 3 / 4 | 0 → 4 | 4 / 6.7% | 0 / 0.0% |
| receipts 7 | 0 / 0 | 0 → 0 | 0 / n/a | 0 / n/a |
| receipts 8 | 8 / 40 | 0 → 40 | 40 / 84.0% | 0 / 0.0% |
| receipts 9 | 0 / 0 | 30 → 30 | 0 / 0.0% | 0 / 0.0% |

For historical p3 all 160 newly proposed units fail the exploratory fill threshold; median absolute fill difference is 50.4 luminance units. The threshold is not calibrated, and reference boxes can miss or include neighboring content, so this is a warning rather than a character verdict. Pages 4 and 5 have more screen passes, but no traced outline has been independently matched to the source. Consequently neither the 17.5% p4 screened-mask proxy nor any other number proves the ≥10% safe-visible-vector target.

The [40 unit panels](contact/panel-index.json) show source / corner segmentation / interior segmentation / newly proposed unit mask at enlarged scale: 20 worst proxy-agreement cases and 20 seeded-random cases (seed 41037), without using OCR labels as ground truth. A low proxy overlap can reflect a missed or inaccurate OCR box; the panels do not display or validate the traced glyph. The masks retain the source ownership geometry; they are not generated vectors.

**Normal-page regression exposure:** with the corner estimator unchanged, the proximity rule changes initial region dispositions on 14 of 22 normal-polarity pages: 523 regions containing 2,149 units. This is planner exposure, not a claim that all units became visible vectors. The full 32-page corner run is recorded in `decomposition.json`; forced containment means its outputs are not an unchanged-visible-output candidate.

| Normal page with changed regions | Regions | Units |
|---|---:|---:|
| receipts 2 | 5 | 12 |
| receipts 10 | 7 | 30 |
| financial 1 | 1 | 4 |
| financial 2 | 1 | 6 |
| financial 3 | 2 | 10 |
| financial 6 | 3 | 5 |
| financial 8 | 1 | 3 |
| financial 9 | 1 | 7 |
| financial 10 | 1 | 4 |
| financial 11 | 2 | 10 |
| mixed 1 | 1 | 4 |
| mixed 2 | 3 | 12 |
| forms 1 | 140 | 488 |
| forms 2 | 355 | 1554 |

The bbox test is therefore the dominant planning bottleneck on these historical pages, and pixel proximity is a useful **bounded research direction**, not an implementation ready to ship. A single further experiment would first need a source-supported estimator/admission rule that handles the failed reverse-panel and small-receipt controls, confines any planner change so normal pages and shared donors remain unchanged, and independently validates each released outline, fill, counters, placement, extraction and rendering against the source. Until then retain #39 containment; no product experiment or default change is recommended.

## Cost, reproducibility, and recommendation

These are contained diagnostics, not a vector-coverage or compression candidate. The complete historical research PDF is 2,273,051 bytes versus 2,247,390 baseline (+25,661); receipts is 1,269,241 versus 1,266,953 (+2,288). This difference includes changed segmentation, donors, containment and shared serialization; it is **not** a compression saving or an estimate of safely recoverable vectors. Probe runtime / max RSS from `/usr/bin/time -v`: historical 2:21.29 / 782,840 KiB; receipts 0:22.42 / 551,804 KiB. Estimator-only offline timing and memory for all 58 images are in local `time-*.txt`; this excludes OCR and full conversion and is not an end-to-end benchmark.


The normal-polarity financial, mixed and forms complete PDFs are byte-identical, so their visible rendering and extraction are unchanged. Historical and receipts render identically in all three engines but have the extraction differences above. Full hashes, sizes and `/usr/bin/time -v` measurements are in [results.json](results.json). Wall times from separate runs include OCR and system load and are not controlled benchmark deltas.

| Document | Baseline bytes | Probe bytes | Baseline elapsed / peak KiB | Probe elapsed / peak KiB | Byte identical |
|---|---:|---:|---:|---:|---|
| historical | 2,247,390 | 2,273,051 | 1:09.10 / 733,820 | 2:21.29 / 782,840 | no |
| receipts | 1,266,953 | 1,269,241 | 0:34.03 / 538,276 | 0:22.42 / 551,804 | no |
| financial | 2,842,414 | 2,842,414 | 8:14.45 / 1,469,956 | 7:44.95 / 1,462,336 | yes |
| mixed | 920,248 | 920,248 | 1:47.36 / 364,140 | 1:49.06 / 363,992 | yes |
| forms | 831,974 | 831,974 | 0:41.68 / 442,784 | 0:43.22 / 441,048 | yes |

The research instrumentation is reproducible on branch `research/hvc41-feasibility` at `88482b4`; its switch is disabled by default. Reproduction commands, exact estimator timing, hashes and the 90-test result are included or linked above. Independent review by Claude remains outstanding.

Engineering risks include polarity mixtures within a page, receipt/table inference, large border and artwork admissions, reference errors, changes to ownership and shared donors, and contour/fill fidelity; safe implementation would need source-validated glyph geometry and per-region polarity handling plus preservation of unaffected pages. That is not justified by the current evidence. **Recommendation: no implementation experiment selected yet.** The bounded follow-up and its prerequisites are set out in the ContactNonText decomposition. Keep #37 containment. Do not infer that all possible estimators are unsafe.
