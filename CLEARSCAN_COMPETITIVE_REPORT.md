# ClearScan competitive reconstruction and quality recovery

## Delivered implementation

The existing `--profile clearscan` now uses the PDF's actual anisotropic glyph geometry and covered-area calculation for canonical acceptance, suppresses emitted glyph ink before raster composition, preserves source-supported faint residual lines, rejects invalid replacement geometry, retains unsupported micro-observations natively, and supplies independent Unicode for raster characters in partially reconstructed words. The normal CLI and library share this path. Faithful remains independent; its preservation contract is unchanged. No new public reconstruction mode, OCR engine or PDF engine was introduced.

Inspect completed PDFs: [300DPI ClearScan](qualification/clearscan_competitive/300/clearscan.pdf), [600DPI ClearScan](qualification/clearscan_competitive/600/clearscan.pdf), matched [300DPI Adobe](qualification/clearscan_competitive/300/adobe.pdf) / [600DPI Adobe](qualification/clearscan_competitive/600/adobe.pdf), and actual qualified [300DPI searchable raster](qualification/clearscan_competitive/300/searchable-raster.pdf) / [600DPI searchable raster](qualification/clearscan_competitive/600/searchable-raster.pdf). The latter are exported directly from the normal library's existing serialized candidate; their4203546/16320330B sizes match the CLI reports exactly and both pass qpdf.

Starting code: `c20a8a91c1109c31bbf7cfdc5ff1b562f5f05986`. Final measured implementation: `08431a7`. Incremental implementation commits are `59ceb20`, `605186b`, `6c32d7b`, `5f88c66`, `0c6350c`, and `08431a7`; baseline evidence is `4a13e12`. Unrelated untracked sandbox/research work and prior evidence were preserved. The sealed holdout was not used. Exact inputs, PDFs, tool versions and hashes are in [run-manifest.json](qualification/clearscan_competitive/run-manifest.json).

**Measured outcome:** the 300 DPI document is appreciably more faithful and 33.0% smaller than the starting ClearScan output. The 600 DPI fidelity improvement is modest; its PDF grew 50.1% because native uncertain detail is retained. Both remain much smaller than their qualified searchable-raster candidates, but much larger than Adobe. Neither converter improves aggregate pristine-relative accuracy over the original synthetic scan. This is a working integrated improvement, not a claim that the competitive quality objective is fully solved.

## Matched Adobe reference and rendering contract

Acrobat XI Pro 11.0.20 / Wine 9.0 (Ubuntu), isolated Xvfb `:109`. The synthetic inputs were generated natively at300/600DPI with declared physical dimensions; they are not physical scanner acquisitions. The exact eight image pages at each genuine raster DPI were embedded losslessly, without resampling, into image-only PDFs: 1800×900 at300 and3600×1800 at600, each432×216pt. Source manifest order and document membership are unchanged. Acrobat settings read from normal public UI controls: **English (US), ClearScan, Downsample To600dpi**. Adobe actually emitted150dpi reduced backgrounds plus some native patches. PDF Type0C font programs and visible text drawing demonstrate reconstruction; producer/extraction alone were not accepted as proof.

Reproducible landscape selection and confirmation failures required bounded runner corrections. Invalid Searchable Image/image-only attempts were excluded. The accepted300 repeat took97.91s;600 took98.82s. The300 repeat differs in file bytes (37100→38295) but all32 compared rendered pages, extracted text, and raster/font/content payload sizes are identical. Other streams/metadata account for1195B. Reference UI inspection used documented control APIs only; no executable inspection or Adobe resources entered the converter. See [reference reproducibility](qualification/clearscan_competitive/reference-reproducibility.json) and [settings](qualification/clearscan_competitive/reference-settings.txt).

Poppler uses integer physical DPI. PDFium uses `nextafter(dpi/72,0)` for exact-size rendering; ordinary `dpi/72` results are retained separately. The latter can round1800 pixels to1801 and resample the entire page. Earlier fractional-DPI Poppler controls shifted vectors1pixel and have been excluded from headline scores, with their evidence preserved. The untouched image-only PDF also shows Poppler sampling error: raw scan and PDF-rendered scan are distinguished. No candidate is independently resized to its pristine ink box. Translation-only alignment is diagnostic.

Primary glyph fidelity below is fixed-position thresholded ink IoU on **552 nonspace instances**, sharing the same pristine truth and physical cells across all arms. Legacy padded/whitespace-window scores, both rendering grids, grayscale appearance panels, counter/centroid/width diagnostics and per-instance records remain available. The two renderers are never averaged.

