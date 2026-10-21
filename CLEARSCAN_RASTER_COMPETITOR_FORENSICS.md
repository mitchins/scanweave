# ClearScan raster competitor forensics

## Finding and decision

**Adobe stores less scan information and uses a more selective representation. OCRmyPDF -O3 on this corpus primarily reduces colour/tonal information, then packs it efficiently; it does not downsample or use JPEG/JBIG2.** Neither saving is an unconditional preservation target.

No production change is included. The two completed shadow controls do not qualify blanket palette quantization or whole-page 150-DPI encoding. Independent review found visible posterization/colour loss in O3, texture/detail smoothing in Adobe, and softened detail in the 150-DPI control. The working font, ownership, faithful and compression paths remain unchanged.

Start: local and fetched remote `0ca94aecd74c35ea1b28bcebe7e11e863aae7f08`. Research branch: `research/raster-competitor-forensics`. No sealed holdout or pristine font oracle was accessed.

## Provenance and method

The same frozen five collections contain 32 pages: ten CORD receipts, five OCR-D historical pages, thirteen Ipswich financial pages, two mixed pages, two NARA forms. These are **development pages**, not 32 independent documents. Membership and licences remain in `qualification/pdf_packaging/{groups,corpus}.json` and its attribution directory.

The audit revalidated the packaging/tonal manifests and all 32 matched input PDF hashes, plus original input hashes. `provenance.json` distinguishes immutable artifact checks from the historically recorded executable that subsequent builds replaced. No historical converter output was regenerated or overwritten. New ordinary main conversions go only into ignored `local/current/`; exact collection hashes are in `current-verification.json`.

Frozen reference commands/version receipts are in `run-manifest.json`: Acrobat XI Pro 11.0.20 ClearScan (UI downsampling selection **600 DPI**); OCRmyPDF **17.13.0**, `--jobs 1 --output-type pdf -O1/-O3`; archive-pdf-tools **1.5.7**, requested `--mask-compression ccitt`. That last flag is **not** evidence of the serialized codec: the actual archived PDFs have Flate soft masks. All archived O3 collection logs report missing optional `jbig2`; no audited resource uses JBIG2. Current tool versions and availability are separately recorded, not substituted for historical versions.

`inspect_pdf.py` records recursive Form traversal, image and mask dependencies, inline images, CTMs, page boxes/rotation/UserUnit, clipping paths, graphics/text operator histories, opacity/blending declarations, palettes, ICC references, JPEG sampling/quantization, encoded hashes/bytes and decoded sample hashes. It is a forensic record, **not a replacement PDF renderer**. Intrinsic original scan DPI is unknown for photographed receipts/book captures; all common input image placements are nominal 300 DPI. JPEG density metadata, where present, is not substituted for PDF placed DPI.

All 32 pages × six arms × two engines are compared at 100 DPI (**384 page comparisons**). Fixed source-selected regions on eleven pages are measured at 300 DPI (**304 region/arm/renderer records**). Source dimensions choose crop coordinates; no candidate-specific resizing, glyph fitting or alignment is performed. Slight competitor page-box differences are recorded. Whole-page metrics use only the shared top-left physical-coordinate overlap, with omitted source/output pixels counted explicitly. Detailed fixed regions have equal crop canvases.

Local contrast witnesses, component counts, colour changes and edge errors are diagnostics, **not counts of erased meaningful marks**. Fixed-point contrast can change because of glyph reconstruction, placement or sampling. Visual source evidence is necessary. There is no pristine typography truth for these pages.

## Complete PDF sizes

| Collection | Input | Adobe XI | OCRmyPDF O1 | OCRmyPDF O3 | archive | ScanWeave Q100 |
|---|---:|---:|---:|---:|---:|---:|
| Receipts | 16,636,741 | 915,781 | 16,651,046 | 3,043,695 | 400,705 | 6,945,090 |
| Historical | 46,826,111 | 1,682,427 | 46,850,005 | 5,802,054 | 616,324 | 24,637,206 |
| Financial | 12,861,431 | 718,276 | 12,901,665 | 5,166,004 | 1,283,825 | 9,782,629 |
| Mixed | 4,351,051 | 235,999 | 4,371,276 | 788,537 | 358,410 | 3,228,942 |
| Forms | 1,294,232 | 625,620 | 1,319,579 | 515,613 | 400,384 | 859,524 |
| **Total** | **81,969,566** | **4,178,103** | **82,093,571** | **15,315,903** | **3,059,648** | **45,453,391** |

