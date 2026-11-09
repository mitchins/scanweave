# ScanWeave #37 — three-page polarity containment

## Disposition

**READY AS CONTAINMENT / SIZE HOLD**, subject to independent review and the outstanding Sonar and security-scan gates described below. This is a size disposition, not a claim that every requested gate passed. The owner’s final rule tests existing `seg.ink` and `seg.paper` with Rec.709 luminance, then selects the existing exact whole-page raster baseline only when that estimate is inverted and final visible occurrences exist. It does not alter segmentation, donors, ownership, region planning, q3, or glyph placement.

The frozen 32-page corpus has 10 inverted estimates and exactly three fallbacks: historical 2 (22 visible glyphs), historical 5 (36), and receipts 4 (7). All 65 paper-coloured visible vector occurrences are suppressed and their actual source ink is retained in the page raster. The remaining seven inverted pages retain their previous output, as do all 22 normal pages.

## D1 — census

Raster bytes are the sum of encoded image XObject streams referenced by the page; isolated page bytes are a separately written one-page PDF including shared resources. The isolated sizes are useful for comparing page cost but do not add up to whole-document size because fonts/resources can be shared. RGB estimates are from the independently instrumented unmodified main build. The page report records both luminances, inversion, pre-route visible count and route. Region/reconstruction records describe the pre-route plan; emitted ownership, patch, coverage and fidelity fields describe the output.

