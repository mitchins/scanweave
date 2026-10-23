# FONT-02 — Render-grounded glyph reuse

## Phase 1: required-program construction

Starting product: remote `main` at `6cc38698f94952dbca3ea187dea6ca2892e6eb54`.
Branch: `product/font02-required-glyphs`. No glyph matching, contour tracing,
OCR, raster ownership, repair threshold or composition changes in this PR.
Healthy reuse and damaged repair remain separate subsequent experiments.

### Implemented change

The document union previously included every traced candidate, including rejected
candidates never referenced by emitted text. Before constructing the shared
ClearScan font, collect required visible occurrence shapes/CIDs, whole-span
invisible-owner CIDs and per-character invisible-owner CIDs. Retain their shape
programs in original order, compact both tables and remap every reference.
`.notdef` remains mandatory; owner-only fonts retain their real placeholder.
All outlines are simple TrueType glyphs: there are no composite dependencies.
The reconstructed and raster-baseline candidates use the same remapped tables.

Recompute glyf/loca, hmtx, hhea, maxp, nominal cmap and PDF CID/GID/Unicode tables.
Retain the original conservative **head design bounding box**, which remains
valid for all required glyphs. This is metadata, not an unused outline. The
required-program builder also accounts for mandatory glyph point/contour maxima
and supplies a nominal U+0000→`.notdef` cmap for a textless font. No searchable
PDF character is added. The historical faithful builder is unchanged.

### Why the FONT-01 subset changed Poppler pixels

A controlled FontTools subset retained every used coordinate, endpoint, flag and
advance but tightened `head.yMin` from −31 to −13. Restoring only the original
`yMin` restored every pixel on all 13 financial pages in both renderers at
150 DPI. Restoring hhea, maxp, OS/2 or cmap individually did not fix page 7;
restoring xMin/xMax/yMax individually did not fix it either. Restoring head.flags
alone had already failed in FONT-01. Thus this emitted metadata change is a
reproduced cause; the internal Poppler/FreeType code path is not inferred.
The Rust construction keeps the design envelope while recomputing retained
hhea (descender −13), maxp and other tables. Actual output checks below pass.

### Complete ordinary-CLI result

| Financial document (13 pages) | Baseline | Required programs |
|---|---:|---:|
| Complete PDF bytes | 3,187,571 | 2,849,237 |
| TrueType glyph slots | 3,264 | 2,238 |
| Decoded font bytes | 1,904,648 | 1,303,200 |
| Encoded font bytes | 1,065,434 | 727,259 |
| Visible glyph draws | 3,717 | 3,717 |

Complete-PDF saving: **338,334 B (10.61%)**. Encoded font saving: 338,175 B;
the remaining 159 B is net serialization/table/content cost. No raster savings
are claimed. FONT-01's 1,027 unpainted slots included mandatory `.notdef`;
1,026 unnecessary programs are removed, with `.notdef` retained. This is
required-program elimination, **not additional canonical reuse**.

Baseline PDF SHA-256: `32b7c13e664b32fadeea41b99d9299479f129bfac3bd20debbbf481a6f885e51`.
Candidate: `74c31136d00a18dbf05fba2d7fba59c85cc201a57ae65d77999a025a692fab0f`.
Full PDFs and renders remain under ignored `qualification/font02/local/`.
Machine-readable measurements: [required-glyph-results.json](qualification/font02/required-glyph-results.json).

### Equivalence and qualification

* All 13 pages: PDFium and Poppler pixel-identical at 150 and 300 DPI (52 checks).
* Every visible/invisible Tj: exact Unicode, glyph coordinates, endpoints, flags,
  hmtx and text matrix after CID/GID remapping. Normalized graphics operators match.
* Encoded image resources unchanged. Native extraction identical in both engines.
* qpdf and OTS pass. Explicit empty and owner-only PDFs pass OTS and qpdf.
* Synthetic 300 DPI: **141,085 B**, byte-identical; both engines checked at 300 DPI.
* Synthetic 600 DPI: **189,052 B**, byte-identical; both engines checked at 600 DPI.
* Faithful forms: **855,127 B**, SHA-256
  `5f17cd97caa7caa79f931edc63692fe2551235f4aa658072cf24482f0f78188c`, byte-identical.
* Initial complete workspace tests and configured denied-warning Clippy passed;
  final clean-build CI and Sonar status will be recorded in the PR closure.
* Independent code review found a mandatory-glyph maxp edge case; it was fixed
  and covered by empty/owner-only table tests. No remaining mapping/bounds blocker.

The first financial CLI run took 496.86 seconds, peak RSS 1,466,412 KiB.
This is an operational measurement, not a speedup claim. A final-binary repeat
is running to verify deterministic serialization.

### Reproduction

```sh
cargo test --workspace --locked
cargo clippy --locked -p scanweave-core -p scanweave-io -p scanweave-cli -- -D warnings
cargo build --release --locked -p scanweave-cli
target/release/scanweave qualification/pdf_packaging/groups/financial-input.pdf financial.pdf
# Existing matched synthetic bundles, with their document-wide donor context:
target/release/scanweave build --bundle qualification/experiments/m1g/fixture/dpi300/input/document.json --profile clearscan --output synthetic-300.pdf --report synthetic-300.json
target/release/scanweave build --bundle qualification/experiments/m1g/fixture/dpi600/input/document.json --profile clearscan --output synthetic-600.pdf --report synthetic-600.json
```

Local read-only verification scripts, table-isolation controls, exact commands,
logs and render hashes are preserved in `qualification/font02/local/`.
Historical inputs/comparators and sealed holdout are unchanged. Rust tests write
legacy evidence locations; those generated changes were copied locally and the
tracked historical evidence restored before publication.

## Phases 2–5: pending, not a production claim

The 42-e registered substitution study, canonical grouping/fitting and separate
constant repair experiment have not yet been qualified. FONT-01 face-label
metrics remain diagnostic; they do not establish rendered interchangeability.
No threshold was lowered and no speculative glyph merge was shipped by Phase 1.