ScanWeave is 10.88× Adobe and 2.97× O3. These are complete collection PDFs with shared fonts, not summed independently serialized page PDFs.

## What actually paints the pages

### Adobe XI

There are **162 indirect JPEG images**: 107 direct DCT streams and 55 outer-Flate/inner-DCT streams. All decoded JPEG headers show **4:2:0** sampling; their quantization tables are recorded individually. There is no JPX, JBIG2 or CCITT image in these Adobe PDFs, and no indirect image mask or soft mask.

There are also **28 small inline one-bit stencils**. These paint the current colour directly; they are not masks selecting another JPEG. Their dictionaries, source payload hashes, CTMs and clips are inventoried. Their payload is inside compressed page content: its incremental serialized byte cost cannot be separated exactly from the surrounding compressed operators. It is **not** double-counted as an independent image stream.

**Twenty-two pages have a roughly 150-DPI image placement; 140 placements are 300 DPI.** `page-layer-summary.csv` identifies every page/object/resolution. Ten pages have only the 300-DPI image tier; 600 in the UI is not the observed emitted background resolution. Some native-tier objects are full-canvas images selected by compound clips, rather than small separately cropped patches. Their encoded cost belongs to the complete stream, not the area of its visible clip.

Example: historical collection page index 2 (`history-02`) has image **31 0**, 840×1145, about 150 DPI, **18,874 B**, plus **32 0**, 1680×2289, 300 DPI, **69,695 B**. Both have full-page CTMs; the latter is selected by a compound path. The lower-resolution image retains paper/bleed-through and visibly softened texture. Selected higher-resolution regions preserve book edges and unsupported details. See isolated component PDFs/renders in `component-results.json`.

Non-font paths are real content: **80 non-font paint operations** overall, including **31 + 22 stroked line segments on the NARA pages**. The forms' rules can therefore be PDF paths while their signatures remain raster. This is not a generic image-only MRC page.

Font-only/non-font renderings show that substantial printed ink is superseded, rather than the entire original scan merely being hidden beneath fonts. However, `history-02`'s non-font image still contains text-shaped faint patterns. Some coincide with bleed-through or unsupported print. Without a clean paper/source-ownership oracle, assigning every residual to obsolete fringe would be unjustified. This milestone does not infer Adobe's internal segmentation/inpainting algorithm.

### OCRmyPDF O1/O3

O1 preserves all **32 matched-input Flate image streams byte-for-byte**, totaling **81,951,978 B**. It adds invisible OCR through 32 Form XObjects. O3 likewise has one full-page image per page and an invisible OCR layer, but changes the images to **Indexed DeviceRGB palettes with 5–40 colours**, using **29 four-bit and three eight-bit** index images, Flate and PNG-style predictor 15. Dimensions and 300-DPI image placements remain unchanged.

O3 raster payload is **15,169,365 B**. This is not DCT re-encoding, resolution reduction, visible font reconstruction or JBIG2. A major causal change is fewer represented colours/tones; the Indexed/predictor representation provides same-sample savings. The installed frozen-version open-source optimizer defaults O3 PNG quality to 30 (quantizer range 20–40); the emitted palettes and source-relative images provide direct evidence independent of that implementation detail. This is normal PDF output, not a PDF/A conversion comparison.

PDFium reports zero paintable non-space text characters for O1/O3/archive and invisible text for all three. O1/O3 have identical extracted-text hashes per renderer; native Poppler/PDFium extraction differs on nine pages in both arms. Those are existing transport/reading-order differences, not evidence that visible text disappeared. No annotation was passed to conversion.

### archive-pdf-tools control

