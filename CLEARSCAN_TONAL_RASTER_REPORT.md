# Whole-page tonal raster compaction

Base: reviewed product `99ec072` (PR1), including bounded source import and default-colour override rejection. Separate branch `improve/whole-page-tonal-raster`. No shaded-paper reconstruction, OCR, glyph eligibility, font dictionary, native exception or faithful changes.

## Primary completed PDFs

| Page | Matched normal CLI baseline B | Q98 trial B | Q100 / selected B |
|---|---:|---:|---:|
| cord-00 | 898,775 | 360,411 | 417,835 |
| cord-05 | 4,452,414 | 1,701,058 | 1,885,848 |
| history-02 | 5,186,194 | 1,791,549 | 2,727,167 |
| history-03 | 9,350,337 | 3,566,007 | 4,577,626 |
| **Total** | **19,887,720** | **7,419,025** | **9,608,476** |

Q100 saves **10,279,244 B / 51.69%** in actual native ScanWeave PDFs. Q98 is a fixed control, not a third product profile; Q100 is retained for its closer source detail, rather than choosing the smallest trial. All four original input resources are full-page DeviceRGB Flate; current lossless source samples are bound to the same native dimensions and physical geometry. See `qualification/tonal_raster/inventory.json` and frozen inspection settings/regions in `controls.json`.

## Integrated implementation

Only ClearScan document assembly considers the representation. A candidate must be one unchanged native whole-page patch, no emitted glyphs, no reduced-background flag, no raster-baseline flag, and no verified source JPEG. Size/colour/sample validation and a 16-million-pixel cap apply; fewer than 64 luminance levels stays lossless. Existing source-image trust checks and verified JPEG passthrough are retained.

The existing Rust image encoder writes quality-100 DCT with full chroma resolution (4:4:4, emitted SOF factors regression-tested). No new executable or crate dependency. Every decoded channel must remain within 12 levels; source dark **and light** thin-ridge evidence is checked in both axes, including faint strokes. These are conservative admission controls, not proof that every possible meaningful mark is detected. Actual fixed-source visual/recognition tests and independent review supplement them. The light-polarity check was added in response to independent review, without relaxing any threshold; final primary PDFs are byte-identical to reviewed Q100 trials.

Existing exact resource reuse and grayscale encoding remain. Encoded DCT resource identities cannot alias lossless native resources. Both complete serialized PDFs are assembled and compared; compact output is selected only when smaller. Encoder failure or failed admission retains lossless output. Public assembly and faithful stay on their original path. The independently qualified searchable-raster baseline also remains lossless.

Focused tests cover invalid buffers, size limits, bitonal exclusion, dark/light faint marks, thin rules, deterministic 4:4:4 encoding, native exceptions/changed patch exclusion, and byte-exact verified source JPEG passthrough. No `/ActualText`, Unicode, placement or canonical glyph code changes.

## Primary preservation result

Independent review inspected original versus Q100 fixed crops and found no apparent lost strokes, punctuation, fine artwork or rules. Source classes include faint thermal text/amount punctuation, dot-matrix numerals, shaded historical blackletter, show-through and the decorated initial. Independent same-geometry Poppler/PDFium ridge checks found zero lost qualifying dark or light ridges on all four pages. Minor tonal differences are present; these are intentionally lossy ClearScan representations, not faithful pixel preservation.

All decoded non-image streams, per-renderer extracted text and placements match each primary baseline. Full-page errors, fixed-region edge/stroke measurements and actual 300% PDF crops are retained separately. Source-native samples are also measured independently from renderer phase. Rendered-output Tesseract strings and financial queries are recorded, not inferred from the unchanged invisible overlay. The selected receipt full-page OCR remains poor; missing queries are not treated as permission to discard visible text.

## Completed 32-page comparison

| Collection | Matched reviewed product B | Updated B | Saved B |
|---|---:|---:|---:|
| Receipts | 11,117,351 | 6,945,090 | 4,172,261 |
| Historical | 34,546,050 | 24,637,206 | 9,908,844 |
| Financial | 9,782,629 | 9,782,629 | 0 |
| Mixed artwork | 3,228,942 | 3,228,942 | 0 |
| Forms | 859,524 | 859,524 | 0 |
| **Total** | **59,534,496** | **45,453,391** | **14,081,105 (23.65%)** |

The frozen 59,599,260 B total predates the donor-test closure. Its additional 64,764 B difference is not credited to this change. Compared with original inputs (81,969,566 B), the updated collection saves 44.55%. It remains 10.88 times Adobe XI's 4,178,103 B and 2.97 times OCRmyPDF -O3's 15,315,903 B. Comparator outputs and document membership remain frozen; no new competitor settings were selected.

| Serialized contribution | Before B | After B |
|---|---:|---:|
| Images | 56,975,284 | 42,894,958 |
| Embedded fonts | 1,632,820 | 1,632,820 |
| Page content streams | 349,979 | 349,979 |
| Other PDF bytes | 576,413 | 575,634 |

