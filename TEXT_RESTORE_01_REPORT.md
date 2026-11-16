# TEXT-RESTORE-01 — interior paper estimate (candidate C)

**Verdict: reject candidate C; no converter code is committed.** The interior estimate corrects false polarity on historical scans and changes their ownership decisions, but “613” becomes more fragmented, Euler's text fidelity falls, the heading remains orange, and extraction changes on 21 pages. The French crop becomes softer in places rather than demonstrably stronger. It does not meet the owner's success criteria. The previous owned-ink fallback remains rejected; its colour-only version improved the heading tint but did not repair “613”. C did not include that paint change because C already regresses shape and controls. The rejected patch is `$B/text-restore/candidate-c/rejected.patch`; `$B=/data/coding/scanweave/work/books01`.

## Diagnosis and experiment

- **613 (8967062):** foreground extraction and page-wide ink colour are contaminated by image content; vector reconstruction loses faint strokes and paints them orange. The compact background is 200-DPI JPEG85 4:2:0, and resampling/compositing can further soften raster residue. The new paper estimate changes 237.8→251.8; this does not repair the problem.
- **Faint heading (8967228):** vector paint uses artwork-contaminated page-wide foreground colour; C changes paper 249.5→230.7 and improves local ink recall but leaves obvious orange colour and soft detail. Adobe registration failed the existing gate; its SSIM is unavailable.
- **French list (12342014):** corner paper 204.3 vs interior-mode 224.7 shifts the foreground threshold and ownership. The baseline mixed vector/200-DPI JPEG path can soften details. C reduces vector-ink pixels 150,562→127,139; the illustrated crop is softer in places, so the increase in crop recall is not proof of better lettering.
- **Dense English (8966753):** faint input and mixed raster/vector ownership leave a large background JPEG and foreground/font payload. C increases size and does not establish a readability improvement.
- **Historical controls:** corner scanner-bed pixels made Aventinus and Luther appear inverted before the polarity gate; calling all their raster retention an intentional confidence fallback was wrong. C corrects polarity but both remain raster-owned under the other gates. Euler's paper estimate falls 254.7→204.1 and 25,117 ink pixels become vector-owned; text-region SSIM drops .9955→.9775. The safety gates alone do not guarantee source-fidelity preservation after changing their input mask.

C selects the most populous ±8-luma neighbourhood in the central half of the image, then uses the median RGB of that neighbourhood. A dark dominant interior mode remains dark, but the central mode can select a large dark mark or a light mark on reversed paper; genuine polarity is not reliably preserved. Foreground delta 60, 0.98 IoU, contact, unsupported-content, compact-raster and all other gates are unchanged. Two focused tests exercise dark scanner borders and dark paper with light text; these do not establish general polarity correctness. The page mode is not necessarily paper on illustration-heavy scans.

## Size and fidelity

PDF size kB / aligned text-region SSIM; source is the reference. Candidate uses the baseline's accepted alignment. Adobe is default-language, lacks Fraktur and deskews; its 8967228 alignment fails the gate. Higher SSIM alone does not prove character identity or legibility.

| Page | Baseline | Candidate C | MRC | Adobe |
|---|---:|---:|---:|---:|
| 8967062 | 92.3 / 0.913 | 86.7 / 0.915 | 105.2 / 0.927 | 151.6 / 0.878 |
| 8967228 | 161.3 / 0.956 | 161.4 / 0.955 | 112.3 / 0.894 | 317.5 / n/a |
| 12342014 | 554.9 / 0.929 | 481.9 / 0.932 | 137.0 / 0.903 | 396.3 / 0.891 |
| 8966753 | 1,467.0 / 0.989 | 1,512.5 / 0.986 | 185.9 / 0.940 | missing |
| Aventinus 0008 | 567.9 / 0.950 | 564.1 / 0.950 | 103.6 / 0.741 | 509.2 / 0.764 |
| Luther 0011 | 441.8 / 0.976 | 441.8 / 0.976 | 98.6 / 0.827 | 345.0 / 0.800 |
| Euler 0025 | 439.4 / 0.996 | 455.9 / 0.978 | 74.5 / 0.763 | 258.3 / 0.767 |

Local-paper-minus-20 ink recall / mean ink ΔE2000: 613 **.857 / 5.14 → .793 / 6.31**; heading **.819 / 7.17 → .919 / 6.00**; French crop **.932 / 6.60 → .939 / 5.67**. These threshold scores are diagnostics, not proof of intact strokes. Source/baseline/C/MRC/Adobe 2× crops: [613](/data/coding/scanweave/work/books01/text-restore/inspect-c/8967062-final.png), [heading](/data/coding/scanweave/work/books01/text-restore/inspect-c/8967228-final.png), [French](/data/coding/scanweave/work/books01/text-restore/inspect-c/12342014-final.png), [English](/data/coding/scanweave/work/books01/text-restore/inspect-c/8966753-final.png), [Aventinus](/data/coding/scanweave/work/books01/text-restore/inspect-c/aventinus_grammatica_1515_0008-final.png), [Luther](/data/coding/scanweave/work/books01/text-restore/inspect-c/luther_babstum_1526_0011-final.png), [Euler](/data/coding/scanweave/work/books01/text-restore/inspect-c/euler_rechenkunst01_1738_0025-final.png). The separate [illustrative Adobe heading crop](/data/coding/scanweave/work/books01/text-restore/inspect/8967228-adobe-illustrative.png) uses a rejected registration and is not quantitative.