Actual structure is **64 JPX colour images plus 32 one-bit Flate soft masks**, all placed at 300 DPI. On each page, a soft mask selects a colour image above an unmasked colour image. Colour layers can carry much less high-frequency information while the mask carries boundaries. This demonstrates a layered representation at native placement resolution; it does not prove the layers retain all original tones or that ScanWeave can safely reproduce its masks. No lossy JBIG2 symbol substitution is present.

### ScanWeave

There are **2,385 indirect images**: eight DCT and 2,377 Flate. Existing reports bind resources to actual writer roles. All 32 fresh-main patch/role records match the frozen sidecars exactly (`role-verification.json`); their hashes are recorded in `run-manifest.json`:

| Role | Objects | Encoded bytes |
|---|---:|---:|
| Native whole-page mixed content | 19 | 35,763,822 |
| Native exceptions | 2,353 | 5,541,808 |
| Reduced paper | 13 | 1,589,328 |
| **All raster** | **2,385** | **42,894,958** |

Whole-page resources alone are 78.68% of complete PDF bytes. Reduced paper placements are 75 DPI on nine pages and 150 DPI on four; native placements are 300 DPI. These are roles from compositor provenance, not semantic classifications inferred from area. Whole-page and exception resources include unreconstructed text and meaningful marks.

All 2,385 encoded image hashes are distinct within their documents: **zero duplicate encoded payload bytes** are demonstrated. Matching decoded sample hashes with dimensions, bit depth, colour interpretation, Decode and mask properties also finds zero compatible duplicate groups (`reuse-accounting.json`). Further exact-resource deduplication cannot close this corpus gap. Fragmentation has overhead, but the entire remaining serialized residual is 511,687 B, far smaller than whole-page raster cost; it cannot be attributed entirely to patches.

Exact colour inspection finds **973 native exceptions containing at most 16 RGB colours**, encoded cost **239,570 B**, including **47 two-colour exceptions totaling 1,097 B**. These are existing exact samples, not binarization candidates. All whole-page resources have more than 16 colours. Lossless small-palette packing might help a subset, but even erasing the entire 239,570-B budget would save only 0.53% of the document total. No measured codec saving for those actual patches is claimed.

The product reports **5,630 visible-owned occurrences**. PDFium separately exposes **6,104 paintable non-space Unicode characters**, versus Adobe's 24,142. These are different measurements (glyph/Unicode ownership, ligatures and OCR differ), not a one-to-one same-character coverage oracle. Current Linn/forms outcomes and receipt numeric search remain represented by the unchanged frozen outputs; no reconstruction improvement is claimed.

## Exact byte accounting and the non-additive gap

`gap-accounting.csv` and `byte-accounting.json` count each indirect stream once at document level. Page references include mask dependencies and flag sharing; page-reference totals are not silently added across shared resources. Non-font drawing and inline stencils share compressed content streams with other operators, so no invented separate compressed-byte allocation is made.

| Component | Adobe | ScanWeave |
|---|---:|---:|
| Indirect raster streams | 2,522,447 | 42,894,958 |
| Embedded font programs, visible/invisible/shared | 1,271,447 | 1,632,820 |
| Remaining streams and serialized residual | 384,209 | 925,613 |
| **Complete PDF** | **4,178,103** | **45,453,391** |

Adobe's raster comprises 173,057 B of reduced-tier resources, 1,291,825 B of clipped 300-DPI resources and 1,057,565 B of other 300-DPI resources. This does **not** imply downsampling saves only 173,057 B: that is a retained cost, not a counterfactual saving.

The measured raster difference is **40,372,511 B**. Font-program difference is **361,373 B**; everything else differs by **541,404 B**. These accounting differences are additive; their *causes* are not. Downsampling, ink removal, palette quantization, JPEG quality and masks interact.

