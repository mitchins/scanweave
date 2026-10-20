# ClearScan contour correction

**Review the [completed 600 DPI PDF](qualification/clearscan_contours/600/final.pdf), then the [1600% serif comparison](qualification/clearscan_contours/300/serif-1600pct.png).** Also available: [300 DPI PDF](qualification/clearscan_contours/300/final.pdf), [italic](qualification/clearscan_contours/300/italic-1600pct.png), [punctuation](qualification/clearscan_contours/300/punctuation-1600pct.png), [kana](qualification/clearscan_contours/300/kana-1600pct.png).

Implemented directly in `--profile clearscan`. The canonical serif/italic outlines now use smooth fitted curves instead of preserved pixel-grid turns. Faithful retains its existing tracing, font scale and preservation policy. The shared document writer also closes its text object correctly.

## Revisions and inputs

Starting HEAD: `4bff4821b1e409fe632536ba4bd2166795dee284`; tracked files were clean. Existing untracked research and Wine automation were preserved. [Initial state](qualification/clearscan_contours/starting-state.json) records the exact tree status.

Implementation: `89b6078` (grayscale curves, independent quadratic conversion, font-frame/metrics corrections) and `da9a2d8` (bounded local simplification), with regression-test commit `ac977ff`. Exact hashes, source-file hashes, image/OCR/oracle hashes, commands and tool versions are in [run-manifest.json](qualification/clearscan_contours/run-manifest.json).

The unchanged eight-page source has 552 non-space character instances per DPI, genuine 300/600 DPI imagery, and identical 432×216 pt geometry. Pristine outlines remain evaluator-only. Frozen Acrobat XI Pro 11.0.20 / Paper Capture outputs under Wine 9.0 were hash-verified and independently rerendered. Their settings were English (US), ClearScan, Downsample To 600 DPI; observed backgrounds are 150 DPI. No Adobe binary internals or font programs were used in implementation.

## Final output scorecard

Primary IoU uses the same 552 instances, fixed physical placement and the existing isolated-glyph cells. Poppler uses integer DPI; PDFium uses `nextafter(dpi/72, 0)` to avoid a one-pixel canvas-ceil error. Unadjusted default-scale results remain in the JSON. Diagnostic alignment is reported separately and never substitutes for the primary score.

| Metric | Degraded source | Adobe XI | Before (`4bff482`) | After |
|---|---:|---:|---:|---:|
| 300 PDFium IoU | 0.94516 | 0.90255 | 0.93114 | **0.95633** |
| 300 Poppler IoU | 0.94516 | 0.75066 | 0.93046 | **0.94994** |
| 300 PDFium ink-area bias | — | -2.79% | +4.80% | **+0.13%** |
| 300 PDFium rendered counter-count mismatches | — | 0 | 5 | 1 |
| 300 PDF bytes | — | 37,100 | 733,974 | **711,770** |
| 300 font bytes | — | 5,963 | 37,064 | 25,340 |
| 300 raster bytes | — | 17,411 | 622,682 | 615,829 |
| 600 PDFium IoU | 0.97807 | 0.94155 | 0.94257 | **0.96772** |
| 600 Poppler IoU | 0.97807 | 0.88319 | 0.92688 | **0.96178** |
| 600 PDFium ink-area bias | — | -2.11% | +3.75% | **+0.21%** |
| 600 PDFium rendered counter-count mismatches | — | 0 | 14 | 0 |
| 600 PDF bytes | — | 50,779 | 1,338,140 | **1,308,145** |
| 600 font bytes | — | 5,880 | 57,352 | 32,536 |
| 600 raster bytes | — | 30,036 | 1,153,207 | 1,158,885 |

[Machine-readable scorecard](qualification/clearscan_contours/scorecard.json) includes per-family results, ten best/worst families, severity strata and actual raster-resource classes. Adobe’s large Poppler/PDFium difference is retained rather than averaged away. Its kana is raster: removing its image operators leaves zero dark pixels in the kana region at both DPIs ([layer audit](qualification/clearscan_contours/adobe-kana-layers.json)).

## Where the staircases became geometry

1. `trace.rs` duplicates binary pixels at 2× resolution and sends them to VTracer with `corner_threshold=0`. This preserves scanner-grid turns as spline corners. Supersampling supplies no new edge information.
2. `glyphs.rs` fed all unrelated cubic spans into `kurbo::cubics_to_quadratic_splines`. That API gives corresponding curves equal control-point counts; one demanding span forced subdivisions onto every other span. It amplified complexity without removing the pixel turns.
3. The first compact fit exposed a separate metrics bug: long cubic handles were used to derive side bearings, although serialized TrueType glyph bounds differ. That shifted characters in native renderers. Compact glyph metrics now use the actual serialized quadratic glyph bounds.
4. Integer font-unit quantization is much smaller than a scan pixel: approximately 0.016 px at 300 DPI in the new frame. It was not the source of one-pixel stairs.

