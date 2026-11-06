# Issue 29 qualification and review evidence

**Outcome: not qualified for shipping.** The two measured approaches remove the confirmed visual corruptions and retain the positive control, but introduce a historical PDFium duplicate and fail strict surrounding-pixel locality. The local-tracing candidate remains uncommitted in the product worktree; no branch was pushed. The direct-raster alternative and its measured costs are documented below. These experiments do not prove that every other narrow rule is impossible.

## Instrumented diagnosis

Page indexes are zero-based. Instrumented release outputs are byte-identical to main. `instrument.py` generates temporary instrumentation; `trace_instrumented.py` joins it to bounds from the embedded TrueType outline, CID-to-GID mapping and PDF text matrix. Bbox-center displacements are geometric centers, not ink centroids. Bbox intersections are not proof of owned-ink overlap. Full instrumentation and donor cohort records are in `instrumented-traces.json`.

| Document / page / symbol | OCR box | Observed ink | Retained donor / size | Median L,T,R,B pads | Replacement | Emitted outline bbox | Normalized similarity | Page-scale mask IoU | Neighbor ink pixels | Interpretation |
|---|---|---|---|---|---|---|---|---|---|---|
| single / 0 / w000053s0000 (t) | [762.0, 823.0, 797.0, 853.0] | [763.0, 824.0, 777.0, 853.0] | w000053s0000 / [14, 29] | [1.0, 1.0, 1.0, 1.0] | [763.0, 824.0, 796.0, 852.0] | [763.5, 824.0, 795.9, 851.9] | 0.820 | 0.106 | 81 | OCR box spans next o |
| single / 0 / w000053s0001 (o) | [785.0, 822.0, 802.0, 853.0] | [780.0, 833.0, 797.0, 853.0] | w000105s0001 / [17, 20] | [1.0, 1.0, 1.0, 0.0] | [786.0, 823.0, 801.0, 853.0] | [786.1, 823.1, 801.3, 852.8] | 0.845 | 0.042 | 6 | OCR box over-tall and shifted into adjacent ink |
| single / 0 / w000102s0000 (t) | [868.0, 1108.0, 901.0, 1137.0] | [868.0, 1109.0, 882.0, 1137.0] | w000198s0002 / [12, 28] | [1.0, 1.0, 1.0, 1.0] | [869.0, 1109.0, 900.0, 1136.0] | [870.6, 1108.9, 900.3, 1136.2] | 0.845 | 0.151 | 49 | OCR box spans next o |
| single / 0 / w000102s0001 (o) | [890.0, 1108.0, 901.0, 1137.0] | [884.0, 1117.0, 901.0, 1137.0] | w000097s0001 / [17, 20] | [1.0, 0.0, 1.0, 0.0] | [891.0, 1108.0, 900.0, 1137.0] | [891.0, 1108.2, 900.0, 1136.6] | 0.884 | 0.203 | 0 | OCR box over-tall and shifted |
| single / 0 / w000130s0001 (r) | [1242.0, 1280.0, 1259.0, 1319.0] | [1244.0, 1288.0, 1259.0, 1307.0] | w000141s0004 / [16, 20] | [1.0, 1.0, 0.0, 1.0] | [1243.0, 1281.0, 1259.0, 1318.0] | [1243.2, 1281.3, 1258.8, 1318.7] | 0.797 | 0.339 | 0 | OCR box over-tall |
| single / 0 / w000175s0001 (o) | [448.0, 1513.0, 472.0, 1555.0] | [450.0, 1525.0, 467.0, 1543.0] | w000175s0001 / [17, 18] | [1.0, 1.0, 1.0, 1.0] | [449.0, 1514.0, 471.0, 1554.0] | [449.1, 1514.2, 470.9, 1553.6] | 0.816 | 0.132 | 12 | OCR box over-tall |
| single / 0 / w000180s0001 (r) | [998.0, 1520.0, 1018.0, 1551.0] | [1002.0, 1521.0, 1017.0, 1541.0] | w000141s0004 / [16, 20] | [1.0, 1.0, 0.0, 1.0] | [999.0, 1521.0, 1018.0, 1550.0] | [999.2, 1521.2, 1017.8, 1550.6] | 0.941 | 0.392 | 0 | OCR box extends below observed r |
| financial / 8 / w000005s0011 (s) | [553.0, 456.0, 567.0, 495.0] | [549.0, 469.0, 567.0, 495.0] | __doc_donor:p000013:w000024s0002 / [18, 26] | [0.0, 0.0, 0.0, 0.0] | [553.0, 456.0, 567.0, 495.0] | [553.1, 456.3, 566.9, 494.7] | 0.854 | 0.200 | 0 | OCR box over-tall and shifted |
| forms / 1 / w000471s0000 (T) | [235.0, 2760.0, 248.0, 2807.0] | [233.0, 2775.0, 246.0, 2793.0] | w000034s0008 / [13, 18] | [0.0, 0.0, 0.0, 0.0] | [235.0, 2760.0, 248.0, 2807.0] | [235.0, 2759.8, 248.0, 2807.1] | 1.000 | 0.079 | 0 | OCR box over-tall |
| forms / 1 / w000471s0001 (O) | [247.0, 2760.0, 264.0, 2807.0] | [248.0, 2776.0, 265.0, 2795.0] | w000380s0003 / [17, 19] | [0.0, 0.0, 0.0, 0.0] | [247.0, 2760.0, 264.0, 2807.0] | [247.0, 2759.3, 264.2, 2806.8] | 1.000 | 0.136 | 0 | OCR box over-tall |
| historical / 1 / w000070s0000 (d) | [100.0, 1077.0, 129.0, 1123.0] | [109.0, 1092.0, 120.0, 1108.0] | __doc_donor:p000005:w000161s0000 / [12, 16] | [5.0, 14.0, 6.0, 15.0] | [105.0, 1091.0, 123.0, 1108.0] | [105.0, 1091.4, 123.2, 1108.0] | 0.810 | 0.541 | 1 | OCR box much larger than target |
| historical / 1 / w000106s0006 (o) | [211.0, 1469.0, 263.0, 1494.0] | [244.0, 1472.0, 259.0, 1492.0] | __doc_donor:p000005:w000058s0005 / [13, 14] | [4.0, 3.0, 5.0, 3.0] | [215.0, 1472.0, 258.0, 1491.0] | [215.0, 1472.2, 260.8, 1491.0] | 0.877 | 0.195 | 265 | OCR box spans preceding glyphs |

