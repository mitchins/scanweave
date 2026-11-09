# Issue 37 — glyph-mask design measurement

**Status: the proposed colour-only design is refuted by source-pixel measurements; no candidate, commit or push was made.** The owner explicitly directed us to stop if the inconsistency path would hide glyphs whose source pixels were cleaned. Main already cleans those pixels, and the proposed mask medians do not supply the dark source ink on the two damaged historical pages.

## Reproduction and method

Main `9655fccc1b9e2ce479dd95d06b5f48ea2bfc0e6d` was built using `cargo build --release --locked -p scanweave-cli`. The five source documents were run with `--dpi 300 --profile clearscan --glyph-sharing off`. The temporary opt-in [instrumentation patch](glyph-measure-instrumentation.patch) does not alter output operations: immediately after final occurrence selection it finds each emitted occurrence’s unit, samples `input.rgb` at all true `unit.mask` locations, and records upper per-channel medians. Per-unit luminance percentiles use linear interpolation and Rec. 709 RGB weights. [Measurement script](glyph_measurements.py), [all measurements](glyph-measurements.json), and linked per-page unit files preserve the data. Emitted-operator audit and prior PDFium maps confirm historical 1–5 and receipts 4, 6, 7, 8, 9 have inverted estimates; only historical 2 (22), historical 5 (36), and receipts 4 (7) have visible shows.

Instrumented output SHA-256 hashes matched the earlier fresh main outputs:

- historical: `8486f69c3d694c4a760ad4845c2cb6b64161467adc3e4061fef9b771b84abd2e`
- financial: `96e3b89df58f3e33629300faebf2b3cde81065437b49f1695c24361b10f472bd`
- mixed: `a7efc67a2d331b756aade6a490328d2690343c43523c5284ae8db25937246f9a`
- receipts: `d2da6b69bb803e6c3a5f5db0c6735f3d3357a2f84f12a98fc99fc3ef836d9360`
- forms: `75dfda81cef2a5857328ede7dd76279d72e65a838fb6d352b7f6ea6673d383ff`

## Why the design does not meet the requirements

The mask is source-sampled but its polarity is inherited from segmentation. When the corners are dark, true mask bits can describe light paper or counters rather than text strokes. Historical 2: 22 units, 2,699 samples, old ink `(236,217,172)` at L=217.79; sampled median `(230,214,156)` at L=213.21; ΔL=+4.58. Historical 5: 36 units, 4,552 samples, old ink `(196,192,173)` at L=191.48; sampled median `(195,191,176)` at L=190.77; ΔL=+0.71. Both replacement colours remain paper-like. The earlier source-core analysis of unambiguously matched OCR characters found median luminance 5.33 across 14 on page 2 and 16.71 across 30 on page 5; it is a partial cross-check, not a comprehensive ground truth.

The threshold cannot both change the affected historical pages and preserve the 22 other pages. Forms 2 has |ΔL|=16.00, versus historical 2’s 4.58 and historical 5’s 0.71. Any T large enough to preserve forms 2 also leaves both historical fills untouched; lowering T far enough to change historical 5 changes forms 2, and still supplies a paper-like median. Forms 2’s p10–p90 unit spread is 50.00, exceeding historical 5’s 42.43, so a single spread cutoff cannot separate those pages either. No threshold was tuned on controls.

The frozen positive reverse-panel control `reverse_panel-72` emits 25 visible units. Its synthetic light text is `(241,238,225)`, but `seg.ink` is `(28,31,36)` and sampled `glyph_ink` is `(31,32,36)`: the mask describes the dark panel. Unit p10–p90 spread is just 1.00, so consistency alone would not flag the wrong colour. In contrast, a source-derived contextual dark-table receipt control emits seven vectors and gives `(55,50,45)` against old `(203,205,204)` (ΔL +153.80), which shows the proposed measurement can work in that case. This control reuses original receipt pages 2–6 and is not independent synthetic ground truth.

## Cleanup and conservative branch

Main’s page reports record vector-owned mask suppression of 2,699 pixels on historical 2, 4,552 on historical 5, and 438 on receipts 4 (plus two fringe pixels on historical 2). `clean_replaced_text` clears unprotected vector-owned source masks before the PDF is assembled. [Invisible-ink experiment](invisible_ink_loss.py) renders main with its visible text switched to `Tr 3` while keeping its existing cleaned imagery: all 22 historical-2 and all 36 historical-5 padded review boxes contain source-dark (L<100) pixels that are at least 20 luminance levels brighter in that render. The boxes may overlap and include adjacent marks, and source/output encoding differs, so those figures are not a unique count of missing character strokes. They do show that simply hiding the vectors does not preserve all source detail in their areas. Historical 2 also has two widely separated per-unit luminance populations (p10 92.75, p90 222.96). Under the owner’s explicit instruction, an inconsistency fallback that would leave cleaned holes must not be shipped.

