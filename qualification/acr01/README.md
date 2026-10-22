# ACR-01 evidence and reproduction

Product base: `0ca94ae`; research reference: PR14 `ffa604ebd4ab47a6af67d2696a5c8fc15fbf3f2e`.
The frozen five collections and all32 page memberships are unchanged in
`qualification/pdf_packaging/{groups,corpus}.json`. See root `ACR_01_REPORT.md`.

Large data, temporary raster probes and comparison images remain under ignored
`local/`. They are deliberately absent from the product PR. Source licences and
attribution remain in the existing corpus documentation; no new data was acquired.

## Obtain the local research sources

A fresh checkout contains the product, not the licensed corpus or ignored research
scripts. Obtain the existing frozen corpus and `reproduction-source.tar.gz` from
the operator's evidence workspace (`qualification/acr01/local/`). The bundle's
SHA-256 and size are recorded in `run-manifest.json`; verify them before extraction.
This is an operator-provided local artifact, not a publicly downloadable release.
Extract from the repository root:

```sh
tar -xzf /path/to/reproduction-source.tar.gz
mkdir -p qualification/residual_resolution/local
git fetch origin refs/pull/14/head
git archive ffa604ebd4ab47a6af67d2696a5c8fc15fbf3f2e qualification/raster_competitors | tar -x -C qualification/residual_resolution/local
```

The archive contains the ACR probe/measurement scripts and the reused R1 inventory
helper. The separate exact PR14 export supplies rendering and resource inspection.
Neither research implementation enters the product binary. Without this local
bundle the research matrix commands below are unavailable; ordinary product
reproduction only needs a build and the input PDFs:

```sh
cargo build --release --locked
for group in historical receipts financial mixed forms; do
  target/release/scanweave "qualification/pdf_packaging/groups/$group-input.pdf" "/tmp/$group-acr01.pdf"
done
```

With the evidence prerequisites installed, the local reproduction commands are:

```sh
cargo build --release --locked
qualification/.venv/bin/python qualification/acr01/local/probes.py
qualification/.venv/bin/python qualification/acr01/local/compare_probes.py
qualification/.venv/bin/python qualification/acr01/local/index_controls.py
qualification/.venv/bin/python qualification/acr01/local/run_product.py
qualification/.venv/bin/python qualification/acr01/local/verify_product.py historical receipts mixed forms financial
qualification/.venv/bin/python qualification/acr01/local/controls.py
qualification/.venv/bin/python qualification/acr01/local/package_results.py
qualification/.venv/bin/python qualification/acr01/local/full_pages.py
```

Run from the repository root with the existing licensed corpus available. PR14's
read-only rendering/inventory helpers are reused from an exact local git export;
no research behavior is imported into the product. Pillow/libjpeg probes and Rust
JPEG output are independently rendered and reviewed; byte equality between these
encoders is not assumed.

Native product PDFs are `local/product/{historical,receipts,mixed,forms,financial}.pdf`.
The full documents preserve donor context; raster-only source probes are separate
under `local/probes/`. Actual Rust fixed-region comparisons are under `local/integrated/`.
Page geometry uses the PR14 common MediaBox/original-CropBox-clip contract. Metrics
use the source's physical coordinates, not per-candidate crop normalization.
