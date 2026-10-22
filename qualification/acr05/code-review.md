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

## Mixed-protection follow-up

Reviewed the current uncommitted three-file fix against `9388a03`. I found no blocking defect in the new document-wide gate. `allows_tonal_images` is computed once after rejecting empty documents and is passed both to per-page composition and final assembly (`document.rs:218-222, 251, 341-342, 370-372`). Thus a single protected page disables tonal resource encoding throughout the document and selects the legacy layout calculation on every page. The single-page `convert_parts` path derives the same gate from its sole input (`convert.rs:735-741`).

The fallback calculation matches the prior ACR-04 rule: for fragmented layouts it declines replacement when native area is at most 20%; otherwise it compares the whole lossless stream against lossless layers plus background with the original 10%-savings condition. `lossless_patch_cost` also retains the previous predictor-0 encoding and clears the compact-background flag before compression. The caller still has the prior independent `native_area > 60%` full-page cleaned-residual fallback; final document assembly is lossless whenever any page is protected.

The new unit coverage checks document-gate truth for all-unprotected, mixed-protected, and faithful inputs, and checks a tonal-versus-lossless cost case. I did not run tests or corpus conversions. A direct mixed-document serialization regression test would improve coverage, but code paths share the same computed flag and I found no mismatch requiring a block.

### Final cost-skip follow-up

The final guard now runs the optional cost comparison only when fragmented native area is at most 60% (`convert.rs:1465`). For area above 60%, the immediately following existing condition selects the same whole-page cleaned residual (`1485-1491`), so skipping the comparison avoids work without changing the chosen layout. The `<=`/`>` split leaves the exact 60% boundary on the comparison path, as before. No blocker found.
