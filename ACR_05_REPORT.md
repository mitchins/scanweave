# ACR-05 — Coherent raster/text composition

## Result and disposition

A small ClearScan layout correction replaces fragmented opaque paper/native crops
with the **existing coherent cleaned residual** when its existing JPEG encoding
is cheaper. It does not add an alpha pipeline, change JPEG settings, erase more
source ink, change fonts, or replace the PDF writer.

The financial PDF falls from **6,898,862 to 3,187,571 bytes**. Its image placements
fall from **1,892 to 13**, one residual per page. Independent inspection finds
locally more coherent paper, without the failed mask candidate's new rectangles.
Improvement is subtle at normal reading size and clearer in selected enlarged
regions. Unsupported raster text becomes softer; no material new character/mark
loss was identified in the inspected views. This is not a claim to have fixed
all faint fringes or typography inconsistencies.

| Complete ordinary-CLI output | ACR-04 bytes | ACR-05 bytes |
|---|---:|---:|
| Historical, 5 pages | 2,278,050 | 2,278,050 |
| Receipts, 10 pages | 1,288,188 | 1,288,188 |
| Financial, 13 pages | 6,898,862 | **3,187,571** |
| Mixed artwork/Linn, 2 pages | 1,130,058 | 1,130,058 |
| NARA forms, 2 pages | 859,524 | 859,524 |
| **32-page total** | **12,454,682** | **8,743,391** |

Financial saves **53.80%** and the corpus **29.80%**. Other19pages are byte-identical,
not merely similar. This remains 2.09× frozen Adobe XI's 4,178,103-byte corpus.
The objective is paper coherence; size is a useful consequence, not visual proof.

## Starting revision and provenance

Branch `product/acr05-seamless-compositing`, from PR#17's verified
`882e8f7de41204bed6d3730af69fbb3a497739a9`. PR#17 remained open; remote main was
`0ca94aecd74c35ea1b28bcebe7e11e863aae7f08`. No research predecessor was merged.
The implementation PR is stacked on ACR-04 and must not merge automatically.

The same five full source collections preserve document-wide OCR/donor context.
All35 frozen source/comparator SHA-256s were revalidated. Adobe, OCRmyPDF and
prior ScanWeave PDFs remain unchanged. The holdout was not opened.

Actual completed financial PDF:
`qualification/acr05/local/product/financial.pdf`, SHA-256
`32b7c13e664b32fadeea41b99d9299479f129bfac3bd20debbbf481a6f885e51`.
The ordinary corpus run used binary SHA-256
`2c29c89f6f9eeb9bd2445afdeb10d5aa0d20545b3deee3592a93dfdf44aafe7f`.
A later test-fixture-only correction/rebuild changes the executable hash, with no
non-test algorithm change; the rebuilt executable is retained separately and
its synthetic300 output is checked against the corpus-build executable.
See [manifest](qualification/acr05/manifest.json), [results](qualification/acr05/results.json)
and the local hash-bound reproduction archive for commands, binaries and scripts.
Tools match ACR-04's pinned Cargo dependencies and qualification environment
(Rust1.99.0, Python3.12, Poppler24.02, PDFium5.14, Tesseract5.3.4, pikepdf10.17).

## Root cause: two paper representations painted opaquely

The actual production path is:

1. `clean_replaced_text` makes a residual containing unsupported ink and paper,
   removing only emitted-vector-owned ink and independently qualified fringes.
2. A second call removes all recognized text from the *background-only* image.
3. `downsampled_background_patch` and `compact_paper_background` make a150/75DPI
   base from that background.
4. Raster fallback regions copy cleaned-source rectangles; `artwork_patches`
   adds32px cells, weak rules add strips, and paper/residual-detail passes add
   further exceptions. `coalesce_patches_rgb` expands touching/overlapping unions
   and recopies their complete rectangles from the cleaned source.
5. `page_pdf` paints reduced paper, opaque native crops, semantic text and vectors.

Consequently, crop paper and underlying paper have different sampling/encoding,
although both originate from the same scan. Native crops are not foreground-only.
Paint ordering alone is not wrong: replacing them with blank paper loses text.
A rectangle is not inherently a defect, and source illumination is not a halo.

The temporary instrumented ACR-04 converter reproduced its6,898,862-byte frozen
financial PDF byte-for-byte (baseline hash:
`8a8d5d32b710177c37b2fff4b2ad472ffc462f355626b5ac98f10d11bcae4182`).
Instrumentation was removed before product development. It captured original,
vector-cleaned and background-only pixels plus initial patch seeds.
**All1,879 native crops match their cleaned-source crop SHA exactly before encoding.**
There is no demonstrated recopy of original dark glyph cores in those crops;
1,032 crop bounds intersect visible glyph bounds, so source binding matters.