- **Codec:** the identical-pixel palette control below isolates one storage difference. Same-resolution encoding of the original acceptable source information has not been shown to approach Adobe's bytes.
- **Resolution:** the whole-page control isolates one concrete 300→150 change, with detail loss. It is not Adobe's protected-region strategy.
- **Representation:** Adobe clips and vector rules, and archive's soft masks, are directly observable. Their separate causal savings need ownership-qualified matched counterfactuals; unavailable here.
- **Eligibility:** Adobe paints substantially more characters. Its OCR differs; no valid byte attribution follows from area or character-count ratios.
- **Exceptions:** 5,541,808 B is their actual cost, not avoidable waste. No exact duplicate payloads remain. Earlier atlas/stencil failures remain rejected.
- **Preservation:** visible competitor losses are demonstrated below, but their bytes cannot be priced independently inside a jointly compressed image.

## Two completed shadow controls

Both use `history-02`, preserve current font resources/placements/searchable operators, and emit actual one-page PDFs. They are **not product modes**. Both renderers are measured at 300 DPI in fixed coordinates. All four PDFs pass qpdf; decoded non-image streams, page geometry and both native text extractions are identical (`control-validation.json`).

| Control PDF | Complete bytes | Raster bytes |
|---|---:|---:|
| Current page, reserialized common writer | 2,743,006 | 2,712,909 |
| E1: O3 palette pixels, expanded RGB/plain Flate | 756,401 | 726,306 |
| E1: identical pixels, Indexed/Flate predictor15 | 626,075 | 595,816 |
| E2: current whole-page raster reduced to 150 DPI, Q100 4:4:4 | 1,042,477 | 1,012,382 |

**E1:** Indexed plus PNG predictor15 saves **130,326 complete-PDF bytes** (17.23%) versus expanded RGB with plain Flate, with pixel-identical Poppler and PDFium results. The predictor differs: this isolates a same-information representation/encoding combination, **not the palette-only contribution**. That is a genuine same-information storage gain **after** O3's quantization. The remaining large reduction versus the current page comes with already-quantized image information. The book corner becomes posterized, with dark tonal gradients and green spine colour damaged. **Reject blanket source palette reduction.**

**E2:** the complete page saves **1,700,529 B** (62.0%), but softens small text/book-edge detail. Fixed text-region dark-contrast witnesses below half rise from 0 in baseline to 40 in PDFium and 600 in Poppler; these counts indicate sampling sensitivity, not 600 erased letters. **Reject blanket whole-page downsampling.** At 1,012,382 raster bytes it still does not approach Adobe's 88,569 image bytes on that page. No source-ownership assumption was used to erase content.

Counterfactual page serialization is the same pikepdf writer in every arm; it is not presented as a new native ScanWeave output-size benchmark. `experiment-results.json` and hash-addressed local PDFs preserve the exact controls. No further encoding setting was searched.

## Preservation findings

All completed pages were inspected in overview; fixed regions retain nearby context and both-renderer measurements. Independent review inspected receipts, history-01/02/04, financial text, artwork, Linn, NARA and both controls.

- **History-02 / cord-00:** O3 posterizes photographed/shaded background, including coloured book-edge information. Adobe keeps colour but smooths texture. ScanWeave is closest to the original samples in these inspected regions.
- **History-04 stamp:** wording and circular outline remain visible in Adobe, but fine stamp detail is softer. O3's seal becomes mottled/darker. Source-like preservation is not established by its low byte count.
- **History-01:** Adobe removes fine paper texture and changes some small heavy glyph shapes/counters. These are not qualified restoration wins without pristine truth.
- **Cord-05:** no obvious amount/decimal disappearance was found in the inspected fixed crops, despite meaningful pixel/contrast changes. This is not proof of all-number correctness.
- **NARA:** many rules become vector paths; signatures and unsupported marks remain image content. Some raster-only fine lines are lighter than in the complete drawing-plus-raster page. Do not mistake font-only or images-only isolation for the complete document.
- **Mixed artwork and title:** illustration detail, original lettering and nearby text are compared independently. The title is hand-drawn-looking printed source content; its authorship is not asserted as handwriting truth.
- **Bleed-through, stains, shading:** broadly retained in all arms, with changed texture/tonality. Not every faint pattern can be classified as meaningful writing rather than damage; uncertain content must not be erased merely because OCR ignored it.