The next table uses hOCR line estimates. The x-height estimate is `x_size - x_ascenders - x_descenders`; it is not a typographic ground-truth metric. Positive Y is downward. Centroid displacement is from retained donor-mask sampling, while the baseline displacement uses the emitted outline bounding edge.

| Document / symbol | Line baseline Y | Estimated x-height | Emitted bottom minus baseline | Emitted top minus x-height line | Donor ink centroid displacement (x,y) |
|---|---|---|---|---|---|
| single / w000053s0000 | 853.09 | 21.00 | -1.18 | -8.04 | [9.8, -0.0] |
| single / w000053s0001 | 853.10 | 21.00 | -0.29 | -9.01 | [5.0, -4.2] |
| single / w000102s0000 | 1137.19 | 21.00 | -0.99 | -7.28 | [8.1, -0.2] |
| single / w000102s0001 | 1137.21 | 21.00 | -0.60 | -7.97 | [2.7, -4.9] |
| single / w000130s0001 | 1309.00 | 21.00 | 9.74 | -6.73 | [0.2, 1.3] |
| single / w000175s0001 | 1541.76 | 21.00 | 11.82 | -6.53 | [1.5, 0.1] |
| single / w000180s0001 | 1540.11 | 21.00 | 10.47 | 2.11 | [-1.0, 3.6] |
| financial / w000005s0011 | 494.62 | 26.00 | 0.10 | -12.34 | [1.8, -6.3] |
| forms / w000471s0000 | 2794.37 | 19.50 | 12.73 | -15.09 | [2.0, -4.9] |
| forms / w000471s0001 | 2794.26 | 19.50 | 12.51 | -15.43 | [-1.1, -1.9] |
| historical / w000070s0000 | 1113.39 | 26.00 | -5.39 | 4.05 | [-1.1, 0.2] |
| historical / w000106s0006 | unavailable | unavailable | unavailable | unavailable | [-15.3, -0.2] |

For single `w000053s0001`, OCR is 17×31 px, observed ink 17×20 px, and the cohort median pads are [1, 1, 1, 0]. Thus inference produces a 15×30 px box: it inherits the tall OCR extent. The financial lowercase `s` donor cohort is labeled `s`, and its witness is 18×26 px; the 14×39 px target OCR box is the cause of the capital-like physical scale. Negative donor pads are dropped by the implementation; the full JSON records discarded counts. The forms examples have discarded negative horizontal pads, while their 47 px OCR heights remain unchanged because their median vertical pads are zero. The recorded cohort labels alone do not prove visual case identity for every donor. Some selected witness IDs differ from the final prototype witness due to subsequent prototype-key reuse; `physical-measures.json` distinguishes the selected and retained witnesses. The candidate gate uses the finally retained donor. Physical mask IoU is computed at page scale with nearest-neighbor mask sampling; it is not a measurement of antialiased PDF pixels.


## Rule and judgment calls

The ClearScan pre-emission gate compares the retained donor mask in the inferred page box to the original owned source mask. It rejects non-finite or unsupported geometry; requires each box edge to stay within max(2 px, 15% of the corresponding source extent) for healthy reuse or max(2 px, 25%) for density-marked repair; requires page-scale nearest-neighbor binary-mask IoU of at least 0.70 or 0.65 respectively; and rejects donor-mask ink sampled on separately owned text or artwork ink. These are conservative engineering choices rather than statistically calibrated bounds. The healthy IoU floor was adjusted from 0.75 to 0.70 after the existing intact glyph-sharing fixture measured 0.742 and failed; the fresh sets were not used for that calibration. All pre-existing gates and thresholds remain.

On rejection the decision is `rejected_donor_geometry`. The candidate traces the original source mask locally and uses it only if the existing `min_ink_iou` fidelity gate passes; otherwise it takes the existing raster fallback. Local tracing was added after the first candidate caused page-wide patch-layout changes. It keeps the unchanged planning/tracing sequence for other glyphs. Source-mask/outline sampling does not establish that every antialiased outline pixel is protected: see the ownership findings below.

The retained witness can differ from the originally selected witness when a prototype key is reused later in planning. The compatibility gate measures the retained witness. Selected and retained mask metrics are both saved; no separate wrong-case cohort has been proved for the financial example.

## Corpus and counts

