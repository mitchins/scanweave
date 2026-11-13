# BOOKS-01 Phase 0 preparation

**Status: selection frozen with material open issues below.** This is not a Phase 1 comparison.

Quiver revisions are in `phase0/repo-pins.json`; FineBooks dataset and image revisions, source URLs and byte hashes are in the provenance and lock files. Twelve IA original-capture JP2 codestreams use irreversible 9/7 wavelets and decode to RGB8 via the pinned Pillow/OpenJPEG versions. Their candidates were fetched as individual tar members. All 12 use the WebP fallback under the accepted rule. Holdout files were hashed as bytes only. The accepted split is book-disjoint and unchanged.

The language rule is `deu_latf` for Quiver Fraktur, `deu_latf+lat` for fontmix, `lat` for Alberti Antiqua, and `deu` for the other Antiqua work; FineBooks uses the volume language string in the accepted proposal. Each string is recorded per dev page.

Each dev PDF embeds decoded RGB8 samples using Flate at the recorded physical DPI. The builder compares the decompressed embedded samples byte-for-byte and checks a second build for identical PDF bytes. The same deterministic check is applied to the 15 per-work PDFs. GT and alignment overlays are local under the designated work directory.

## FineBooks registration

Patch matching uses 128-pixel access-image patches and searches each exact quarter-turn around the scandata crop; the accepted rule is in `phase0/REGISTRATION.md`. Residual is p95 among inliers, in JP2 pixels; the fraction is the proportion of qualifying matches within 2 px. A dash means not measurable, not zero. Where available, the scale and translation in the source lock apply to the rotated JP2 frame.

| Page | Residual px | Inliers / patches | Inlier fraction | Ink delta | Decision |
|---|---:|---:|---:|---:|---|
| finebooks/conchologiaiconi05reev/8967333 | — | 0 / 0 | 0.00 | — | webp: insufficient spatially separated matches |
| finebooks/conchologiaiconi05reev/8966753 | 1.83 | 7 / 9 | 0.78 | — | webp: correlation residual or inlier requirement failed |
| finebooks/conchologiaiconi05reev/8967228 | 0.00 | 8 / 8 | 1.00 | — | webp: no measurable GT line ink |
| finebooks/conchologiaiconi05reev/8967062 | — | 0 / 7 | 0.00 | — | webp: insufficient spatially separated matches |
| finebooks/pisciumquerelaee00sche/9684341 | 1.59 | 3 / 21 | 0.14 | — | webp: correlation residual or inlier requirement failed |
| finebooks/pisciumquerelaee00sche/9684355 | 1.17 | 2 / 13 | 0.15 | — | webp: correlation residual or inlier requirement failed |
| finebooks/pisciumquerelaee00sche/9684335 | 1.31 | 2 / 14 | 0.14 | — | webp: correlation residual or inlier requirement failed |
| finebooks/pisciumquerelaee00sche/9684354 | 0.86 | 1 / 10 | 0.10 | — | webp: correlation residual or inlier requirement failed |
| finebooks/trudyrusskagoent161881russ/12341923 | 0.10 | 1 / 9 | 0.11 | — | webp: correlation residual or inlier requirement failed |
| finebooks/trudyrusskagoent161881russ/12342014 | 1.71 | 3 / 11 | 0.27 | — | webp: correlation residual or inlier requirement failed |
| finebooks/trudyrusskagoent161881russ/12341934 | 1.99 | 1 / 12 | 0.08 | — | webp: correlation residual or inlier requirement failed |
| finebooks/trudyrusskagoent161881russ/12342041 | — | 0 / 9 | 0.00 | — | webp: correlation residual or inlier requirement failed |

## Quiver DPI evidence

Physical sizes are implied by the TIFF tags, in millimetres. Confidence is moderate when METS includes a format and low when it supplies no physical format or dimensions. TIFF values are used provisionally in the latter case; they have not been independently confirmed.

