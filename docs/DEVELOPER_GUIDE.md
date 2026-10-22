# Developer guide and historical implementation notes

Preserved from the pre-consolidation README at `1597671`. The root README is the current quickstart. Detailed guarantees and measurements below have their stated fixture scope; historical claims are not universal product guarantees.

# ScanWeave

**A reconstruction pipeline for scanned documents: vectorize what is provably
safe, raster-fallback what is not, and keep every page searchable.**

ScanWeave converts a page raster plus an OCR page (word/char boxes with a
declared pixel binding) into a single searchable PDF whose text layer is bound
to the *visual* evidence rather than to OCR labels alone. The pipeline is built
around one question: **which ink can be safely turned into vector glyphs, and
which must be preserved as exact source pixels?**

- **Ownership solver** — many-to-many mapping between connected ink components
  and OCR symbol boxes. Touching characters merge into one unit that carries
  every span involved; disconnected marks (dots, dakuten) stay attached; ink
  that extends beyond its symbol boxes is *suspect* and never vectorized.
- **Transactional fallback** — a region that is suspect, that touches non-text
  (rules, stamps, barcodes), that is caller-protected, or whose traced outline
  fails the fidelity policy degrades to an exact source raster patch plus an
  invisible label overlay. No pixel is discarded and no label is lost.
- **One shared font** — one CID per (glyph shape, semantic string) pair across
  the whole document, so repeated content costs nothing extra. Wrong OCR labels
  never corrupt the visual: the shape and the string travel independently.
- **Honest measurement** — every run reports the candidates it actually
  serialized and measured (vector vs whole-page searchable raster, ranked by
  real bytes), the per-occurrence ink IoU, coverage denominators, and the
  byte accounting of what was emitted.

## Current functionality

`scanweave input.pdf output.pdf` runs Tesseract, collects document-wide glyph
observations, reconstructs and reuses supported canonical outlines, removes
superseded source ink, and assembles a searchable layered PDF. ClearScan is the
PDF-to-PDF default. `--profile faithful` remains an independent preservation
profile.

ClearScan retains native samples for verified full-page image inputs near the
requested resolution. Other page graphics, crops and rotations use Poppler.
Verified source JPEG resources remain reusable without recompression. Eligible
whole-page tonal residuals, including pages with emitted vectors, may use
optimized Q85 4:2:0 JPEG at approximately 200 DPI when encoded savings justify
reduction. Eligible tonal native exceptions may use source-resolution Q90 4:4:4;
binary and tiny resources retain lossless encoding. Complete PDF size selects
the beneficial candidate. Verified source JPEG passthrough remains unchanged.
Paper grain and small tonal differences are intentionally permitted; this is not
a pixel-preservation guarantee. Encoding uses already-cleaned residual pixels,
so this change does not restore source ink beneath vector glyphs. Faithful does
not use these lossy representations. See [ACR-04 measurements](../ACR_04_REPORT.md)
for exact eligibility, quality evidence and limitations.
Sparse OCR can retry Tesseract's block layout when confidence and character-box
evidence support it. No new OCR model is required.

Real scans remain challenging: some receipts yield no usable OCR, historical
styles may provide no accepted vectors, and preserved tonal imagery can remain
much larger than Adobe/OCRmyPDF output. Search correctness depends on the supplied
recognition. See [real-document results](../CLEARSCAN_REAL_DOCUMENT_REPORT.md) and
[packaging results](../CLEARSCAN_PACKAGING_REPORT.md) for actual measurements and
known failures. Earlier milestone reports document historical development;
M1-C is not the current feature set. The independent holdout remains sealed.

### Measured real-document state

On the fixed 32-page development corpus, current ClearScan outputs total
12,454,682 bytes versus matched ACR-01's 18,556,766 bytes (32.88% smaller).
See the [ACR-04 report](../ACR_04_REPORT.md) for source-detail checks and limits.
Whole-page residuals and eligible native exceptions can use lossy JPEG;
faithful remains independent and unchanged.
Adobe XI totals 4,178,103 bytes on the same inputs: substantial tonal-raster
and shaded-page limitations remain. CORD annotated numeric search is 17/49;
some pages still yield no usable OCR or vector reconstruction.

