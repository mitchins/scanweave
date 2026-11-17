# STROKE-02 — per-unit segmentation: ownership-reference blocker

**The requested per-unit experiment is blocked by the existing ownership gate.** No new converter behavior was enabled and no 36-page re-run was made. The user explicitly directed that a gate unable to evaluate per-unit masks be reported rather than worked around. The 36-page results below are the **previous trace-stage experiment**, not results of the proposed per-unit segmentation.

`build_plan` labels connected components from page-wide `seg.fg` and assigns each original component ID to exactly one text or artwork unit. `visual_invariant_ok` verifies those IDs and their counts; it does not compare a unit's current mask pixels with the pixels in its assigned components. A focused executable test shows that the invariant still passes when a unit gains an unregistered mask pixel, and also when the altered mask overlaps a separate artwork mask. The separate contact gate uses original artwork bounding boxes: it can reject contacts with *known* artwork, but it has no component records for newly proposed pixels. This test shows the scope of the ownership check; it does not claim that the contact gate would miss every overlap.

The existing 613 region is **already vector-planned**, with three units. Its problem is the fragmented masks and global fill, not wholesale region rejection. On that page the original segmentation has 1,562 components (738 text-owned, 824 artwork). Applying the already-generated line-pooled sidecar at coverage ≥ .5 as a diagnostic proposal gives:

| OCR digit box | Original foreground pixels | Proposed mask pixels | Added pixels outside original foreground |
|---|---:|---:|---:|
| 6 | 34 | 92 | 58 |
| 1 | 10 | 49 | 39 |
| 3 | 23 | 92 | 69 |

All 166 added pixels have original component label zero. The masks are **diagnostic proposals, not validated ground truth**; at this threshold they do not touch one another. Replacing the units' masks after ownership planning would leave these pixels outside the gate's component reference. Rebuilding the page's component map from a patched foreground would instead change that reference and can change which existing pixels are classified as artwork. Either requires an explicit ownership reconciliation that the existing gate cannot perform on its own. I did not silently change the reference or add a substitute gate.

Per-unit paint has a separate, implementable scope: `PageParts` currently carries one `ink`, and `emit_text_runs` sets one fill for the page's visible text. A per-symbol color map passed through `PageParts`, with the fill selected immediately before each visible occurrence and stock ink as fallback, would be needed. The measured global ink is RGB (167,137,90), consistent with the shell-brown diagnosis. Color plumbing alone would not resolve the ownership blocker, so it was not added as an untestable converter change.

The next design must reconcile proposed local pixels with the original foreground/artwork ownership reference while preserving component identity, contact checks, fallback and pixel exclusivity. This is an engineering gap in the current gate, not a claim that local segmentation is impossible. [Numeric evidence](/data/coding/scanweave/work/stroke01/research/stroke02/ownership-evidence.json) and [focused test](/data/coding/scanweave/work/stroke01/crates/scanweave-io/tests/ownership_reference.rs) are available. The source/actual #39/previous experimental PDF strips remain unchanged: [613 1×](/data/coding/scanweave/work/books01/stroke02/final/613-1x.png), [613 2×](/data/coding/scanweave/work/books01/stroke02/final/613.png), [French 1×](/data/coding/scanweave/work/books01/stroke02/final/french-1x.png), [French 2×](/data/coding/scanweave/work/books01/stroke02/final/french.png).

## Previous 36-page trace-stage result

**The real converter did not achieve the text-restoration objective.** All 36 development pages ran successfully. The 613, French list and four controls are byte-identical to #39; no raster-byte displacement or increase in vector-owned ink was measured. Four other pages changed slightly. This is a default-off research measurement, not a merge candidate.

1. **Does 613 beat MRC?** No: the real candidate PDF is identical to #39 and still fragments/discolors the numerals. The earlier crop-only layered prototype looked promising but was not emitted by this converter path. In the actual PDF's 3×3 counter test, one source-near-paper pixel darkens by more than twice the local residual-noise proxy in both #39 and the candidate. Candidate and #39 counter pixels are identical; the existing defect remains. The proxy is not independently calibrated scanner noise.
2. **Are the French letters better without artificial bolding?** No measurable change: the French-list PDF is byte-identical to #39. The earlier crop-only reconstruction is not evidence of improved converter output.
3. **What changed?** A Python pre-pass supplies per-line coverage estimated from OCR character boxes, pooled source-color cores and a local edge-width blur estimate, with an enclosed-paper veto. `SCANWEAVE_STROKE_COVERAGE` enables an experimental converter path that proposes subpixel coverage contours for already vector-eligible, unshared local units. OCR supplies geometry, not glyph shapes. Existing contact, ownership, topology and .98 source-fidelity gates remain in force; a declined candidate returns the stock trace. **This does not retry raster-owned regions**: the planner rejects them before tracing. It also retains stock vector paint rather than the crop prototype's tonal layers. Blur and ink estimates are exploratory, not a calibrated physical fit.

   The pooled crop paint was sRGB (143,141,111); the darkest tenth of observed source cores had median RGB (155,152,128), (169.5,168,135.5), and (166,164,132) for 6/1/3. Their warm hue is source-supported, but the paint is darker and cannot be called true ink without modeling blur.
