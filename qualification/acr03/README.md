# ACR-03 bounded object-first prototypes

Research derivatives only. No normal converter changes, new product profile or
inference-time oracle. See [the report](../../ACR_03_REPORT.md) for the decision.

## Prerequisites and provenance

Run from the repository root using `qualification/.venv/bin/python`. Exact packages,
source/baseline/comparator hashes and helper revisions are in `run-manifest.json`.
The existing licensed development artifacts must be available locally; neither
large corpus images nor Acrobat binaries are redistributed here. Preserve their
existing CORD/OCR-D attribution. The controlled DejaVu fixtures and drawn annotation
are authored controls, not claimed genuine handwriting. The genuine seal remains
an independent real-document check. Never read the sealed holdout.

Product base: `8f14cd329493ad0cc226e480d152d7a464fb4731`. PR16 helpers are exported
from `38cc218f8f1e50e56679fd12d5d72c1d4a44a697`, not merged. The original fixed
physical-coordinate renderer/inspector comes from PR14 evidence revision
`ffa604ebd4ab47a6af67d2696a5c8fc15fbf3f2e`.

```sh
qualification/.venv/bin/python qualification/acr03/prepare_reference.py
qualification/.venv/bin/python qualification/acr03/test_prototype.py
qualification/.venv/bin/python qualification/acr03/prototype.py --case logo
qualification/.venv/bin/python qualification/acr03/prototype.py --case logo --oracle
qualification/.venv/bin/python qualification/acr03/prototype.py --case annotation
qualification/.venv/bin/python qualification/acr03/prototype.py --case annotation --oracle
qualification/.venv/bin/python qualification/acr03/prototype.py --case seal
qualification/.venv/bin/python qualification/acr03/prototype.py --case financial
qualification/.venv/bin/python qualification/acr03/prototype.py --case shade
```

Repeat the five fixed cases with `--representation masked`. Seal/shade must fall
back to the complete unchanged historical baseline. The rejected B diagnostics
are reproduced **only** by adding `--emit-rejected`; they are saved separately in
`local/rejected/` and must never be described as qualified output.

```sh
qualification/.venv/bin/python qualification/acr03/prototype.py --case seal --representation masked --emit-rejected
qualification/.venv/bin/python qualification/acr03/prototype.py --case shade --representation masked --emit-rejected
/usr/bin/time -v qualification/.venv/bin/python qualification/acr03/prototype.py --financial-all
qualification/.venv/bin/python qualification/acr03/prototype.py --historical-controls
qualification/.venv/bin/python qualification/acr03/compare.py
qualification/.venv/bin/python qualification/acr03/layers.py
qualification/.venv/bin/python qualification/acr03/review_render.py
qualification/.venv/bin/python qualification/acr03/verify_acr03.py
qualification/.venv/bin/python qualification/acr03/diagnostics.py
qualification/.venv/bin/python qualification/acr03/account.py
```

The financial command modifies the full thirteen-page ACR-01 document in one shared
resource/font context; it does not concatenate independently converted pages.
Each page's source and cleaned residual come from the frozen full collections.
Standalone case PDFs also retain the full original document and change one page.
Their sizes are **whole-document intervention sizes**, not standalone page sizes.

For a fresh local evidence bundle, export/run PR16 `fixtures.py` and
`prepare_prototypes.py` using their pinned code; the latter selects controlled
indices 6,16,24,28 into one four-page input. Convert all four pages together with
the pinned ACR-01 binary and existing `adobe-acrobat-sandbox/clearscan.sh`, following
PR16's README and frozen settings. Do not overwrite archived comparator outputs.
Authoring paper/difference masks are consumed only with `--oracle`.

## Output contract

`local/` holds full PDFs, native object/support masks, paper plates, isolated
paper/object/font/raster PDFs, two-renderer sheets, logs and review evidence.
`results.json` records exact serialized sizes, per-resource-role stream costs and
per-page financial decisions. `run-manifest.json` binds artifacts and scripts.
`region-results.json` contains fixed-coordinate diagnostic metrics, never an
aggregate acceptance score. Local review records must be newly inspected, not
regenerated as automatic approval by a script.

The prototype intentionally supports only the exercised unrotated zero-origin,
default-UserUnit ScanWeave PDFs, with fresh text matrices and one CID per visible
show. It is not a general PDF editing library or a security sandbox.
