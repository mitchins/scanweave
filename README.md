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

## Status

Scanned-document reconstruction is a research-grade pipeline. Milestone state:

| Milestone | State | Evidence |
|---|---|---|
| M0 / M0-Q | PROVISIONAL (accepted baseline, known inherited visual-gate failures) | `M0_Q_REPORT.md` |
| M1-A | CLOSED (independently approved) | `M1A_REPORT.md` |
| M1-B | CLOSED (independently approved + operator-review corrections) | `M1B_REPORT.md` |

**Honest limitations:** the 8 default fixtures still fail the strict visual
gates (inherited, documented, thresholds never relaxed); PDFium appends an
all-fallback line's owners at the end of its extraction order (mixed lines are
fixed); single-image sources only; no benign corpus has been mounted (the
corpus holdout is sealed). See the reports for the full list.

## Build

```bash
cargo build --release
```

Requires a Rust toolchain (2021 edition). The qualification harness
additionally needs Python 3.12 with `pypdfium2`, `numpy`, `Pillow`,
`fontTools`, `jsonschema` (see `qualification/.venv`), plus Poppler's
`pdftotext`/`pdftoppm`.

## Usage

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

- Apache License, Version 2.0 ([LICENSE-APACHE](LICENSE-APACHE))
- MIT license ([LICENSE-MIT](LICENSE-MIT))

at your option. Unless you explicitly state otherwise, any contribution
intentionally submitted for inclusion in the work by you shall be dual licensed
as above, without any additional terms or conditions.

## Contributing

This is a research codebase: behaviour changes come with a regression test and
an independent review, and no threshold is ever relaxed to make a gate green.
`qualification/policy/` records every policy revision explicitly.
