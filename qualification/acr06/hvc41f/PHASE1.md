# HVC-41F Phase 1: renderer, patch and encoding diagnostics

**Recommendation for independent review:** A3 (the outside-pattern, path-only Form XObject), B1 (one exact-mask combined path per glyph, with colour derived from the decoded #39 paper ring), and the bounded C encoding are the strongest of these tested alternatives. This is a diagnostic recommendation, not a qualified final page. **A3 gives up the embedded-font architecture**: its outlines are ordinary path operators. A2 is also path-only, but retains the pattern and did not remove the observed Splash behavior. No Phase D final 38-glyph PDF was built. The 38-glyph file discussed below is explicitly a size-measurement build.

B1 improved the measured ring match and the three samples had no changes beyond the one-pixel ownership boundary in the four tested renderers. It did **not** eliminate the measured tone discontinuity. Claude must judge the remaining seams and the B2 exceptions independently before any final assembly. The path-only approach, renderer registration differences, 4× topology proxy, and residual halo remain open risks.

## Frozen inputs and methods

The decision ledger SHA-256 was `391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef`; the HVC-41E composed PDF was `9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0`; the #39 historical baseline was `68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b`. The three sampled accepted proposals were 243 (`t`), 38 (`W`), and 18 (`B`). [Input verification](verified-inputs.json) checks all 38 outlines, placement matrices and fill values against the actual HVC-41E font and pattern, plus owner and patch mask hashes and containment. For the three A samples the original compressed patch streams have the same raw SHA-256 across A0–A3, and their patch operations occur in the HVC-41E composed PDF.

The scripts require `SCANWEAVE_HVC41F_*` switches, matching hashes and frozen OCR sidecars where conversion inputs are used. The failing Tesseract stub was first in PATH; no invocation was observed. With research disabled, the [OCR-locked replay](default-replay.json) produced byte-identical PDFs for all 32 pages. No product-default code was changed. Research code was committed as `2e8ffde` on `research/hvc41-feasibility`.

## A. Poppler diagnosis

A0 is the original Type 3 `d0` inside the tiling pattern. A1 uses `d1`, outward-rounded individual glyph bounds and their union as FontBBox. A2 uses the same Bézier path inside the pattern without text operators. A3 uses the same path in a Form XObject outside the pattern, with no text operators. All use the same frozen patch, matrix and external colour. A0–A3 were rendered at 96 and 300 DPI in Splash default, explicit AA, no AA, Cairo, PDFium and MuPDF. PDFium and Poppler extraction, and six PDFium searches, matched baseline on every isolated PDF: [A0–A2 semantics](phase-a-semantics.json), [A3 semantics](phase-a3-semantics.json).

[The complete metrics](phase-a-metrics.json) give each glyph/variant/engine/resolution. For shape, a vector mask is defined by a >10 RGB-level difference against the same renderer's patch-only page; IoU compares this mask with PDFium's same-variant mask, aligned in page pixel coordinates. This includes pixel-grid/rounding differences between renderers. Centroid offsets are against A0/PDFium. Intermediate-edge pixels have luminance between 20% and 80% of the frozen fill-to-paper interval in a one-pixel dilation of that vector mask; this is an operational smoothness measure, not a perceptual score. Beyond-boundary coordinates are recorded in the metrics.

| 96 DPI, three-glyph average | Splash-AA IoU vs PDFium | Splash beyond-boundary pixels | Cairo IoU | MuPDF IoU |
|---|---:|---:|---:|---:|
| A0 Type 3 pattern | 0.611 | 10 | 0.777 | 0.868 |
| A1 bounded `d1` | 0.541 | 23 | 0.936 | 0.782 |
| A2 path pattern | 0.611 | 10 | 0.954 | 0.860 |
| A3 path Form | 0.847 | 0 | 0.864 | 0.860 |

At 300 DPI, mean Splash-AA IoU against the same variant's PDFium mask is 0.820 / 0.659 / 0.821 / 0.815 for A0/A1/A2/A3; the corresponding beyond-boundary counts are 2 / 65 / 2 / 0. These numbers do not establish renderer equivalence. The per-glyph centroid and shape data, including the `t` sample where A3 IoU is lower than A0, remain available for review. At 96 DPI A0 and A2 have the same Splash-AA IoU and outside count; turning Splash AA off also leaves their IoU and outside count unchanged. A3 responds visibly to the no-AA setting and removes these outside pixels with AA on. A1 changes rendering markedly and worsens Splash's measured outside count. Together, these results implicate the tiling-pattern rendering path, rather than Type 3 alone, as a contributor. They do **not** prove Poppler's internal cache or rasterisation mechanism; no backend instrumentation was performed.

The 300-DPI nearest-neighbour grids have separate non-overlapping labels: [t](../local/hvc41f/phase-a-grid-243.png), [W](../local/hvc41f/phase-a-grid-038.png), [B](../local/hvc41f/phase-a-grid-018.png). Their [index](phase-a-panel-index.json) records hashes. A3's path Form is useful for diagnosis but is not an embedded-font replacement.

## B. Paper and boundary measurements

The #39 page background is a 1158×1569 JPEG image; it was decoded and bilinearly mapped to source geometry before sampling. For each glyph, candidate paper is the brighter half of a 12-source-pixel annulus outside the owned mask, excluding the reference-ink proxy and ownership. B1 uses the RGB median of those samples in one combined exact-mask fill; this is locally measured but still flat, so varying paper texture can remain unmatched. B2 copies the nearest eligible decoded-background ring samples into an inpainted local image with an explicit 8-bit `/SMask` exactly equal to the removal mask. The source image stream remains unchanged. This sampling does not prove that every bright ring pixel is paper or exclude every possible artwork pixel.

All 38 masks were measured in source space, with zero `patch & ~owned` pixels. Relative to the nearest eligible paper samples, mean absolute ΔL averaged over the 38 glyphs is 11.76 for B0 and 6.61 for B1. B2 is 0 **by construction of this nearest-sample metric**, so that figure is not evidence of zero rendered halo. [Per-glyph measurements](phase-b-paper-metrics.json) and the three actual PDF trials are retained.

The following patch-only render metric compares the mapped owner inner boundary with the median nearby rendered paper ring, averaged over 3 glyphs × 4 renderers. It can include resampling and residual background near the edge; it is not a direct isolated seam visibility score.

| DPI | Variant | Mean boundary/ring absolute ΔL | Changed pixels beyond one render-pixel ownership band |
|---:|---|---:|---:|
| 96 | B0 HVC-41E | 21.51 | 10 |
| 96 | B1 local median | 18.18 | 0 |
| 96 | B2 local image + SMask | 20.02 | 9 |
| 300 | B0 HVC-41E | 23.27 | 2 |
| 300 | B1 local median | 16.01 | 0 |
| 300 | B2 local image + SMask | 16.09 | 0 |

The [full renderer data](phase-b-render.json) enumerate **every** beyond-band exception with coordinates and signed ΔL. They comprise 10 B0/Splash pixels at 96 DPI (W and B), 2 B0/Splash pixels at 300 DPI (`t`), and 9 B2/MuPDF pixels at 96 DPI (3 per glyph). B0's changes correlate with the pattern/Splash behavior above; B2's small changes correlate with rendering a soft-masked image. The precise backend causes are not established, and these exceptions are not pre-approved as harmless antialiasing. B1 has none by this geometric test. The boundary panels mark the one-pixel band yellow and farther pixels red: [96 and 300 DPI panel index](phase-b-panel-index.json).

The frozen-reference ghost and under-replacement proxies were recomputed from actual PDFium vector-only renders: [data](phase-b-ghost.json). For A0 and A3 respectively they are unchanged: `t` ghost 16 and under-replaced 15; `W` ghost 92 and under 0; `B` ghost 80 and under 0. The ghost proxy includes adjacent legitimate reference ink and cannot by itself identify a doubled stroke. The enlarged panels show the source ink and replacement, but visual seam, punctuation and ghost-stroke acceptance remains for independent review. B1/B2 isolated extraction and searches also matched: [semantics](phase-b-semantics.json).

## C. Non-final size measurement

The selected A3/B1 combination was applied to the frozen 38 solely to measure encoding and make the requested contact sheet. The glyph outlines were quantised to 0.001 font units; cubic segments were replaced by a line only when their control hull was within 0.01 source pixel of the chord and their projections were monotone. This simplified 1,073 of 4,560 cubic segments. Patch paths trace the exact union of owned source-pixel cells, combine collinear boundary edges and use even-odd fills; they do not paint individual pixel rectangles. Four mask tests, including all 512 possible 3×3 masks, diagonal contacts, holes and deliberate foreign pixels, passed.

For all 38 glyphs, contour counts and 4× raster connected-component/hole counts matched before and after. The per-glyph [geometry ledger](phase-c-size.json) records the checks and source-pixel errors. Across glyphs the mean of each glyph's 17-sample-per-cubic geometric error is **0.000840 px**; the maximum sampled error is **0.007764 px**. The maximum conservative per-glyph bound from quantisation plus simplified curve control hull is **0.011593 px**. Forty-four 4× raster pixels changed across the 38 individual glyph tests. Matching sampled raster topology is evidence, not a formal proof that every continuous curve topology is identical.

| Complete historical PDF | Bytes | Increase against #39 |
|---|---:|---:|
| #39 | 2,247,390 | — |
| HVC-41E Type 3 pattern | 2,521,001 | 273,611 |
| A3/B1 C size-only build | 2,319,452 | 72,062 |

The size-only delta comprises 59,174 compressed path-Form bytes, 12,589 compressed patch-stream bytes, 29 other invocation-stream bytes, and 270 bytes of structural/serialization overhead. The increase is 201,549 bytes below HVC-41E's, but remains positive: append-only overlays cannot deliver net source-raster compression. Assembly took 1.75 s wall and 262,484 KiB peak RSS in the measured run; it reused frozen inputs, so this is not conversion time. The diagnostic's SHA-256 and per-glyph data are in [phase-c-size.json](phase-c-size.json). PDFium and Poppler extraction, six PDFium searches, original page content and image streams matched, and qpdf passed for this size-only PDF; these checks do not constitute Phase D qualification.

[The 38-glyph size-only contact sheet](../local/hvc41f/size-only-38-contact.png) and [index](phase-c-panel-index.json) show source and actual PDFium-rendered measurement output. All figures and local PDF/render paths are research artifacts, not committed binaries.

## Disposition

Stop here for independent A–C review. A3 avoids the measured Splash outside-boundary pixels in these samples but substitutes paths for the research Type 3 font. B1 is the better observed patch candidate, yet its paper-edge luminance difference and flat-tone texture remain. B2's nine 96-DPI MuPDF exceptions also remain for review. No conclusion is made that either patch is visually acceptable, and no final 38-glyph qualification or product integration is authorised by these diagnostics.