Conservative source-paper samples on pages1/2 show raw-paper versus reconstructed
paper mean-channel differences mostly zero (largest patch means below0.12),
whereas decoded crop-versus-reduced-base differences reach several levels.
Broader decoded-paper selection finds local blue-channel differences up to8.67.
These populations differ and are not one additive error budget. The principal
supported boundary mechanism here is **resampling/encoding of opaque source paper**,
not wholesale duplicated dark glyphs or a newly discovered global cleanup defect.
Faint glyph-shaped remnants are a separate, inherited issue.

[Patch provenance](qualification/acr05/patch-provenance.json) includes selected worst
objects, coordinates, actual bytes, fallback reasons, paint order, colour deltas
and the full local ledger hash. Initial fallback/artwork seeds are known; later
paper/detail/weak-rule seeds were not individually captured and remain explicitly
uncertain when no original seed intersects. No uncertain label is promoted to
pixel-ownership permission.

## Completed competing repairs

All shadow PDFs preserve the same font/text layer and physical page coordinates.
They are not final product measurements; rewrites include serialization effects.

| Candidate | Financial bytes | Finding |
|---|---:|---|
| A: source-paper matching | 7,271,592 | Better than B; thin rules soften; +5.4% over baseline |
| B: decontaminated foreground +8bit coverage/SMask | 17,728,351 | Rejected: new small rectangular surrounds; high resource cost |
| C: one existing cleaned residual | 2,920,643 | Selected shadow; coherent paper, disclosed raster softness |
| Actual Rust integrated C | **3,187,571** | Accepted on tested pages; same existing encoder, native CLI |

A estimated bounded local paper using15px closing and5px smoothing, then shifted
paper contribution toward the underlying base while retaining ink contrast.
B used the same estimate, straight foreground colour and grayscale alpha rather
than paper-contaminated RGB. Its small-mark decomposition/encoding was not robust:
visible new boxes appeared around digits, specks and a rule. Transparency alone
therefore fails this task; this result does not isolate mask sampling from
foreground colour error. Neither A nor B is production code.

Blinded X/Y review preferred Y(A), rejecting X(B) before reading their identity or
sizes. C then tested a simpler hypothesis: avoid the resolution/tone transition
rather than estimating paper again. It uses the *same already-cleaned source*
with the existing ACR-04 whole-residual representation. No erased ink is restored.
The Pillow shadow and Rust encoders yield different bytes; only the ordinary
Rust CLI result is claimed as a product improvement.

## Focused implementation

The previous whole-page decision compared **lossless Flate costs** and required
native area above20%, even though final ClearScan resources could use JPEG. Busy
pages1/2/13 could have hundreds of crops yet never reach that cost comparison.
Pages3/6/11 reached it but still chose layering. Those criteria do not measure
paper continuity or the actual supported representations' cost.

The new code retains the established fragmentation guard (>32 native regions),
but compares the existing whole-residual JPEG stream with the existing reduced
base/native-crop encodings. It removes the20%-area prerequisite, without changing
any ownership, glyph acceptance or protected-pixel threshold. On qualifying pages
it emits a full-page patch copied from **cleaned `patch_source`, never `input.rgb`**.
The existing writer supplies approximately200DPI Q85/4:2:0 and keeps physical extent.

Explicit caller-protected inputs skip this new comparison. Non-tonal/ineligible,
non-beneficial or failed optional encodings retain the earlier layout. Existing
whole-page area fallback is unchanged. No new public option or dependency.

The chooser estimates image-stream cost, **not** complete alternative-layout PDF
cost or cross-page reuse. Final assembly compares lossless/tonal PDFs of the
chosen layout only. Independent review calls this a non-blocking approximation;
near ties/shared resources may choose a non-smallest layout. Actual complete
corpus sizes, not that estimate, establish this mission's saving.
[Decision audit](qualification/acr05/decision-audit.json) records every financial page.

## Visual, boundary and typography evidence

Independent review inspected all13 final financial overviews in both engines,
fixed native300DPI windows on pages1,2,11,13 and controls7,8, and font/nonfont
ablations. Source-selected boxes were frozen before candidates; worst-patch
coordinates were selected from the baseline ledger. The other19pages reuse ACR-04
visual qualification only because their complete PDFs are byte-identical.

Paper is locally more coherent; no new material lost numeral, rule, mark, colour,
layout defect or cleanup rectangle was found in those views. Unsupported words
such as SELECTMEN/Moulton are **noticeably softer at high zoom** than native crops.
This is a real resolution trade-off, not a packaging-only or sharpness improvement.
The existing historical shaded page, red seal, thermal receipt, Linn and NARA
controls are unchanged. No general guarantee is inferred for every unseen mark.