There is no universal content-loss approval. Review sheets are evidence for these fixed examples, not a guarantee on unknown documents. Source-relative statistics and visual judgments are kept separate in `region-results.json` and `INDEPENDENT_REVIEW.md`.

## Prioritized next product proposal (not implementation)

### 1. Ownership-qualified residual-resolution representation — largest conditional opportunity

Target the **19 whole-page resources / 35,763,822 B**, beginning with history-02/03 and one photographed receipt. Adobe's clipped 150/300-DPI resources and archive's colour-plus-mask structure establish that different detail classes can coexist compactly. E2 supplies a measured **1.70-MB page-level upper control saving**, **not safe recoverable savings**. Safe bytes remain unmeasured; no fraction of the whole 35.76 MB is promised.

Use the current PDF assembler: lower-resolution paper/illumination plus native samples for independently verified fine text, marks and artwork. First qualify those protection regions against complete source evidence; do not rely on OCR rectangles or reopen shaded-paper font reconstruction. A subsequent bounded trial should retain full native detail in the existing fixed faint-mark regions and evaluate all transition boundaries in both engines. Reject any lost mark, halo, excessive source changes, larger complete PDF or material search regression. If ownership cannot be established, stop rather than build a generic MRC pipeline.

Required changes would be limited residual-resource/ownership selection and serialization using existing codecs. Runtime/memory impact is **not measured**: at least one additional page pass and protection buffer would be needed; existing run receipts show financial conversion is already costly. This direction is independent of improving canonical fonts, but **not yet safe for automatic product adoption**.

### 2. Exact small-palette packing — small, intrinsically preservation-safe candidate

Target the **973 ≤16-colour exception resources / 239,570 B budget** recorded by object. Retain every RGB value, location, mask, Decode and placement; represent exact samples using Indexed RGB and the minimum legal index bit depth plus existing Flate/predictors. This is independent of fonts and spatial segmentation. E1 establishes an actual identical-sample representation/encoding benefit, but on a larger already-quantized image; it is not a measured saving for these exceptions.

A next bounded codec test can evaluate these exact resources without changing samples, using whole-PDF size as selection. Reject any renderer pixel difference, Unicode/placement change, unsupported colour-space/mask interpretation, or size increase. Encoding needs a bounded colour lookup and packed-index buffer; actual runtime/peak memory and net bytes must be measured before implementation approval. Its maximum resource budget is only 0.53% of current PDFs, so it cannot be sold as the main gap closure.

**Do not prioritize another global JPEG-quality search.** All four relevant Q100 whole-page controls already underwent guarded qualification. Adobe's much coarser 4:2:0/quantization and O3's few-colour reduction show possible bytes, but this milestone does not qualify their losses. Refuse blanket whitening, coarse palette reduction, unprotected downsampling, unsafe bitonal masks and lossy symbol substitution.

## Validation and limitations

Five mechanical instrument tests (approximately 93% measured tool coverage) exercise nested Forms, shared image resources, masks, inline stencils, CTM order, unchanged input bytes, real PDF rendering/ordered replay, page-size differences and generated pipeline outputs. CI uses small generated PDFs, not corpus/oracle access. Full corpus resource inventories, source-relative renders and independent review are separate evidence. Current product equivalence is checked against frozen collection hashes rather than asserted from green tests.

Every numbered Adobe/OCRmyPDF question, causal gap and required conclusion has an explicit disposition in [questions.md](qualification/raster_competitors/questions.md), including unresolved exact preservation/causal attribution. The source is not pristine ground truth, and neither green CI nor isolated layers establish visual correctness on all documents. Existing P01–P08 limitations remain disclosed.

Reproduction, exact version/command/hash records and local artifact references are in [the harness README](qualification/raster_competitors/README.md). Large renders/collection derivatives stay ignored and local. Only compact tooling, accounting, reports and representative evidence are committed. Review/CI receipts are published on [research PR #14](https://github.com/mitchins/scanweave/pull/14); it is not automatically merged.
