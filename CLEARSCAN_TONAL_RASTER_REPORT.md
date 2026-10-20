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

## Corpus and publication status

The frozen 32-page corpus rerun and a matched reviewed-product baseline are in progress. The historical 59,599,260 B collection predates the donor closure and differs on some partially reconstructed pages; those inherited differences must not be attributed to JPEG. Complete before/after byte accounting, native searches, renderer checks, timing/memory and synthetic regressions will be appended before this PR is marked ready.

PR1 final review and operator decisions are in `CLEARSCAN_PUBLICATION_REVIEW.md`. PR2/3 remain published negative evidence; no rejected code is integrated and no PR is merged automatically.