Exactly eight whole-page images changed: CORD 00/05/06/07/08 and history 00/02/03. Their streams save 14,080,326 B; remaining savings are 779 B of serialization overhead. All 32 pages retain identical ownership/patch decisions, geometry, decoded non-image streams, font programs, Unicode maps and graphics operations. No native exceptions or reduced paper changed. Independent review inspected all eight changed pages in Poppler and PDFium, including faint show-through, ornament, red stamp, receipt punctuation and small printed strokes. No apparent meaningful detail loss or objectionable ringing/blocking was found. This is development-corpus evidence, not universal lossy-encoding safety.

## Search, regression and mechanical checks

Native financial-number search remains **17/49 in both renderers**. Rendered-image OCR was independently rerun and strings retained in `rendered-ocr.json`; full-page thermal OCR remains unreliable (the two primary receipts retain 0/5 tested queries). Changed recognized strings are disclosed, not counted as OCR improvement or hidden by the unchanged overlay. Source/renderer crop metrics and visual review, rather than word-count changes, establish the image decision.

Current matched Linn is **820 painted glyphs**, forms **504**, identical before/after. The older 748/500 figures predate donor closure; JPEG did not increase vector coverage. Standalone Linn (666,153 B), forms (859,524 B), the mixed collection (3,228,942 B), and faithful CORD-00 (1,500,534 B) are byte-identical to their matched baselines. Synthetic 300/600 DPI outputs are **185,119 / 258,720 B**, byte-identical to the established real-convergence PDFs, preserving all glyph geometry, canonical reuse, background and Unicode. Normal ClearScan repeat serialization is deterministic.

Unfiltered workspace Rust tests, Clippy with warnings denied and all nine Python CI contracts pass. The donor regression is included, not filtered. Corpus PDFs pass qpdf and embedded-font OTS checks (inherited font timestamp warnings only); both independent renderers parse/render all pages. Known P01–P08 visual limitations remain recorded in the prior reports and are not relabeled as passing. The new code does not address shaded-paper reconstruction or rough fallback text.

## Runtime and memory

The codec adds encode/decode admission work and a second complete serialization only on eligible pages. It is not a speed optimization. Primary normal CLI measurements below include OCR and conversion; peak RSS is process-wide, not only the encoder.

- cord-00: 1.79 s; peak RSS 45,584 KiB.
- cord-05: 8.90 s; peak RSS 279,068 KiB.
- history-02: 7.43 s; peak RSS 154,160 KiB.
- history-03: 13.48 s; peak RSS 353,164 KiB.

Matched before/after collection wall seconds: receipts 46.18/41.92, historical 135.97/115.71, financial 662.66/750.21, mixed 158.30/165.17, forms 53.29/80.59. These two-worker runs overlapped other qualification work; unchanged financial/mixed/forms files demonstrate that their timing fluctuations are not codec effects. Do not infer a causal corpus speedup. Isolated history-02 increased from 3.51 to 7.43 seconds. Full timing/RSS records are in `measurements.json` and run sidecars.

## Reproduction, review and remaining cost

Base `99ec072`; implementation `5e6f4d9`, followed only by report/qualification-script timeout corrections. `run-manifest.json` records actual PDF hashes and sizes. Input identities, dimensions, encodings and geometry are in `inventory.json`; source attribution remains `qualification/pdf_packaging/attribution/ATTRIBUTION.md`. No new datasets or sealed holdout were used.

Use the existing qualification Python environment with pikepdf, PDFium, Pillow and NumPy. Build the release converter; `run.py` accepts `SCANWEAVE_BIN` and groups; `synthetic.py`, `check_controls.py`, `measure.py`, `outline_inventory.py` and `verify_results.py` reproduce checks. `baseline.py` requires a release binary built from 99ec072 at its documented path. `controls.json` freezes the two settings and inspection regions before encoding. The Q98 trial's original private module is retained compressed as `q98-trial-module.rs.gz`; Q100 is the only production setting. Bulk inputs, renders, OCR sidecars and collections remain local/ignored; representative complete PDFs and small comparison sheets are committed. The hashes allow regeneration, not a promise of a hosted bulk-artifact service.

Remaining raster is **35,763,822 B whole-page**, **5,541,808 B native exceptions**, and **1,589,328 B reduced paper**. The largest single residual is history-04's **8,318,245 B** native layer with 36 painted vectors; history-01 retains 4,047,178 B with 25 vectors. These partially reconstructed pages are deliberately excluded from unchanged-whole-page encoding. This is the largest demonstrated remaining bottleneck, rather than PDF syntax or fonts. It requires evidence appropriate to retained content and vector/raster boundaries; this round does not extend the codec to those regions.

Independent findings are in `qualification/tonal_raster/INDEPENDENT_REVIEW.md`. CodeRabbit reviewed the small PR and raised three missing subprocess-timeout findings in qualification scripts; explicit bounded timeouts now fail the audit rather than hanging or recording success. No runtime-code blocker was reported. PR1's separate targeted review is in `CLEARSCAN_PUBLICATION_REVIEW.md`; its oversized CodeRabbit skip is not approval. PR2/3 remain negative evidence. No PR is automatically merged or closed.