The accumulated implementation and whole-page compaction are merged in
[PR #1](https://github.com/mitchins/scanweave/pull/1) and
[PR #4](https://github.com/mitchins/scanweave/pull/4). Rejected shaded-paper and
fringe experiments (#2/#3) are closed unmerged; their evidence branches remain
available. No rejected reconstruction path was promoted.
The damaged-crossbar donor regression is now corrected by selecting a supported
actual witness when a cohort medoid is unsuitable; all original assertions and
thresholds remain. See [the repair evidence](../qualification/pr_closure/DONOR_FIX.md)
and [publication status](../GITHUB_CONSOLIDATION.md) for CI/review history. No skipped
local test is presented as a green workspace run.

## Build

```bash
cargo build --release
```

Requires a Rust toolchain (2021 edition). The qualification harness
additionally needs Python 3.12 with `pypdfium2`, `numpy`, `Pillow`,
`fontTools`, `jsonschema` (see `qualification/.venv`), plus Poppler's
`pdftotext`/`pdftoppm`.

## Usage

Convert an image-only scanned PDF directly:

```bash
./target/release/scanweave input.pdf output.pdf
# Optional: --dpi 600 --lang eng+jpn --profile faithful
```

This path defaults to ClearScan and 300 DPI. Install Poppler (`pdfinfo`,
`pdftoppm`), Tesseract and the requested language data first (for example,
`apt install poppler-utils tesseract-ocr tesseract-ocr-eng`). The converter
imports supported native full-page image samples or renders cropped/rotated
pages, obtains Tesseract character boxes, and sends
normalized, pixel-bound OCR to the existing document converter. It preserves
physical page geometry; it does not reuse pre-existing PDF text. Pages where
Tesseract finds no words remain images, with an explicit warning.

`output.pdf.json` records the input hash, tool identities, raster/OCR hashes,
hOCR, effective arguments and conversion results. Temporary inputs are removed
automatically. Publication uses unique same-directory temporary files; PDF and
report are two separate renames. Source-image hints have separate 512 MiB caps
on aggregate decoded work and retained encoded bytes, checked before decoding.
These are not a process peak-memory limit. The document budget is 512 MiB of
RGB page samples, with an 80-million-pixel per-page cap. Split larger documents.
The established `scanweave-cli` binary remains an alias. The image/bundle CLI
and library interfaces below remain available.

See [real-document results](../CLEARSCAN_REAL_DOCUMENT_REPORT.md) for current
measurements, representative PDFs and real-document limitations.


One page (hOCR or the normalized OCR JSON):

```bash
scanweave build page.png --ocr page.hocr --dpi 300 \
    --mode auto --output out.pdf --report out.json
```

A whole document from a hash-verified bundle (per-page source/OCR pairing):

```bash
scanweave build --bundle document.json \
    --mode auto --output document.pdf --report document.report.json
```

Modes: `reconstruct` (vector + fallback patches) and `auto` (ranks the
reconstruction against the whole-page searchable raster baseline by actual
bytes, with the fidelity policy as a hard gate). `--min-ink-iou F` sets the
fidelity threshold explicitly; the default is the SPEC's conservative 0.98.

## Layout

```
crates/scanweave-core   # schema types: OCR page, bundle, limits, pixel hashing
crates/scanweave-io     # ownership, planning, tracing, fonts, PDF assembly,
                        # one-page convert + multi-page document convert
crates/scanweave-cli    # `scanweave build` (single page and --bundle)
probes/m0-font-pdf      # the qualification harness's measuring instrument
qualification/          # gates, experiments, baseline comparisons, fixtures
```

## Qualification

```bash
cargo test                                            # unit + behaviour tests
qualification/.venv/bin/python qualification/checks.py    # e-proofs + visual gates
qualification/.venv/bin/python qualification/test_text_search.py
qualification/.venv/bin/python qualification/test_m1b_paint_fidelity.py
qualification/.venv/bin/python qualification/test_m1b_document_search.py
qualification/.venv/bin/python qualification/test_m1b_baselines.py
```

The harness renders with two independent engines (Poppler and PDFium) and
compares against the source raster at native scan DPI; search gates use native
PDFium find. Nothing is gated on a renderer's own extraction order alone.

## License

Dual-licensed under either of

- Apache License, Version 2.0 ([LICENSE-APACHE](../LICENSE-APACHE))
- MIT license ([LICENSE-MIT](../LICENSE-MIT))

at your option. Unless you explicitly state otherwise, any contribution
intentionally submitted for inclusion in the work by you shall be dual licensed
as above, without any additional terms or conditions.

## Contributing

This is a research codebase: behaviour changes come with a regression test and
an independent review, and no threshold is ever relaxed to make a gate green.
`qualification/policy/` records every policy revision explicitly.