## Segmentation and paper fill

No segmentation, ownership, donor, region, fallback, or text-placement code was changed. `seg.paper` still drives an absolute-luminance-distance foreground mask and is passed to cleanup. The source mask can therefore classify light paper as foreground on the inverted pages. [Main mask index](main-mask-index.json) records the reconstructed masks from prior PDFium source renders. The exploratory [segmentation investigation](segmentation-investigation.json) compares them to an 8-level dominant-interior-mode hypothesis; this is not a validated paper estimator or a proposed segmentation change. Pixel-count differences for the ten pages follow. These measurements support an effect on segmentation; they do not prove that it causes historical’s low vector coverage.

| Page | Current foreground pixels | Hypothetical mode foreground pixels | Differing mask pixels |
|---|---:|---:|---:|
| historical 1 | 3492211 | 676476 | 4017293 |
| historical 2 | 1721353 | 427128 | 1947239 |
| historical 3 | 2673305 | 1231916 | 3760803 |
| historical 4 | 6857458 | 2346896 | 9013710 |
| historical 5 | 3379382 | 1021682 | 4173096 |
| receipts 4 | 483466 | 796275 | 1118053 |
| receipts 6 | 5432429 | 4281977 | 8003034 |
| receipts 7 | 973904 | 166508 | 1103398 |
| receipts 8 | 640407 | 544742 | 1058661 |
| receipts 9 | 716511 | 182768 | 899277 |

`emit_patches` first paints a full-page rectangle in `seg.paper`, then draws image patches above it. [PDF operator audit](main-pdf-audit.json) records this paper fill and the text fill for each page. The rectangle itself is not the text fill; its visible contribution depends on patch coverage and edges. No paper fill was modified.

## All 32 pages

ΔL means L(`seg.ink`) − L(`glyph_ink`); spread is the p90 minus p10 of per-unit median luminances. A dash means no visible unit and therefore no defined glyph median. There is no candidate decision or before/after mask difference because no safe threshold or candidate was produced.

