# HVC-41C: corrective development run

**HOLD at the required control stop.** The contextual rule admits ordinary development text, but the completed-font validation rejects visually recognizable clean-control glyphs under the unchanged 0.90 IoU bound. This is a **validation-method defect**, not evidence that historical outline reconstruction fails. No historical recovery pilot, p1 admission run, live emission gate, per-glyph p1 ledger or reconstructed candidate PDF was produced. Historical capability and verified coverage remain unmeasured; do not interpret the absence of newly verified glyphs as 0% recoverability.

The [frozen development rule](RULE_FREEZE.md), its code and its control results were committed as `773db80` before any historical recovery pilot. Controls are calibration data, including a contrast bound adjusted after observing the photograph control; a future candidate requires fresh held-out qualification. The OCR-lock code is research commit `2c52dd6`. No product default, PR, release or merge was made.

## OCR lock and prior incident

The HVC-41B report records that an ordinary CLI was inadvertently started and may have invoked Tesseract before it was stopped. It was not repeated here. The [locked runner](locked_run.py) requires a frozen sidecar, checks input-PDF and hOCR SHA-256 before launch, and places a failing Tesseract stub first in PATH. In the CLI, `SCANWEAVE_HVC41C_LOCK_OCR` requires `SCANWEAVE_HVC41C_OCR_SIDECAR`; the replay checks source hash, page count, dimensions, canonical pixel hash and hOCR hash. The locked process-launcher rejects Tesseract calls before execution. No Tesseract/leptess dependency appears in the workspace manifests or lockfile; no library-level Tesseract linkage was found.

[OCR-lock regression](ocr-lock-tests.json): missing sidecar and mismatched source hash, dimensions, pixel hash and hOCR hash all failed closed; a valid frozen white-control replay succeeded and reported the stub uninvoked. The Rust lock test passed. Every baseline-replay log reports that the stub was not invoked.

## F1 — Positive-control admission and false rejections

The context method excludes other OCR boxes, artwork component bboxes, supplied protected-region bboxes and page edges from an exterior word ring. It uses ring paper and word-level source contrast; it does not require paper on tight character-box edges. Counts below are offline word decisions. The baseline planner groups units by OCR span; on all three positives its text-region count equals the distinct observed span count, so the admitted word-span count is also shown. The gate is not connected to live emission.

| Development control | OCR words admitted / total | Baseline text regions / admitted mapped word spans | Rejected-word classes |
|---|---:|---:|---|
| white | 20/20 | 20 / 20 | none |
| financial-01 | 132/136 | 136 / 132 | ink_fraction: 2, low_contrast: 1, artwork_bbox_overlap: 1 |
| financial-02 | 127/129 | 129 / 127 | insufficient_dark_ink: 1, ink_fraction: 2 |

Source-panel spot checks confirm recognizable `Invoice` and `Chicken` on white, and `IPSWICH` and `TOWN` on both financial pages. Financial page 1’s `TREASURER` is a confirmed false rejection caused by a conservative artwork-bbox overlap. The other five rejected OCR entries are punctuation or small marks; their semantic identity was not established from the source, so they are not all labelled false rejections. See [admission panels](admission-panel-index.json), [rejected panels](rejected-panel-index.json), and [visual spot-check record](visual-review.json).

## F2 — Negative controls and fallback

| Control | Evaluated OCR words | Admitted words | Baseline text regions / word spans mapped |
|---|---:|---:|---:|
| reverse-panel | 15 | 0 | 20 / 15 |
| small-receipt | 9 | 0 | 12 / 9 |
| black-border | 15 | 0 | 20 / 15 |
| photograph | 34 | 0 | 40 / 32 |

The admitted-word list is empty for reverse panel, small receipt, black border and photograph. The photograph is a difficult negative: an initial lower-contrast development rule admitted 26 words belonging to photographic artwork; the frozen ≥100 contrast bound removes those admissions on these calibration inputs ([development history](calibration-history.json)). This is not evidence that all photographs or low-contrast documents are safe. Some baseline regions do not map to words returned by the Python hOCR parser, as the table shows; those regions were not independently assessed. No changed-control PDF or live fallback was built in this run, so the offline decisions do not prove output preservation for a future integrated rule.

## Completed-font control validation — stop condition