| Page | Paper RGB / L | Ink RGB / L | Inverted | Visible before → after | Raster fallback | Image bytes before → after | Isolated PDF bytes before → after |
|---|---|---|---|---|---|---|---|
| historical 1 | [56, 53, 52] / 53.57 | [233, 216, 197] / 218.24 | True | 0 → 0 | False | 451,336 → 451,336 | 467,783 → 467,783 |
| historical 2 | [1, 1, 1] / 1.00 | [236, 217, 172] / 217.79 | True | 22 → 0 | True | 306,274 → 4,053,348 | 320,722 → 4,067,878 |
| historical 3 | [41, 40, 43] / 40.43 | [205, 186, 165] / 188.52 | True | 0 → 0 | False | 252,220 → 252,220 | 267,858 → 267,858 |
| historical 4 | [39, 39, 40] / 39.07 | [200, 175, 148] / 178.37 | True | 0 → 0 | False | 629,404 → 629,404 | 641,584 → 641,584 |
| historical 5 | [34, 33, 34] / 33.28 | [196, 192, 173] / 191.48 | True | 36 → 0 | True | 558,993 → 8,327,288 | 581,250 → 8,349,626 |
| financial 1 | [214, 198, 155] / 198.30 | [49, 32, 16] / 34.46 | False | 281 → 281 | False | 168,983 → 168,983 | 970,716 → 970,716 |
| financial 2 | [215, 199, 156] / 199.30 | [50, 33, 17] / 35.46 | False | 197 → 197 | False | 118,923 → 118,923 | 918,844 → 918,844 |
| financial 3 | [212, 197, 153] / 197.01 | [46, 30, 15] / 32.32 | False | 244 → 244 | False | 154,805 → 154,805 | 956,556 → 956,556 |
| financial 4 | [214, 197, 157] / 197.73 | [60, 44, 24] / 45.96 | False | 345 → 345 | False | 159,351 → 159,351 | 962,905 → 962,905 |
| financial 5 | [212, 196, 153] / 196.30 | [54, 39, 21] / 40.89 | False | 182 → 182 | False | 141,195 → 141,195 | 941,647 → 941,647 |
| financial 6 | [213, 198, 156] / 198.16 | [50, 36, 24] / 38.11 | False | 207 → 207 | False | 160,726 → 160,726 | 962,143 → 962,143 |
| financial 7 | [215, 199, 159] / 199.51 | [57, 42, 26] / 44.03 | False | 235 → 235 | False | 144,818 → 144,818 | 946,115 → 946,115 |
| financial 8 | [215, 199, 158] / 199.44 | [56, 40, 20] / 41.96 | False | 437 → 437 | False | 189,804 → 189,804 | 995,136 → 995,136 |
| financial 9 | [212, 195, 151] / 195.44 | [68, 51, 27] / 52.88 | False | 329 → 329 | False | 151,487 → 151,487 | 954,088 → 954,088 |
| financial 10 | [212, 196, 154] / 196.37 | [56, 39, 22] / 41.39 | False | 280 → 280 | False | 131,041 → 131,041 | 932,876 → 932,876 |
| financial 11 | [215, 199, 157] / 199.37 | [55, 39, 20] / 41.03 | False | 420 → 420 | False | 167,809 → 167,809 | 972,635 → 972,635 |
| financial 12 | [213, 198, 155] / 198.08 | [60, 43, 21] / 45.03 | False | 215 → 215 | False | 115,613 → 115,613 | 916,054 → 916,054 |
| financial 13 | [214, 199, 159] / 199.30 | [51, 36, 22] / 38.18 | False | 345 → 345 | False | 170,890 → 170,890 | 975,130 → 975,130 |
| mixed 1 | [228, 218, 193] / 218.32 | [133, 127, 111] / 127.12 | False | 482 → 482 | False | 253,560 → 253,560 | 552,591 → 552,591 |
| mixed 2 | [255, 255, 255] / 255.00 | [0, 0, 0] / 0.00 | False | 784 → 784 | False | 256,604 → 256,604 | 672,829 → 672,829 |
| receipts 1 | [137, 107, 96] / 112.58 | [24, 19, 18] / 19.99 | False | 0 → 0 | False | 83,699 → 83,699 | 105,457 → 105,457 |
| receipts 2 | [121, 136, 133] / 132.59 | [58, 62, 56] / 60.72 | False | 12 → 12 | False | 66,397 → 66,397 | 90,532 → 90,532 |
| receipts 3 | [144, 141, 134] / 141.13 | [56, 57, 52] / 56.43 | False | 28 → 28 | False | 168,476 → 168,476 | 197,892 → 197,892 |
| receipts 4 | [166, 123, 88] / 129.61 | [203, 205, 204] / 204.50 | True | 7 → 0 | True | 122,528 → 1,230,205 | 145,409 → 1,253,169 |
| receipts 5 | [202, 184, 164] / 186.38 | [123, 106, 100] / 109.18 | False | 7 → 7 | False | 48,912 → 48,912 | 72,151 → 72,151 |
| receipts 6 | [152, 111, 57] / 115.82 | [224, 208, 193] / 210.32 | True | 0 → 0 | False | 485,445 → 485,445 | 509,125 → 509,125 |
| receipts 7 | [29, 30, 14] / 28.63 | [191, 191, 172] / 189.63 | True | 0 → 0 | False | 60,807 → 60,807 | 82,724 → 82,724 |
| receipts 8 | [14, 12, 13] / 12.50 | [210, 197, 190] / 199.26 | True | 0 → 0 | False | 58,362 → 58,362 | 80,585 → 80,585 |
| receipts 9 | [77, 63, 38] / 64.17 | [154, 149, 131] / 148.76 | True | 0 → 0 | False | 59,408 → 59,408 | 82,643 → 82,643 |
| receipts 10 | [191, 188, 183] / 188.28 | [94, 77, 71] / 80.18 | False | 28 → 28 | False | 71,595 → 71,595 | 94,390 → 94,390 |
| forms 1 | [255, 255, 255] / 255.00 | [0, 0, 0] / 0.00 | False | 297 → 297 | False | 386,679 → 386,679 | 464,231 → 464,231 |
| forms 2 | [255, 255, 255] / 255.00 | [19, 19, 19] / 19.00 | False | 207 → 207 | False | 351,145 → 351,145 | 429,265 → 429,265 |

[Machine-readable census and document hashes](owner-census.json). The original main reproduction is release `--locked`, main `9655fcc`, `--dpi 300 --profile clearscan --glyph-sharing off`. Earlier experiments established that inverted masks own paper regions/counters and that OCR-box occupancy cannot reliably identify the inverted pages; those experiments were rejected, not included in this implementation.

## D2 — source pixels and visual review

The three fallback image streams are losslessly decoded and compared sample-for-sample with the canonical source RGB:

| Page | Dimensions | Source and embedded SHA-256 | Differing samples | Encoded raster bytes |
|---|---|---|---:|---:|
| historical 2 | 1116×1835 | `499b941c10c957ccad6da6cd15c4abaa6f2dba808b6cde1a6b4288887c2ab449` | 0 | 4,053,348 |
| historical 5 | 1757×2440 | `05fd20bf4f986c2beff79d195ce4283c4c92eeca8d4aa775a7954b82dab5d43b` | 0 | 8,327,288 |
| receipts 4 | 1109×1479 | `a23cb7331c230e71c2e7645ac8dcda34f8fc399b4e7d7df1ec3e1de8ae886c6d` | 0 | 1,230,205 |

[Embedded-sample evidence](owner-embedded.json). Source-versus-output renders at 96 and 300 DPI are in [renderer measurements](owner-source-render-metrics.json). PDFium and MuPDF produced zero pixel differences on all three at both scales. Poppler produced zero for historical at 96 DPI, but source and output have one-pixel rounding differences in some 300-DPI raw renders; forcing matched dimensions gives the [Poppler matched results](owner-poppler-matched.json). At forced 300 DPI historical 2 and 5 match exactly; receipts 4 has 1,024,316 changed pixels with mean channel difference 2.363. At reading size Poppler also differs on historical 2 and receipts 4 under forced scaling. These are renderer sampling/geometry effects: decoded embedded samples are identical.

[All 65 indexed glyph panels](owner-glyph-panel-index.json), [named Chicken, Nos, quod and historical page 5 panels](owner-named-panel-index.json), and the actual [panel directory](/data/coding/scanweave/qualification/acr06/local/ink37/panels-final/) include source / main / candidate crops at reading size and 4× nearest-neighbour, with individual sheet SHA-256 hashes. Independent review by Claude is outstanding.

## D3 — unaffected pages

For all 29 unaffected pages, decoded page content and referenced image, font and ToUnicode streams are identical between main and candidate: [resource hashes](owner-resources.json). The three wholly unaffected documents (financial, mixed and forms) are byte-identical in full. Three-engine 300-DPI comparisons of historical and receipts show zero changed pixels on every unaffected page; the three other documents are identical PDFs. [Pixel diff masks and counts](owner-pixel-diffs.json) record the direct comparisons. Donor collection and shared font inputs are unchanged; no unaffected glyph needs a change panel.

The seven no-vector inverted pages were also compared with their source within OCR word boxes using dark source pixels as an ink proxy: [measurements](owner-no-vector-source.json). Main already differs from the source on these pages due to its existing image encoding; the proxy is not an ink ownership mask and does not prove every stroke is intact. The candidate is identical to main on those pages, so it introduces no new measured visual change. The pre-existing source differences should not be described as source-exact.

## D4 — semantics

PDFium and Poppler extract exactly the same text from every historical and receipts page as main; full PDF identity covers the other documents. PDFium word-search hit lists are identical for every distinct extracted word: [search evidence](owner-search-probe.json), [historical text](owner-historical-semantics-probe.json), [receipts text](owner-receipts-semantics-probe.json). Poppler extracted text is byte-identical. The direct [ActualText and ToUnicode comparison](owner-actualtext.json) matches exactly on all three routed pages. Main already fails to expose four receipt page 7 OCR words with zero-width character boxes to PDFium; this page is not routed, and the candidate introduces no additional loss.

qpdf checked 40 candidate/control PDFs with zero failures; OTS passed 26 distinct font programs: [checks](owner-pdf-checks.json).

## D5 — compression cost