The correction extracts subpixel isocontours from the retained original grayscale samples after local paper/ink normalization. An adaptive least-squares cubic fit uses chord parameterization, bounded reparameterization, shared tangents, and physical-neighborhood corner detection. The grayscale fit bound is 0.15 source px. A complexity-regularized coverage objective selects among these curves and bounded simplification of the existing contours (0.15/0.30/0.45 px). It preserves substantial counters and separate components; subpixel noise holes below 0.8 px² are excluded from grayscale candidates. Self-intersections and invalid contour hierarchy are rejected. Canonical/local acceptance thresholds were not lowered.

Each independent cubic is then converted to quadratics at at most 0.05 source-pixel approximation accuracy. Document identity, variants, Unicode ownership and outline sharing remain in the existing dictionary/assembler.

## Actual embedded geometry

These are serialized TrueType points, including on/off-curve points—not sampled polylines. Pristine counts are evaluator-only reference-font counts.

| Target | Pristine points | 300 DPI before → after | 600 DPI before → after |
|---|---:|---:|---:|
| serif e | 28 | 258 → **79** | 492 → **135** |
| serif 8 | 48 | 366 → **146** | 768 → **166** |
| serif g | 45 | 330 → **132** | 660 → **244** |
| serif 6 | 38 | 354 → **154** | 660 → **212** |
| italic a | 31 | 198 → **119** | 390 → **134** |
| comma | 9 | 66 → **19** | 144 → **43** |
| exclamation | 18 | 66 → **49** | 126 → **84** |
| カ | 28 | 258 → **142** | 366 → **311** |
| ナ | 18 | 210 → **111** | 216 → **115** |
| な | 70 | 456 → **225** | 624 → **508** |
| か | 47 | 390 → **302** | 594 → **452** |

Total embedded points fell **16,427→8,251** at 300 DPI and **25,954→10,919** at 600 DPI. Total glyph cardinality stayed **59/60** respectively, including `.notdef` and the semantic owner.

An exact-curve tangent diagnostic finds unsupported >15° joins near the representative 300 DPI `e` falling **82→3**, `8` **122→4**, `g` **105→4** and comma **18→0**. The rule excludes joins near pristine corners; it is a representative diagnostic, not a global correctness gate. [Actual outline audit](qualification/clearscan_contours/outline-audit.json).

On 43 common target instances, sampled design-space mean boundary error improved **0.356→0.320 px** at 300 DPI and **0.343→0.253 px** at 600 DPI. No candidate was resized to the oracle’s bounding box. True near-vertical source intervals were measured at identical positions:

| DPI | Paired intervals | Signed width error, px | Absolute width error, px | Error SD, px |
|---|---:|---:|---:|---:|
| 300 | 6,050 | +0.218 → +0.112 | 0.433 → 0.256 | 0.489 → 0.348 |
| 600 | 2,778 | +0.354 → +0.097 | 0.479 → 0.415 | 0.492 → 0.503 |

The 600 DPI width SD slightly worsens despite lower bias/MAE. Counter results are also mixed: on 427 common 300 DPI counter-bearing instances, absolute counter-area error improves **7.058→6.606 px²**, but mean relative error changes **4.788%→4.963%**. At 600 DPI, 398 common instances improve **37.385→28.799 px²**, **5.927%→4.687%**. The remaining 300 DPI PDFium counter mismatch is italic `8` at `p06s0067`; Poppler retains two, that `8` and italic `a` at `p06s0021` (12→2 before/after). These are retained failures, not hidden by the averages.

## Font rendering and complete-page composition

A tighter contour alone produced 300 DPI IoU **0.9495 Poppler / 0.9156 PDFium**. Painting the same embedded outlines as paths isolated a text-rendering difference. A near-equivalent control halving font coordinates and doubling text-matrix scales improved both readers to **0.9508 / 0.9565**, within TrueType quantization error of the same physical geometry.

