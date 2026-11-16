# TEXT-RESTORE-01 — investigation and rejected candidates

**Verdict: no converter change is ready to ship.** A conservative raster fallback restores much of the missing “613” and heading ink and removes their orange tint, but changes extracted characters/order on four development pages. A colour-only alternative improves the heading's colour while leaving “613” fragmented. Neither makes the French list stronger. The owner’s text-restoration success criteria are therefore **not met**. The experimental patch and local measurements are at `$B/text-restore/failed-candidates.patch` and `$B/text-restore/measurements.json`; `$B` is `/data/coding/scanweave/work/books01`. No generated pixels, OCR text or PDFs are committed.

## Causes

- **8967062, “613”:** the word is vector-owned. Foreground segmentation uses a page-wide 60-luminance-distance threshold; a single page-wide ink colour is the median of all detected foreground, including coloured shells. The vector is painted orange-brown, and its binary shape loses faint stroke portions. In the numeral box, only about 17% of pixels at least 20 luma below local paper also pass the page-wide segmentation threshold; this is a diagnostic, not a ground-truth stroke mask. A 200-DPI JPEG85 4:2:0 background and PDF compositing further soften remaining raster detail.
- **8967228, faint italic heading:** three OCR spans are vector-owned and receive the same artwork-contaminated page-wide paint. The baseline visibly recolours and fragments the heading; its 200-DPI JPEG residual is also softer than the 500-DPI source. The existing Adobe global fit is 8.12° and fails the predeclared 2° registration gate, so Adobe's image metrics are unavailable. An [illustrative crop using that rejected fit](/data/coding/scanweave/work/books01/text-restore/inspect/8967228-adobe-illustrative.png) is not a quantitative comparison.
- **12342014, French list:** the report records 353 visible and 199 invisible owners, with 150,562 text-ink pixels vector and 69,230 raster. Source-edge cleanup, binary contour decisions and the 200-DPI JPEG residual leave some letters softer than Adobe's reconstruction. The tested colour/fallback changes do not improve this page; its candidate PDF is byte-identical to baseline.
- **8966753, dense English:** the source is already faint. The baseline keeps 590 spans invisible and 380 visible, with 503 `UnsupportedContent` and 81 fidelity fallbacks. Its 1.467 MB comprises about 985 kB background JPEG, 214 kB font program, 211 kB foreground images and the remainder streams/structure. The proposed guard does not fire and its output is byte-identical; it offers no size or legibility benefit.

Historical-page retention is partly intentional: non-text contact, unsupported content and the 0.98 per-unit binary IoU gate route uncertain units to raster. Binary thresholding can also miss faint source coverage, so an outline can satisfy that gate while the actual character is damaged. The raster route is not necessarily source-exact at display: the existing compact residual can be resampled to 200 DPI and JPEG encoded. These are different failure points; none justifies relaxing the existing gates.

## Alternatives and results

The colour-only candidate estimated paint from the final vector-owned source pixels rather than page-wide artwork. It made the heading less orange, but “613” remained fragmented. The second candidate added a **new, stricter** safety gate: with at least 32 vector-owned pixels, a maximum RGB-channel difference of at least 20 between the owned-ink median and existing page-wide paint routed vector regions to the existing raster fallback. It changed no glyph-sharing, global DPI, background codec or existing safety threshold. The threshold was a bounded pilot heuristic, not a validated universal boundary. It fired on six of 36 pages. Its fallback is still subject to the existing 200-DPI JPEG path and may blur fine strokes.

In the “613” crop, source-ink recall under a fixed local-paper-minus-20 threshold improved from **0.857 to 0.968**, and source-ink mean ΔE2000 fell from **5.14 to 3.47**. On the heading, recall improved **0.819 to 0.941** and ΔE2000 fell **7.17 to 3.54**. The candidate still looks softer than the source; these threshold measurements are supporting evidence, not proof that all strokes or colours are correct.

