# Final report evidence review

## Result

I found no unsupported headline measurement or material contradiction in `CLEARSCAN_TYPOGRAPHY_REPORT.md` against the final scorecard, validity table, real-document metrics, geometry binding, and owner-frame review.

- The 300/600 DPI final PDF byte counts and SHA-256 hashes match `scorecard.json` and `validity.json`.
- The 300 DPI isolated-IoU, moderate-damage, area-bias, occurrence, outline, and paired-stage values match `scorecard.json`. The 600 DPI figures also match; the report correctly calls the small regression rather than claiming a quality gain.
- `validity.json` covers both synthetic final ScanWeave PDFs and all 15 real final PDFs: each has qpdf status 0 and every embedded ScanWeave font has OTS status 0. The two Adobe 600-DPI warnings are accurately disclosed.
- `geometry-binding.json` verifies all 515 visible 300-DPI outline/placement records match the geometry-scored PDF. At 600 DPI one visible occurrence differs; the report's geometry and stem conclusions are explicitly scoped to 300 DPI and make no 600-DPI geometry-improvement claim.
- `real/final/metrics.json` supports 8/15 vector-bearing pages, unchanged raw Poppler non-space sequences, and five pages with renderer extraction differences. `real/financial-search.json` is the supporting artifact for the 77/77 query claim.

## Evidence note to refresh

`design-geometry-review.md` still ends with the superseded 200-unit owner-frame review: it says the full-em frame is being tested and that layout-order measurements must be repeated. That paragraph is stale and contradicts the completed final report and `owner-frame-review.md`. Replace it with a short pointer to the full-em review, or remove that obsolete paragraph. The corresponding final output is the 300-DPI PDF at SHA-256 `8e57afa9599f3be936f44a13b326e09b40b7e82cfdd57c32bd80666944d8cc4c`; the 600-DPI geometry binding has one changed occurrence and should remain described separately.

No product or measurement defect was found in this bounded final review.