| Page | Reading CER baseline → C | MRC | Adobe |
|---|---:|---:|---:|
| 8967062 | 3.385 → 3.413 | 3.413 | 0.780 |
| 8967228 | 1.378 → 1.378 | 1.311 | 0.911 |
| 12342014 | 0.555 → 0.555 | 0.553 | 0.373 |
| 8966753 | 0.014 → 0.014 | 0.015 | — |
| aventinus_grammatica_1515_0008 | 0.559 → 0.557 | 0.554 | 0.806 |
| luther_babstum_1526_0011 | 0.227 → 0.227 | 0.227 | 0.643 |
| euler_rechenkunst01_1738_0025 | 0.611 → 0.611 | 0.613 | 0.843 |

All 36 conversions succeeded; 36 structured OCR records and selected PSMs match baseline. PDFium reading-normalised extraction nevertheless differs on 21 pages (15 unchanged), so equal OCR recognition does not establish equal PDF text. Conditional search remains 340/396; median CER .337→.336. Total size **16,315,763→16,216,271 bytes**; summed per-page wall **985.9→1,380.8 s** with three workers. Candidate conversions ran with no concurrent build; baseline includes six reused pilot runs and is not a controlled speed comparison.

**U+FFFE investigation.** The baseline already exhibits PDFium U+FFFE on invisible raster-owned hyphenated hOCR words: a box/ownership audit finds 105 candidate positions across 24 pages, including three in Estor 0819. At those positions the source hOCR contains a hyphen, owner is invisible, and PDFium's single-character text extraction returns U+FFFE; its raw character API reports U+0002. The rejected fallback exposed additional occurrences by changing ownership; it did not introduce this class of behavior. The exact PDFium/encoding mechanism remains unresolved, so no speculative fix is included. Details containing OCR text remain local in `$B/text-restore/hyphen-audit.json`.

## Paper estimate changes

32/36 pages changed by more than 10 luma; 20 pages flipped inverted→normal, none normal→inverted. Values below are baseline corner-based → C interior-mode luminance; `*` marks a polarity flip. Full corner medians, interior medians, vector counts and every page are in `$B/text-restore/paper-audit.json`.

| Page | Paper luma | Page | Paper luma |
|---|---:|---|---:|
| estor_rechtsgelehrsamkeit02_1758_0007* | 52.8 → 198.9 | estor_rechtsgelehrsamkeit02_1758_0819* | 54.0 → 201.0 |
| euler_rechenkunst01_1738_0025 | 254.7 → 204.1 | euler_rechenkunst01_1738_0031 | 254.7 → 207.9 |
| luther_babstum_1526_0010* | 49.0 → 216.5 | luther_babstum_1526_0011* | 40.9 → 216.5 |
| aventinus_grammatica_1515_0006* | 33.5 → 194.3 | aventinus_grammatica_1515_0007* | 32.8 → 202.5 |
| aventinus_grammatica_1515_0008* | 38.6 → 198.1 | benner_herrnhuterey04_1748_0013* | 19.1 → 190.8 |
| benner_herrnhuterey04_1748_0014* | 12.9 → 191.8 | alberti_pictura_1540_0008* | 1.0 → 220.7 |
| silesius_seelenlust01_1657_0010* | 42.7 → 188.2 | silesius_seelenlust01_1657_0021* | 40.1 → 192.2 |
| silesius_seelenlust01_1657_0423* | 38.6 → 193.5 | bohse_helicon_1696_0009 | 141.4 → 128.6 |
| bohse_helicon_1696_0036 | 140.6 → 123.4 | meyfart_rhetorica_1634_0021* | 38.0 → 141.7 |
| meyfart_rhetorica_1634_0022* | 41.2 → 138.2 | arnold_ketzerhistorie01_1699_0114* | 34.2 → 181.5 |
| arnold_ketzerhistorie01_1699_0115* | 33.8 → 194.9 | luther_auszlegunge_1520_0003* | 35.6 → 218.3 |
| luther_auszlegunge_1520_0029* | 39.0 → 217.3 | blumenbach_anatomie_1805_0047* | 35.4 → 210.5 |
| 8967333 | 236.4 → 252.8 | 8967228 | 249.5 → 230.7 |
| 8967062 | 237.8 → 251.8 | 9684341 | 174.2 → 193.3 |
| 12341923 | 201.6 → 223.7 | 12342014 | 204.3 → 224.7 |
| 12341934 | 166.2 → 181.8 | 12342041 | 204.4 → 221.6 |


`cargo test --locked -- --test-threads=1` stopped with two existing integration-test failures in `polarity_gate`: `inverted_no_vector_page_is_not_routed` and `normal_estimate_does_not_route`. Both use central marks that dominate the sampled interior; C classifies the marks as paper. The two new focused mask tests passed. Cargo stopped at that test binary, so subsequent test binaries were not run; details are in `$B/text-restore/candidate-c/cargo-test.log`. The candidate and all output PDFs, screenshots and OCR remain local. No benchmark holdout, Acrobat or comparator reruns were used. The converter remains at the production baseline.
