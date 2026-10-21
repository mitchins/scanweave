# Wave 2 — contained Rust decomposition

Base: `22881dc49c57b9eaf642d583ea5c46a1e80b4642`, verified after PR #11 merged,
fresh main CI/Sonar passed and the open PR count reached zero. The complete
main intake is 121 unique OPEN HIGH findings, all Maintainability. This branch
targets exactly the nine originally assigned keys. No source scope, rules,
coverage settings or Quality Gate thresholds change. Wave 3 has not begun.

## Exact scope

| Sonar key | Existing function / change | Baseline complexity |
|---|---|---:|
| `AaFbqrv5Df3ZA7hnTDt_` | `pdf::assemble`: extract its existing ToUnicode CMap builder | 31 |
| `AaFbqrvpDf3ZA7hnTDt7` | `page_pdf::assemble_with_options`: extract ordered image-resource pool | 32 |
| `AaFbqrvuDf3ZA7hnTDt9` | `tonal_image::preserves_details`: name the existing ridge-preservation rule | 31 |
| `AaFbqrwMDf3ZA7hnTDuD` | `source_image::decode_rgb`: separate JPEG header validation/decoding | 31 |
| `AaFbqrwVDf3ZA7hnTDuF` | `visual_dict::count_components`: separate existing component flood fill | 31 |
| `AaFbqrwrDf3ZA7hnTDuJ` | `convert::to_ocr_page`: explicit OCR type imports | n/a |
| `AaFbqryBDf3ZA7hnTDuS` | `Validator::spans`: separate parent-reference validation after all span checks | 41 |
| `AaFbqryGDf3ZA7hnTDuU` | `json_util::rebuild_string`: separate existing Unicode escape branch | 31 |
| `AaFbqryNDf3ZA7hnTDuV` | `pdf_input::convert_pdf`: separate page-count and physical-page geometry parsing | 39 |

These are extractions of existing logical units, with unchanged public interfaces.
No changes to `convert_parts`, `clean_replaced_text`, canonical reconstruction,
text emission, document state machines, OCR settings or image encoding policy.
The two CMap builders remain distinct: their existing empty-codespace behavior
differs, so sharing them would not be a mechanical refactor.

Preserved invariants include JPEG header-before-decoder errors; dimension checks;
first matching Poppler size/rotation line; width-before-height errors; rotation
fallback; original floating arithmetic and strict comparisons; span-content
validation before parent checks; LIFO traversal and dy-before-dx neighbor order;
first-placement PDF resource IDs and collision-checked exact keys. Tests cover
these boundaries, including negative rotations, competing errors, malformed
buffers, reuse enabled/disabled, Unicode ownership and non-finite ridge inputs.

## Frozen document equivalence

The existing eight-page fixture runs through the normal `scanweave build` path
with both profiles. Evaluator references never enter conversion.

| Profile | DPI | Before bytes | After bytes | PDF equality |
|---|---:|---:|---:|---|
| ClearScan | 300 | 185,119 | 185,119 | SHA-256 identical |
| Faithful | 300 | 383,603 | 383,603 | SHA-256 identical |
| ClearScan | 600 | 258,720 | 258,720 | SHA-256 identical |
| Faithful | 600 | 577,922 | 577,922 | SHA-256 identical |

All 32 pages have exact before/after RGB sample hashes in **each** renderer:
Poppler at `-r 300/600` and PDFium at `scale=dpi/72`. This is cross-version
identity within each renderer, not a claim that Poppler and PDFium produce
identical samples. Both engines' extracted Unicode hashes also match for every
document. Byte equality includes ActualText, glyph programs, images and resource
references. The [machine-readable receipt](sonar-high-wave2-validation.json)
records PDF/render/text hashes, fixture hashes, executable identity and timings.
Generated PDFs/renders remain outside Git; frozen historical evidence is not
replaced. No expensive real-corpus regeneration is necessary for zero-byte-diff
maintenance.

A standalone differential compiles original-main and candidate JSON scanners
with the same compiler and compares 25,210 generated seeded/truncated/byte-mutated cases (not necessarily unique inputs).
There are zero differences in returned values, typed error context or panic
outcomes. Eight inputs panic in **both private rebuild implementations**; this
is an inherited internal parser quirk, not introduced or fixed here. Public
scanner malformed-input outcomes also match. Passing equivalence does not claim
that every existing parser behavior is correct; a behavioral correction needs a
separate contract and authorization, not concealment inside this refactor.

## Reproduction

Build the base and candidate in separate target directories or sequentially.
For each revision, DPI and profile:

```sh
cargo build --release --locked --bin scanweave
# Preserve the baseline executable before switching source revisions.
target/release/scanweave build \
  --bundle qualification/experiments/m1g/fixture/dpi300/input/document.json \
  --profile clearscan --output /tmp/wave2-300.pdf --report /tmp/wave2-300.json
sha256sum /tmp/wave2-300.pdf
pdftoppm -r 300 -png /tmp/wave2-300.pdf /tmp/wave2-300
pdftotext -layout /tmp/wave2-300.pdf -
```

Repeat with `dpi600`/600 and `faithful`. Hash decoded RGB pixels rather than PNG
container metadata. PDFium uses its bundled renderer and native text API.
Run `cargo test --workspace --locked` followed by denied-warning Clippy on the
three library/CLI packages. Do not compile into the same Cargo target directory
concurrently with executing doctests: the initial local baseline test run passed
all executable tests but a concurrent build invalidated dependency metadata for
rustdoc (`E0463`). This local qualification problem is retained in the receipt;
it is not a skipped test or a product failure. The final unfiltered run is
sequential.

## Mechanical qualification

All E0–E7 font/Unicode/ownership/determinism proofs pass. The eight P01–P08
visual failures and P08 PDFium cardinality/coverage finding exactly match the
committed historical report; green CI does not imply those limitations vanished.
The per-page first-word native PDFium queries are smoke controls, not exhaustive
Unicode search qualification. Independent read-only review verified the source,
tests and actual equality receipts and found no blocking new behavior change.

## Review and disposition

Independent read-only source review found no new behavioral difference in all
nine extractions. Final executed tests, CI, Sonar and CodeRabbit disposition are
recorded against the final PR head before merge approval. Main's nine original
keys remain OPEN until an approved merge and fresh main analysis verify closure;
a clean PR analysis alone is not called nine server-verified main fixes.
The remaining Wave 1 Python complexity finding stays explicitly open.
No merge or Wave 3 work is authorized by this implementation receipt.
