# Shaded-paper ownership: bounded negative result

## Outcome

**No shaded-page image-processing code is promoted.** Two bounded candidates were implemented through the existing ClearScan path, converted the fixed `history-02` PDF, and were independently inspected. Illumination-aware evidence recovers character observations, but the completed replacement page fails the visual and size gates. Both candidate patches and actual emitted-output measurements are retained; the normal converter was rebuilt and its output verified byte-for-byte against the published baseline.

This work is separate from the accumulated implementation in [catch-up PR #1](https://github.com/mitchins/scanweave/pull/1). Base implementation: `8bc191e`; publication/evidence checkpoint: `5fe99c1`. No new OCR, font writer, compositor, public profile or third approach was introduced. Faithful and the sealed holdout are untouched.

## One-page diagnosis

Source `history-02` is 1676×2287 native pixels on a 402×548.64-point page. The photograph includes dark surroundings and a page frame. Global corner RGB `[41,40,43]` is not the paper underneath the text; median page luminance is 183. The existing absolute difference rule consequently calls **69.744%** of the page foreground, including essentially all unprinted top paper.

The diagnostic sheet is [illumination.png](qualification/shaded_paper/illumination.png). It contains original appearance, existing foreground, spatial paper estimate, candidate ink confidence and the candidate foreground. [Accepted source/vector/final/raster/Adobe crops](qualification/shaded_paper/accepted-glyphs.png) show 12 genuine printed observations with neighboring context. The [previous rejected cleanup example](qualification/real_convergence/inspection/history-02-words.png) remains a negative control, not a delivered page.

The local estimate is a bilinearly interpolated 90th-percentile field over 128-pixel cells, clamped at field boundaries. A dark border cannot make brighter interior paper count as ink: foreground requires a **one-sided 60-level darkness residual**. This retains the existing conservative darkness separation; identity/style, tracing, source fidelity and donor acceptance thresholds are unchanged. The earlier rejected 64-pixel, 85th-percentile, absolute-residual/half-contrast attempt was not reintroduced.

| Fixed visually selected region | Existing foreground | Candidate foreground |
|---|---:|---:|
| Dark outer photographic margin | 0% | 0% |
| Unprinted top paper | 100% | 0% |
| Printed text plus interline paper | 92.939% | 13.908% |
| Show-through and spots | 99.937% | 0.172% |
| Whole photograph | 69.744% | 12.920% |

These are region classification fractions, **not** pixel-level truth or glyph accuracy. In particular, faint show-through is meaningful source content; excluding it from text evidence does not authorize erasure. The source samples remain immutable.

## Two candidates and three gates

### A — Spatial paper evidence, existing ownership/contact rules

The actual normal CLI produced **792 bounded observations** versus two previously, with 860 unchanged OCR characters. The recovered sample includes genuine printed digits, Gothic letters and punctuation, rather than the illuminated paper component.

However, all 192 text regions still fall back as `ContactNonText`. The page-frame artwork component's bounding box encloses the text; the planner treats box intersection as contact even where artwork samples are distant. Result: **zero actual visible glyph draws**, no superseded ink, **5,186,191 B**. It is not a successful reconstruction despite the observation gain. Gate 1 has useful evidence; Gates 2/3 have no completed replacement mechanism to accept.

### B — Same paper model plus actual-sample contact verification

The second implementation responds to that measured failure, rather than varying the paper threshold. It retains the same illumination field and four-pixel contact margin, but checks actual artwork samples inside the expanded region. Protected regions and suspect connected components retain their vetoes. This is one paper model with a bounded ownership refinement, not two independent estimators or a relaxed glyph matching rule.

It unlocks **73 actual visible glyph draws across 63 painted GIDs**, independently counted from the emitted CID/GID operations. The page still has 32 `ContactNonText` and 136 `UnsupportedContent` fallbacks. Those proposals are not counted as successful replacements.

Gate 2 is incomplete: some shapes are plausible, but accepted `1`, `9` and `G` show rough/stepped edges in vector-only renders. There is no pristine original for this historical page, so neither identity correctness nor better source typography is established for all 73 draws. We do not claim every narrower contact check or every B outline is wrong.

**Gate 3 fails visibly.** Both PDFium and Poppler show a light rim/double edge around the accepted `1` and `G`, and glyph-shaped residuals in the raster-only layer. This is not a renderer-only sampling anomaly. See [PDFium crops](qualification/shaded_paper/accepted-glyphs.png) and [independent Poppler crops](qualification/shaded_paper/poppler-glyphs.png). Normal-page context and 300%/800% comparison sheets are retained locally; selected contextual and high-zoom crops are committed. The original, published output, frozen Adobe page and candidate are compared at matching physical coordinates without glyph-wise bbox normalization.

B suppresses 16,345 source-ink pixels, but **zero antialias-fringe pixels**. The local illumination model is used for evidence segmentation; the downstream cleanup still receives the old global corner-paper value. In `convert.rs`, fringe cleanup first refuses an emitted vector without an independent donor halo. For witnessed cases, source coverage normalization still uses `(paper - source_dark).max(1.0)` with the old global paper estimate. Local-only glyphs therefore lack fringe evidence, while the dark-corner value is unsuitable for normalization on the much lighter page. The zero-fringe counter and retained rings establish the failed integration boundary; no further counterfactual was run to apportion those two causes or claim that changing the paper value alone would solve it. Merely recovering observations is insufficient. No blanket rectangle erasure or whitening was attempted to hide the failure.

## Actual serialized bytes and performance

| Arm | PDF bytes | Raster stream | Embedded fonts | Content | Other | Draws |
|---|---:|---:|---:|---:|---:|---:|
| Published baseline | 5,186,194 | See previous corpus inventory | — | — | — | 0 |
| A | 5,186,191 | 5,171,835 | 487 | 11,883 | 1,986 | 0 |
| B | 5,245,369 | 5,163,535 | 67,204 | 12,022 | 2,608 | 73 |
| Restored normal converter | **5,186,194** | Baseline identical | Baseline identical | Baseline identical | Baseline identical | **0** |

A→B saves only **8,300 raster bytes**, while fonts add 66,717 B and content adds 139 B. Total grows **59,178 B** versus A, or **59,175 B** versus the published page. Both A and B retain one whole-page image resource. No useful compact residual representation has been established by this trial.

A wall time was 8.18 s / 166,648 KiB command RSS; B was 33.57 s / 152,332 KiB. Detailed stage times are in `audit.json`: B spends 18,917 ms in tracing/placement/cleanup and 8,003 ms in raster composition. These are GNU-time command maxima, not process-tree PSS. No speedup claim is made. The frozen Adobe PDF used for rendering is the **five-page historical collection** (1,682,427 B), page index 2; that file size must not be presented as a single-page comparison.

## Search, preservation and restoration

Both candidates retain 860 nonspace characters in both native PDFium and Poppler extraction. A extraction is identical to published; B changes whitespace but its nonspace sequence is identical in each renderer. This is semantic transport, not independent proof of OCR correctness. No OCR hypotheses or labels were changed.

Rejected code was restored before completing the branch. The ordinary rebuilt CLI generated `restored.pdf` with exactly the published SHA-256:

`8f14ae1e0831cafced4e9606c5924fd5b2dc1a5a8f09f252ff7ed3302bee072d`

There is **no source-code delta** under `crates/` or `probes/` relative to the published implementation. Therefore history-03, Linn, forms, receipts and the synthetic fixture were not run through a failed candidate; the conditional full-corpus rerun was not triggered. The existing 59,599,260-byte/32-page measurements, 17/49 receipt queries, 748 Linn paints, 500 form paints and synthetic regression evidence remain the frozen product baseline, not newly rerun shaded-page results. No new claim of full-corpus improvement is made.

## Review, CI and publication

Independent review confirmed 0/73 actual draws, 63 unique GIDs, byte decomposition, source-core-only suppression, unchanged nonspace extraction, rings in both renderers and exact normal-CLI restoration. It supports this narrow rejection, not a general impossibility claim. [Review findings](qualification/shaded_paper/independent-review.md) include the remaining contour uncertainty.

The separate PR contains diagnostics, rejected patches, measurements and a small actual embedded-vector PDF; it does not enable the failed path. Full A/B final/raster PDFs and larger renders remain local with hashes and reproduction instructions, avoiding another bulk image-data push. See [README](qualification/shaded_paper/README.md) and `manifest.json`.

The catch-up PR's unfiltered Rust CI remains blocked by `clearscan_repairs_a_damaged_glyph_from_same_document_donors`; the auto-accounting contract is corrected and passes. Python qualification and publication hygiene passed on the code checkpoint. Clippy passes locally. P01–P08 inherited failures remain documented. CodeRabbit was requested on the catch-up PR but skipped its 1,242-file change set; that is not an approval. The evidence PR is separately submitted for review and CI; no automatic merge is authorized.

## Single demonstrated bottleneck

**Locally valid paper/ink evidence is not carried consistently through to the replacement edge and paper compositor.** The observation stage improves, but source-edge remnants survive accepted glyph painting. This is the strongest concrete blocker from this bounded trial; rough contour selection remains an additional observed limitation. A third candidate or broader reconstruction programme was not started.
