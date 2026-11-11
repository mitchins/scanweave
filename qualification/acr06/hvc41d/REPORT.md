# HVC-41D — completed-font development and isolation stop

**HOLD at the owner’s isolation stop condition.** The single historical p1 run reached a real completed PDF with one embedded Type 3 research-font glyph, and its source shape and text semantics passed the measured checks. It is **rejected**, because the patch required to remove ink beneath that glyph covers 15 source pixels outside the saved owned-unit mask. The rejected trial is retained only for examination; it is not a safe candidate. After dropping it, the retained zero-glyph PDF is byte-identical to #39. There are **zero verified emitted glyphs** and zero emitted reference-ink coverage in the retained result. This is evidence about this overlay boundary, not evidence that historical reconstruction is impossible.

The admission and validator development freeze is commit `2a10fc3`, before the one p1 recovery run. Code is research-only: prototype commit `fc84a50`, fail-closed ownership guard `ba24ffa`, and baseline-hash guard `5c29507` on `research/hvc41-feasibility`. No production default, other historical recovery page, PR, merge, q3 or new OCR was used. Claude’s independent review is pending.

## OCR lock and baseline

The HVC-41B accidental ordinary-CLI invocation remains recorded in the [HVC-41C report](../hvc41c/REPORT.md); it was not repeated. The HVC-41C CLI lock rejects a Tesseract launch and requires the frozen OCR sidecar. The HVC-41D runner additionally requires the sidecar and verifies the input PDF SHA-256, all hOCR hashes, p1 dimensions, canonical pixel hash and decoded source-RGB hash before the one-shot marker is created. A failing Tesseract stub was first in PATH; no invocation marker appeared. Six fail-closed cases, including absent sidecar and mismatched PDF, dimensions, canonical pixels, decoded RGB or hOCR, are in [ocr-lock-regression.json](ocr-lock-regression.json). The original CLI-side lock and valid-sidecar regression were tested in HVC-41C. There is no Tesseract library dependency in the inspected workspace. The original preflight compared its baseline argument to the same frozen path; after the run, its SHA-256 was independently checked against the #39 provenance and a direct baseline-hash guard was added in `5c29507`. The p1 recovery was not rerun after that correction.

All five documents, 32 pages, were replayed with the research switches off through the existing OCR-locked runner; completed-PDF hashes and status are recorded in [default-replay.json](default-replay.json). This is a default regression check, not a p1 recovery trial.

## F1–F2: admission and development controls

The unchanged [HVC-41C word-level rule](../hvc41c/RULE_FREEZE.md) uses local source pixels and an exterior ring, excluding OCR word boxes, artwork/protected bounding boxes and the page edge; uncertain words stay on the baseline. On development controls it admitted 20/20 white words, 132/136 and 127/129 financial words, and zero evaluated words on reverse-panel (15), small-receipt (9), black-border (15) and photograph (34). Some negative planner regions were not mapped by the offline hOCR parser; the results are not a claim that every negative region was evaluated. One financial false rejection was a real `TREASURER` blocked by an artwork bbox. These are calibration data, not held-out controls. This run did not rebuild controls with live admission.

## Validator calibration

The [frozen rule and numerical bounds](RULE_FREEZE.md) use actual unshifted PDF placement: minimum directional one-pixel tolerant overlap ≥0.93, centroid offset ≤1 source pixel, area ratio 0.91–1.20, fill-luminance error ≤15, and source-supported hole and separate-component correspondence. Raw IoU remains a manual-review warning; no shift search is used. From 141 source/embedded-font glyphs visually reviewed across white and financial controls, 101 passed all criteria: white 20/22, financial p1 79/117, financial p2 2/2. Of 118 whose colour error was within the unchanged 15-unit bound, 101 passed all checks. Thus the overall pass rate is 71.6%; it is conservative, and the 23 colour failures must not be hidden when assessing its usefulness. The previously problematic white `C` passes; the white `N` also passes the tolerant metrics but has low raw IoU and is flagged for human review. The test does not prove its local outline is perfect.

Conditioned on an original passing glyph, the development perturbations rejected 404/404 two-pixel shifts, 101/101 each 85% and 115% scales, 36/36 filled-counter cases, 101/101 added-punctuation cases, 7/7 dropped-dot/punctuation cases, 101/101 colour errors of 16, and 10/10 cross-character examples (one c/e, four n/h, five l/1). These generated examples are limited, not a guarantee of rejection of all possible defects. [Positive ledger](validator-positives.json), [negative ledger](validator-negatives.json), [summary](validator-summary.json) and [non-overlapping contact-sheet index](control-sheet-index.json) contain the cases and panel hashes. The validator is calibrated on development data only and requires later held-out qualification.

## F3–F5: the one p1 run and final disposition

| Stage | Result |
|---|---:|
| Frozen pre-containment proposals | 275 |
| Source-context word rule | 171/190 words admitted; 273/275 proposals mapped to admitted words |
| Isolated reference and neighbour checks | 62 reached embedded-font diagnostic |
| Frozen completed-font numerical validator | 54 passed; 8 failed |
| Individually reviewed for the completed-PDF trial | 1 provisionally selected; 53 conservatively declined |
| Completed-PDF isolation | 0 accepted; the one trial glyph failed ownership |
| Verified emitted glyphs / reference-ink coverage | 0 / 208,768 pixels = 0% |

The most common early rejection was a padded glyph reference intersecting a neighbouring OCR character (208 proposals; reasons overlap). Some OCR labels did not match their saved symbol entry. These conservative rejections are not claims that those glyphs are wrong. The [275-row final ledger](p1-final-ledger.json) and [panel index](p1-ledger-panel-index.json) cover every proposal; [preflight metrics](p1-preflight-ledger.json), [admission decisions](p1-admission.json), [review sheets](p1-review-index.json) and [visual review](p1-visual-review.json) retain the intermediate results.