| Document | Main bytes | Candidate bytes | Change | Main SHA-256 | Candidate SHA-256 |
|---|---:|---:|---:|---|---|
| historical | 2,246,646 | 13,762,217 | +11,515,571 | `8486f69c3d694c4a760ad4845c2cb6b64161467adc3e4061fef9b771b84abd2e` | `f8b77a52c0998b85770e8e75b548d47f3ed0e4759154990a3679d5e5ba3bdd9c` |
| financial | 2,842,414 | 2,842,414 | +0 | `96e3b89df58f3e33629300faebf2b3cde81065437b49f1695c24361b10f472bd` | `96e3b89df58f3e33629300faebf2b3cde81065437b49f1695c24361b10f472bd` |
| mixed | 920,248 | 920,248 | +0 | `a7efc67a2d331b756aade6a490328d2690343c43523c5284ae8db25937246f9a` | `a7efc67a2d331b756aade6a490328d2690343c43523c5284ae8db25937246f9a` |
| receipts | 1,266,836 | 2,374,622 | +1,107,786 | `d2da6b69bb803e6c3a5f5db0c6735f3d3357a2f84f12a98fc99fc3ef836d9360` | `52793f8f78582418eb781f5dbfa6186ca19cabcb350f3a72940b4f09a563f6c3` |
| forms | 831,974 | 831,974 | +0 | `75dfda81cef2a5857328ede7dd76279d72e65a838fb6d352b7f6ea6673d383ff` | `75dfda81cef2a5857328ede7dd76279d72e65a838fb6d352b7f6ea6673d383ff` |
| **Entire corpus** | **8,108,118** | **20,731,475** | **+12,623,357 (155.7%)** | — | — |

The three isolated-page increases are shown in D1. The cost is substantial and cannot be traded away by lossy fallback under this fix. A separate proposal is to study retaining source ink in tightly bounded exact patches with independently qualified mask geometry and text ownership; it requires separate evidence and must not weaken this fallback.

## D6 — controls

The frozen seed-370611 set, supplemental controls, positive reverse and dark-table variants, photo, binding shadow, coloured paper, normal visible vectors, shared-donor context and new black-border page were measured. An inverted no-vector control is not newly routed, including the true reverse controls: these preserve their **existing** output, which must not be assumed source-exact. The contextual dark-table page 3 has seven main vectors, is routed, and its rendered output matches the source. The contextual page 2 has 28 normal-polarity vectors and remains unchanged. The new black-border page has dark text but no main vectors, so the rule leaves it unchanged.

| Control | Page | Paper L | Ink L | Inverted | Visible before | Fallback | Source-render differing pixels when routed |
|---|---:|---:|---:|---|---:|---|---:|
| controls / binding_shadow.pdf | 1 | 237.55 | 94.28 | False | 14 | False | — |
| controls / black_border.pdf | 1 | 5.00 | 240.13 | True | 0 | False | — |
| controls / blue.pdf | 1 | 206.15 | 35.98 | False | 36 | False | — |
| controls / faded_brown.pdf | 1 | 230.96 | 98.43 | False | 78 | False | — |
| controls / photograph.pdf | 1 | 141.13 | 76.35 | False | 57 | False | — |
| controls / pink.pdf | 1 | 203.07 | 33.30 | False | 26 | False | — |
| controls / receipt_table.pdf | 1 | 56.51 | 235.06 | True | 0 | False | — |
| controls / reverse_page.pdf | 1 | 36.72 | 232.50 | True | 0 | False | — |
| controls / reverse_panel.pdf | 1 | 240.85 | 38.01 | False | 0 | False | — |
| controls / white.pdf | 1 | 255.00 | 20.00 | False | 27 | False | — |
| controls / yellow.pdf | 1 | 228.99 | 41.25 | False | 24 | False | — |
| controls-supplemental / midtone_table.pdf | 1 | 120.00 | 230.06 | True | 0 | False | — |
| controls-supplemental / reverse_with_margin.pdf | 1 | 255.00 | 34.23 | False | 0 | False | — |
| controls-supplemental / small_receipt.pdf | 1 | 35.00 | 230.06 | True | 0 | False | — |
| positive-controls / dark_table-108.pdf | 1 | 33.19 | 241.06 | True | 0 | False | — |
| positive-controls / dark_table-160.pdf | 1 | 33.19 | 241.06 | True | 0 | False | — |
| positive-controls / dark_table-44.pdf | 1 | 33.19 | 241.06 | True | 0 | False | — |
| positive-controls / dark_table-72.pdf | 1 | 33.19 | 241.06 | True | 0 | False | — |
| positive-controls / reverse_page-108.pdf | 1 | 30.72 | 236.98 | True | 0 | False | — |
| positive-controls / reverse_page-160.pdf | 1 | 30.72 | 236.98 | True | 0 | False | — |
| positive-controls / reverse_page-44.pdf | 1 | 30.72 | 235.92 | True | 0 | False | — |
| positive-controls / reverse_page-72.pdf | 1 | 30.72 | 236.77 | True | 0 | False | — |
| positive-controls / reverse_panel-108.pdf | 1 | 241.06 | 30.72 | False | 0 | False | — |
| positive-controls / reverse_panel-160.pdf | 1 | 241.06 | 30.72 | False | 0 | False | — |
| positive-controls / reverse_panel-44.pdf | 1 | 241.06 | 30.72 | False | 0 | False | — |
| positive-controls / reverse_panel-72.pdf | 1 | 241.06 | 30.72 | False | 25 | False | — |
| table-candidates / DejaVuSans-20.pdf | 1 | 41.11 | 220.96 | True | 0 | False | — |
| table-candidates / DejaVuSans-28.pdf | 1 | 41.11 | 220.96 | True | 0 | False | — |
| table-candidates / DejaVuSans-36.pdf | 1 | 41.11 | 220.96 | True | 0 | False | — |
| table-candidates / DejaVuSans-44.pdf | 1 | 41.11 | 220.96 | True | 0 | False | — |
| table-candidates / DejaVuSerif-20.pdf | 1 | 41.11 | 220.96 | True | 0 | False | — |
| table-candidates / DejaVuSerif-28.pdf | 1 | 41.11 | 220.96 | True | 0 | False | — |
| table-candidates / DejaVuSerif-36.pdf | 1 | 41.11 | 220.96 | True | 0 | False | — |
| table-candidates / DejaVuSerif-44.pdf | 1 | 41.11 | 220.96 | True | 0 | False | — |
| table-context / table-context-control.pdf | 1 | 132.59 | 60.72 | False | 12 | False | — |
| table-context / table-context-control.pdf | 2 | 141.13 | 56.43 | False | 28 | False | — |
| table-context / table-context-control.pdf | 3 | 129.61 | 204.50 | True | 7 | True | 0 |
| table-context / table-context-control.pdf | 4 | 186.38 | 109.18 | False | 7 | False | — |
| table-context / table-context-control.pdf | 5 | 115.82 | 210.32 | True | 0 | False | — |
| new-border / black-border-new.pdf | 1 | 0.00 | 255.00 | True | 0 | False | — |

