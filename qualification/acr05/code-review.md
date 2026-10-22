# ACR05 independent code review

Reviewed the uncommitted `convert.rs` and `page_pdf.rs` changes against `882e8f7` on `product/acr05-seamless-compositing`. Review was read-only; no conversions or tests were run.

## Findings

- **No blocking correctness defect found in the new composition path.** The candidate is formed from `patch_source` (the already-cleaned residual), never `input.rgb`; therefore choosing a single residual does not restore source text ink under emitted vectors (`convert.rs:1463-1467`). The same samples feed the fallback whole-page patch at `1481-1487`.
- **Caller protection remains gated at both assembly entry points.** Per-page layout comparison is skipped if `input.protected_regions` is nonempty (`convert.rs:1462`). The single-page API bypasses tonal assembly for protected inputs (`convert.rs:646`); document assembly selects the tonal fallback only when all pages have no caller-protected regions (`document.rs:364-367`). Faithful assembly remains on the old path because the compositor branch is ClearScan-only.
- **Physical sizing follows the existing page affine and does not alter placement.** The chooser passes the existing transform-derived page extents to `encode_residual`; the selected whole patch retains the original raster dimensions and full-page bbox. The assembly path changes encoded sample dimensions only, using the existing residual encoder; image placement/content operators are untouched.
- **Actual serialized-PDF selection remains the final codec gate.** The assembly wrapper builds the lossless and tonal PDFs and chooses by complete PDF byte length (`page_pdf.rs:1143-1162`). Optional residual/native encoder failures inside serialization retain the lossless resource (`1227-1235`, `1240-1255`).

## Qualification caveat

The *layout* precheck in `coherent_residual_is_smaller` compares encoded image stream lengths only (`page_pdf.rs:318-345`). It does not account for PDF object/content-stream overhead or cross-page resource reuse between the two alternative layouts. The later full-PDF comparison chooses lossless versus tonal encoding for whichever layout was already selected; it does not serialize both the fragmented and coherent layouts. This is a non-blocking approximation for the current bounded decision, but the report should call it a stream-cost estimate rather than an exact whole-PDF cost comparison. Near-ties or repeated identical patches could select a layout that is not smallest in the final document.

The existing `native_area > 60%` whole-page fallback remains independent of the new fragmented-cost comparison (`convert.rs:1481`); it is not newly guarded by that comparison. Its input is still the cleaned, native-resolution residual and protected documents do not enter the lossy tonal assembler. No further regression was established from source inspection.
