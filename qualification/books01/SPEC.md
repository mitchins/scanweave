# BOOKS-01: Scanned Book Benchmark and Failure Analysis

**Status: PROPOSED, awaiting owner review. No comparison has been run.**

**Scope.** This milestone is research and benchmark infrastructure only. It makes no converter changes, does not revive FONT-04, does not continue HVC, and opens no production PR.

**Baseline.** ScanWeave `main` at `ab7dfba` (#39).

**Separate debt.** #40 (reverse-print safety) is tracked independently as outstanding correctness debt. BOOKS-01 can record evidence relevant to it, such as dark book-edge borders in the dev pages, but does not fix it.

Proposed page list: [`corpus.proposed.json`](corpus.proposed.json). Selection tools: [`selection/`](selection/).

---

## 1. Corpus

### 1.1 Sources

| | OCR-D Quiver GT | FineBooks BHL IMPACT GT |
|---|---|---|
| **What** | 14 GitHub repos `tboenig/{16..19}_{frak,ant,fontmix}_{simple,complex}`. Ground truth for OCR-D Quiver workflow benchmarking. | HF dataset `finebooks/bhl-impact-gt`, rev `b7bda5f`. 2,165 pages from 6 BHL volumes, transcribed by the IMPACT / BHL-Europe projects (2011–12). |
| **Extent** | 33 works, 1500–1835. 86 pages with PAGE-XML. | 6 volumes, 1708–1913; English, French, German, Latin. |
| **Scripts** | Fraktur, Antiqua and mixed. Includes Greek and Hebrew in fontmix, and music notation. | **Antiqua only, no Fraktur.** Greek and Cyrillic appear in places. |
| **GT format** | PAGE-XML 2019: regions, lines and text, under the OCR-D GT guidelines. | PAGE-XML 2010 with region polygons. Also plain text, markdown and Docling forms. |
| **GT licence** | The README metadata says CC0 1.0, but the GitHub repo licence field says **CC-BY-SA-4.0**. We treat it as CC-BY-SA-4.0 until clarified. | **CC-BY 3.0**, credited to IMPACT / Biodiversity Heritage Library. |
| **Image licence** | **Public Domain Mark 1.0** in every work's METS (all 33 checked). Holders include SBB-PK, SUB Göttingen, SLUB, BSB, HAB and ULB Halle. | Internet Archive marks all 6 items `NOT_IN_COPYRIGHT`. BHL per-item rights are recorded at Phase 0. |
| **Images** | Uncompressed RGB TIFF, 1000–2319 px wide. DPI tags are unreliable (133, 200, 300, 326 and 330 seen). | The dataset ships lossy WebP access renditions. Internet Archive also has `_orig_jp2.tar` original captures at **300–500 ppi**, plus its own MRC PDF. |
| **GT caveats** | Word-level GT is not guaranteed. Line-level GT is present. | U+FFFD (illegible) appears on about 9% of pages and is scored as a wildcard. About 19% of pages lack ReadingOrder. Long-s, ligatures and hyphenation are kept as printed. |

Remote-service rule: everything is downloaded from the official origins (GitHub, Hugging Face, archive.org) and processed **locally**. Nothing is uploaded anywhere. Images, ground truth and outputs stay under `qualification/books01/local/` and are never committed. Only manifests, hashes, code and metric JSON are committed.

### 1.2 Development set: 36 pages from 15 works

**OCR-D Quiver, 24 pages from 12 works.** Difficulty tags were visually confirmed from the contact sheet.

| Work | Pages | Why it's in the set |
|---|---|---|
| aventinus_grammatica_1515 | 0006, 0007, 0008 | 16th-c. Fraktur, brace tables, library stamp, dense |
| luther_babstum_1526 | 0010, 0011 | Fraktur, stained paper, **hand-coloured woodcuts** |
| luther_auszlegunge_1520 | 0003, 0029 | Fraktur, heavily stained paper |
| silesius_seelenlust01_1657 | 0010, 0021, 0423 | ornamental initial, **music notation**, index layout |
| arnold_ketzerhistorie01_1699 | 0114, 0115 | fontmix, 8 marginalia regions, footnotes, about 5,900 chars per page, colour target in frame |
| meyfart_rhetorica_1634 | 0021, 0022 | fontmix, marginalia, foxed paper |
| bohse_helicon_1696 | 0009, 0036 | fontmix, large ornamental initial, foxing |
| estor_rechtsgelehrsamkeit02_1758 | 0007, 0819 | headpiece ornament, show-through, marginalia |
| euler_rechenkunst01_1738 | 0025, 0031 | numeric tables, symbols, **book edge and dark border** |
| benner_herrnhuterey04_1748 | 0013, 0014 | fontmix title page, footnotes, dark border |
| alberti_pictura_1540 | 0008 | Antiqua Latin, **handwritten marginalia**, stained paper |
| blumenbach_anatomie_1805 | 0047 | Antiqua, footnotes, book edge and dark border |

**FineBooks, 12 pages from 3 volumes.** Four pages per volume, chosen by a deterministic rule over the GT features: the illustration page with the most image regions, the densest text page, the page with the most U+FFFD, and a table page if one exists (otherwise the median text page).

| Volume | Pages (BHL PageID) | Coverage |
|---|---|---|
| conchologiaiconi05reev (1849, 500 ppi) | 8967333, 8966753, 8967228, 8967062 | **colour plates**, faint text, sparse text |
| pisciumquerelaee00sche (1708, 400 ppi) | 9684341, 9684355, 9684335, 9684354 | engraved landscape plate, Latin italic, **Greek** |
| trudyrusskagoent161881russ (1881, 400 ppi) | 12341923, 12342014, 12341934, 12342041 | title layout, dense French, multi-column list, **numeric tables** |

**What the dev set covers:**
- difficult Fraktur: 16th–18th c.;
- mixed typefaces: fontmix, italic and Greek;
- damaged paper: stains, foxing and show-through;
- illustrations: hand-coloured woodcuts, colour and engraved plates, ornaments;
- marginalia: printed and handwritten;
- complex layouts: brace tables, numeric tables, music, multi-column, footnotes, title pages;
- book edges and dark borders.

**Gaps:**
- No page combines Fraktur with colour plates.
- Handwritten marginalia appears on only 1 page.
- Damaged paper is judged visually, not measured.

### 1.3 Holdout: 74 pages, book-disjoint, sealed

- **Quiver:** 62 pages from 20 works, including petrarca, kistler, huebner, glauber, valentinus, justi (marginalia), luz, buerger and lessing.
- **FineBooks:** 12 pages from birdsofgreatbrit02butl, histoirenaturell10cuvi and daschitinskelett00prel, chosen by the same 4-page rule.

No work or volume appears in both dev and holdout; the manifest enforces this with an assert. Holdout images have **not been opened**: only XML features were used to select them. They stay sealed until the harness, metrics and thresholds are frozen, and then they are run **once**. A further 21 Quiver pages from dev works are a "reserve" for swapping a dev page within the same work, and never move to holdout.

## 2. Reproducible lossless source PDFs

Each page gets one source PDF. It is the only input any tool sees, and the reference image all fidelity is measured against.

1. **Image.** Decode the best-available original to RGB 8-bit, or grey if the original is grey.
   - Quiver: the TIFF.
   - FineBooks: the IA original-capture JP2, **if** it registers to the GT coordinate space by a pure scale. Check at Phase 0 with an affine fit of GT line boxes to the image. Otherwise use the dataset WebP, decoded and flagged `lossy-origin`.
   - No resampling, deskew or crop.
2. **Embedding.** Embed losslessly in a one-page PDF with Flate (PNG predictors). The page size comes from the resolved physical DPI.
   - **DPI resolution:** IA `ppi` metadata or scandata. For Quiver, the TIFF tag, accepted only when the implied page size is plausible for the format; otherwise derive it from the METS or holding-library record.
   - The resolved DPI and its provenance are recorded per page. These details matter because ScanWeave's background resolution depends on the DPI.
3. **Pinning.** Pin the generator (pikepdf or img2pdf, exact version). The page hash, the image-sample hash and the PDF hash all go in `sources.lock.json`. A rebuild must be byte-identical.
4. **Multi-page sets.** Build per-work multi-page PDFs (dev works 1–3 pages) as a second input shape, so that cross-page effects such as font and glyph reuse and JBIG2 symbol dictionaries show up.

## 3. Tools and tracks

| Tool | Version pin | Input | OCR |
|---|---|---|---|
| ScanWeave | `main` `ab7dfba`, release build, default mode | source PDF + image | its own Tesseract invocation |
| OCRmyPDF | version in `qualification/.venv` | source PDF | Tesseract, same version and models |
| Archive MRC (`recode_pdf`, archive-pdf-tools 1.5.7 + recorded shim) | as in `LEDGER.md` | source image + hOCR | hOCR from the shared frozen Tesseract run |
| Adobe Acrobat XI ClearScan | existing `adobe-acrobat-sandbox/clearscan.sh` (Wine/Xvfb) | the image-only source PDF | Adobe's own OCR |
| Reference only | IA's published MRC PDF for the 6 FineBooks volumes | (different source generation) | IA's OCR |

**OCR models.** The system Tesseract 5.3.4 currently has only `eng`. We will add official `tesseract-ocr/tessdata_best` models from GitHub, pinned by hash: `deu`, `lat`, `fra`, `grc`, and `script/Fraktur` or `frk`/`deu_latf`. The language string per page comes from the GT language metadata and is the same for every Tesseract-based tool.

**Tracks:**
- **Track E (end-to-end):** each tool does its own OCR. This measures the product as users get it.
- **Track M (matched OCR):** one frozen Tesseract hOCR per page goes to ScanWeave and `recode_pdf`. This isolates representation and compression from recognition. OCRmyPDF can't take external hOCR, so it appears in Track E only. Adobe appears in Track E only.

**Adobe XI.** The Wine prefix and display are shared, controlled infrastructure. Running it needs the owner's go-ahead (§7 Q1). Adobe outputs are measured but treated as opaque: no internals are read.

## 4. Metrics

All metrics are per page, and are aggregated by source, script (Fraktur, Antiqua or fontmix) and tag. Every number keeps its page ID so failures can be traced.

**Size**
- Bytes per page for single-page and per-work PDFs.
- Ratio to the lossless source PDF.
- Byte attribution: background or foreground images by codec, masks (JBIG2 or CCITT), fonts and glyph programs, text layer, structure. Gathered with `pikepdf` object walking.

**OCR accuracy against GT**
- Extract text with Poppler `pdftotext` and PDFium. Score both.
- **CER/WER, diplomatic:** keep long-s, ligatures and case.
- **CER/WER, reading:** fold long-s, ligatures, case and Unicode NFKC, and join line-break hyphens. This aligns with FineBooks `bhl-ocr-eval`; the rules are adopted and pinned at Phase 0.
- U+FFFD in GT is a wildcard.
- **Bag-of-characters recall:** order-independent, to separate recognition from reading order.
- **Line-order agreement:** Kendall τ against the GT ReadingOrder, where one exists.

**Extraction and search**
- Per page, 20 GT words of 4+ characters after reading normalization, deterministic seed. Report the PDFium search hit rate, plus false hits on 20 control words from other pages.
- Copy/paste sanity: no control characters and no duplicated text layers.

**Layout fidelity**
- Match extracted line boxes (pdfplumber or PDFium char boxes) to GT TextLine polygons: matched-line F1 at IoU ≥ 0.5, and median centroid offset in source pixels.
- Marginalia and footnote regions are scored separately, because they're where reading order breaks.

**Visual fidelity**
- **Renders:** PDFium, Poppler Splash and MuPDF at the source DPI and at 150 DPI.
- **Region-stratified error against the source:** split into text regions (GT polygons), illustration and graphic regions, and background/paper. For each, report SSIM, ΔE2000 for colour regions, and **ink recall/precision** (source ink pixels reproduced, and spurious ink added) with a fixed binarization.
- **Automated defect detectors:**
  - glyph substitution: a vector or symbol glyph whose shape mismatches the local source ink, measured by a contour IoU threshold;
  - missing text or ink;
  - halos;
  - colour or posterization shift in illustrations;
  - border and book-edge inversion (#40-class evidence only).
- **Blinded visual review.** For every dev page, side-by-side crops from tools A–D in shuffled order go to an independent reviewer, who uses a fixed defect taxonomy (wrong character, missing ink, halo, blur or texture loss, colour shift, layout/reading-order break). Tool identities are revealed only after scoring.
- **Fidelity gate:** sizes are reported **next to** fidelity, never alone. An output with any wrong-character or missing-text defect is flagged, and is excluded from "smallest acceptable" comparisons.

**Render latency and memory**
- Per output, render-time median and p95 over 5 warm runs, plus peak RSS, in PDFium, Poppler and MuPDF, at 150 DPI and the source DPI.
- Conversion wall time and peak RSS per tool. Adobe gets wall time only, flagged because it runs under Wine.

## 5. Compression-opportunity analysis

Once dev measurements exist:
1. Attribute each tool's bytes by component and by region class: text, illustration, paper.
2. For each region class, compare ScanWeave's bytes with the **smallest output that passes the fidelity gate on that region**. Report the gap in bytes and where it comes from: codec, resolution, segmentation or masks.
3. Rank the opportunities by gated bytes per page. Each ranked opportunity names its fidelity risk.
4. Out of scope: proposing converter changes. Any follow-up needs its own milestone, starting with a break-even model, expected usable coverage and fidelity safeguards, as the #41 disposition requires.

## 6. Bounded execution plan

| Phase | Work | Stop |
|---|---|---|
| **0. Fetch and freeze** | Pin repo SHAs, the HF revision, IA files and tessdata hashes. Build lossless source PDFs and `sources.lock.json`. Check IA JP2 registration to GT. Check that the harness runs on 1 page. Keep holdout sealed: fetch and hash it only. | Manifest frozen |
| **1. Pilot** | 6 dev pages (2 Fraktur, 2 fontmix, 2 FineBooks) × 4 tools × both tracks. Validate every metric end to end. Write a defect-taxonomy panel. | **Owner review** |
| **2. Dev comparison** | All 36 pages, single-page plus per-work PDFs, all metrics, blinded review, opportunity ranking. | **Owner review** |
| **3. Holdout** | Only after harness, metrics and thresholds are frozen and committed. One run, no tuning. | Final report |

**Estimated budget:**
- Disk: about 3 GB local. Dev images are about 0.4 GB, holdout images about 1 GB, outputs and renders about 1.5 GB.
- CPU: Phases 1 and 2 take about 2–4 hours wall. Adobe under Wine is the slowest.

**Roles:**
- Codex implements the harness.
- Claude reviews and does the blinded visual scoring.
- Admin and VM/Wine work is done directly by Claude, not Codex.

**Guardrails:** no converter changes, no default changes, no PR to `main`. Branch `research/books01-benchmark`. Explicit-path staging only; `local/` is never committed.

## 7. Questions for the owner

1. **Adobe XI:** may Phase 1 use the existing Wine/Xvfb Acrobat sandbox? It has been off-limits recently. If not, Adobe is deferred and the benchmark runs three tools.
2. **FineBooks images:** prefer IA original-capture JP2 (300–500 ppi, needs a registration check) over the dataset WebP? Proposed: yes, with WebP as a fallback flagged `lossy-origin`.
3. **Quiver GT licence:** accept the conservative CC-BY-SA-4.0 reading? This only matters if GT-derived files are ever redistributed; we don't plan to.
