# ACR-04 reproduction

Read `../../ACR_04_REPORT.md` first. `results.json` contains unique collection
resource costs and per-page references; `page-accounting.csv` charges references
per page and must not be summed to infer unique shared stream costs.

Large licensed inputs and outputs are local, not downloadable repository assets.
Their identities are in `reproduction-manifest.json`. Local reproducibility source
is hash-bound in `local/reproduction-source.tar.gz`; extract into this directory
only after verifying its manifest hash. It contains the experiment runner,
ordinary CLI runner, accounting verifier, regression controls and independent
rendering helper, without images or PDFs. Existing source/comparator PDFs remain
under `qualification/pdf_packaging/groups/` and are never overwritten.

Representative commands (from repository root, existing qualification environment):

```sh
cargo build --release --locked
qualification/.venv/bin/python qualification/acr04/probe.py --inventory
qualification/.venv/bin/python qualification/acr04/run_product.py
qualification/.venv/bin/python qualification/acr04/local/verify_product.py historical receipts financial mixed forms
```

The runner records exact invocation, binary/input/output hashes, wall time and
`/usr/bin/time -v` RSS. Its immutable candidate executable and all final PDFs live
under `local/`; do not substitute the rejected sequential build. Probe controls
are frozen-decoded-image experiments, not ordinary-converter results.

Review notes distinguish sampled visual judgements from mechanical guarantees.
`examples/` contains a compact synthetic complete PDF and the actual financial
75-versus-15 optical-recognition disagreement, with aligned source/baseline/final
views. Pristine synthetic truth is evaluator-only. The sealed holdout is unused.