## Eight-page 300 DPI scorecard

| Measurement | Source | Adobe XI | Previous ScanWeave | New ScanWeave |
|---|---:|---:|---:|---:|
| Glyph IoU, PDFium exact-size | 0.94516 | 0.90255 | 0.89301 | 0.91080 |
| Glyph IoU, Poppler physical-DPI | 0.85458¹ | 0.75066 | 0.84744 | 0.93046 |
| Moderately damaged glyph recovery, mean PDFium Δ vs raw scan | 0 | -0.01820 | -0.02461 | +0.00429 |
| Confusable visual identity errors, tested448 instances | 0 | 0 | 0 | 0 |
| Visible vector occurrences /552 | N/A | 544 | 280 | 515 |
| Distinct painted outline paths | N/A | 27 | 26 | 51 |
| Canonical replacements / prototype IDs | N/A | not inferred | 278 /27 | 495 /35 |
| Embedded font bytes | 0 | 5,963 | 35,332 | 35,332 |
| Raster payload bytes | 4,120,866 | 17,411 | 917,473 | 622,682 |
| Actual PDF bytes | 4,124,819 | 37,100 | 1,093,038 | 732,603 |
| Nonspace extracted character errors vs known source² | source OCR1 | 13 | 1 | 1 |
| Conversion wall seconds | N/A | 97.91 | 30.10 | 35.44 |
| ScanWeave peak RSS KiB | N/A | not measured³ | 201,448 | 207,412 |

New/searchable-raster size ratio: 0.1743 (4,203,546B candidate). New/Adobe ratio: 19.75×. Vector-owned source ink: 123,760/130,344 pixels (94.9%). Actual image resources: previous281, new62, Adobe10.

Exact serialized byte accounting, new: raster622,682; fonts35,332; content55,074; other streams1,303; overhead18,212. Raster classes: {'residual_background': 582949, 'native_fallback_artwork_unknown': 39733}. Native mixed bytes cannot honestly be split among background, fallback, unknown marks and artwork by assigning compressed bytes proportional to pixel area. Core superseded text has no separate retained dark payload, as directly audited below.

## Eight-page 600 DPI scorecard

| Measurement | Source | Adobe XI | Previous ScanWeave | New ScanWeave |
|---|---:|---:|---:|---:|
| Glyph IoU, PDFium exact-size | 0.97807 | 0.94155 | 0.93798 | 0.94272 |
| Glyph IoU, Poppler physical-DPI | 0.91652¹ | 0.88319 | 0.92348 | 0.92698 |
| Moderately damaged glyph recovery, mean PDFium Δ vs raw scan | 0 | -0.02290 | -0.01624 | -0.01624 |
| Confusable visual identity errors, tested448 instances | 0 | 0 | 0 | 0 |
| Visible vector occurrences /552 | N/A | 544 | 481 | 460 |
| Distinct painted outline paths | N/A | 21 | 45 | 49 |
| Canonical replacements / prototype IDs | N/A | not inferred | 476 /41 | 445 /35 |
| Embedded font bytes | 0 | 5,880 | 52,464 | 52,464 |
| Raster payload bytes | 16,259,502 | 30,036 | 754,225 | 1,153,207 |
| Actual PDF bytes | 16,263,472 | 50,779 | 889,147 | 1,334,401 |
| Nonspace extracted character errors vs known source² | source OCR1 | 16 | 1 | 1 |
| Conversion wall seconds | N/A | 98.82 | 66.55 | 87.11 |
| ScanWeave peak RSS KiB | N/A | not measured³ | 726,608 | 742,876 |

New/searchable-raster size ratio: 0.0818 (16,320,330B candidate). New/Adobe ratio: 26.28×. Vector-owned source ink: 479,523/544,428 pixels (88.1%). Actual image resources: previous80, new250, Adobe11.

Exact serialized byte accounting, new: raster1,153,207; fonts52,464; content66,286; other streams1,335; overhead61,109. Raster classes: {'residual_background': 359328, 'native_fallback_artwork_unknown': 793879}. Native mixed bytes cannot honestly be split among background, fallback, unknown marks and artwork by assigning compressed bytes proportional to pixel area. Core superseded text has no separate retained dark payload, as directly audited below.

