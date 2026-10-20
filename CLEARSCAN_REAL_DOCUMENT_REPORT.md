# ClearScan real-document convergence

## Delivered result

Normal `scanweave input.pdf output.pdf` now produces **59,599,260 B** across the established 32-page development corpus, versus **81,309,831 B** previously: **21,710,571 B (26.70%) saved**. It is 27.291% smaller than the matched input PDFs. This is a real-corpus improvement, not extrapolation from synthetic data. It remains substantially larger than Adobe XI and OCRmyPDF -O3.

For personal inspection, start with [Linn's complete PDF](qualification/real_convergence/outputs/scan-linn.pdf), then [CORD-05](qualification/real_convergence/outputs/cord-05.pdf). Linn demonstrates increased vector coverage; CORD-05 demonstrates efficient preservation where reconstruction fails. The former still exceeds its original input size. Neither establishes general reconstruction quality.

Source baseline: `b4387d4` (includes `80b2a42`). Product changes: `5998611`; missing-paint correction: `13288a8`. Initial HEAD/status, executable hashes, exact commands, input/comparator/output hashes and timings are in `qualification/real_convergence/`. Unrelated research material and the sealed holdout were preserved. Faithful's preservation contract and independent profile remain intact.

## Complete same-input comparison

All figures are actual serialized bytes. Document membership and page order match the frozen packaging comparison; comparator PDFs were not regenerated or altered.

| Document | Pages | Input | Adobe XI | Previous ScanWeave | Updated ScanWeave | OCRmyPDF O1 | OCRmyPDF O3 | archive-pdf-tools |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Receipts | 10 | 16,636,741 | 915,781 | 17,870,922 | 11,117,351 | 16,651,046 | 3,043,695 | 400,705 |
| Historical | 5 | 46,826,111 | 1,682,427 | 47,108,340 | 34,546,263 | 46,850,005 | 5,802,054 | 616,324 |
| Financial | 13 | 12,861,431 | 718,276 | 10,488,347 | 9,865,593 | 12,901,665 | 5,166,004 | 1,283,825 |
| Mixed | 2 | 4,351,051 | 235,999 | 4,991,909 | 3,210,072 | 4,371,276 | 788,537 | 358,410 |
| Forms | 2 | 1,294,232 | 625,620 | 850,313 | 859,981 | 1,319,579 | 515,613 | 400,384 |
| **Total** | **32** | **81,969,566** | **4,178,103** | **81,309,831** | **59,599,260** | **82,093,571** | **15,315,903** | **3,059,648** |

`scorecard.csv/json` contains all 35 document/arm records. `page-results.json` contains every page's funnel, two-renderer source deviations, search probes and timings. Document bytes are explicitly document totals, not invented per-page allocation.

## What changed

### Native image import and lossless representation

The ordinary PDF workflow recognizes a deliberately narrow, verified image-only page: one full-page image, `q/cm/Do/Q` operations, matching MediaBox/CropBox, no rotation, UserUnit, annotations, masks or extra painting. Supported source images are 8-bit DeviceGray/RGB Flate or JPEG. Geometry, dimensions, decoding and relevant dictionary properties are checked. A decoded RGB hash and physical transform bind an encoded source resource to the actual conversion input. Arbitrary source resources are not copied.

At matching requested resolution, the CLI uses the image's native samples instead of rendering it through a slightly different pixel grid. This avoids needless changes such as 3301-to-3300 sampling. Unsupported/cropped/rotated PDFs retain the existing Poppler path. A mechanical cropped/rotated control exercised that fallback.

For pages with no emitted vector replacements, the converter skips unnecessary raster cleanup/composition and writes one native image with the available Unicode overlay. Existing source JPEG can pass through unchanged. Source Flate competes with actual lossless encodings; ClearScan chooses the smallest measured stream among no predictor, TIFF and PNG Up predictors. True grayscale and collision-checked resource reuse remain enabled. Faithful retains its previous encoding selection.

On partially reconstructed pages, the same predictor selection reduces native exception costs. A cleaned whole-page alternative is considered only against actual encoded patch costs and needs a 10% advantage; it did not explain Linn's gain. Existing qualified reduced-paper encoding is retained. No new lossy native-patch codec was enabled.

### OCR and avoidable work

The current Tesseract engine compares default PSM 3 with at most two controls, PSM 6 and 11, on four specified receipts. Normal ClearScan retries PSM 6 only for sparse, low-evidence results. It accepts the retry only with a substantial increase in reliable multicharacter words with valid bounded character boxes. Border-only word counts do not qualify. PSM 11 was not selected.

Removed a discarded component-extraction pass in ownership construction. More substantially, zero-vector pages no longer execute expensive cleanup and patch coalescing whose result cannot improve their visible reconstruction. This does not skip searchable owners.

### A real paint omission fixed

An independent content-stream audit found that text emission grouped only contiguous occurrences of a span. A later group for the same span could be skipped. Five NARA digits (`5`, `1`, `9`, `1`, `3`) were therefore counted as replacement proposals but not painted. The writer now collects all occurrences of each span while retaining their order. Forms now paint **500 actual glyph draws**, rather than 495 before this correction. It adds 54 B. Font/image streams and Poppler raw/layout plus PDFium extraction are identical in the controlled comparison. `comparisons/restored-form-digits.png` shows the source, missing paint and corrected paint.

## Representative page diagnosis and outcome

Standalone sizes differ from shared-font collection sizes.

| Case | Previous bytes | New bytes | Main finding |
|---|---:|---:|---|
| cord-00 | 1,500,534 | 898,775 | Still no usable OCR/observations/vectors. Native sample retention and lossless encoding save bytes without inventing text. |
| cord-05 | 7,257,909 | 4,452,414 | 179 OCR characters but one bounded observation and no vectors. Skip expensive unproductive recomposition. |
| history-02 | 7,581,692 | 5,186,194 | 860 characters, only two bounded observations, zero vectors. Severe shaded-paper segmentation failure; retained native raster. |
| history-03 | 14,990,381 | 9,350,337 | 404 OCR characters, 165 observations, zero accepted vectors. Whole-page native imagery dominates. |
| scan-linn | 863,702 | 662,429 | Native sample geometry produces usable evidence; actual visible glyph draws rise **279 → 748**. Remains larger than its original scanned input. |
| nara-form-01 | 449,532 | 453,483 | Real reconstruction retained; five skipped digits fixed. Slight size regression is explicit. |
| nara-form-02 | 402,476 | 407,997 | Reconstruction preserved; no size win over previous output. |

The one-pass original diagnosis is `diagnosis.json`; complete final page funnels are in `page-results.json`. Proposal counts, local accepted occurrences, CID paint operations and PDFium text characters are different quantities. For example Linn has 723 visible-owned occurrence records but 748 painted glyphs. The final corpus has **5,404 actual visible glyph draws**, versus **4,963** in frozen previous PDFs, and 3,489 unique painted GIDs summed per document. These are emitted-font measurements, not a new dictionary score. Reuse and legitimate variants remain document-wide. Real scans have no pristine outline truth; no real IoU improvement is claimed.

### Historical blocker: tested and rejected

History-02 has corner luminance around 40 versus page median around 183. The global foreground/background rule marks roughly 70% of the page as foreground/artwork, preventing ordinary character ownership. A bounded local-background correction recovered hundreds of observations and 27–30 candidate vectors. Actual renders showed overly heavy text and cleanup halos on aged paper, including after a local coverage adjustment. It was rejected; no identity threshold was loosened and the source raster remains. The rejected patch and word comparison are preserved. Thus the glyph-eligibility secondary objective is not solved for this historical case; the receipt search and Linn coverage improvements are the demonstrated secondary gains.

A native-patch JPEG control was also rejected: aggregate maximum/mean pixel limits did not establish faint-mark preservation. It is not in the converter. Previously failed atlas/stencil approaches were not repeated.

## Raster, fonts and remaining bytes

| New payload | Bytes | Resources |
|---|---:|---:|
| Native whole-page images | 49,861,104 | 19 |
| Native exceptions | 5,674,184 | 2,292 |
| Reduced paper | 1,580,345 | 13 |
| **All raster** | **57,115,633** | **2,324** |
| Embedded fonts | 1,572,929 | — |
| Page content | 348,374 | — |
| Other PDF structures | 562,324 | — |

Previous raster payload was 78,923,800 B. Raster still occupies 95.8% of the new PDFs. No inventoried native gray resource is strictly two-valued `{0,255}`; histograms are preserved per object. Uniform or near-white patches are not thereby proven bitonal document content. A mask encoder is therefore not justified by this sample inventory. There is no claimed atlas or stencil saving.

Native-sample audits on cord-00/05 and history-02/03 show zero changed decoded pixels relative to source images. For Linn and both forms, changed native pixels were confined to the audit limits around emitted replacements; no changed pixels outside those limits were found. These rectangles are audit bounds, not erasure masks. The existing source-supported ownership footprint still controls cleanup. Image streams did not change in the final five-digit fix.

Full-page and 300% source/previous/new/Adobe sheets were inspected for text, artwork, faint marks and layer boundaries. New Linn text is coherent but Adobe remains smoother in examples. The rejected historical halos are not delivered. Source-relative renderer differences are recorded separately from semantic/visual judgments; no whole-page MAE is used as sole acceptance. Native import intentionally changes the old resampling phase. These observations are development-corpus evidence, not proof that all subtle marks on unknown documents are preserved.

The 59.60 MB result remains about **14.3× Adobe** and **3.9× OCRmyPDF -O3**. Unsupported shaded/tonal pages and native exceptions dominate; fonts and syntax are secondary. The next priority is qualified shaded-page ownership/eligibility and a controlled compact representation for retained tonal content, rather than another font-system rewrite. That work was not begun here.

## Search, OCR and semantics

Independent CORD annotation-derived financial queries improve **11/49 → 17/49** in both Poppler and native PDFium. Frozen Adobe is 24/49, OCRmyPDF O1/O3 15/49, archive-pdf-tools 13/49. Four query gains are on CORD-01 after PSM 6; native sample import contributes further gains. Configurations were not selected just for word count.

Existing transport probes derived from prior OCR rise 76/84 → 80/84; these are not independent OCR accuracy. CORD-00 remains without recognized text. CORD-06 still has empty PDFium extraction from its narrow border-only owners. Some whitespace-normalized order/hyphen differences remain on 16 pages; per-page results retain them rather than averaging renderers together. No full-corpus text ground truth is fabricated.

## Runtime and memory

| Collection | Wall seconds | GNU-time command RSS KiB |
|---|---:|---:|
| Receipts | 32.17 | 467,456 |
| Historical | 89.66 | 750,564 |
| Financial | 544.28 | 1,384,432 |
| Mixed | 119.22 | 298,212 |
| Forms (final paint correction) | 66.13 | 357,192 |

These are measured command maxima, not an aggregated process-tree PSS peak. Overlapping jobs/tests affect wall time. Financial's parent orchestration was interrupted (143); its child completed successfully (GNU-time exit 0, 9:04.28), with complete PDF/report. This is marked in its run record. No speedup is claimed against its previous approximately 521-second run. Tracing/placement/cleanup remains expensive; detailed stage timings are retained.

A controlled CORD-05 ablation with identical input, OCR and encoding compares forced recomposition with skipping unnecessary zero-vector work: **139.483 s → 6.315 s**. PDF SHA-256 and extracted-text SHA-256 match exactly. Recomposition alone took 130,930 ms in the slow arm. This establishes the focused runtime gain without attributing it to OCR or lossy encoding.

## Regression and review

The normal synthetic eight-page outputs are **185,119 B at 300 DPI** and **258,720 B at 600 DPI**, with 531/517 visible occurrence records. All 16 pages are pixel-identical to frozen packaging-baseline hashes in both Poppler and PDFium at physical 300/600 DPI after the final span correction. Decoded fonts/maps/content and native extraction remain equal; qpdf and OTS pass. Consequently the established synthetic fidelity (.9566875/.9682678 in that evaluator) is preserved, not newly improved. Canonical reuse/background cleanup survive.

The final workspace run passed 107 test executions with the two inherited failing tests explicitly excluded and separately logged. The focused source-import/OCR/predictor/span tests, E0–E7, PDF/font validation, actual extraction, native query tests and independent renders are recorded beside this report. Two inherited Rust failures remain: `regress_auto_reports_the_selected_candidate` and `clearscan_repairs_a_damaged_glyph_from_same_document_donors`; they were separately executed and logged. P01–P08 inherited visual/native failures remain visible in `e0-e7-p01-p08.json`. Prior evidence overwritten by those tests was restored exactly. No failures were silently treated as passes.

Independent code/evidence review challenged native lossy patch qualification, source-image trust/binding, unsafe import cases, misleading glyph-count terminology and the span paint omission. Native lossy changes were removed; strict importer controls, hash/geometry binding and tests were added; emitted glyphs were independently counted; the five-digit omission was fixed and independently rechecked. The reviewer found no remaining blocker in that correction and confirmed final arithmetic. See `independent-review.md`.

## Reproduction and artifacts

See [the run instructions](qualification/real_convergence/README.md), `run-manifest.json`, `scorecard.csv`, `page-results.json`, `measurements.json`, `outline-inventory.json` and individual run logs. Input identities, licences and original attribution remain in `qualification/pdf_packaging/`; this round adds no new dataset or holdout access.

Representative PDFs, synthetic outputs, selected comparison sheets and small controls are committed. The 59.6 MB complete collection outputs and large raw sidecars remain local ignored artifacts with hashes and reproducible commands; they are not silently represented as externally hosted files. They can be regenerated from the established development inputs. This round makes the ordinary converter materially smaller and recovers some real text, while explicitly retaining the historical segmentation and tonal-raster limitations.