4. **PDF size, text coverage and cost.** The figures are sums across 36 pages, except medians as marked. Baseline timings are from the earlier sequential BOOKS-01 runs; host conditions were not controlled across batches. Candidate pre-pass time is additional.

   | Measure | #39 | Experimental |
   |---|---:|---:|
   | PDF bytes, total | 16,315,763 | 16,315,054 |
   | Encoded raster bytes, total | 14,696,444 | 14,696,444 |
   | Planned vector / raster units | 5,339 / 17,685 | 5,339 / 17,685 |
   | Vector / total text-ink pixels | 1,093,241 / 33,816,721 | 1,093,241 / 33,816,721 |
   | Conversion wall seconds, sum / median | 985.9 / 20.48 | 1,236.4 / 19.87 |
   | Coverage pre-pass seconds, sum / median | — | 169.5 / 3.54 |
   | PDFium 150-DPI warm render median, median page | 11.65 ms | 11.55 ms |

   Vector area is 3.23% of the converter's **segmentation-derived** text-ink area, which may include segmentation errors. The converter's occurrence labels total 5,027 `visible_tounicode`, 17,997 `invisible` and 50,468 `unmapped` for each run; these are not interchangeable with the region-unit counts. No ownership disposition changed. Thirty-two PDFs were byte-identical. The other four were 9684355, 9684335, 9684354 and 12341934; their changed-pixel fractions at 150 DPI were .000976, .000753, .001151 and .000038 respectively. On 9684355, an additional disabled-path conversion reproduced #39 byte for byte, confirming an experimental-path effect on that page. The report does not enumerate all selected local trace methods, so their exact count is unavailable; zero report-marker mentions does not prove zero selections.

   | Target / control | #39 bytes | Candidate bytes | #39 → candidate seconds |
   |---|---:|---:|---:|
   | 8967062 | 92,310 | 92,310 | 8.53 → 11.48 |
   | 12342014 | 554,944 | 554,944 | 53.66 → 76.74 |
   | 8967228 heading | 161,265 | 161,265 | 23.05 → 22.50 |
   | Aventinus 0008 | 567,928 | 567,928 | 45.25 → 47.40 |
   | Luther 0011 | 441,781 | 441,781 | 4.62 → 4.57 |
   | Euler 0025 | 439,391 | 439,391 | 4.94 → 3.62 |

5. **Regressions and extraction.** PDFium text extraction is exactly equal on every page: zero character, order or ownership-difference findings, and zero new U+FFFE. This particular PDFium extraction counts 113 U+FFFE in each run; the pre-existing bug remains unresolved. The four controls' baseline and candidate PDFs are byte-identical, so their 1×/2× images cannot regress relative to #39. Four non-control PDFs differ visually in small areas; no claim of defect-free glyphs is made for those changes. Mean page-level 150-DPI channel difference across all pages is .00105/255. The prototype incurs extra cost without reducing raster data.
6. **Ready to merge?** No. This path demonstrates the integration boundary: coverage can influence already-eligible local tracing, but cannot recover the raster-owned text where the main opportunity lies. A future design must carry independently validated latent/source evidence through ownership planning while preserving the existing contact and fidelity safeguards, and must prove raster displacement and OCR preservation. No gate was relaxed. Full `scanweave-io` tests passed, including unit-level exact fallback and the existing glyph-sharing parity suite. A disabled-path page was byte-identical to #39.

Real-PDFium strips at [613 1×](/data/coding/scanweave/work/books01/stroke02/final/613-1x.png), [613 2×](/data/coding/scanweave/work/books01/stroke02/final/613.png), [French 1×](/data/coding/scanweave/work/books01/stroke02/final/french-1x.png), [French 2×](/data/coding/scanweave/work/books01/stroke02/final/french.png), [Aventinus](/data/coding/scanweave/work/books01/stroke02/final/aventinus_grammatica_1515_0008.png), [Luther](/data/coding/scanweave/work/books01/stroke02/final/luther_babstum_1526_0011.png), [Euler](/data/coding/scanweave/work/books01/stroke02/final/euler_rechenkunst01_1738_0025.png), and [heading](/data/coding/scanweave/work/books01/stroke02/final/8967228.png). Each control also has a `-1x.png` companion. Adobe's heading registration failed and is marked unavailable.

[Per-page numeric results](/data/coding/scanweave/work/stroke01/research/stroke02/results-pages.json); local artifacts are under `/data/coding/scanweave/work/books01/stroke02/pages/`. Research binary SHA-256: `a946a466ca25a2ca72967ac000241c979ff73389c3f363e3e6923170b2fe5a06`.