¹ Rendered image-only PDF, not the raw sample score in the first row. Source PDFium exact-size equals raw source. Poppler's larger error on Adobe is reproducible and retained; it is not averaged away. The ordinary PDFium600 padded-window diagnostic slightly regresses,0.82361→0.82276, despite exact-size isolated improvement. Renderer dependence remains a real limitation.

² The one ScanWeave error is inherited supplied OCR, preserved independently; Adobe's13/16 are recognition/extraction errors and must not be counted automatically as visual glyph reconstruction mistakes. Native PDFium and Poppler both reproduce supplied synthetic OCR. The bounded six-character identity classifier found0/448 failures per DPI and renderer, with no margin below0.05. This excludes punctuation/kana/style confusions and does not prove arbitrary visual safety. Selected canonical witnesses have0 known identity/style mismatches in the audited assignments.

³ `/usr/bin/time` around the Wine runner does not include the resident Acrobat process, so its small shell RSS is not comparable memory evidence.

At300, the moderate-damage group contains253 instances: PDFium new-minus-source mean+0.00429,173 improve and77 regress;299 initially healthy instances regress on average. At600,549/552 are initially healthy and only3 moderately damaged. There are no heavy-damage (<0.8 source IoU) instances in this eight-page fixture, so it cannot establish broad severe-damage recovery. Independent existing damaged-donor regression renders do improve e/a/8 at300:0.835/0.826/0.910→0.972/0.977/0.966. Those are a separate diagnostic, not substituted for the matched-document aggregate.

## What caused the fidelity gap

### S0–S5 stage evidence

The following are PDFium exact-size means. S1–S3 use unique prototype witnesses per page; S0/S4/S5 use actual emitted target occurrences. They are linked but are **not an additive decomposition across different populations**. S1/S2 placed diagnostics, available per occurrence, use the same inferred replacement box without oracle normalization.

| Stage | Starting300 | New300 | New600 |
|---|---:|---:|---:|
| S0 source, accepted set | 0.94286 | 0.94443 | 0.97843 |
| S1 selected grayscale witness | 0.97386 | 0.97279 | 0.97863 |
| S2 binary canonical raster | 0.93802 | 0.94173 | 0.94901 |
| S3 actual embedded vector, nominal witness frame | 0.92519 | 0.94737 | 0.94720 |
| S1 grayscale witness at inferred target frame | 0.97604 | 0.97409 | 0.97503 |
| S2 mask at inferred target frame | 0.93726 | 0.94231 | 0.94438 |
| S4 placed vector, no images | 0.92482 | 0.93453 | 0.94494 |
| S5 final PDF | 0.91413 | 0.91625 | 0.94495 |
| S5−S4, paired target population | -0.01069 | -0.01829 | 0.00001 |

The three largest supported mechanisms are:

1. **Acceptance geometry was wrong.** `convert.rs` used an X-derived scale for Y and a coarse overlap count that admitted tiny horizontal overlaps as covered ink. PDF assembly used independent X/Y scales and anchors. The corrected ClearScan fidelity calculation uses the emitted geometry and actual fractional covered area. This raises300 visible vectors280→515 and physical Poppler glyph IoU0.84744→0.93046. Faithful's existing0.98 contract is preserved through its original wrapper. The previous uniform-scaling idea was not adopted. Crop/anchor transforms and translated text-region width calculations were corrected.
2. **Binary canonical construction discards grayscale edge information.** On paired witness crops, S1→S2 loses about0.031 at300 and0.030 at600, before tracing/placement. The selected donor is often better than the target; thresholding loses that advantage. Grayscale samples/halo are now retained for evidence and antialias ownership. Bounded grayscale contour, resampling, threshold and coverage variants were tested in real PDFs; they regressed and were discarded. No fusion improvement is claimed. The existing robust observed representative remains the best demonstrated internal choice in this round.
3. **Residual edge/compositor interaction remains at300.** Paired S4→S5 loses0.01829, while600 is essentially unchanged. Source-supported unknown fringe/detail retained around vector text can still change edges. The old blanket source-rectangle copy problem is removed: coalesced patches copy the cleaned raster. Dark vector-owned source cores are absent in the actual raster-only render. Remaining residual coverage and rasterizer phase must not be mislabeled as a wrong glyph identity.