At frozen exception boundaries, the source-relative paper-step diagnostic uses
3pixel strips, at least12 source-paper positions and matched300DPI coordinates:

| Renderer | ACR04 mean /95th percentile | ACR05 mean /95th percentile |
|---|---:|---:|
| PDFium | 0.368 /1.308 | 0.714 /2.487 |
| Poppler | 1.624 /7.479 | 1.295 /4.584 |

These are0–255 channel-level errors relative to source paper, **not a universal
seam score**. Removing grain and changing sampling can worsen this diagnostic,
as PDFium shows, despite avoiding independent opaque-image boundaries. The
renderer disagreement and worse PDFium metric are preserved, not hidden behind
a favourable mean. Visual context, readability and source-relative detail review
remain necessary. See `boundary-summary.json`; full edge records remain local.

Fonts-only renders of pages1/2/11/13 are pixel-identical before/after in both
engines. Font programs, ToUnicode and text operator sequences match across all32
pages. Glyph identities/counts/placement and cleanup counts are unchanged.
All13 final raw residual hashes match the captured vector-cleaned source; a
bicubic decoded-raster diagnostic finds no below128 samples on its tested cleared
dark-core cohort. This does **not** prove all weak fringes are gone.

Baseline75DPI background-only, native exceptions, vector-only and final views
remain in local layer atlases. The new paper and unsupported ink share one image:
there is no independently emitted paper-only/exception layer to ablate. It is
reported as a combined residual, not an invented independent background layer.
Weak source fringes and differing raster/vector sharpness remain visible;
intrinsic reconstructed contour irregularities are unchanged and out of scope.

## Byte accounting and functionality

| Financial stream/resource class | ACR04 | ACR05 |
|---|---:|---:|
| Raster | 5,275,473 | 1,973,037 |
| Font programs | 1,065,434 | 1,065,434 |
| Page content | 149,888 | 121,243 |
| Other structures/resources | 408,067 | 27,857 |
| Images | 1,892 | 13 |
| Extra masks | 0 | 0 |

No bytes inside a compressed image are allocated to paper/text by pixel area.
The coherent image contains unsupported text and other retained source content.
Across32pages: raster6,640,529; fonts1,632,820; content321,334; other148,708 bytes,
506 unique images. [Results](qualification/acr05/results.json) and
[page accounting](qualification/acr05/pages.csv) distinguish unique resources and
page references.

Native PDFium and Poppler extraction is unchanged on all32pages; financial text
operators including ActualText are byte-identical. CORD numeric queries remain
**17/49 with identical per-query outcomes**. The prior page7 rerenderOCR75→15
regression remains: that control's representation is unchanged; optical OCR still
reads15 while visible75 was previously confirmed. No OCR repair is claimed.
Other rerendered optical token differences remain in `rerender-ocr.json`, separate
from unchanged native semantics.

Financial conversion:467.40s, peak RSS1,467,936KiB, versus archived ACR04 477.11s /
1,371,484KiB. Concurrent qualification differs; no causal speedup is asserted.
New layout costing does additional encoding work and can increase memory.

## Verification and remaining limitation

* Unfiltered locked Rust workspace:138tests pass, including donor repair; denied
  warning Clippy and15existing Python CI scripts pass.
* E0–E7 pass. Historical P01–P08 failures remain separately disclosed and unchanged;
  green CI does not establish that those visual failures disappeared.
* qpdf syntax and OTS font validation pass for all five completed PDFs.
* Repeated synthetic300 output is deterministic; faithful forms remain exactly
  855,127bytes /SHA `5f17cd97caa7caa79f931edc63692fe2551235f4aa658072cf24482f0f78188c`.
* Synthetic300:173,746→141,085bytes. Same552-instance isolated exact-size IoU:
  PDFium0.95667259→0.95850952; Poppler0.94973258→0.95452117; search unchanged.
  This is final composition, not improved font geometry. Synthetic600 remains
  byte-identical at189,052bytes; counts remain531/552 and517/552.
* Independent code review found no blocker, with the stream-cost caveat above.
  Independent final visual review passes tested content with explicit softness,
  residual-fringe and sampling limitations. No automatic merge.

**Remaining compositing/typography limit:** faint residual source edges and
inconsistent reconstructed-versus-raster stroke shape/sharpness remain after
paper rectangles are removed. This mission does not justify wider ink erasure or
another font redesign. Any later repair must qualify those specific footprints
and glyph appearances together; paper alpha alone was demonstrably insufficient.
