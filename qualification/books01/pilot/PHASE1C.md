# BOOKS-01 Phase 1c — search audit and review workload

Phase 2 remains on hold. The capped queue below misses all four previously concerning panel locations; the human follow-up and a review strategy that can address this coverage gap are needed before expansion. No conversion, holdout access, Wine or detector recalibration occurred. The existing human-panel files were not modified.

## Conditional search misses

The original metric is unchanged: sample distinct reading-normalised GT tokens that occur somewhere in the frozen hOCR, then search each PDF with PDFium case-insensitive literal search. Every one of the 175 misses across six pages and seven rows was audited. `results/phase1c/search-audit.json` records an ID, cause and nearest-string edit count for each miss. Query, nearest actual extracted string and literal search result are in the local-only `$B/pilot/phase1c/search-evidence.json`. Its nearest-string search is evidence, not proof that a repeated token is the corresponding GT occurrence. Because the original sample is of unique word types, it cannot establish occurrence-specific recognition; occurrence counts are recorded and the metric has not been redefined.

| Row | Misses | Query normalisation | Hyphen/line break | Split/merge | Proven text-layer loss | Sampling/definition | Other |
|---|---:|---:|---:|---:|---:|---:|---:|
| Source | 74 | 0 | 0 | 0 | 0 | 0 | 74 |
| sw-E | 10 | 10 | 0 | 0 | 0 | 0 | 0 |
| sw-M | 10 | 10 | 0 | 0 | 0 | 0 | 0 |
| sw-build | 10 | 10 | 0 | 0 | 0 | 0 | 0 |
| OCRmyPDF-E | 3 | 0 | 0 | 0 | 0 | 0 | 3 |
| MRC-M | 10 | 10 | 0 | 0 | 0 | 0 | 0 |
| Adobe-E | 58 | 0 | 0 | 0 | 0 | 0 | 58 |

The source PDF has no OCR layer, hence its misses. All 40 ScanWeave/MRC misses have a diplomatic text-layer token whose reading-normalised form is the query; PDFium finds that diplomatic form. In the examined cases the relevant distinction is long-s versus normalised s. **None of these ScanWeave misses is evidence of a missing or altered text-layer character**; the literal search query and diplomatic spelling differ. The audit also records a supplemental diplomatic-form result alongside the original metric: the 10 misses per matched row are recovered. This is a diagnostic lower bound, not a replacement search metric; only an exact reading-normalised token with a successful literal diplomatic search qualifies.

The three OCRmyPDF and 58 Adobe misses are `other`: they have independent OCR, and the nearest different token cannot establish whether recognition or PDF text encoding caused the difference. The evidence does not justify calling those misses text-layer loss. Adobe means Acrobat default OCR language (not matched); no Fraktur support; page straightened (deskew). OCRmyPDF has its own Tesseract invocation and PDF text renderer, so its OCR can produce different spellings; the literal search responds to the resulting Unicode characters, not just their visual glyphs. For the Luther page, the actual OCRmyPDF PDF contains a subset NotoSans font with ToUnicode, ScanWeave contains ScanWeaveDoc with ToUnicode, and Archive MRC contains GlyphLessFont with ToUnicode (`font-resources.json`). Thus a glyph-less font is **not** a sufficient explanation for the observed OCRmyPDF difference; the independent OCR and Unicode text mapping are possible contributing mechanisms, and the available artifacts do not isolate them.

## Ranked review queue

The [queue definition](phase1c/QUEUE.md) ranks the existing flagged scores within each page, row and detector, deduplicates overlapping boxes and pixel-identical crops, and caps review at 10 candidate crops per page, no more than three per output row, plus two random controls. The committed index contains no images; source/output crops are local in `$B/pilot/phase1c/queue/`. Coverage below is the fraction of original flagged **candidate instances**, including duplicate detector/row instances, represented by a selected crop and an equivalent output at IoU ≥ 0.5. It is not recall or a percentage of defects.

| Page | Flagged instances | Covered instances | Candidate crops | Controls | Total | Time at 20 s/crop |
|---|---:|---:|---:|---:|---:|---:|
| aventinus 0008 | 609 | 12 (1.97%) | 6 | 2 | 8 | 2m 40s |
| luther 0011 | 210 | 13 (6.19%) | 7 | 2 | 9 | 3m 00s |
| arnold 0114 | 2,864 | 13 (0.45%) | 6 | 2 | 8 | 2m 40s |
| benner 0013 | 370 | 13 (3.51%) | 7 | 2 | 9 | 3m 00s |
| 8967333 | 77 | 8 (10.39%) | 4 | 2 | 6 | 2m 00s |
| 12342014 | 639 | 27 (4.23%) | 9 | 2 | 11 | 3m 40s |
| **Total** | **4,769** | **86 (1.80%)** | **39** | **12** | **51** | **17m 00s** |

A simple sixfold projection to 36 pages is **306 crops / 102 minutes**, including 72 controls; it is a projection from six pages, not a measured Phase 2 workload. The caps can produce fewer than 10 candidates where pixel deduplication and per-row caps exhaust eligible rows.

The queue does **not** cover panel-001/crop-0018, panel-002/crop-0055, panel-003/crop-0056 or panel-004/crop-0014 when both overlap and the concerned output are required. This is a coverage check against previously selected examples, not an independent detector evaluation or precision/recall estimate. The greedy overlap rule can suppress a different output at the same location; that and the low flagged-instance coverage require owner review before this queue is used for the larger run. Earlier AI crop assessments remain provisional; human-panel records are not modified here.