| Page | Paper RGB | seg.ink RGB | glyph.ink RGB | ΔL | Unit p10 / p90 | Spread | Visible units |
|---|---|---|---|---:|---:|---:|---:|
| historical 1 | [56, 53, 52] | [233, 216, 197] | — | — | — / — | — | 0 |
| historical 2 | [1, 1, 1] | [236, 217, 172] | [230, 214, 156] | 4.58 | 92.75 / 222.96 | 130.22 | 22 |
| historical 3 | [41, 40, 43] | [205, 186, 165] | — | — | — / — | — | 0 |
| historical 4 | [39, 39, 40] | [200, 175, 148] | — | — | — / — | — | 0 |
| historical 5 | [34, 33, 34] | [196, 192, 173] | [195, 191, 176] | 0.71 | 161.63 / 204.05 | 42.43 | 36 |
| financial 1 | [214, 198, 155] | [49, 32, 16] | [48, 32, 16] | 0.21 | 23.75 / 45.24 | 21.49 | 281 |
| financial 2 | [215, 199, 156] | [50, 33, 17] | [51, 34, 17] | -0.93 | 26.71 / 46.91 | 20.21 | 197 |
| financial 3 | [212, 197, 153] | [46, 30, 15] | [48, 31, 15] | -1.14 | 20.94 / 42.34 | 21.40 | 244 |
| financial 4 | [214, 197, 157] | [60, 44, 24] | [62, 46, 25] | -1.93 | 37.05 / 55.21 | 18.16 | 345 |
| financial 5 | [212, 196, 153] | [54, 39, 21] | [57, 42, 22] | -2.86 | 31.49 / 51.16 | 19.67 | 182 |
| financial 6 | [213, 198, 156] | [50, 36, 24] | [52, 38, 24] | -1.86 | 24.97 / 48.75 | 23.77 | 207 |
| financial 7 | [215, 199, 159] | [57, 42, 26] | [58, 43, 26] | -0.93 | 32.95 / 50.89 | 17.93 | 235 |
| financial 8 | [215, 199, 158] | [56, 40, 20] | [57, 40, 20] | -0.21 | 31.26 / 51.66 | 20.40 | 437 |
| financial 9 | [212, 195, 151] | [68, 51, 27] | [69, 52, 27] | -0.93 | 43.31 / 64.94 | 21.63 | 329 |
| financial 10 | [212, 196, 154] | [56, 39, 22] | [56, 38, 21] | 0.79 | 29.59 / 48.36 | 18.77 | 280 |
| financial 11 | [215, 199, 157] | [55, 39, 20] | [56, 40, 20] | -0.93 | 30.45 / 48.88 | 18.43 | 420 |
| financial 12 | [213, 198, 155] | [60, 43, 21] | [61, 43, 21] | -0.21 | 35.60 / 54.46 | 18.86 | 215 |
| financial 13 | [214, 199, 159] | [51, 36, 22] | [51, 36, 22] | 0.00 | 26.31 / 47.36 | 21.05 | 345 |
| mixed 1 | [228, 218, 193] | [133, 127, 111] | [134, 127, 110] | -0.14 | 120.20 / 134.98 | 14.77 | 482 |
| mixed 2 | [255, 255, 255] | [0, 0, 0] | [0, 0, 0] | 0.00 | 0.00 / 0.00 | 0.00 | 784 |
| receipts 1 | [137, 107, 96] | [24, 19, 18] | — | — | — / — | — | 0 |
| receipts 2 | [121, 136, 133] | [58, 62, 56] | [60, 68, 84] | -6.74 | 66.61 / 69.52 | 2.91 | 12 |
| receipts 3 | [144, 141, 134] | [56, 57, 52] | [52, 53, 48] | 4.00 | 48.18 / 74.95 | 26.78 | 28 |
| receipts 4 | [166, 123, 88] | [203, 205, 204] | [55, 50, 45] | 153.80 | 45.97 / 56.69 | 10.71 | 7 |
| receipts 5 | [202, 184, 164] | [123, 106, 100] | [170, 109, 115] | -13.22 | 118.23 / 123.13 | 4.90 | 7 |
| receipts 6 | [152, 111, 57] | [224, 208, 193] | — | — | — / — | — | 0 |
| receipts 7 | [29, 30, 14] | [191, 191, 172] | — | — | — / — | — | 0 |
| receipts 8 | [14, 12, 13] | [210, 197, 190] | — | — | — / — | — | 0 |
| receipts 9 | [77, 63, 38] | [154, 149, 131] | — | — | — / — | — | 0 |
| receipts 10 | [191, 188, 183] | [94, 77, 71] | [80, 80, 80] | 0.18 | 64.81 / 99.85 | 35.04 | 28 |
| forms 1 | [255, 255, 255] | [0, 0, 0] | [0, 0, 0] | 0.00 | 0.00 / 25.40 | 25.40 | 297 |
| forms 2 | [255, 255, 255] | [19, 19, 19] | [3, 3, 3] | 16.00 | 0.00 / 50.00 | 50.00 | 207 |

## Frozen controls

[Original seed 370611](controls-truth.json), [supplemental seed 370612](supplemental-truth.json), [font-size variants seed 370613](positive-controls-truth.json), [dark-table variants seed 370614](table-candidates-truth.json), [single source-derived receipt](table-source-control-truth.json), and [contextual source-derived receipt](table-context-truth.json) were frozen before any candidate run. Generators and font hashes are in the manifests; the [DejaVu licence](DejaVu-LICENSE.txt) is recorded. The positive reverse-panel variant emits 25 vectors. The contextual receipt’s third page emits seven; it is derived from the failing corpus and is not an independent fresh control. The other attempted dark-table variants emitted no vectors. A dash means no emitted units.