A known-original-font outline injection through the existing assembler is preserved as `oracle-assembly.pdf`; its unhinted `TTGlyphPen` reconstruction loses original hinting instructions while the pristine Pillow reference is hinted. The resulting matched515-instance IoU0.8397 is **not a valid proof that pristine design outlines or placement are intrinsically inaccurate**. The independent reviewer then executed a full-original-font control retaining all source programs/global hint tables: 6642247B,515 replacements, matched IoU0.85807 Poppler /0.82821 PDFium. The source fonts have zero per-glyph instruction programs, so lost per-glyph hinting is not the demonstrated cause. Even original full font programs at known nominal positions do not reproduce the Pillow bitmap reference through independent PDF renderers. This exposes an unresolved rasterizer/nominal-placement calibration limit: the remaining IoU gap cannot be assigned wholly to outline geometry. Both control PDFs and per-instance records are preserved. No oracle enters normal inference. Actual nominal/vector, source mask, placed glyph and final layers are independently inspectable.

### Geometry, stroke bias and identity

`geometry.json` records every rendered instance's ink area, threshold counters, bbox displacement, centroid and width proxy. At300, new PDFium ink-area bias is+7.60% versus previous+2.80% and Adobe−2.79%; counter mismatches improve48→5 but stroke thickening remains. At600, new bias+3.76% versus previous+3.39%, and14 counter mismatches remain. Thus higher IoU does not establish unbiased stroke weight or complete serif preservation. The perimeter-based width proxy is not a direct stem measurement.

At300, mean centroid error improves0.304→0.232px in PDFium and0.357→0.164px in Poppler. At600 it improves0.185→0.173px /0.240→0.232px. Individual bbox/centroid differences remain separate from shape-aligned diagnostics. Tiny terminals, punctuation, kana, italic a and serif g/6 remain visibly stair-stepped in enlarged samples. Adobe is smoother but changes weight and some serif detail; smoothness alone is not source fidelity.

The ten best and ten worst families for **each converter and renderer**, with instance counts and gains, are in `family-rankings.json`; the800% sheets show source, pristine, Adobe, previous and new at fixed physical crops. Many “best” family averages remain negative versus the scan. Normal-scale full pages and enlarged examples were inspected; meaningful page content remains coherent, but the remaining contour limitations are visible.

## Canonical reuse and completed ink replacement

At300,552 immutable observations support35 assigned canonical IDs serving495 replacements; additional accepted local vectors bring actual visible text to515 occurrences. The PDF contains51 distinct painted outline paths (55 used GIDs), not515 independent outlines. One canonical a serves58 occurrences over6 pages, including48 healthy and10 donor-repaired occurrences; e serves71 over6pages.600 has445 canonical replacements from35 assigned IDs and460 actual visible vector occurrences. These counts include real variants and conservative excess partitions; not every additional path has been proved a legitimate typeface variant. The fixture has24 underlying nonspace source character/style identities, so cardinality still exceeds the ideal.

Replacement is connected to raster ownership: only actually emitted, finite, nonempty vector placements suppress their source ink. Donor-supported AA fringe removal is bounded by witness coverage and observed intensity agreement. Unsupported micro-components stay native, without invalid zero/reversed geometry or pseudo-glyph outlines. Caller-protected content is retained natively even without OCR; bounds are clamped before copying.

The **actual raster-only PDF audit** finds0 dark(<170) raster pixels within the audited emitted occurrence crops at both resolutions, and0 dark raster/vector overlap. It examines116860 original dark pixels at300 and457285 at600. Source dark pixels not covered by either final vector or raster number744/5443; these differences include contour substitutions and are not automatically missing-content failures. Source-core suppression counters123760/479523 use the converter's ownership masks and therefore differ from this independent threshold count. See `final/ownership-audit.json` and the emitted `raster-only.pdf` / `S4-vector-only.pdf`.

Selective native ridge retention preserves horizontal/vertical thin source marks missed by segmentation; discovery crosses storage-tile seams. The reviewer’s faint250/252-gray line negative retains≈98.6% contrast, with one250→252 rendered endpoint despite byte-exact stored250. Shorter, diagonal or weaker unknown marks are not universally protected by that detector. Photo/artwork/protected patches remain native. A valid page-edge protected sliver previously panicked; the clamped-box regression now passes.

The named300 DPI fallback8 discrepancy was isolated: its stored native samples and geometry are correct; exact-size PDFium reproduces the source crop, while Poppler introduces patch sampling differences. Tiling/interpolation alternatives did not produce a justified correction and were rejected. Source sampling and vector reconstruction must not be conflated.

## Compression and rejected alternatives

