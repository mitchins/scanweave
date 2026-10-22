# ACR-01 — Adobe-competitive raster reconstruction

## Result

**Implemented native-resolution JPEG85 whole-page tonal fallback in ClearScan.**
The five complete development documents (32 pages) shrink from **45,453,391 B to
18,556,766 B: 59.17%**. Existing fonts, page text operators, ToUnicode, extraction
and glyph ownership are unchanged. Faithful retains its preservation path.

Base: `0ca94aecd74c35ea1b28bcebe7e11e863aae7f08`;
branch: `product/adobe-competitive-raster`. PR14 remains research-only, open at
`ffa604ebd4ab47a6af67d2696a5c8fc15fbf3f2e`, not merged. Its object findings and
fixed-coordinate renderer were reused. The R1 report is preserved at `7c22c6d`.
No holdout, pristine source oracle, OCR labels or competitor assets entered encoding.

## Quality–size frontier

Seven source-selected pages: history-01/02/04, cord-05, annual-111, scan-linn and
nara-form-01. Six settings produced **42 complete raster-only probe PDFs**:

| Raster probe | Seven-page PDF sum | Findings |
|---|---:|---|
| Native 300-DPI JPEG70, 4:4:4 | 4,800,160 B | Strong blinded visual group; more edge/tonal error than JPEG85 |
| Native 300-DPI JPEG85, 4:4:4 | 6,574,518 B | **Selected:** strong detail and colour, ample practical saving |
| 200-DPI JPEG85, 4:4:4 | 3,522,248 B | Readable but softer small serifs, handwriting and ornament |
| 16-colour Indexed/Flate | 4,920,794 B | Posterized photographic tones and altered seal colour |
| 32-colour Indexed/Flate | 6,643,923 B | Similar content-specific colour/tonal limitations |
| Layered mask300 / background100 / foreground-colour75 DPI | 1,531,004 B | Smallest; substantial contour/texture changes, not qualified as universal default |

JPEG probes used Pillow/libjpeg, fixed qualities and no chroma subsampling. Indexed
probes used median-cut, no dithering, 8-bit indices, predictor15 and Flate6. Fourteen
same-quantized-sample RGB/Indexed controls separate representation savings from
upstream quantization damage; decoded RGB hashes match. They do not qualify colour
quantization. Layered masking used a source-only local Gaussian paper estimate,
binary foreground mask and weighted colour layers, with conventional PDF images
and a soft mask. It contains no borrowed AGPL code or symbol substitution.

The layered probe is the best **size-focused** result, not a demonstrated product
winner. JPEG85 is the best **visual-quality/balanced** choice here: blinded review
ranked native JPEG70/85 together, while diagnostic edge/tonal errors favour85 and
its integrated saving is already substantial. Lower DPI is not required for this
improvement. No further qualities, masks or parameter sweeps were tried.

These probes are not ScanWeave integration claims. Product results below come from
ordinary CLI conversions of the original **complete collections**, preserving
multi-page witnesses and font context.

## What changed

- `tonal_image.rs`: deterministic JPEG85 encoding using the existing Rust image
  encoder, native dimensions and full chroma sampling. Existing bounds reject
  invalid, small, near-bitonal and oversized buffers. No pixel-exact veto is used
  to disqualify normal JPEG tonal/noise changes.
- `page_pdf.rs`: a single full-page tonal residual is eligible even if vector
  glyphs are present. Encoding consumes the **emitted cleaned patch**, not original
  source RGB, so superseded ink is not restored. Both resource and complete-PDF
  size comparisons retain the existing representation when compaction costs more.
- `convert.rs`: single-page ClearScan library/build conversion uses the same tonal
  assembly as document conversion. Faithful still takes its original branch.
- `document.rs`: explicit caller-protected regions conservatively disable the
  tonal candidate for the document. This preserves the caller's native contract
  without a new ownership system. Verified source JPEG passthrough remains intact.

Native exception patches and reduced-paper machinery are unchanged. A large
unresolved component may still yield a full-page image, but that image need not
remain lossless RGB. Unsupported text stays visibly represented independently of
OCR. No OCR, glyph grouping, canonical outlines, raster cleanup or Unicode logic
was changed. No new executable dependency, public profile or quality slider.

## Complete native product PDFs

| Collection | Previous ScanWeave | ACR-01 | Reduction |
|---|---:|---:|---:|
| Receipts, 10 pages | 6,945,090 | 2,208,177 | 68.21% |
| Historical, 5 pages | 24,637,206 | 5,114,421 | 79.24% |
| Financial, 13 pages | 9,782,629 | 9,018,954 | 7.81% |
| Mixed, 2 pages | 3,228,942 | 1,355,690 | 58.01% |
| Forms, 2 pages | 859,524 | 859,524 | 0% — existing encoding won |
| **Total** | **45,453,391** | **18,556,766** | **59.17%** |

Frozen comparator totals: Adobe XI **4,178,103 B**, OCRmyPDF-O3 **15,315,903 B**,
Internet Archive **3,059,648 B**. ACR-01 is **4.44× Adobe** and **1.21× OCRmyPDF-O3**.
Original matched inputs total81,969,566 B. Competitor outputs were not regenerated.

