# Answer ledger

Scope: frozen 32-page development corpus, base `0ca94ae`. Evidence identifiers refer to `object-inventory.json`, `byte-accounting.json`, `page-layer-summary.csv`, `region-results.json`, `layer-results.json`, `component-results.json`, `experiment-results.json` and the engineering report. ANSWERED is bounded to these artifacts; it is not knowledge of proprietary internals.

## Provenance, structure and separation

| ID | Question | Disposition | Evidence / limitation |
|---|---|---|---|
| P1 | Are source/comparator identities, membership and settings frozen? | ANSWERED | Original manifests checked; 32 matched input and original input hashes checked. `run-manifest.json`, `provenance.json`; no historical output overwritten. |
| P2 | Is current ordinary ScanWeave the audited Q100 result? | ANSWERED | Fresh main build/conversions compared by exact collection hash in `current-verification.json`; timing unavailable for recovered historical receipt is disclosed. |
| P3 | Are original capture DPI and placed resolution distinguished? | ANSWERED | Common inputs place images at nominal300 DPI. Original photograph/book capture DPI is unavailable; PDF CTM resolution and JPEG density metadata are separate. |
| S1 | What objects paint every page? | ANSWERED | Recursive paint graph and state references for all32 pages in all6 arms. Text operators/fonts, paths, images, Forms, inline stencils, clips and masks retained. Operator history is not an alternative renderer. |
| S2 | What are exact image bytes and effective resolutions? | ANSWERED | Unique indirect raw-stream bytes; CTM/UserUnit axis DPI. Inline payloads are recorded separately inside content, not assigned an invented compressed-byte share. |
| S3 | What do masks/transparency do? | ANSWERED | Archive's32 soft masks select colour images; Adobe's28 inline stencils paint current colour. No Adobe indirect SMask/Mask. Parent links and mask dependencies recorded. No explicit opacity/blend overrides observed in this corpus. |
| S4 | Can isolated parts reconstruct the rendered page? | ANSWERED | 32 converter/page cases ×2 renderers: original-order tagged replay pixel-identical. Font/nonfont/images derivatives and selected individual image/mask views are actual PDFs/renders. Simple RGB addition is not asserted. |
| S5 | Is semantic role always established? | ANSWERED | No: mixed-raster/unclassified is retained, rather than calling an image 'paper' by area. ScanWeave writer-role metadata, direct stencil/soft-mask structure and observed source regions support narrower roles where available. |
| S6 | Are exact duplicated resources versus placements distinguished? | ANSWERED | Encoded/decoded hashes, referencing pages and placements retained. Current SW2385 image payloads have distinct encoded hashes; no byte saving from duplicate image payloads is demonstrated. |
| S7 | Are non-font drawing operations separated from fonts? | ANSWERED | Adobe80 non-font paint operations; NARA53 stroked line segments. SW32 non-font paints include page-background fills. Compressed operator bytes cannot be allocated independently from the stream. |

## Adobe XI questions

| ID | Question | Disposition | Evidence / limitation |
|---|---|---|---|
| A1 | Background resolution on each page? | ANSWERED | 22pages have ~150DPI tier; 140 image placements are300DPI. Ten pages have only300DPI images. Per-page/object rows list actual values; not every150DPI pixel is semantically paper. UI600 is not emitted DPI. |
| A2 | Paper texture retained/reduced/flattened/removed? | ANSWERED | Historical and receipt fixed crops retain gradients/stains but smooth fine texture; not universally flattened/white. Source-relative metrics and independent visual review. Exact production mechanism unknown. |
| A3 | Which regions remain near source resolution? | ANSWERED | 300DPI objects/compound clips in graph; individual history02/04 image components show selected book edges and residual unsupported detail. Native means nominal matched input300, not unknown capture DPI. |
| A4 | Photos/illustrations preserved at higher quality than paper? | SUPPORTED INFERENCE | Selective300DPI objects and artwork crops support spatial distinction; all Adobe JPEGs still use4:2:0/coarse quantization. 'Higher quality' is not guaranteed; mixed-artwork detail is softened. No standalone photograph resource should be invented inside a mixed compressed image. |
| A5 | Encoding of rules, ornaments and stamps? | ANSWERED | NARA53 non-font stroked paths; signatures remain raster. Historical ornament/stamp fixed crops and image clips retain their content with smoothing. Inline stencils also exist; roles are object-specific. |
| A6 | Are masks present and what do they select? | ANSWERED | No indirect image masks/soft masks. 28inline one-bit stencils paint current colour; compound path clipping selects native-tier JPEG content. These are different mechanisms. |
| A7 | What happens to unrecognized text/handwriting? | ANSWERED | Unsupported text fragments and NARA signatures visible in non-font images. Other recognized original lettering can enter fonts. No universal all-handwriting-raster claim. |
| A8 | Are source ink fringes retained under visible glyphs? | UNRESOLVED | Text-shaped residual patterns remain in history02's non-font layer, but original fringe versus bleed-through/faint print cannot all be classified. Missing measurement: verified source-pixel ownership for the same glyph footprints. Obtain by manual source/layer evidence, not a rectangular mask or pristine font fed to conversion. |
| A9 | Do glyphs replace source image content or only overlay? | ANSWERED | Font-only/non-font comparisons show substantial print removed from images, especially history04 and NARA. Some residual raster remains. This establishes emitted representation, not Adobe's reconstruction algorithm. |
| A10 | Show-through, stains, faint marks and coloured annotations? | ANSWERED | Broadly retained in fixed historical/receipt/stamp regions, with changed texture, colour and local contrast. Some distinctions are visibly degraded; no blanket preservation certification. |
| A11 | How much saving is resolution versus encoding? | UNRESOLVED | Exact retained bytes are measured, but causal savings interact with ink removal/clips/JPEG quality. E2 isolates one whole-page150DPI control, not Adobe's strategy. Need matched same-information source/Adobe layers at both resolutions with verified ownership to separate effects. |
| A12 | Visible damage accompanying small size? | ANSWERED | Softer stamp/illustration detail, smoothed texture, changed small heavy glyph shapes/counters in inspected regions. Some differences include physical placement/sampling; they are not all erasures. Source is preservation reference, not pristine typography truth. |

