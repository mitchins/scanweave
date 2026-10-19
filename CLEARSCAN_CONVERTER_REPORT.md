# ClearScan converter implementation report

## Scope and code state

This report records the product-path integration and runs from the local tree whose starting commit was `cfb5d240f04a01f0289ab9df470ceb3fd53b2a86`. The implementation commit is `b76b9d638eff0c81c8c8f8204db72fd12a4ee6f9`; qualification output PDFs and input hashes are preserved alongside the measurement scripts. Existing unrelated untracked research and fixture material was left untouched.

The `clearscan` profile now invokes document-wide observation collection, prototype/donor selection, font embedding, occurrence assignment, source-ink suppression and PDF assembly through the normal CLI/library path. The development-only `canonical-experimental` switch and uniform-scale experiment were removed from the user-facing profile selection. `faithful` retains its independent preservation behavior. ClearScan derives source DPI from the page raster-to-PDF transform, so bundle page geometry remains authoritative even if the command line's default DPI differs. A final assignment guard rejects healthy outline reuse when traced-prototype/source-mask IoU is below 0.80; donor-supported repairs are not subject to this guard.

Raster assembly now suppresses source ink only for occurrences whose vector glyph was actually emitted, removes a validated antialias fringe, and puts a compact low-resolution background beneath original-resolution fallback/artwork patches. A second background cleanup prevents recognized fallback text from remaining as a soft duplicate underneath its native-resolution patch. F1 image sharing and grayscale encoding remain in use. This is a real product path, but the synthetic accuracy results below show that its reconstruction policy is not yet good enough to claim source-faithful restoration.

## Synthetic multi-page conversion

The M1-G fixture contains eight pages, 552 scanned glyph observations and 600 pristine-truth occurrence slots at each resolution. The two resolutions use corresponding physical page geometry. Pristine references were used only by the independent evaluator. Runs used the current ClearScan CLI and the `measure.py` evaluator; Poppler and PDFium renders were measured independently.

| Measure | 300 DPI | 600 DPI |
|---|---:|---:|
| Canonical prototype IDs | 38 | 43 |
| Accepted prototype IDs emitted | 27 | 41 |
| Embedded font outlines (including `.notdef`) | 57 | 58 |
| Accepted vector occurrences | 278 | 476 |
| Segmented text ink owned by vectors | 60,611 / 130,344 (46.5%) | 507,072 / 544,428 (93.1%) |
| Source-mask ink suppressed | 60,611 px | 507,072 px |
| Fringe samples suppressed | 45,538 px | 343,543 px |
| PDF bytes | 1,093,038 | 889,147 |
| Searchable-raster PDF bytes | 4,210,019 | 16,320,387 |
| Reduction against searchable raster | 74.0% | 94.6% |
| Embedded font bytes | 35,332 | 52,464 |
| Encoded image payload | 917,473 | 754,225 |
| Content streams | 71,628 | 59,011 |
| Image XObject references | 281 | 80 |
| Reported conversion wall time | 30.4 s | 68.2 s |
| Peak RSS (`/usr/bin/time -v`) | not measured on guarded rerun (pre-guard: 201,752 KB) | 727,076 KB |

At 300 DPI, 256 accepted occurrences reused canonical prototypes and 22 were classified as repairs. At 600 DPI, 475 reused canonical prototypes and one was classified as a repair. The emitted typeface contains shared outlines, and the compositor removes corresponding original foreground pixels. PDF-size reduction is therefore not merely image-stream deduplication. The 300 DPI assignment guard increases bytes by 5,962 B relative to the pre-guard candidate while refusing eight poor healthy reuses. The remaining patch/resource payload is still large relative to Adobe XI and needs care on dense or high-resolution pages.

### Pristine-relative appearance

Mean glyph IoU for source scan and final renders:

| Resolution | Source | Final Poppler | PDFium |
|---|---:|---:|---:|
| 300 DPI | 0.9053 | 0.8044 | 0.7912 (pre-guard PDF only) |
| 600 DPI | 0.8998 | 0.8487 | 0.8236 |

For the pre-guard accepted set, source-to-pristine IoU was 0.9413 at 300 DPI and 0.9785 at 600 DPI; final-render IoU was 0.9129 / 0.8930 and 0.9377 / 0.9081 (Poppler / PDFium). These values are retained as historical pre-guard measurements, not as scores for the final 300 DPI file. The final guarded 300 DPI file was measured with Poppler; a new PDFium render was unavailable after the environment reboot. The small Poppler gain does not establish robust improvement across damaged glyphs: the output still regresses against source impressions overall. Do not treat the “repair” label as proof of visual improvement.

The 300 DPI `0` case `p06s0003` is a clear failure: source IoU 0.907 and pre-guard output IoU 0.584. It was assigned to a three-member prototype with similarity 0.903; the selected prototype's source-mask overlap was 0.751. The guard rejects it; final Poppler output IoU rises to 0.714, but remains below the scan. The 800% crop is preserved. This implicates prototype assignment/tracing and final rendering together; the current evidence does not isolate one as the sole cause. Existing GX geometry measurements found bbox scaling generally aligned well (P0 mean bbox IoU 0.972); uniform scaling regressed to 0.965 and is not used.