| Encoded resource class | Previous | ACR-01 |
|---|---:|---:|
| 19 whole-page images | 35,763,822 | 8,868,097 |
| 2,353 native exceptions | 5,541,808 | 5,541,808 |
| 13 reduced-paper images | 1,589,328 | 1,589,328 |
| **All image streams** | **42,894,958** | **15,999,233** |
| Embedded font programs | 1,632,820 | 1,632,820 |

Seventeen whole-page resources use DCT; two retain Flate. Their placement resolution
is unchanged. Page content349,979 B, other streams63,940 B and serialized remainder
510,794 B complete the new accounting. No content is omitted to obtain these totals.
`qualification/acr01/page-results.csv` reports every page's referenced image bytes,
image counts and unchanged ownership/CID draw counts. Shared resources and fonts
are not apportioned by image area; page-reference bytes are not additive file sizes.

## Visual and functional qualification

The separate read-only reviewer inspected blinded C1–C6 probes without settings or
byte counts, then reviewed actual Rust output in PDFium and Poppler at native
300-DPI coordinates and enlarged details. All seven integrated cases passed under
the revised material-content contract. Inspection found:

- Receipt amounts45,000/55,000/47,000/33,000/39,000 and separators remain readable.
- Historical ornament, punctuation, stamp wording/red outline, faint reversed
  printing and shaded green book-edge colour remain visible.
- Linn body serifs/punctuation remain readable, with no new patch seams or ghosts.
- NARA rules, handwritten name and signature are unchanged; the entire two-page
  PDF is byte-identical to baseline.
- Financial numeric column185,5,1,7,4,1,1 and total204 remain clear. An independent
  source-selected supplement `[.78,.64,.97,.91]` was added because the old financial
  crop largely missed that column; this correction is recorded locally.

JPEG grain and edge-tone changes are disclosed and accepted; this is not pixel-
exact preservation or a claim that reconstructed typography improved. The indexed
and simple layered probes showed greater colour/contour changes and were not
selected. Normal-scale corpus overviews and source-relative diagnostic metrics
supplement selected detailed regions; they do not certify every faint mark on
all32 pages. Existing OCR failures and historical font limitations remain.

For **all32 pages**, decoded page text/graphics operators, embedded font programs,
ToUnicode streams, geometry, occurrence/reconstruction records and extraction
match the frozen product. Native PDFium/Poppler receipt numeric search stays
**17/49** in both engines. Glyph reuse and source-ink cleanup are unchanged.
The maintained raw CID auditor counts784 Linn draws and504 forms draws before and
after; these include the existing draw inventory and differ from older748/500
figures. No increased coverage is claimed or inferred from those counting methods.

## Tests, performance and reproducibility

New Rust tests cover native dimensions,4:4:4 sampling, deterministic encoding,
thin rules/decimal-sized marks, invalid buffers, cleaned-versus-original samples,
serialized size selection, lossless entry points, both single/document APIs and
explicit caller protection. Unfiltered workspace Rust tests, denied-warning
Clippy and the existing Python qualification/search/paint/translation controls
passed locally. qpdf and OTS validate all five product PDFs/fonts. Fresh PR CI and
Sonar results are recorded on the PR, not inferred from local tests.

Synthetic300-DPI output remains **185,119 B** and the600-DPI PDF is also byte-
identical to its frozen reference. Matched real faithful forms remain **855,127 B**
with identical SHA-256 under old/new binaries. Equal PDF bytes preserve both-renderer
results; independent rendering is also checked through existing controls.

Measured native collection runs (two conversion workers, not isolated timing):
receipts28.52s/458,964KiB peak RSS; historical61.67s/725,740KiB;
financial446.21s/1,424,792KiB; mixed99.31s/302,128KiB; forms39.88s/379,108KiB.
Do not infer a controlled runtime speedup from older archived runs. Financial
processing and document memory remain operational costs, not solved by this codec.

`qualification/acr01/run-manifest.json` records fixed settings, tool versions,
input/manifests/binary hashes and local script identities. `qualification/acr01/README.md`
gives local reproduction commands. Actual PDFs, per-resource accounting, all probe
and integrated renders, diagnostics, reviewer records and logs remain under ignored
`qualification/acr01/local/`. Large data and experimental PDFs are not in Git.
Rust tests regenerate some historical evidence paths: those test-generated files
were archived locally and original tracked evidence restored byte-for-byte.
The sealed holdout remains unopened. No automatic merge is authorized.

## Next measured bottleneck

Simple full-resolution JPEG closes most of the initial whole-page cost without
requiring MRC. It does **not** establish that JPEG alone can reach Adobe's4–6MB.
Financial output now accounts for48.6% of the remaining PDF bytes; unchanged native
exceptions alone cost5.54MB, and whole-page tonal payload still costs8.87MB.

The next bounded milestone should target the financial collection's retained text/
rule exception representation, comparing a source-supported high-resolution mask
with compact colour layers against the current exception resources. The present
MRC probe's colour/contour weaknesses must be addressed before such a design ships.
That is a conditional next task, not another implementation in ACR-01. Preserve
faint digits, rules, signatures and colour; do not chase Adobe's size through
unsupported character substitution or content omission.