All five main group PDFs were byte-identical to the frozen R2a baseline; `baseline-identity.json` records hashes and commands. The 32-page group census below counts decision labels, which do not by themselves prove a repair is genuine. The damaged-crossbar m1d positive control passed unchanged and still repairs.

| Group | Diagnostic suspects rejected / total | Main repair decisions | Candidate repair decisions |
|---|---:|---:|---:|
| financial | 65 / 65 | 858 | 826 |
| forms | 62 / 62 | 143 | 111 |
| historical | 25 / 25 | 53 | 2 |
| mixed | 88 / 88 | 543 | 431 |
| receipts | 0 / 0 | 2 | 2 |

All 240/240 diagnostic suspects were rejected. All 12 specifically traced bad glyph substitutions across the nine word-context examples were rejected, and the source/main/candidate preview is `local/donorfix/confirmed-defects-preview.png`. The reviewer must still judge all changed substitutions; the 240 diagnostic suspects are not all confirmed defects.
Across the 54 runs, including repeated content in the multi-page and single-page fresh sets, main reported 2691 repair decisions and candidate reported 2347. Historical loses 51 reported repairs; 50 had main source-mask IoU below 0.5 (median 0.071). This supports concern about those substitutions but is not pristine-truth proof that none was genuine.

The set includes the five groups, single-page input, competitive 300/600 sets, all 27 P2/P2′/P2″ sheets and all nine FONT-01 sheets at their prescribed DPIs, plus both fresh sets and their individual pages. Runtimes are wall-clock and were collected with overlapping parallel jobs, so their differences are indicative rather than controlled benchmarks. Embedded font bytes below are unique compressed font-stream lengths within each PDF; decoded sizes and per-page reported font bytes are in `metrics.json`.

| Input | Main PDF B | Candidate PDF B | Main font B | Candidate font B | Main s | Candidate s | Changed rows | Byte identical |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| competitive300 | 198602 | 201260 | 18343 | 20018 | 37.9 | 42.5 | 15 | no |
| competitive600 | 415886 | 415887 | 8100 | 8101 | 38.0 | 76.7 | 190 | no |
| financial | 2849237 | 2861814 | 727259 | 737535 | 479.7 | 531.7 | 138 | no |
| font01-test-0 | 294280 | 294196 | 61746 | 61076 | 12.3 | 11.1 | 9 | no |
| font01-test-1 | 196306 | 196306 | 96085 | 96085 | 31.0 | 23.8 | 1 | yes |
| font01-test-2 | 825528 | 824472 | 96379 | 96374 | 77.6 | 75.0 | 2 | no |
| font01-train-0 | 328837 | 328810 | 77422 | 77399 | 13.1 | 13.1 | 1 | no |
| font01-train-1 | 451502 | 451796 | 99861 | 99925 | 31.2 | 26.3 | 8 | no |
| font01-train-2 | 898250 | 900968 | 101221 | 101980 | 88.3 | 85.8 | 5 | no |
| font01-validation-0 | 273701 | 273701 | 66504 | 66504 | 9.9 | 9.7 | 0 | yes |
| font01-validation-1 | 180461 | 180461 | 91281 | 91281 | 22.1 | 22.3 | 2 | yes |
| font01-validation-2 | 750491 | 750491 | 88745 | 88745 | 81.1 | 69.7 | 2 | yes |
| forms | 843699 | 847175 | 41147 | 43745 | 43.6 | 53.7 | 307 | no |
| fresh-200 | 143156 | 143597 | 37970 | 38281 | 8.2 | 8.8 | 12 | no |
| fresh-300 | 133721 | 134739 | 34403 | 35306 | 13.7 | 15.5 | 19 | no |
| fresh-600 | 125728 | 126675 | 43638 | 44488 | 41.8 | 42.4 | 9 | no |
| fresh-fractional | 139197 | 139819 | 32779 | 33274 | 13.7 | 15.1 | 7 | no |
| fresh | 473947 | 477136 | 83357 | 86122 | 58.8 | 67.1 | 43 | no |
| fresh2-200 | 142026 | 141966 | 37038 | 36988 | 8.3 | 9.0 | 9 | no |
| fresh2-300 | 133285 | 134295 | 33532 | 34507 | 13.6 | 14.7 | 21 | no |
| fresh2-600 | 124656 | 125772 | 44083 | 45194 | 41.7 | 42.8 | 13 | no |
| fresh2-fractional | 139091 | 139414 | 33237 | 33544 | 14.1 | 15.3 | 6 | no |
| fresh2 | 473822 | 476448 | 82993 | 85294 | 60.1 | 62.9 | 41 | no |
| historical | 2266058 | 2265825 | 3472 | 3425 | 68.5 | 77.6 | 60 | no |
| mixed | 917603 | 932259 | 249013 | 259950 | 105.8 | 134.2 | 346 | no |
| p2-0 | 351126 | 351126 | 79436 | 79436 | 12.4 | 14.7 | 0 | yes |
| p2-1 | 423847 | 420966 | 97113 | 96531 | 16.3 | 17.4 | 6 | no |
| p2-2 | 395569 | 395590 | 82800 | 82824 | 14.8 | 15.0 | 4 | no |
| p2-3 | 235970 | 235970 | 99037 | 99037 | 31.1 | 31.0 | 0 | yes |
| p2-4 | 219351 | 219610 | 96964 | 97227 | 24.4 | 24.1 | 4 | no |
| p2-5 | 539438 | 542158 | 124259 | 124728 | 31.1 | 31.6 | 5 | no |
| p2-6 | 1060220 | 1060220 | 110008 | 110008 | 97.4 | 100.6 | 1 | yes |
| p2-7 | 1091322 | 1096373 | 128334 | 128640 | 104.6 | 110.3 | 4 | no |
| p2-8 | 1007964 | 1008520 | 118641 | 118875 | 90.7 | 97.3 | 4 | no |
| p2pp-0 | 364598 | 364598 | 90471 | 90471 | 14.6 | 14.2 | 0 | yes |
| p2pp-1 | 337666 | 337657 | 78158 | 78145 | 17.9 | 13.2 | 3 | no |
| p2pp-2 | 335312 | 335327 | 69766 | 69772 | 11.8 | 11.6 | 1 | no |
| p2pp-3 | 227702 | 227941 | 104922 | 105136 | 31.5 | 30.9 | 3 | no |
| p2pp-4 | 429926 | 430975 | 105470 | 106250 | 28.8 | 25.5 | 6 | no |
| p2pp-5 | 477347 | 477795 | 110300 | 110310 | 31.0 | 26.8 | 2 | no |
| p2pp-6 | 926741 | 927891 | 117322 | 117615 | 98.4 | 86.7 | 11 | no |
| p2pp-7 | 988893 | 989247 | 125027 | 125250 | 104.1 | 92.5 | 5 | no |
| p2pp-8 | 937899 | 937899 | 131451 | 131451 | 101.1 | 95.3 | 2 | yes |
| p2prime-0 | 369241 | 369583 | 76646 | 76807 | 14.7 | 16.3 | 1 | no |
| p2prime-1 | 407463 | 407817 | 78991 | 79276 | 16.0 | 17.1 | 1 | no |
| p2prime-2 | 421335 | 421756 | 107234 | 107433 | 17.7 | 18.1 | 2 | no |
| p2prime-3 | 539878 | 541128 | 114823 | 115827 | 30.7 | 31.2 | 5 | no |
| p2prime-4 | 487097 | 487907 | 115928 | 116359 | 31.0 | 32.4 | 6 | no |
| p2prime-5 | 545200 | 545295 | 112450 | 112507 | 33.4 | 32.6 | 2 | no |
| p2prime-6 | 1102835 | 1102835 | 134327 | 134327 | 101.4 | 102.2 | 2 | yes |
| p2prime-7 | 1270843 | 1271773 | 140221 | 140162 | 116.2 | 117.5 | 5 | no |
| p2prime-8 | 1132113 | 1132814 | 135408 | 135960 | 117.8 | 110.9 | 10 | no |
| receipts | 1271232 | 1271232 | 16712 | 16712 | 29.8 | 32.7 | 0 | yes |
| single | 387157 | 394081 | 113198 | 119289 | 33.1 | 33.1 | 82 | no |

