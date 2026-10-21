# Frozen raster competitor forensics

Read the root `CLEARSCAN_RASTER_COMPETITOR_FORENSICS.md` and `questions.md` first.
This harness is read-only with respect to frozen inputs/competitors. New derivatives
and renders go under ignored `local/`; **never replace a comparator to reproduce a result**.
The sealed holdout is not an input to any command.

## Reproduce

From the repository root, with the existing frozen files restored locally:

```sh
python3 -m venv qualification/.venv
qualification/.venv/bin/pip install --require-hashes --only-binary=:all: -r .github/requirements-ci.txt
# System Poppler pdftoppm/pdftotext are also required.
V=qualification/.venv/bin/python
$V qualification/test_raster_competitors.py
$V qualification/raster_competitors/run_inventory.py
$V qualification/raster_competitors/account.py
$V qualification/raster_competitors/render_compare.py
$V qualification/raster_competitors/text_inventory.py
$V qualification/raster_competitors/layers.py
$V qualification/raster_competitors/components.py
$V qualification/raster_competitors/experiments.py
```

Optional ordinary converter equivalence (expensive; not a competitor regeneration):

```sh
cargo build --release --bin scanweave --locked
$V qualification/raster_competitors/verify_current.py
```

That last command resumes verified scratch outputs. For an intentionally fresh
repeat, use a new scratch copy of the harness and an empty `local/current/` plus
`current-verification.json`; retain the original receipts. It does not silently
accept a changed output hash. The historical run completed and logged success,
but its supervising process ended before writing timing; its recovered PDF hash
was checked explicitly. That entry has no invented wall-time value.

`run-manifest.json` records exact historical commands/versions, current versions,
source/licence records and hashes. Packaging and tonal manifests are checked
without modifying them. Historical executable drift is separate from artifact
provenance. Common image-only inputs use nominal300DPI; original receipt/book
capture resolution is unknown.

## Data contracts

- `object-inventory.json`: six arms × five documents, all32pages, object IDs,
  recursive paint graph, masks, inline images, filters, JPEG tables/sampling,
  palettes, decoded hashes and physical placement. `state_ref` resolves into
  `graphics_states` inside the same document. Decimal operands are preserved as
  strings rather than rounded for display. This is an operator record, not a renderer.
- `byte-accounting.json` / `gap-accounting.csv`: exact unique document-stream
  costs; separately labelled non-additive page-reference costs include masks.
  `serialized-residual` is measured remainder, not a pure patch/syntax estimate.
- `page-layer-summary.csv`: per-image placement/role/resolution and referencing page.
- `regions.json`: fixed source-selected coordinates, committed before conclusions.
  `region-results.json`:100DPI page and300DPI region measurements, two renderers.
  No semantic bytes are assigned by region/image area. Contrast/component
  diagnostics are not erased-character counts.
- `layer-results.json`: font/nonfont/image isolation and **ordered replay** proof.
  All tested text modes are0/3. Clipping text modes fail explicitly; unsupported
  separation is not approximated. Components are not asserted to add as RGB arrays.
- `component-results.json`: individual Adobe/archive image isolation with original
  clips and soft masks. `local/components/*-smask.png` visualizes archive mask samples.
- `experiment-results.json`: two fixed shadow controls, not product modes.
  E1 tests lossless representation of already-quantized pixels; E2 tests unprotected
  whole-page150DPI and is rejected. Neither qualifies a production change.
- `text-inventory.json`: native extraction hashes and render-mode character counts,
  not proof of OCR truth or one-font-outline-per-Unicode-character.
- `artifact-manifest.json`: hashes/locations of actual shadow PDFs and retained local
  representative derivatives. Large render sets stay local, not ordinary Git history.

Every regenerated measurement should be compared to the committed values.
Software versions can affect rendering; disclose changes rather than replacing
historical numbers. `render_cached` is only for the frozen hash-verified dataset;
use an empty scratch render directory when inputs or renderer versions change.

## Rights

See `qualification/pdf_packaging/README.md#rights-and-attribution` and its
`attribution/` directory. CORD: Clova AI/CORD authors, CC BY4.0; OCR-D contributors
and libraries: CC BY-SA4.0; Ipswich/NARA public-domain records; OCRmyPDF mixed-source
REUSE records include the Linn brochure CC BY-SA3.0/GFDL alternative. Source rights
continue to apply. Derived comparison sheets and historical-page control PDFs
here are distributed as CC BY-SA4.0 with those attributions. They show cropped,
rendered and/or lossy converted comparisons; the source originals remain intact.

No Adobe program resource is copied into ScanWeave. Only public PDF output
objects, normal renders and measurements are inspected. No executable internals
are examined. Rejected trial PDFs are labelled as controls, not recommended output.
