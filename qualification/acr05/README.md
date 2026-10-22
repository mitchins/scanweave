# ACR-05 reproduction and evidence

See [ACR_05_REPORT.md](../../ACR_05_REPORT.md). Large PDFs, raw source/residual
samples and rendering atlases stay in ignored `local/`; no frozen input is modified.

`manifest.json` binds the frozen source/comparator corpus and local source archive.
The archive contains the paper/alpha probes, coherent shadow PDF generation,
read-only patch ledger, ordinary CLI runner, accounting/semantic verifier,
boundary diagnostic and independent rendering scripts. Dependencies are the
existing qualification virtualenv and exact read-only ACR02/PR14 helpers.
It is not a public downloadable corpus; the operator's existing licensed local
inputs are required. Source authoring truth does not enter production conversion.

Commands from repository root, after verifying/extracting the local source archive:

```sh
cargo build --release --locked
qualification/.venv/bin/python qualification/acr05/local/run_product.py
qualification/.venv/bin/python qualification/acr05/local/verify_product.py historical receipts financial mixed forms
qualification/.venv/bin/python qualification/acr05/local/search_controls.py
```

The runner expects its immutable executable at `local/scanweave-candidate`,
records exact binary/source/output hashes and RSS, and resumes only matching runs.
Temporary ACR04 dump instrumentation was removed before implementation; the
captured baseline PDF was byte-identical. It supplies evidence only, never a
runtime dependency. Two final executable hashes differ after an inactive test
fixture edit; the rebuilt executable reproduces the same synthetic300 PDF.

`results.json` has exact collection bytes and page references, `pages.csv` lists
actual vector counts, and `decision-audit.json` records old coverage/cost gating.
Full object/patch inventories remain hash-bound locally; selected provenance and
uncertainty are preserved in `patch-provenance.json`. Do not allocate compressed
image bytes to paper/text by area or sum shared per-page references as unique bytes.
`boundary-summary.json` deliberately preserves the worse PDFium diagnostic.

Independent review notes document actual inspected coordinates, views and limits.
The candidate identity X=B /Y=A was hidden until the first judgement; C/final were
not blinded. Examples preserve context and include adverse raster softness.
No claim is made that all source fringes or intrinsic font defects are repaired.
