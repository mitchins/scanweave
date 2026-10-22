# ACR-01 evidence and reproduction

Product base: `0ca94ae`; research reference: PR14 `ffa604ebd4ab47a6af67d2696a5c8fc15fbf3f2e`.
The frozen five collections and all32 page memberships are unchanged in
`qualification/pdf_packaging/{groups,corpus}.json`. See root `ACR_01_REPORT.md`.

Large data, temporary raster probes and comparison images remain under ignored
`local/`. They are deliberately absent from the product PR. Source licences and
attribution remain in the existing corpus documentation; no new data was acquired.

The local reproducibility scripts, SHA-bound in `run-manifest.json`, are:

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