Inputs with no changed substitution: font01-validation-0, p2-0, p2-3, p2pp-0, receipts. Outputs changed without any reported substitution decision, proposal, or prototype change: none. An unchanged report alone cannot prove pixel identity for individual glyphs on a changed page.

## Fresh truth

The generator and first seed 290611 were frozen before candidate evaluation. Because local-tracing fallback was revised after the first set was examined, a second generator and seed 290612 were frozen before running the revised candidate on that set. The text and fonts are the same; the seeded stroke-removal positions differ, so the second set is not an independent typography design. The set uses the Bitstream Vera license for DejaVu fonts (DejaVu modifications public domain); `/usr/share/doc/fonts-dejavu-core/copyright` contains the license. Font and generator hashes are in `fresh-sha256.txt` and `fresh2-sha256.txt`. RAQM shaping was available for fi/fl/ff/ffi. True small-caps fonts were unavailable; uppercase text is present. The 435-point fractional page contains 1813 source pixels. The 600-DPI pages, 200-DPI pages, mixed serif/sans/italic/bold text, narrow glyphs and punctuation, manually tightened spacing, faint ink and removed strokes are represented; the set is small and does not prove coverage of every real-world ligature or damage pattern.

PDFium page-wide ink IoU against the pristine PNGs at the original image dimensions follows. A 0.0001-pixel canvas adjustment avoids PDFium floating-point ceil; there is no glyph-wise registration. Threshold is luma <128.

| Set / DPI or scale | Main IoU | Candidate IoU | Candidate minus main false-positive pixels | Candidate minus main false-negative pixels |
|---|---:|---:|---:|---:|
| fresh / 200 | 0.918764 | 0.919864 | 25 | -110 |
| fresh / 300 | 0.916424 | 0.929754 | -490 | -1821 |
| fresh / 600 | 0.914106 | 0.913918 | 153 | -11 |
| fresh / fractional | 0.925339 | 0.926617 | -6 | -217 |
| fresh2 / 200 | 0.921935 | 0.922228 | 40 | -60 |
| fresh2 / 300 | 0.916882 | 0.930174 | -492 | -1811 |
| fresh2 / 600 | 0.913494 | 0.915231 | -171 | -1035 |
| fresh2 / fractional | 0.924851 | 0.926328 | -63 | -199 |

The first seed at 600 DPI has slightly lower aggregate IoU in the candidate and 153 more false-positive pixels. This is a possible regression for independent review, not proof of a visibly incorrect glyph. All second-seed aggregate IoUs improved.

## Functional checks and limitations

Genuine qpdf 11.9.0 `--check` was run on 49 changed PDFs; failures: none. OTS 9.3.0 was run on their embedded fonts; failures: 0. Full results are in `functional.json`.