| Page | DPI | Implied size mm | METS extent | Confidence |
|---|---:|---:|---|---|
| quiver/estor_rechtsgelehrsamkeit02_1758_0007 | 300 | 126.07 × 213.87 | 1132 S., [49] Bl. | low |
| quiver/estor_rechtsgelehrsamkeit02_1758_0819 | 300 | 123.7 × 213.78 | 1132 S., [49] Bl. | low |
| quiver/euler_rechenkunst01_1738_0025 | 200 | 164.59 × 235.59 | [6] Bl., 277 S. | low |
| quiver/euler_rechenkunst01_1738_0031 | 200 | 164.59 × 235.59 | [6] Bl., 277 S. | low |
| quiver/luther_babstum_1526_0010 | 300 | 146.98 × 198.97 | [22] Bl.; Titelholzschn., Ill. (Holzschn.); 4 | moderate |
| quiver/luther_babstum_1526_0011 | 300 | 146.98 × 199.98 | [22] Bl.; Titelholzschn., Ill. (Holzschn.); 4 | moderate |
| quiver/aventinus_grammatica_1515_0006 | 300 | 148.67 × 206.59 | [44] Bl.; 4 | moderate |
| quiver/aventinus_grammatica_1515_0007 | 300 | 148.67 × 206.59 | [44] Bl.; 4 | moderate |
| quiver/aventinus_grammatica_1515_0008 | 300 | 148.67 × 206.59 | [44] Bl.; 4 | moderate |
| quiver/benner_herrnhuterey04_1748_0013 | 300 | 131.49 × 220.73 | [6] Bl., 180 S. | low |
| quiver/benner_herrnhuterey04_1748_0014 | 300 | 131.49 × 220.73 | [6] Bl., 180 S. | low |
| quiver/alberti_pictura_1540_0008 | 300 | 94.66 × 155.53 | 120 S., [6] Bl.; Druckerm.; 8 | moderate |
| quiver/silesius_seelenlust01_1657_0010 | 300 | 97.54 × 156.8 | [8] Bl., 402 S., [3] Bl. : Frontisp., Noten | low |
| quiver/silesius_seelenlust01_1657_0021 | 300 | 92.96 × 156.8 | [8] Bl., 402 S., [3] Bl. : Frontisp., Noten | low |
| quiver/silesius_seelenlust01_1657_0423 | 300 | 97.71 × 156.8 | [8] Bl., 402 S., [3] Bl. : Frontisp., Noten | low |
| quiver/bohse_helicon_1696_0009 | 326 | 99.73 × 162.84 | [6] Bl., 96 S., [2] Bl., S. 97 - 188, [2] Bl., S. 189 - 280, [2] Bl., S. 281 - 364, [2] Bl., S. 365 - 472, [2] Bl., S. 473 - 572, [2] Bl., S. 573 - 648, [2] Bl., S. 649 - 740, [2] Bl., S. 741 - 837, [1] Bl., S. 851 - 941, [2] Bl., S. 943 - 1014, [2] Bl | low |
| quiver/bohse_helicon_1696_0036 | 330 | 98.52 × 162.1 | [6] Bl., 96 S., [2] Bl., S. 97 - 188, [2] Bl., S. 189 - 280, [2] Bl., S. 281 - 364, [2] Bl., S. 365 - 472, [2] Bl., S. 473 - 572, [2] Bl., S. 573 - 648, [2] Bl., S. 649 - 740, [2] Bl., S. 741 - 837, [1] Bl., S. 851 - 941, [2] Bl., S. 943 - 1014, [2] Bl | low |
| quiver/meyfart_rhetorica_1634_0021 | 300 | 98.98 × 159.94 | [8] Bl., 441, 54 S., [4] Bl. | low |
| quiver/meyfart_rhetorica_1634_0022 | 300 | 98.98 × 159.94 | [8] Bl., 441, 54 S., [4] Bl. | low |
| quiver/arnold_ketzerhistorie01_1699_0114 | 300 | 196.34 × 332.57 | [11] Bl., 422, 728 S., [26] Bl; 2° | moderate |
| quiver/arnold_ketzerhistorie01_1699_0115 | 300 | 196.34 × 332.57 | [11] Bl., 422, 728 S., [26] Bl; 2° | moderate |
| quiver/luther_auszlegunge_1520_0003 | 300 | 154.09 × 214.21 | [38] Bl.; Titeleinfassung; 4 | moderate |
| quiver/luther_auszlegunge_1520_0029 | 300 | 151.13 × 214.21 | [38] Bl.; Titeleinfassung; 4 | moderate |
| quiver/blumenbach_anatomie_1805_0047 | 300 | 143.93 × 227.5 | XVI, 549, [1] S. | low |

## Smoke and costs

The first smoke attempt failed because the prepared model directory omitted Tesseract’s `hocr` configuration. The system Tesseract 5.3.4 configuration was copied locally (hash in costs), and the same page was retried. The completed report records `native_source_samples`; no comparison was run.

Logical disk bytes: {'src': 1056450237, 'sources': 513641002, 'gt': 3080493, 'qa': 191793448, 'smoke': 1681772, 'tmp': 27082533, 'tessdata_best': 200694865}. Saved source file bytes: 1,056,320,306. PDF/GT build wall time: 60.9 s. The original fetch, registration and smoke elapsed times and actual network bytes were not captured; they are explicitly null in the cost record.

## Open issues

- All 12 FineBooks XML files contain TextRegion polygons and text but no TextLine elements. Line counts are zero, region text is preserved without inventing line boxes, and line-polygon ink containment cannot be measured. The accepted rule therefore forces fallback even when the patch correlation alone might pass. Line-level alignment metrics for these pages require a separately approved methodology or different GT.
- For Quiver works whose METS gives no physical format or dimensions, the TIFF DPI is provisional and low confidence. A catalogue-based physical-size check remains needed before treating those page sizes as established.
- Fetch, registration and smoke timing and actual network byte totals were not instrumented; the missing measurements cannot be reconstructed reliably.
- Registration did not establish image correspondence for every JP2 candidate, particularly sparse plates. The fallback is safe under the acceptance rule but original-capture use remains unverified for those pages.