Poppler and PDFium sometimes disagree measurably (for example 300 DPI aggregate glyph IoU differed by 0.0125 on the pre-guard PDF). We preserve renderer-specific numbers rather than averaging them. The guarded 300 DPI Poppler renders and metrics are in `300/evaluation/`; pre-guard Poppler and PDFium renders are in `300/pre_guard/evaluation/`. The 600 DPI final PDF is byte-identical to the pre-guard file and its two-renderer measurements remain applicable.

## Same-input Acrobat XI comparison

The frozen three-page Adobe XI inputs were reconverted by current ScanWeave at identical page size and raster input. Adobe outputs were generated by Acrobat Pro 11.0.20 Paper Capture Plug-in with ClearScan (existing Adobe XI evidence records the Wine/runtime settings). The paired records and SHA-256 hashes are in `frozen_adobe_comparison.json`.

| Input DPI | Adobe XI bytes | ScanWeave bytes | Size ratio | Adobe mean glyph IoU (Poppler/PDFium) | ScanWeave mean glyph IoU (Poppler/PDFium) |
|---|---:|---:|---:|---:|---:|
| 300 | 46,213 | 1,960,987 | 42.4x | 0.7988 / 0.8682 | 0.8291 / 0.8698 |
| 600 | 51,429 | 3,353,502 | 65.2x | 0.8649 / 0.9130 | 0.9002 / 0.9213 |

Input glyph IoU to pristine was already 0.9891 at 300 DPI and 0.9946 at 600 DPI; neither converter improved this nearly clean source. Adobe uses three 150 DPI grayscale JPEG backgrounds and compact CID Type 0C fonts. ScanWeave currently emits one embedded TrueType font plus 93 image rows at 300 DPI and 81 at 600 DPI, including native-resolution fallback/artwork patches. It is smaller than searchable-raster, but far larger than Adobe XI. The result does not justify adopting Adobe's lossy background policy blindly; it identifies residual image representation and resource count as a significant size gap.

For the synthetic 8-page fixture, Poppler and PDFium extraction matches the supplied OCR at 300 DPI. At 600 DPI, PDFium matches, while Poppler's non-space sequence differs in 552 characters. In the separate three-page frozen comparison, Poppler `-raw` matches the supplied OCR on ScanWeave outputs; PDFium produces one U+FFFE in place of a hyphen. The same U+FFFE occurs in frozen pre-task ScanWeave output, so it is an inherited PDFium Unicode extraction issue. Adobe yields additional extracted characters on this fixture and does not match the supplied OCR exactly. OCR engine/text differences are not evidence of font quality.

## Fallback, tests and review

The named 300 DPI fallback `8` defect remains unresolved. For `p00s0001`, input/pristine IoU is 0.9172 and final output/pristine IoU is 0.7576 Poppler / 0.7551 PDFium. The decompressed XObject samples match the source crop and the PDF placement matrix bounding box is consistent with expected geometry; a small offset search and a row-inversion hypothesis did not explain it. The row-inversion change made output worse and was reverted. The remaining failure is in patch sampling/composition or renderer interaction, and raster fallback should not be described as undamaged.

Validation run:

- `cargo test -p scanweave-io`: passed (6 unit and 6 HOCR tests).
- `cargo test -p scanweave-cli`: passed.
- `cargo test --workspace --exclude m0-font-pdf`: passed.
- `cargo test -p m0-font-pdf --test m1b_behavior -- --skip regress_auto_reports_the_selected_candidate`: passed (12 tests).
- Full workspace test still fails at `m1b_behavior::regress_auto_reports_the_selected_candidate` (`reconstruct` vs expected `raster_baseline`). It failed on the starting revision before these edits and is recorded as inherited.
- `git diff --check`: passed.

Independent review found the faithful-mode `None` preservation behavior and protected-pixel handling corrected. Review also checked that vector-owned pixel suppression is gated on actual emission and that the low-resolution background/fallback layer order is sensible. The reviewer noted no focused test for fallback/artwork pixel fidelity; the current end-to-end Poppler/PDFium renders are evidence, but the fallback `8` counterexample remains.

No genuine receipt or historical-book page was present in the checked-out sample set. `qualification/fixtures/documents/doc4_invoice` is a test fixture and is not represented as real-domain evidence. **REAL-DOMAIN VALIDATION NOT RUN: no genuine sample in checkout.**

## Engineering conclusion

The integrated path now performs document-wide canonical reuse and real raster-ink suppression through the normal ClearScan profile. It vectorizes a substantial share of text, preserves searchable text, and produces smaller PDFs than the matched searchable-raster outputs at both resolutions. The final 300 DPI reuse guard rejects eight low-agreement healthy substitutions and produces a small Poppler improvement, but the output does **not** yet produce a generally more pristine glyph image on the M1-G fixture. The `0` assignment is still materially wrong and the fallback `8` remains defective. In paired Adobe comparisons (measured before the final guard) it is marginally closer by glyph IoU but 42–65 times larger.

The largest current quality limit is canonical glyph assignment/shape selection as rendered: the `0` failure is concrete and the accepted set as a whole regresses against pristine truth. The largest size limit is the residual native-resolution image patch population and its encoded bytes. These should be handled as product defects within the existing pipeline; the current output PDFs make both problems inspectable. No release qualification or default-profile change is claimed.