## OCRmyPDF questions

| ID | Question | Disposition | Evidence / limitation |
|---|---|---|---|
| O1 | Single original page-image role or extra imaging layers? | ANSWERED | One full-page indirect image each of32pages, plus invisible OCR Form. No added foreground/background/mask layer on these artifacts. |
| O2 | Filters afterO3? | ANSWERED | All32 images Flate, predictor15; no DCT/JPX/JBIG2/CCITT. |
| O3 | Dimensions, colours and sampling changes? | ANSWERED | Same image dimensions/300DPI placements; RGB8 source becomes Indexed RGB with5–40palette entries, 29four-bit/3eight-bit images. No JPEG chroma sampling applies. |
| O4 | Primarily lossy re-encoding of the same full page? | ANSWERED | Yes, specifically colour/tonal quantization plus index packing; not JPEG and not segmentation. E1 separates lossless packing of already-quantized samples from their upstream loss. |
| O5 | Downsampling or recompression? | ANSWERED | No image-dimension/placed-DPI downsampling observed. Sample representation changes and compression are measured. |
| O6 | Changes input→O1→O3? | ANSWERED | O1 raw image streams identical to input; O3 palettes differ. The full raster payload changes81,951,978→15,169,365B. Invisible OCR Form streams remain the same betweenO1/O3. |
| O7 | Visible raster text plus invisible OCR? | ANSWERED | PDFium text modes3 only and actual font-only derivatives blank. Native visible character counts0. This does not imply OCR correctness. |
| O8 | Do faint marks/small glyphs/rules/graphics survive? | ANSWERED | Fixed regions retain many readable marks and amount digits, while colour/tonal distinctions change. Posterization and local-contrast failures are documented; not all source detail survives unchanged. |
| O9 | Materially degraded document? | ANSWERED | History02's coloured/shaded book edge and cord00 photographic background visibly posterize; history04 stamp becomes mottled/darker. These losses block blanket adoption despite readable text. |
| O10 | Gain without segmentation? | ANSWERED | Complete PDFs81,969,566input→15,315,903O3 at unchanged spatial resolution. This is achieved with fewer colour/tonal samples; it is not preservation-safe gain for all source information. |
| O11 | Did JBIG2 cause the gain? | REFUTED | Archived logs explicitly lack optional jbig2; actual PDFs contain no JBIG2 resources. |
| O12 | Are OCR/optimization/PDF-A effects mixed? | ANSWERED | Frozen commands use output-typepdf, not PDF/A. O1 versusO3 retains same OCR extraction and forms while changing image data. No additional OCR run or PDF/A counterfactual is needed to establish this. |

## Region preservation and gap attribution