The trial glyph was a visually reviewed isolated blackletter `t` at source box `[526,1342,536,1366]`. Its final embedded-font render had tolerant score 1.0, IoU 0.940, area ratio 0.955, centroid offset 0.139 source pixels and fill-luminance error 1.99. The page reference proxy contains 208,768 pixels. In the rejected trial, 126 proxy pixels overlapped the glyph’s midpoint mask; seven source-reference pixels fell outside that midpoint mask but received antialiased font coverage. This is **not verified emitted coverage**, because the patch fails ownership. The [residual check](p1-final-residual.json) found no dark raster pixel under any of its 156 antialiased font-support pixels, and the patched background under the midpoint font mask equalled the sampled paper colour. It does not cure the outside-ownership violation.

The page-level before/after geometry, source and baseline are visible in the [4× glyph panel](/data/coding/scanweave/qualification/acr06/local/hvc41d/final-243-glyph-4x.png), [4× line context](/data/coding/scanweave/qualification/acr06/local/hvc41d/final-243-context-4x.png) and [reading-size context](/data/coding/scanweave/qualification/acr06/local/hvc41d/final-243-context-reading.png). Their “candidate” column is the **rejected** trial, not the final retained output. The [rejected trial PDF](/data/coding/scanweave/qualification/acr06/local/hvc41d/historical-rejected-243.pdf) is provided for inspection; the [retained PDF](/data/coding/scanweave/qualification/acr06/local/hvc41d/historical-candidate.pdf) is the baseline byte for byte and is not presented as reconstruction proof.

## F6: integration, ownership and semantics

The baseline page’s original content stream and image bytes were not rewritten. Its invisible semantic text, donor results, existing font, CID resources, `/ActualText` and ToUnicode streams were retained. The trial appended a separate patch and a pattern containing a separate embedded Type 3 font. On a control, ordinary `/Artifact` text, empty `/ActualText` and a form overlay still caused PDFium text extraction changes; text inside the pattern rendered while both PDFium and Poppler extraction remained unchanged. This is an empirical control result, not a universal PDF semantics guarantee.

The trial’s patch was 156 pixels; the independently recorded owned unit had 141. All 141 owner pixels were included, but **15 patch pixels were outside the unit** ([ownership audit](p1-ownership-check.json)). Render differences also extend beyond the exact patch mask: at 300 DPI PDFium 4, Poppler 45 and MuPDF 42 pixels; at 96 DPI respectively 14, 19 and 13. No renderer changed pixels beyond a two-render-pixel envelope, but an envelope is not the saved ownership mask. This is the precise reason for rejection; the edge differences are not relabelled as compliant. The research finalizer now refuses a patch outside its saved ownership mask; its three focused tests pass. No other candidate was added after the failed completed-PDF trial.

For the rejected trial, PDFium and Poppler extraction was byte-identical to baseline on all five pages, and searching `Bacharias` returned the same one hit. Original page content, image streams and ToUnicode streams matched on all five pages ([candidate checks](candidate-checks.json)). These checks concern the rejected trial; zero-glyph byte identity trivially preserves the baseline semantics. qpdf passed on both PDFs, and OTS passed on the unchanged embedded TrueType font. `pdffonts` identifies the separate trial Type 3 font as embedded; Type 3 has no standalone binary program for OTS ([validity](validity.json), [OTS](ots-checks.json)).

## F7–F8: rendering, bytes, runtime and limitations

The rejected completed PDF was rendered with PDFium, Poppler and MuPDF at 96 and 300 DPI. On pages 2–5 of its complete historical document every comparison had zero changed pixels; p1 changes and exact-mask overruns are tabulated in [render-diffs.json](render-diffs.json). Full local renders are under `qualification/acr06/local/hvc41d/renders/`. The source/baseline/trial panels above show a visually recognizable glyph, but visual similarity cannot override the ownership failure.

| PDF / operation | Complete bytes | Wall | Peak RSS |
|---|---:|---:|---:|
| #39 historical / retained zero glyph | 2,247,390 | unchanged baseline | unchanged baseline |
| Rejected one-glyph trial | 2,251,545 (+4,155) | assembly 0.68 s | 204,632 KiB |
| One-shot admission and font preflight | diagnostic, not a final PDF | 1.51 s | 331,540 KiB |
| Three-renderer five-page comparison | local renders | 73.30 s | 251,684 KiB |

The baseline 32-page total is 8,108,979 bytes; substituting the rejected historical trial would make the sum 8,113,134 bytes (+4,155), calculated from the completed document files, not from a separate corpus PDF. The pilot timings exclude the earlier baseline conversion, OCR and the independent visual review. No full product test suite was rerun: product code and defaults were unchanged, and focused OCR-lock and ownership-guard checks were run. The ownership mask comes from the earlier matching HVC-41 interior unit dump, and is a segmentation ownership record, not ground-truth text annotation. The OCR-local reference is approximate; it can omit faint edges or include marks. The single retained identity review is not an independent lead review. No p3/p4 recovery experiment was conducted. The frozen controls are development data, no fresh held-out qualification exists, and reverse or artwork safety cannot be generalized from them.

The next bounded question is whether an independently validated replacement can be clipped or constructed entirely inside the actual owned footprint while retaining source ink, counters, neighbours, exact semantics and renderer isolation. This is a **proposed future investigation**, not a completed fix or authorization to change #41’s production path.
