# ACR-05 ordinary-CLI financial output: independent visual review

**Disposition: no material visual blocker found; the coherent residual is acceptable for the inspected corpus under ClearScan's readability-oriented lossy contract.** It provides more consistent local paper presentation, but must not be sold as a new font-reconstruction improvement or universally sharper text.

## Artifact and inspection

Actual ordinary-CLI `local/product/financial.pdf`: **3,187,571 bytes**, SHA-256 **`32b7c13e664b32fadeea41b99d9299479f129bfac3bd20debbbf481a6f885e51`**. This is the integrated output, not shadow `C.pdf` or blinded X/Y. Source, ACR04 and frozen Adobe remain unchanged.

I inspected **all thirteen financial page overviews in both PDFium and Poppler** (26 sheets), compared with source, ACR04 and Adobe. Detailed 300-DPI checks use the frozen primary windows on indices 0,1,10,12 and controls6,7, including amount columns, subtotals/rules, body text and small punctuation. Both-engine actual-layer ablations were additionally inspected for page10.

Evidence is under `local/final-review/`: `pN-{renderer}-page.png`, fixed/worst crop sheets, `render-details.py`, `render-pages.py`, and page10 `*-layers.png`. Source box definitions and exact cap/rounding contracts remain in the preceding baseline and blinded-review records. Layer example crop is page index10 source pixels **(250,750,950,1050)** at300DPI, without registration/resizing. Derivatives use the existing recursive font-show isolation, retaining original physical geometry and paint operations; originals were not overwritten.

## Paper appearance and content

- Paper around the inspected native-content transitions is coherent. The conspicuous little rectangular borders produced by rejected X are absent. Compared with ACR04, local paper/edge texture feels more consistent around mixed text, especially beside isolated numbers and rule fragments. This is a **subtle high-zoom compositing improvement**, not an unmistakable dramatic normal-page transformation: normal-view ACR04 was already broadly readable and coherent.
- The completed pages retain source-supported paper colour and broad shading. No white cleanup rectangle, green decoder failure, major new halo, geometric discontinuity or missing content block was observed across the thirteen overviews in either engine.
- Selected numeric details remain readable: `15 00`, `4 00`, `$295 00`, `185`, `5`, `1`, control rows `32 75`, `33 75`, `22 00`, and table figures/ellipsis. Fine rules and separated dots remain visible. No material visual numeral substitution was found in these checks. This is not a new OCR accuracy assertion; rerender OCR can change even when human-readable text survives.
- **Retained raster text is visibly softer at300DPI than ACR04's native patches.** SELECTMEN, Moulton and unsupported body-word portions demonstrate the tradeoff. The selected words remain readable; no meaningful thin stroke or punctuation was identified as disappearing. Larger repeated vector text retains its previous appearance. At normal reading scale the whole page remains usable.
- The output is not entirely free of source-shaped faint residuals. Page10 nonfont ablation still reveals weak old edge patterns at vector-replaced words. They are not a second full-strength text layer and do not establish a newly introduced double-outline defect in the complete render. Do not claim this change eliminates every source fringe.

## Intrinsic typography versus compositor

Page10 font-only ablation shows that some uneven outline geometry belongs to the embedded vector glyph itself. Nonfont paint supplies unsupported words and paper; those words soften under residual representation. The final page combines both. Therefore sharper vector shapes next to softer raster words are still an inherited mixed-representation inconsistency. This milestone improves packaging/paper continuity; it does not repair rough canonical contours or increase valid font coverage.

Adobe remains smoother on a number of visible glyphs and has different background texture, but the source is the content reference. Its appearance does not justify deleting meaningful source marks. The integrated result is acceptable without claiming Adobe-equivalent typography.

## Scope and stability limits

All thirteen pages received two-engine normal-view inspection; selected windows, not every word/mark, received high-detail review. This is not a universal guarantee for arbitrary scanned content. No code changes or sealed holdout access occurred in this review.

The other nineteen development pages were reported byte-identical to ACR04. Their previous two-renderer visual qualification may be reused **only with the recorded hash-equivalence verification**; I did not pretend to rerender them as newly changed pages here. Font/Unicode/ownership invariants, extraction, faithful behaviour, deterministic serialization and Rust tests remain separate mechanical evidence supplied by engineering, not proven by pictures.

**Final independent visual conclusion:** accept the tested integrated residual-selection result with explicit softness and residual-fringe limitations. The paper change is useful and locally cleaner, but the strongest measurable benefit is reduced resource cost rather than improved font geometry. No additional imaging technique is requested by this review.