| ID | Question | Disposition | Evidence / limitation |
|---|---|---|---|
| R1 | Are major non-font content classes compared? | ANSWERED | Fixed source-selected paper, shade, captured photographic background, illustration, rules, seals, signature/title lettering, bleed-through, unsupported print and vector/exception regions; all32 page overviews. Classes can overlap; their compressed bytes are not apportioned by crop area. |
| R2 | Can statistics certify every meaningful mark? | REFUTED | Contrast/component errors include phase and font changes. Human-readable crop review is retained, and no globalSSIM/PSNR approval used. No oracle asserts ambiguous faint marks are disposable. |
| G-A | Same-information codec gap? | UNRESOLVED | E1 exactly demonstrates130,326B Indexed-versus-expanded-RGB saving for the same O3 palette pixels. Acceptable original-source information versus Adobe's codecs is not isolated; need matched verified samples/encodings before general savings attribution. |
| G-B | Resolution gap? | UNRESOLVED | E2 measures1,700,529B saving on a controlled page with detail loss. Exact Adobe-only resolution contribution remains entangled with changed samples/ownership and quality. |
| G-C | Representation gap? | SUPPORTED INFERENCE | Adobe clip-selected resolutions/vector rules and archive native-resolution JPX+soft-mask structures are observed. Their causal byte advantage is not isolated with equivalent source-preserving layers. |
| G-D | Eligibility gap? | UNRESOLVED | Adobe24,142 versusSW6,104 paintable Unicode characters; SWreport5630visible-owned occurrences. OCR/ownership differ, so no per-character or area-based byte attribution. Need identical qualified occurrence sets and source-owned residuals. |
| G-E | Exception gap? | ANSWERED | 2353exceptions/5,541,808B; no exact duplicate payloads. Full serialized residual511,687B is an upper budget, not proven patch-only overhead. Equivalent safe mask/atlas savings not established; earlier negative controls stand. |
| G-F | Preservation-loss contribution? | UNRESOLVED | Local losses demonstrated, but bytes of an individual lost mark/texture inside a compressed image cannot be priced separately. A matched controlled representation retaining those exact marks would be required. No additive causal waterfall. |
| E1 | Does palette packing alone save bytes? | ANSWERED | Actual626,075 versus756,401B PDFs, identical pixels in both engines. Quantizing original source is separately rejected by source evidence. |
| E2 | Does blanket150DPI close the gap safely? | REFUTED | Actual1,042,477B control softens detail; renderer-dependent contrast failures. Still1,012,382rasterB versusAdobe88,569B on history02. |

## Required closing conclusions

| ID | Question | Disposition | Evidence / limitation |
|---|---|---|---|
| C1 | Why is Adobe smaller? | ANSWERED | More visible reconstructed typography, removed source print,150/300clip-selected JPEG imagery with4:2:0/coarse quantization, vector rules/stencils. It represents less scan detail as well as using a different structure. Exact additive causal shares remain G-A…G-F limitations. |
| C2 | Why isO3 smaller without visible fonts? | ANSWERED | Full-page RGB→small Indexed palettes and Flate/predictor packing at the same spatial resolution. It discards tonal/colour information, not just smarter encoding of identical original samples. |
| C3 | Where areSWnon-font costs? | ANSWERED | 35,763,822Bwhole pages;5,541,808Bexceptions;1,589,328Bpaper. All can contain non-vectorized text; none is automatically 'non-text'. |
| C4 | Which Adobe techniques are observable/reproducible? | ANSWERED | Standard PDF DCT, clipping, multi-resolution placements, inline stencils, vector rules are reproducible formats. Safe ownership/quality selection is not established merely by observing them. |
| C5 | Which savings are unacceptable/risky? | ANSWERED | Coarse palette colour/texture damage, unprotected150DPI softening, altered fine stamp/illustration/glyph detail. No blanket approval for competitor trade-offs. |
| C6 | Are exceptions too conservative? | UNRESOLVED | Actual cost and retained fine detail support preserving them. No independently safe ownership/representation counterfactual demonstrates unnecessary exceptions. Next measurement would compare the same protected source samples, not reduce acceptance thresholds. |
| C7 | More JPEG optimization worthwhile? | SUPPORTED INFERENCE | No high-value safe gain demonstrated beyond currentQ100. Adobe's4:2:0/quantization illustrates lower bytes with losses. Do not initiate another global quality search on this evidence. |
| C8 | Segmentation, masks, resolution, codecs or combination? | SUPPORTED INFERENCE | Largest conditional opportunity is spatially selective representation with verified protection, not one globalcodec. Archive demonstrates native-resolution masks; Adobe uses clips instead. No genericMRC or newcodec is implemented. |
| C9 | What improves independently of fonts? | ANSWERED | Exact small-palette sample packing can preserve samples; residual-resolution selection is conditional on ownership. Former has small actual239,570Bresource budget; latter targets35.76MB but no safe saving qualified. |
| C10 | Attainable savings under preservation requirements? | UNRESOLVED | No new large production-safe saving qualified.130,326Bsame-palette saving is proven on the control, not on original ScanWeavepatches.239,570B is a resource budget, not promised saving. Need the bounded next trial specified in the report; do not label the1.70MBunprotected control safe. |

No unlisted internal Adobe mechanism is claimed. No finding is silently converted into a production implementation. The research PR is for evidence review, not automatic merge.