ClearScan now reserves half the em for the tallest observed ink, with placement cancelling that coordinate scale. The invisible semantic-owner frame uses the same scale; leaving it full-em caused a real Poppler layout-comma regression, which was fixed. A quarter-pixel bearing experiment was rejected because it helped PDFium while harming Poppler. Gasp/header/PREP controls did not resolve the discrepancy. [PDFium’s renderer](https://github.com/chromium/pdfium/blob/main/core/fxge/cfx_renderdevice.cpp) has distinct text-bitmap/path behavior and origin rounding; the controls support font-rendering conditioning as causal, without isolating every hinting/gamma contribution.

The final PDF, [vector-only](qualification/clearscan_contours/300/final/stages/S4-vector-only.pdf) and [raster-only](qualification/clearscan_contours/300/final/raster-only.pdf) were independently rendered. The target Latin glyphs are embedded vectors; their old staircase is visible in vector-only output, so it was not raster blur. Current source-ownership audits find **zero original dark pixels retained under accepted vectors** and zero dark raster/vector double paint. The compositor’s existing suppression/background logic was retained. Vector-only→final IoU loss is **0.00020 at 300** and **0.00061 at 600** on the emitted-occurrence population; this is separate from the 552-cell metric.

All final pages were rendered with both readers at **100%, 300%, 800%, 1600%**, bound by [zoom-renders.json](qualification/clearscan_contours/zoom-renders.json). Full local renders and committed representative pages accompany fixed-physical-size neighboring-context sheets. Photographs, artwork and raster interpolation were not smoothed. The earlier raster-fallback `8` sampling diagnosis is preserved; it is not confused with these font outlines.

## Reuse, replacement and bytes

| DPI | Observations | Actual vector occurrences | Canonical replacements | Accepted canonical identities | Distinct painted outlines |
|---|---:|---:|---:|---:|---:|
| 300 | 552 | 515 → **531** | 495 → **511** | 35 → 37 | 51 → 52 |
| 600 | 552 | 460 → **517** | 445 → **502** | 35 → 43 | 49 → 57 |

The higher accepted identity counts are pre-existing candidate families whose improved traces now emit successfully, not newly fragmented dictionary groups. The leading canonical outlines retain **71 and 58 uses at 300 DPI**; healthy and damaged observations still share them. The 300 DPI output has 24 repaired canonical occurrences; the others are compatible reuse. Unsupported occurrences remain raster (21/35 at 300/600). Their actual decisions are listed in the scorecard.

The source raster baseline candidate is **4,193,849 / 16,298,699 B**; final outputs are **711,770 / 1,308,145 B**. Relative to the accepted converter, total savings are **22,204 / 29,995 B**. At 300 DPI raster payload falls 6,853 B; at 600 it grows 5,678 B as ownership/accepted coverage changes. The final raster payload is still roughly **87%/89%** of each PDF. Adobe remains much smaller; the contour correction is not presented as a solution to residual-background cost. Exact grayscale encoding and resource reuse remain active.

## Strong repairs and remaining regressions

At 300 DPI the 44 initially damaged instances (source IoU <0.90) improve **0.88469→0.93725**; 38 improve and 6 regress. The 122 initially healthy instances (source ≥0.97) change **0.97780→0.95756** against source, even though they improve over the previous converter. At 600 DPI source remains better on aggregate: **0.97807 vs 0.96772**. A clearer vector is not automatically a better source reconstruction.

The strongest before/after families include serif `6` and italic `0` at 300 DPI. Serif comma, some kana, and 600 DPI italic question marks regress relative to the accepted converter. [Best/worst sheets](qualification/clearscan_contours/300/final-worst-800pct.png) and all per-family metrics show them. Donor `0`/`8` contours can retain waviness and local defects.

Kana has only two impressions per character on this fixture’s kana page and no supported canonical donor. These are local embedded outlines, not successful donor restorations. Bounded simplification reduces their complexity while retaining the local source-IoU floor; some raster-derived irregularity remains. The regularized objective can trade a bounded amount of grayscale fit for fewer controls, so the source floor is not a universal pixel-appearance non-regression guarantee.

## Genuine pages

The existing ten CORD training receipts and five OCR-D historical pages were rerun with unchanged region OCR and full-page composition inputs. All 15 conversions completed; **203 actual vector occurrences**, including seven pages with zero vectors, match the prior coverage. Real pristine fonts are unavailable. The receipt bold text can still appear rough or overly solid; broad real-font restoration is not demonstrated. Source paper, redactions, line art and photographs remain visible in the inspected CORD-02 and historical comparisons.

| Input | Visible vectors | Before bytes | After bytes |
|---|---:|---:|---:|
| cord-00 | 0 | 1,522,261 | 1,522,334 |
| cord-01 | 28 | 1,334,717 | 1,338,700 |
| cord-02 | 58 | 368,010 | 371,283 |
| cord-03 | 2 | 1,944,141 | 1,944,186 |
| cord-04 | 8 | 824,763 | 825,909 |
| cord-05 | 0 | 6,757,733 | 6,757,805 |
| cord-06 | 0 | 1,051,682 | 1,051,794 |
| cord-07 | 0 | 845,002 | 845,125 |
| cord-08 | 0 | 1,320,955 | 1,321,073 |
| cord-09 | 33 | 1,317,431 | 1,316,276 |
| history-00 | 30 | 9,633,136 | 9,630,638 |
| history-01 | 17 | 5,100,804 | 5,098,148 |
| history-02 | 0 | 8,187,599 | 8,188,552 |
| history-03 | 0 | 15,238,008 | 15,238,149 |
| history-04 | 27 | 10,427,116 | 10,417,037 |

All real PDFs parse and their fonts pass OTS; actual CID text matches each supplied span. Native numerical search finds **77/77 queries derived from original OCR word tokens**. Poppler merges OCR words `80` and `000` into `80000` on CORD-09 while PDFium retains the supplied boundary; that renderer-only concatenation is recorded separately. It must not be called a missing supplied numerical string. Existing hyphen/reading-order differences remain on CORD-04 and four historical pages. No unavailable recognition or pristine-font truth is invented. Exact inputs, attribution and CC BY / CC BY-SA derivative conditions are preserved in [real/ATTRIBUTION.md](qualification/clearscan_contours/real/ATTRIBUTION.md).

## Runtime, validation and review

Observed release conversion wall time/RSS: **37.94 s / 197.2 MiB** at 300 DPI (before 32.85 s / 201.4 MiB), **80.83 s / 723.6 MiB** at 600 (before 83.51 s / 726.7 MiB). Single runs do not establish a speedup; 600 CPU time slightly increases. Stage timing and `/usr/bin/time -v` records are retained.

**88 Rust tests pass**, with the same two inherited failures explicitly skipped: `regress_auto_reports_the_selected_candidate` and `clearscan_repairs_a_damaged_glyph_from_same_document_donors`. Their prior reproductions remain in the accepted typography evidence. **E0–E7 pass**; inherited P01–P08 visual/native-cardinality failures remain recorded. Final synthetic and real PDFs pass qpdf and OTS; frozen Adobe 600 retains its existing qpdf linearization warnings. All 16 synthetic pages pass raw/layout/PDFium text-order checks; native search and CID ownership pass. The supplied OCR’s inherited `c` for pristine `e` at `p07s0000` is preserved; matching supplied OCR is not a claim of perfect recognition (551/552 known non-space labels are correct). The ordinary 300 DPI conversion repeats byte-for-byte.

Independent review caught the missing `ET` and error-path panic, and checked the semantic-owner scale correction. These issues were fixed. It independently verified actual font point counts, exact saved bytes/hashes, renderer metrics, and the bounded local source-floor logic. [Review findings](qualification/clearscan_contours/independent-review.md).

## Reproduce

```sh
cargo build --release -p scanweave-cli
python qualification/clearscan_contours/run.py --measure --zooms --repeat
python qualification/clearscan_contours/design_geometry.py --dpi 300 --arms previous final --representative
python qualification/clearscan_contours/design_geometry.py --dpi 600 --arms previous final --representative
python qualification/clearscan_contours/paired_widths.py
python qualification/clearscan_contours/counter_geometry.py --dpi 300
python qualification/clearscan_contours/counter_geometry.py --dpi 600
python qualification/clearscan_contours/real/convert.py final --region-ocr
python qualification/clearscan_contours/real/evaluate.py final
```

Use the existing qualification Python environment (NumPy, Pillow, pikepdf, pypdfium2, FontTools), Poppler, qpdf and OTS. Compressed JSON archives are hydrated by `run.py` on a fresh checkout. The normal converter commands receive only the scan/OCR bundle. Negative trial PDFs remain locally preserved; committed trial metrics distinguish rejected binary-only/looser-fit/bearing controls from the final implementation.

**Remaining quality limit:** noisy or insufficiently supported witness geometry, especially small kana and particular donor contours. The canonical Latin glyphs no longer inherit the binary grid as permanent corners; this round implements that correction without changing the OCR or document-wide grouping system.

Direct 1600% inspection of the italic word confirms that some roughness is still genuine vector geometry: the `6` and a damaged `0` retain irregular contours. Other `a`/`0` impressions in the same sheet are raster fallback, distinguishable in the raster-only row. These are not all solved by the smooth canonical `e`, `8`, `g` and punctuation examples.