The table shows **PDF size in kB / aligned text-region SSIM**. Source is the fidelity reference; higher SSIM does not prove better legibility. Candidate measurements reuse the baseline's accepted registration, and Adobe uses its unmatched default OCR language, has no Fraktur support and deskews.

| Page | Baseline | Rejected fallback | MRC | Adobe |
|---|---:|---:|---:|---:|
| 8967062 | 92.3 / .913 | 78.0 / .890 | 105.2 / .927 | 151.6 / .878 |
| 8967228 | 161.3 / .956 | 160.0 / .954 | 112.3 / .894 | 317.5 / unregistered |
| 8966753 | 1,467.0 / .989 | 1,467.0 / .989 | 185.9 / .940 | missing |
| 12342014 | 554.9 / .930 | 554.9 / .930 | 137.0 / .903 | 396.3 / .891 |
| Aventinus 0008 | 567.9 / .950 | 567.9 / .950 | 103.6 / .741 | 509.2 / .764 |
| Luther 0011 | 441.8 / .976 | 441.8 / .976 | 98.6 / .827 | 345.0 / .800 |
| Euler 0025 | 439.4 / .996 | 439.4 / .996 | 74.5 / .763 | 258.3 / .767 |

The three control PDFs were byte-identical to baseline. The list and dense page were also byte-identical. No owner was asked to adjudicate a new panel.

| Page | Reading CER baseline → rejected fallback | Search hits baseline → fallback |
|---|---:|---:|
| 8967062 | 3.385 → 3.376 | 0/0 → 0/0 |
| 8967228 | 1.378 → 1.378 | 0/0 → 0/0 |
| 8966753 | .014 → .014 | 19/19 → 19/19 |
| 12342014 | .555 → .555 | 15/15 → 15/15 |
| Aventinus 0008 | .559 → .559 | 6/7 → 6/7 |
| Luther 0011 | .227 → .227 | 7/9 → 7/9 |
| Euler 0025 | .611 → .611 | 15/19 → 15/19 |

The sampled search has no recognised GT words on the two affected plate pages; independently, PDFium finds `613` in both baseline and fallback. Across 36 pages, conditional literal search stayed **340/396**, and median reading CER stayed **0.337**. Nevertheless, PDFium reading-normalised extraction differed on four pages: Estor 0819, Benner 0013 and 8967062 changed an extracted hyphen to U+FFFE, and 9684341 reordered characters. Those are material unresolved semantic risks, not safe equivalence. The other 32 pages had identical reading-normalised extraction.

Across 36 pages, baseline → rejected fallback total size was **16,315,763 → 16,277,014 bytes**. Sum of per-page wall times was **985.9 → 1,358.5 seconds**, but the candidate ran concurrently with a Rust test build and timings are not a controlled performance comparison. All 36 conversions completed; original inputs and comparator outputs were reused.

Local source/baseline/candidate/MRC/Adobe 2× crops: [613](/data/coding/scanweave/work/books01/text-restore/inspect/8967062-final.png), [heading](/data/coding/scanweave/work/books01/text-restore/inspect/8967228-final.png), [dense English](/data/coding/scanweave/work/books01/text-restore/inspect/8966753-final.png), [French list](/data/coding/scanweave/work/books01/text-restore/inspect/12342014-final.png), [Aventinus](/data/coding/scanweave/work/books01/text-restore/inspect/aventinus_grammatica_1515_0008-final.png), [Luther](/data/coding/scanweave/work/books01/text-restore/inspect/luther_babstum_1526_0011-final.png), [Euler gutter](/data/coding/scanweave/work/books01/text-restore/inspect/euler_rechenkunst01_1738_0025-final.png). Unavailable or unregistered Adobe rows are labelled in the images.

The final experimental code passed `cargo test --locked -- --test-threads=1`, including the added owned-ink regression. Test-generated evidence files were restored. The extraction regressions above are the reason the candidate is rejected, regardless of the test results; no converter change is retained.