| Set / case | Page | Visible units | seg.ink | glyph.ink | ΔL | Spread |
|---|---:|---:|---|---|---:|---:|
| measured / binding_shadow | 1 | 14 | [97, 94, 89] | [38, 35, 28] | 59.14 | 1.39 |
| measured / black_border | 1 | 0 | [243, 240, 233] | — | — | — |
| measured / blue | 1 | 36 | [17, 39, 62] | [18, 38, 62] | 0.50 | 4.12 |
| measured / faded_brown | 1 | 78 | [123, 94, 70] | [123, 94, 69] | 0.07 | 2.81 |
| measured / photograph | 1 | 57 | [76, 77, 71] | [52, 53, 48] | 23.93 | 24.36 |
| measured / pink | 1 | 26 | [61, 25, 34] | [61, 26, 36] | -0.86 | 2.72 |
| measured / receipt_table | 1 | 0 | [239, 235, 224] | — | — | — |
| measured / reverse_page | 1 | 0 | [232, 233, 229] | — | — | — |
| measured / reverse_panel | 1 | 0 | [35, 38, 47] | — | — | — |
| measured / white | 1 | 27 | [20, 20, 20] | [21, 21, 21] | -1.00 | 4.00 |
| measured / yellow | 1 | 24 | [53, 40, 19] | [53, 41, 20] | -0.79 | 2.69 |
| supplemental-measured / midtone_table | 1 | 0 | [234, 230, 219] | — | — | — |
| supplemental-measured / reverse_with_margin | 1 | 0 | [30, 35, 39] | — | — | — |
| supplemental-measured / small_receipt | 1 | 0 | [234, 230, 219] | — | — | — |
| positive-measured / dark_table-108 | 1 | 0 | [245, 241, 230] | — | — | — |
| positive-measured / dark_table-160 | 1 | 0 | [245, 241, 230] | — | — | — |
| positive-measured / dark_table-44 | 1 | 0 | [245, 241, 230] | — | — | — |
| positive-measured / dark_table-72 | 1 | 0 | [245, 241, 230] | — | — | — |
| positive-measured / reverse_page-108 | 1 | 0 | [241, 237, 225] | — | — | — |
| positive-measured / reverse_page-160 | 1 | 0 | [241, 237, 225] | — | — | — |
| positive-measured / reverse_page-44 | 1 | 0 | [239, 236, 226] | — | — | — |
| positive-measured / reverse_page-72 | 1 | 0 | [240, 237, 225] | — | — | — |
| positive-measured / reverse_panel-108 | 1 | 0 | [28, 31, 36] | — | — | — |
| positive-measured / reverse_panel-160 | 1 | 0 | [28, 31, 36] | — | — | — |
| positive-measured / reverse_panel-44 | 1 | 0 | [28, 31, 36] | — | — | — |
| positive-measured / reverse_panel-72 | 1 | 25 | [28, 31, 36] | [31, 32, 36] | -1.35 | 1.00 |
| table-measured / DejaVuSans-20 | 1 | 0 | [232, 220, 198] | — | — | — |
| table-measured / DejaVuSans-28 | 1 | 0 | [232, 220, 198] | — | — | — |
| table-measured / DejaVuSans-36 | 1 | 0 | [232, 220, 198] | — | — | — |
| table-measured / DejaVuSans-44 | 1 | 0 | [232, 220, 198] | — | — | — |
| table-measured / DejaVuSerif-20 | 1 | 0 | [232, 220, 198] | — | — | — |
| table-measured / DejaVuSerif-28 | 1 | 0 | [232, 220, 198] | — | — | — |
| table-measured / DejaVuSerif-36 | 1 | 0 | [232, 220, 198] | — | — | — |
| table-measured / DejaVuSerif-44 | 1 | 0 | [232, 220, 198] | — | — | — |
| table-source / receipt-photo-p4 | 1 | 0 | [203, 205, 204] | — | — | — |
| table-context / receipt-context | 1 | 12 | [58, 62, 56] | [60, 68, 84] | -6.74 | 2.91 |
| table-context / receipt-context | 2 | 28 | [56, 57, 52] | [52, 53, 48] | 4.00 | 26.78 |
| table-context / receipt-context | 3 | 7 | [203, 205, 204] | [55, 50, 45] | 153.80 | 10.71 |
| table-context / receipt-context | 4 | 7 | [123, 106, 100] | [170, 109, 115] | -13.22 | 4.90 |
| table-context / receipt-context | 5 | 0 | [224, 208, 193] | — | — | — |

## Reviews, tests and limitations

No candidate was generated, so no candidate glyph panels, three-renderer diffs, extraction/search comparison, qpdf/OTS checks, or candidate gates can be claimed. The [65-glyph panel index](glyph-panel-index.json), [automated visual review](glyph-review.txt), [pixel diffs](pixel-diffs.json), and [semantic checks](semantic-checks.json) concern an earlier rejected raster-fallback prototype only; they are not a review or qualification of this design. An independent Claude review remains outstanding.

The previous raster-fallback prototypes were rejected: they changed unrelated ownership and text extraction; their saved [first patch](rejected-prototype.patch), [automated code review](code-review.txt), and [per-page comparison](report-comparison.json) are retained as history. The earlier Python and clippy runs applied to those rejected experiments, not this design. The locked measurement build passed and reproduced the prior main PDF hashes; no final `cargo test --workspace --locked`, clippy, or Python CI result is claimed because no implementation is being shipped.

Main’s low historical vector coverage may involve the inverted mask; these data do not establish a causal attribution. OCR correctness and the desired true source glyph colour are not established solely by mask sampling. The source-derived receipt control is not independent; the synthetic reverse control has pristine colour and text truth but no separate human review of all source marks. The raster-only comparison includes compression and padded neighboring content.

**Outcome:** as explicitly instructed for refuted evidence and cleaned-away ink, stop rather than ship an unsupported fill or invisible glyphs over holes. The temporary instrumentation was removed; the product worktree remains clean on `fix/ink-paper-polarity-37`. No commit, push, or PR was made.