The validator removes other PDFium page objects in memory and renders an existing embedded-font text object from the completed baseline PDF. Source reference uses the exterior word-ring paper level and a character crop padded by three source pixels; characters with overlapping same-word neighbors are skipped. Both source and rendered masks use midpoint thresholds. A first crop-render implementation produced dimension mismatches and was corrected to render the full source geometry before this final evaluation; neither the 0.90 IoU nor the 15-unit fill bound changed. The selection is a small first-eligible-per-word sample, not a random or exhaustive quality study.

| Control | Glyph objects sampled | IoU ≥0.90 | Fill error ≤15 | Median IoU |
|---|---:|---:|---:|---:|
| white | 5 | 2 | 5 | 0.760 |
| financial-01 | 12 | 4 | 11 | 0.873 |
| financial-02 | 12 | 6 | 10 | 0.905 |

In total 12/29 meet IoU, 26/29 meet fill, and 10/29 meet both. On white, the `C` in `Chicken` is visibly the same recognizable character in source and completed-font render, but its unshifted IoU is 0.755 and its fill error is 2.0 luminance units. A second repeated `C` scores 0.760; the recognizable `N` scores 0.759. A post-hoc sensitivity diagnostic shifts the first `C` mask one source pixel left and yields 0.921, while the `N` remains 0.759 even at the best tested shift. These shifted values were **not** used for admission, nor were thresholds relaxed. The discrepancy may involve registration, rasterization, stroke differences or reference construction; its exact cause is not established. Under the owner’s instruction, the clean-control failure is a validation-method defect and requires stopping before p1. Inspect [font-control panels](font-control-panel-index.json), [glyph ledger](font-control-ledger.json), and [alignment diagnosis](alignment-diagnostic.json).

## F3–F5 — Historical p1 proposals, emitted glyphs and coverage

Not run after the control stop. The earlier 275 proposals are HVC-41B pre-containment proposals, not re-evaluated HVC-41C results. No number passed a live admission, font-render or source-character review in this run; no p1 glyph was emitted or verified and verified source-ink coverage is **not measured**. No unchanged historical PDF is presented as reconstruction evidence. Pages p3 and p4 were not investigated.

## F6 — Donors, text and PDF resources

No HVC-41C reconstruction path or overlay was implemented or invoked after the validator stop. No mixed-vector candidate exists, so isolation of an appended font, OCR duplicate-extraction behavior and source-footprint patching are not qualified. The HVC-41B finding remains relevant: using its global interior segmentation rebuilt owners and changed donor decisions and text-show grouping; it is not used as a workaround. The exact integration boundary remains to be designed and tested for separately approved work. The no-op locked baseline replay changes no PDF bytes, so its donors, text streams, `/ActualText`, ToUnicode, CID resources, rendering and semantics are unchanged by byte identity.

## F7 — PDF size, runtime and RSS

These are complete no-op baseline replays, **not candidate recovery results**. All reconstruction switches were off; only the mandatory OCR lock and sidecar input were on. Hashes, page counts, timings and stub checks are in [baseline results](baseline-results.json).

| Document | Pages | Baseline / replay bytes | Replay wall time | Peak RSS KiB | Byte identical |
|---|---:|---:|---:|---:|---|
| historical | 5 | 2,247,390 / 2,247,390 | 1:01.89 | 753,560 | True |
| receipts | 10 | 1,266,953 / 1,266,953 | 0:24.79 | 552,996 | True |
| financial | 13 | 2,842,414 / 2,842,414 | 7:20.89 | 1,957,196 | True |
| mixed | 2 | 920,248 / 920,248 | 1:42.95 | 449,040 | True |
| forms | 2 | 831,974 / 831,974 | 0:37.24 | 467,584 | True |

All 32 pages are covered by five byte-identical PDFs; corpus bytes remain 8,108,979. No experimental historical candidate was generated, so no candidate-specific size, runtime or RSS exists. Individual control-glyph validation uses existing outputs and creates only in-memory isolated renders and local PNGs.

## F8 — Visual examples and disposition

No newly emitted historical glyph exists to review. The source-only admitted-word panels, source-reference versus actual completed-font panels, and source-context panels for all six financial rejections have SHA-256 indexes linked above. The visible examples support the validation-method stop; they do not certify all existing glyphs. Full Rust/product CI, three-renderer candidate qualification, source-footprint preservation and historical extraction/search for a new output were not run because no candidate passed the control stop. Further work requires a separately authorized repair of the independent rendered-glyph validator and subsequent held-out qualification; do not tune IoU or infer a historical reconstruction failure from these results. Claude’s independent review remains outstanding.