F1 exact image reuse and true-gray DeviceGray encoding remain enabled. Reduced residual background alone may use JPEG95/98/100 if decoded max error≤3, MAE≤0.25 and actual encoded saving≥10%; native fallback/artwork/faithful imagery remains lossless. This bounds codec error against the already reduced background, **not** total source-to-reduced-background error. The source-sensitive native ridge/protected paths are therefore necessary.

Blanket native guards around every vector glyph preserved detail but cost994579B at300 and about1.27MB at600. Broad residual tiles captured paper grain and cost4.62MB; connected residuals3.75MB. Both were rejected. The final selective representation reduces300 raster payload917473→622682B, but600 grows754225→1153207B. Background/native mixed classes explain this growth; it is not hidden as an aggregate compression win. Font bytes are unchanged and still not the largest cost. Pipeline timing attributes34.03s/82.07s to page conversion versus0.58s/2.34s donor collection and0.23s/0.42s reconstruction PDF serialization. Grouping/tracing within page conversion are not separately instrumented, so these timings do not prove a specific tracing speedup. Wall-time runs shared the host with validators; memory and exact bytes are more directly comparable than small timing differences. An existing-pixel predictor probe shows negligible additional synthetic saving; no codec/font architecture project was started.

Adobe remains19.75× smaller at300 and26.28× at600, mainly through much smaller raster backgrounds and native-retention decisions, plus compact font programs. Its background/detail trade-offs cannot be copied blindly. Remaining ScanWeave bytes are overwhelmingly raster even after the now-verified source-core removal, so redundant full-resolution text underneath vectors is no longer the explanation for the audited cores.

## Older frozen three-page benchmark

This is compared separately, never against the eight-page output. Values are actual serialized PDFs and PDFium exact-size nonspace glyph IoU.

| DPI | Raw source IoU | Adobe bytes /IoU | Previous bytes /IoU | New bytes /IoU |
|---|---:|---:|---:|---:|
| 300 | 0.98913 | 46,213 /0.86833 | 1,975,585 /0.90246 | 1,680,640 /0.90455 |
| 600 | 0.99460 | 51,429 /0.91427 | 3,360,529 /0.93578 | 3,261,331 /0.95438 |

The frozen Adobe outputs are46213/51429B. Current ScanWeave remains much larger; both converters reduce fidelity relative to this nearly pristine scan. Poppler, PDFium, extraction, font and image measurements are preserved per arm rather than replaced by the eight-page summary.

## Genuine receipt and historical-page verification

Ten CORD v2 **training** receipts and five OCR-D historical pages were obtained and converted with original full-page imagery. Exact sources, hashes, licence/attribution, crop geometry and commands are in `real/ATTRIBUTION.md` and manifests. CORD CC BY4.0 and OCR-D CC BY-SA4.0 derivative conditions are retained. Annotation boxes select OCR text regions; transcription is never supplied to the converter. The existing English Tesseract engine is unchanged. Capture DPI is unknown:300 is nominal geometry here, not asserted genuine300DPI acquisition.

| Page | PDF bytes | Observations | Vector ink px | Seconds | Peak RSS KiB | Native text agrees across renderers |
|---|---:|---:|---:|---:|---:|---|
| cord-00 | 1,525,038 | 167 | 0 | 0.87 | 51,808 | no |
| cord-01 | 1,334,960 | 133 | 757 | 0.50 | 44,828 | yes |
| cord-02 | 365,379 | 157 | 4,739 | 0.30 | 35,672 | yes |
| cord-03 | 1,945,040 | 93 | 135 | 1.82 | 69,136 | yes |
| cord-04 | 825,187 | 44 | 316 | 0.34 | 45,128 | no |
| cord-05 | 6,759,637 | 68 | 0 | 60.54 | 403,424 | no |
| cord-06 | 1,052,788 | 1 | 0 | 1.12 | 51,032 | no |
| cord-07 | 845,801 | 15 | 0 | 0.74 | 48,764 | no |
| cord-08 | 1,321,975 | 46 | 0 | 1.16 | 55,324 | no |
| cord-09 | 1,315,847 | 78 | 6,280 | 0.58 | 45,480 | yes |
| history-00 | 9,642,229 | 262 | 2,586 | 31.58 | 210,220 | no |
| history-01 | 5,106,941 | 240 | 1,697 | 10.38 | 107,084 | no |
| history-02 | 8,197,382 | 9 | 0 | 32.64 | 167,648 | no |
| history-03 | 15,241,848 | 165 | 0 | 87.88 | 446,964 | no |
| history-04 | 10,439,769 | 529 | 3,685 | 44.51 | 204,728 | yes |