[Control measurements](owner-controls.json); [frozen seed and licences](../controls-truth.json); [new border generator and hashes](black-border-new-truth.json). Contextual dark-table cases are derived from the corpus and are not independent real-world documents. Mixed-polarity reverse panels with a normal page estimate remain outside this containment.

## E — checks, reviews and open items

- Release build: passed. Rust `cargo test --workspace --locked` and requested clippy: passed after the final functional edits. Python CI gates: all passed. The temporary `.venv` link and test-generated tracked evidence were removed/restored.
- CodeRabbit found inaccurate emitted ownership/fidelity reporting in an earlier patch; those fields were corrected while preserving reconstruction-plan records. The clean-patch rerun reviewed all six changed product files and found no new findings; the prior finding is addressed.
- Sonar: not run; `sonar-scanner`, `cargo-llvm-cov`, and `SONAR_TOKEN` are unavailable locally. The configured hosted Sonar workflow runs on pull requests; this task explicitly reserves opening the PR for Claude.
- Security: [cargo-audit](owner-cargo-audit.json) found two existing `quick-xml 0.36.2` vulnerabilities, RUSTSEC-2026-0194 and RUSTSEC-2026-0195 (denial-of-service advisories), plus five unmaintained and two unsound warnings. This patch does not change dependencies; the security gate is not clean. A Codex Security diff scan was started but its draft failed because the scan output ancestry includes group-writable `/home/mitch/.codex`; that scan remains incomplete. No completed security scan is claimed.
- Claude’s independent code, panels, font mapping and size review is outstanding. No PR has been opened.
- The pre-existing OCR page 7 extraction and no-vector raster differences are not repaired here. Poppler has documented resampling/rounding differences. Sharing-on and automatic document selection are not fully corpus-qualified.

Product commit `786abe5` was pushed to `fix/ink-paper-polarity-37`; no PR was opened. The dependency advisories and outstanding Sonar and Codex Security scan mean this is not a merge-ready security disposition.