**The strict surrounding-pixel check is not clean.** With a four-source-pixel margin, 69393 differing renderer pixels remain in aggregate. With a 16-render-pixel margin at 150 DPI, 41104 remain, including 6955 with channel delta greater than 8. Counts sum both renderers and are not independent physical pixels. Largest cases `(count, >8, document, zero-based page, renderer)` are: [(14832, 2614, 'p2-5', 0, 'pdfium'), (8251, 1661, 'p2-5', 0, 'poppler'), (5959, 1310, 'p2pp-5', 0, 'pdfium'), (5680, 1101, 'p2pp-5', 0, 'poppler'), (1604, 46, 'p2-7', 0, 'poppler'), (1373, 1, 'p2-7', 0, 'pdfium'), (1089, 13, 'p2pp-6', 0, 'poppler'), (1032, 5, 'p2pp-6', 0, 'pdfium'), (353, 155, 'mixed', 1, 'pdfium'), (237, 0, 'font01-train-2', 0, 'poppler')]. Both margin definitions and every page result are in `functional.json`.

For P2-prime sheet 2, the first candidate had 85,928 different PDFium pixels at 150 DPI; local source tracing reduced that to 397 on the targeted comparison, with none beyond 16 render pixels. On P2 sheet 5, the revised candidate still changes raster patch coalescing despite unchanged vector coverage; 14,832 PDFium and 8,251 Poppler pixels differ beyond 16 render pixels. These are measured output differences, not proof of new semantic errors. They fail the requested strict unchanged-surroundings criterion and require review. No codec or sharing code was changed.

PDFium or Poppler extracted-text bytes differ on 16 document-page-renderer comparisons; affected-word search differences: 0. Exact diffs, native PDFium search results, Poppler extracted-text searches, and hashes are in `metrics.json`; complete extracted text files are under `local/donorfix/text/`. Search differences: []. Text equality is not asserted when hashes differ. On historical page index 1, PDFium adds a second ‘Quoquo and moves the word it; a one-pixel w000105s0001 target is not accepted by the local tracing-and-fidelity path and falls back to an invisible owner. This is a new extraction regression.

The independent pixel-center ownership audit matched 24601 visible PDF glyphs against captured source-owned masks, with 0 unmatched glyphs, 0 missing page snapshots, and 0 provenance mismatches. It found 4 glyph/neighbor overlaps: [('fresh', 2, 'w000001s0003', 'w000001s0002', 4), ('fresh', 2, 'w000007s0002', 'w000007s0001', 3), ('fresh2', 2, 'w000001s0003', 'w000001s0002', 4), ('fresh2', 2, 'w000007s0002', 'w000007s0001', 3)]. `ownership-audit.json` contains all cases and mask-capture provenance. This is a flattened-outline pixel-center test, not a proof about fractional antialias coverage. The two `ffi`-area cases of 4 and 3 pixels in each combined fresh document also occur in unchanged main. Across the same documents, the audit found 48 overlap pairs in main versus 4 in the candidate, with no new or increased pairs and 44 removed; `ownership-comparison.json` records this comparison. Therefore the requested absolute no-overlap assertion is not met even though those cases predate this candidate.

Workspace tests (`cargo test --workspace --locked`), the specified denied-warning clippy command, the unchanged m1d positive control, and all 20 Python CI gates passed. Logs and exit codes are under `local/donorfix/checks/`; qpdf 11.9 was extracted into temporary storage and OTS 9.3.0 built at the CI-pinned revision. The first candidate’s initial workspace run failed the exact sharing fixture, and its 0.75 healthy-mask floor was calibrated against that fixture before the fresh runs. The initial `uv tool install qpdf` provided an unrelated program; it was not used as the qpdf validator.

## Measured containment option

The first candidate sent rejected targets directly through region-level raster fallback. It rejected all 240 diagnostic suspects and retained the m1d control; its main-to-candidate group repair counts were financial 858 to 826, forms 143 to 111, historical 53 to 2, mixed 543 to 431, receipts 2 to 2. Its full metrics, functional checks, and panels are preserved in metrics-v1.json, functional-v1.json, panel-index-v1.json, panel-sha256-v1.txt and local/donorfix/panels-v1/. This containment also introduced the historical PDFium duplicate and broad patch differences, including 85,928 different PDFium pixels on P2-prime sheet 2. It is measured, but is not a qualified safe production recommendation. Local tracing reduced that change but still fails strict pixel locality and historical extraction. A third isolated experiment padded the one-pixel crop before invoking the existing tracer; it still fell back and produced the same duplicate (padded-experiment.json). These failed approaches do not prove that every conceivable narrow rule is impossible.

## Review panels

There are 1443 indexed rows, including decision, prototype, or visibility changes. Every row includes source/main/candidate word context at 150 DPI equivalent and 4× nearest-neighbor enlargement. `panel-index.json` gives coordinates, decisions, owners, metrics and matched PDF outline bounds; a missing outline bound means no visible glyph or an ambiguous match, not a zero-sized glyph. Claude has not yet reviewed the entire set. Contact-sheet hashes follow; the index hash is included as well.