All15 ordinary conversions complete and qpdf/OTS checks pass. Photos, woven receipt backgrounds, page stains, decorative initials and native unsupported text are preserved in inspected full-page comparisons. Several pages have no vectorized ink: photographed small text, sparse compatible observations and English OCR on historical typography limit reconstruction. No unavailable pristine-font ground truth is invented. Output lossless native rasters can be larger than the original compressed JPEGs; these samples do **not** establish a receipt compression win.

Real native extraction exposes limitations the simple synthetic input misses. A partially reconstructed word formerly lost unvectorized characters in native PDFium even though Poppler ActualText looked complete. The normal path now interleaves missing character CIDs with visible glyphs in original OCR byte order, preserves independent Unicode, remaps document CIDs, and fits invisible glyph frames using actual font metrics. On all31 pages of the two synthetic documents plus15 real pages, the actual ToUnicode-decoded CID sequence matches nonspace ActualText exactly (`semantic-audit.json`). This is a transport check, not proof that OCR was correct.

Native renderer outputs nevertheless differ on real pages through reading order, underscore positioning and PDFium's U+FFFE hyphen marker (four real pages). This remains a user-visible extraction/search limitation; it is not concealed by whitespace normalization or the correct CID audit. Token-search checks pass, but arbitrary native phrase/numeric search has not been exhaustively established. No real-document reconstruction quality or compression claim is inferred merely from successful parsing/search.

## Mechanical verification and independent review

- Workspace Rust tests pass with two inherited failures excluded and separately reproduced/documented: `m1b_behavior::regress_auto_reports_the_selected_candidate` and `m1d_reconstruction::clearscan_repairs_a_damaged_glyph_from_same_document_donors`. The latter was reproduced on untouched startingc20; current donor expectations are not presented as a new regression. The updated document donor regression passes after actual repaired8 render evidence, not merely changed expectations.
- Fourteen focused IO regressions cover partial Unicode ownership, OCR byte order, semantic font frames, invalid replacement boxes, native micro-observations, no-OCR protected content, boundary clamping and faint-line tile seams. The introduced faithful min-IoU regression was fixed.
- E0–E7 pass, including actual deterministic serialization. Inherited P01–P08 visual gates and P08 native-cardinality failure remain recorded in `probe-results.json`; they are not silently counted as passes.
- All19 current ScanWeave PDFs pass qpdf and unique TrueType font OTS checks. Adobe300 passes qpdf; frozen Adobe600 returns status3 with linearization/hint-table warnings (operation succeeds with warnings), preserved rather than rewritten. All21 PDFs render in both engines. Native PDFium token search is exercised on every page. The final300 rerun is byte-identical (SHA256`515294f52a947153357a30a518f6bf7fb9b4eeb4ed1ed44f9fefd966897df725`).
- Independent review found the semantic ownership/remapping consistent, challenged unqualified unknown-line loss and page-edge panic (both corrected), identified the oracle hinting confound, and required stale scorecards to be refreshed. See `final-review.md`, `oracle-control-review.md`, `review.json` and the retained negative fixtures. The review does not certify arbitrary source fidelity.

## Remaining competitive deficit and next conditional fix

The largest **typography** limiter is canonical contour construction from thresholded scan masks: it loses grayscale edge/serif/weight information before the existing tracer receives the shape. Actual reuse, placement-contract correction and redundant source-core removal are now demonstrated. Additional matching machinery or more dictionary clusters would not by itself correct that measured loss. The grayscale contour variants tested here were worse and were removed; claiming fusion success would be unsupported.

The largest **size** limiter is native uncertain/background raster retention, especially600DPI, not repeated canonical outlines. Any further background reduction must first preserve the concrete faint-line and native-fallback regressions, including short/diagonal low-contrast marks not covered by the current ridge test. Real vector coverage and English historical OCR also remain weak. The next bounded code correction should target a demonstrably better grayscale contour representation on these same witness groups, measured after final rendering, while retaining the corrected compositor and independent faithful path. No CFF encoder, replacement OCR/PDF engine, generalized MRC system or new public experimental profile was begun.

The implemented correction delivers a substantially stronger300DPI conversion and fixes real content/semantic defects. It does not establish aggregate restoration beyond the original scan,600DPI size improvement over the starting converter, or Adobe-level compression. Those are explicit remaining product gaps, not erased by the scorecard.