- `c5b62821583215d1385b0168c75123636750c757ae03fb4872c0ef16beac5105`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0001.png`
- `be75891dd3b343ae4f6d805693689b2e5a6e8be670e1720548a5a16170bcb0b7`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0002.png`
- `0cddc228358bdd345a9056641fb7b8f2b73aae1aa818d9c249b284d60859ca33`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0003.png`
- `a277ae889ed7811241fbe4e6b41b11f3b29be05f0dc3543c3ded8f83420add33`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0004.png`
- `55cf0683d7625f9afff17e6d113bf0df16bb86ba5253c49492a45b0d9681a006`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0005.png`
- `93e728ccb418dd2d47391381bd418ef9068351ccba9480a0b09695e421b77e1d`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0006.png`
- `498ae5c5066e775954987e9167bb1bd9d6653da19cd570cfdf993d7e6440015b`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0007.png`
- `60ad7731277f979d265240262981af79911d64448651f990b5edbcf4677fdc56`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0008.png`
- `4884ec25e6e10e0d5c78f109bedf180c26feca33dad13c6cbda497067c70d4c8`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0009.png`
- `993e67cf10e1f8375e58b7dda7e2ef4c26e680aecff1127bfa4f7f0bded1fcea`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0010.png`
- `970d97f0397f988832df1da75b296a1d33a95fabec7f4e061609d9fc392e9d7d`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0011.png`
- `e4b61612b3546c83adf9431f70cf98e0407b3df939e217578a19b83c2537c736`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0012.png`
- `23e0f48c910793075d421b2f92365122feb3c6f07444af89219d7a70a3820acd`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0013.png`
- `b9c0599472a4aeafff7f367c15c55ce3aa1c46fb9f78f33dc5a690ce757a587d`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0014.png`
- `6b9f807fb39e7f68fe7cf9d3712257b52655371931dd36148d2bde414ae9655f`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0015.png`
- `2288cfd96c6f6969442c1d75f241eb5ef6a5b9d16649da790dd0ac2f18c631e3`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0016.png`
- `19e5c7ed30a4737490c15118aa703b096a1b9f3aee202db7838a8b97a73d1783`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0017.png`
- `772d7145e849b6d1ede319416fb890239b08e7b305f279a975100e6c83a6c65f`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0018.png`
- `2ad88363bb23fa7506718f463c3a44b477da4572c86b252fa99b16a4c1d11443`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0019.png`
- `17b58778cc903b4d98e3f76ea130529c777058925ed0a1e1ab00cfd9db8293e4`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0020.png`
- `50f34ebbdb8baeafc916ba0666a539ad18df9523ec05ef5c8f23a6dfc05ecf58`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0021.png`
- `839d06d14cbcc27a916e416ff0014b44ed9632dce0a91faeb35bcd17697caab8`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0022.png`
- `50d2b55b0eb7627dae58d8bfe04416c10513438afd23b05970352d768f7bd03d`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0023.png`
- `4f2fd20802631e349477a54e2d36c1fa3953ab41decb9aa83d1d7e150884edfb`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0024.png`
- `80220f9dd819d9a5a8949a4a6f5ae794e6a05bcb3a4f7a13fe80d36083dc6b7d`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0025.png`
- `faa9db1932e7f7e257aa3c2bbc25c8c01148c0e8b906b3e293612795f8c2961b`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0026.png`
- `6a08ecd62dce898a41ab1050fe88c92a38493afd34d52f9564192e5f4a1790a6`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0027.png`
- `0ab67768b2d106bb8d2e1507232b1a5c8f1e295e91393d92026d889fd4053d65`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0028.png`
- `5d8a59091094625da78286b806509596f10bbd99970c2017e413e8a518e5777a`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0029.png`
- `4a1e2cc8eb35ba9b3168e29be6825b533a629dd13b187312b3cc3cebfbb60086`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0030.png`
- `590f31b3060dfade5d9506561cd95c6793d7e4727000594081866612e960add6`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0031.png`
- `f59393453ba46b7d346674d540d8c02368a2c1dd02c2337e4412ad514dbddc9e`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0032.png`
- `42265294ff96734eba3b81df7448e5f904f540678f13311d77c66879dce495dc`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0033.png`
- `fe3384d95eba4415b1e40ff71cd63a89ad5efd99bec40d60cf7c6dda121e36ff`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0034.png`
- `7a29c7eb9e71a7c313232256808257600bbbdd955f65d9f972efd16669808b13`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0035.png`
- `ea7909843e2f37420d682f2cd10f3a4abfbf194dfe82757c7dd58dc096fc3a9b`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0036.png`
- `bff678fa0a0e99b4b7b40762c18a1e5fcc92c56dfe6681b3d25ea5f6f35c1ee6`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0037.png`
- `525e14a0cea16885a6c0caaf6c089d72d903ce9b1d099853d659ff25aa74c369`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0038.png`
- `019252fc7c755c844d9d4840b8c28ef85e56e5b6e2cf6bf3ac8b2863ee7f6ea6`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0039.png`
- `292c6dbe3a79b331d6b76b02988616d6c1b70ac5d6dcb85b4720e35a5e7024b6`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0040.png`
- `a98717f0c8cba71bc72a1be6c6fdeeee75d9426c2e10e0babffe6e89019830e9`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0041.png`
- `fc284395f30c2e9f8a4c2f4935397a7cc284208c86282cec0a6a86c448d54896`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0042.png`
- `eb5b8b05995126a743e8fa93159e3e93c3aa09460b5bfe48f1baf53fcfa81831`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0043.png`
- `7502dcd270f4ce213d3a7b61aad4fa5cd7befbb070c9e0f88304d040c7512275`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0044.png`
- `92faff0cca88414f284389b5aab5237554e20cc90984e850746ebf6782add496`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0045.png`
- `cc5aff1527b8eb219584b3e40b10e222543ca33e672e001de401e41ba327a302`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0046.png`
- `88a14a434428521f38a6b56796bc1f9ae0116c6f4bb9f5cba3e7d0494998c171`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0047.png`
- `b9b5946e35a914160c532011122da618bb9f7e7be07323d1d9b6bdbcf0443bae`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0048.png`
- `09ca7fd36c9468819b3d4416371502c1fb34a4caafb8fa7e5e8dc3e3ed8d6bc7`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0049.png`
- `38ceb28e4940991d89b24017afb42c3a95243dd4b535c67a773259d55756aff8`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0050.png`
- `3544fa57cafa2fd4a89439affdc552fe977c950344d664594c31b5edacbcfc5e`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0051.png`
- `b729c6ab97889d60d0f31a40d36e8efcfa0f6cb8b2ef5915e1bf695a5f7407f2`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0052.png`
- `c35e219d2e5d6a1d703a42e3852d6e5a46abbf259e1e4b4b30c7a82c9ece0d4f`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0053.png`
- `6daed34ad28586002e7d8b3c1bdcc4fed1d35618b3cbf1aeca28ad0adc8c134f`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0054.png`
- `955ab98291e36e8019713333dd09e6022fc1ce0b5486016afc8c5fbd19e785f5`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0055.png`
- `b823f017c1a19c9580b2185dbb9141fcce3a00be35299dcc963019763a4335b3`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0056.png`
- `0acd5f89ce4bac6142260de4559932e66b4f5ad4eaf5625580ad4ccc4bc99410`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0057.png`
- `764dd9a085bd73f22d1fd56ede8f4ae2190810b50ebc826ae19018075e289205`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0058.png`
- `c469e8487620f8b581e9b10dcd55dac37dc9456c3c32f712c40f245024ead51f`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0059.png`
- `4f4974302c716047666a66948ece92891c5e4916cee5b93cb7559775d0fa33a6`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0060.png`
- `a3e3bbe76787c2ef62b7c1ad2193c33548565d970f31d3e4c91d4497124a5c8f`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0061.png`
- `0b7e994668ca73849c098a05e7a5800ef76c5a67c014c1e2a17f25c417f6d11a`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0062.png`
- `ea008cc329abd009d2cec3a7778eda3a6c55b76deb9773efa3deff7be5cc456b`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0063.png`
- `fc0010c19d5558f1f034fce4529c70cd3974c2925ba343702f791c98f2db6c05`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0064.png`
- `443980c0f51a3074fe9cf5ebdef33b66b30f656f6c65e0d932e1e75ac3711f6a`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0065.png`
- `3645ad1615f36ed38acc4cc583ed33e8f85767e5825abf3d412b8be28b3b7386`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0066.png`
- `17d4fb6123880fde87640fae8fdb0fbc5a58c10eee2b79dbee60858334c429bf`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0067.png`
- `8ddb0c5edcc3bf2f224c442b91734dd3a3eee3c4387048275e6c71f00b3909c7`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0068.png`
- `f91f56c1d13d3d45c3bc5e785e2304f46ae1276fa48b012b01aaca47705c92ac`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0069.png`
- `52d64df37a25000c34d1a6dfead9b583124751a6aef727cb0972c19e1b207c28`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0070.png`
- `b93ff1ac265a2f650e17a113480b8959bd83d0d27387f40b525f1726cdad9cc2`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0071.png`
- `7bf15f97fab3d5f76e330b01b090b2ee35c78d07edd9ddc50e9d15da52cee996`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0072.png`
- `01678a693966841047fe2b0ba461a770c44a3506d1329ed5a91e26479ad4ee3c`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0073.png`
- `6212ce8ba5ac5cc1222fd7b86d32fa0eeba64416861d0be5e7ee6e3d9581d258`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0074.png`
- `78107294b426015531caaa70f70a6d9d655f5156ea27cd2fe11f3e2772f510b0`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0075.png`
- `a919a8d1b236f1fbc72fb3a3c5c9954cc38d212e19858cf0dd08fb1ba5596119`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0076.png`
- `854638ca898c6011fde130fd1652dd0d4db18019ae62c76faaadcc79acdfb0c4`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0077.png`
- `c1792b9b818a7080829243fb4d79db8175b489a9537790d1fa0c024d7adc8d04`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0078.png`
- `8997c252709ae9eb19610ea4f561237f72e2cccc8f3113e48df6f77808cc563b`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0079.png`
- `66e86f6eb8c626dc9c248cef233953510fe6246a480fa463feaaf346c459f76f`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0080.png`
- `559b3433dda0efe0c39b36e4c9054f9a7a71f4cb51f10f7703f7af398338a6bd`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0081.png`
- `b73f27d44834b9327614cf8be6ac3480ddbe9dca16edafad30310ea7ba326f25`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0082.png`
- `2113a23998708a45d8c960db593898a4c71c1cb7525c5cb261547eb926899365`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0083.png`
- `eb65e651b8b27ba92783efa67ac70409d4fc6708e087028960a6d12d45985296`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0084.png`
- `f69d077cc9802a0bd4ae04ebfb132383797860d789f6db9061c5e8951f6b629f`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0085.png`
- `5ae152fc07ace089aa456880b8b927210bb9fd72c4013d7e183250e49672533b`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0086.png`
- `8ff1c17d7610b08a00bd93bab86662ca07fe0e57b419348c23cd3e01512d4d35`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0087.png`
- `f002bcfb726b07d239a64fd1293c660892a79ac339e7c18c8cd11d7e40ae668b`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0088.png`
- `a348ca7c02e8b6703ebaf84e25b26ffec64ce697e4d423268bdd7f769a93b257`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0089.png`
- `7c51c0187f24b6330fa6a9f196aa93105c79a0b919e66907f6f2b79a2e5f39c8`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0090.png`
- `fbc347b7a3c59c1dd16def426394371287aa6771c53b6c64832cb324680c61d3`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0091.png`
- `fa34a0e04f11c002c4fdc901425532d195cb4ea9deb7f487a2ea343e395295bb`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0092.png`
- `920f1ebc4b670960dc261eb06af49fb5319764558cd06c69cd852dec3dccba22`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0093.png`
- `68e775ecdd80d1026d7c5998cb92d40f6470ebb5a32004853df8995e1417c053`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0094.png`
- `8b4692f2cc2f11b3c1fe3ea5dd3d1d13a8e86ddcb9c9d7d166eec1e9f5704ed7`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0095.png`
- `25335a9df4bef48abd5a9fcb00ae370465f8d774b0422c0e3c778e627aa04c1a`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0096.png`
- `4bd6cffc9a3ab9292352fa7109f4f14ef4dc90ea7a0260d03990ecccb9c9931f`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0097.png`
- `345d5b46d6c1ff405d3d7e2eeb793dc959df77c26aa5ddf40fed6467688725c4`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0098.png`
- `2a070f3c8b1d3fc5311914977ae582a0ae22cf1909686d7e27d1753f4fe4cd58`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0099.png`
- `1797907bfe099e4180224bd623b242df83ce2d71d90eb0acb066650ee0e37dda`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0100.png`
- `b1c6aa90ac752bb7a99f91852e2c2eb03563c5831d107ed3339d960c75f5a929`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0101.png`
- `4c0eacf7b32803fa95207ee11e4ce1991315e6dd299fe1ce2466f376eebded7a`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0102.png`
- `330681d5ff8dc8a1f7080f4398ee752cef6d60a7725baceee6298d8f0318689d`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0103.png`
- `af7b0621598beeb2bccf4cd6dabe85732653ba1135d3bd257599ed851e0bf30f`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0104.png`
- `9a6f6e0e76969ca0fc632214bcc2697ea9f078be1438f3ef88ae433fa85e29e3`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0105.png`
- `72b7d9bed14df4c7622ba6fb13fcce539954ed97dabebd67ad04dff0947b01a9`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0106.png`
- `6b3d11bc854b79a65b8b84a8f22a249a822ba91b8ab5d3721525d0d05ffdeeea`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0107.png`
- `2d07754818de6cafe861097b91729edd21ab1987726046155b1c50b76c8b5555`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0108.png`
- `688033ee731368e6f3f88c201010d8aa985eed1da1841362bdf5430cd28555ca`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0109.png`
- `4c030ffa6d561cc519adccc9767e6910fe01786d4de5009412e3873bd6af6d51`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0110.png`
- `66eaa0c943bb0eb1c448772dbd19be9835097af5bdaffff6da32e5bc420e6a73`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0111.png`
- `1e2d734796327e4da1fecf0e070438ae92c6311434a17a15cc6ff0ea075c6639`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0112.png`
- `f608efa985069276185791bc8d780eab6df44cc8659973899ebb123e255a8fe9`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0113.png`
- `0a921b7de0cc8a2d886f2d3772f4f77f1592cc2fbd00cc4cd69e6f3e422b0ed9`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0114.png`
- `5712b2dec97e623c6caee3906001544413891a085a4007a9ba2c0aa9d288cbe0`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0115.png`
- `bfcce31e3806000cadac79ffab95791f6d1fa1d47d25b65b6f6f2036ff5d8d40`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0116.png`
- `cebdba6ea05901952b4fac1ac505ab18ce89e7c72b187513351b7eea0992f2aa`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0117.png`
- `0cf5a7afdd94fefa66f9ab9ccc07902427d29a9289199bc4a3b58041b1caeb0e`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0118.png`
- `45d40171f72885e3a84883abb8d0da3267e3e98fc4c59997bfdc6f1862a4ce04`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0119.png`
- `c86d71978cd78237dc658d3ad7c3ab5ed647b47d119984b73f062a3f43d90f0d`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0120.png`
- `bfe93c0710a73df9c59a012c624a39680ae5e645c1302b6ab7612967ce03a999`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/sheet-0121.png`
- `2b64e0a0dec97134f86379aabb4b20fd82d385591e4f67cc8a36b9abeb293118`  `/data/coding/scanweave/qualification/acr06/local/donorfix/panels/index.json`

## Open issues and review judgment

The strict surrounding-pixel and absolute no-overlap checks are not clean, as detailed above. The new historical PDFium duplicate, the P2 sheet 5 distant differences, and the first-seed 600-DPI truth regression are unresolved review items. Neither measured candidate is qualified for shipping. The source-local fallback is intentionally conservative but can remove genuine improvements on damaged glyphs; only the m1d crossbar is positively established as preserved. The second fresh set changes the damage seed but shares the same typography. No claim is made that all 240 suspect substitutions were corrupt or that all panel rows have been independently reviewed.
