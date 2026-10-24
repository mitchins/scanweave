# FONT-04 R2a evidence reproduction

R1 acceptance is `fa8a08b`; the stop decision is `dc0849b`. R2a resumes as
frozen-method evidence gathering. P2 is excluded from every command below.

All paths are relative to the repository root. Python commands use
`qualification/.venv/bin/python`, with
`PYTHONPATH=qualification/font04/local/R2a/pdfium-python:.` so that the
qualification Python bindings load the same pinned chromium/8100 library as
native conversion. Its SHA-256 is
`b8784cbd652ad2993332b7695e2c80f3a797f877fc47d9be97b66bca9639539e`.
Set `SCANWEAVE_PDFIUM_LIBRARY` to the absolute path of
`tools/src/pdfium/lib/libpdfium.so` for native runs. The reporting build is
retained at `local/R2a/reporting/scanweave`; the row-worker build is retained at
`local/R2a/resume-optimized/scanweave`. Binary hashes appear in every run receipt.

`r2a_run.py BINARY DIRECTORY` runs the explicit five development inputs,
default and cover-2.0, financial cover-1.5, and cover-2.0 repeats at eight
threads instead of four. Each PDF is checked against the pre-optimization
baseline or financial golden immediately. Existing successful receipts are
reused only with the same binary and expected PDF hash. Any other existing
receipt fails instead of being overwritten. Reporting financial reruns use
`--groups financial`. Final serial benchmarks use
`--no-repeat --no-comparison`; the full optimization qualification already
covers comparison and repeat outputs. Preserve GNU time `.time` files beside
all `.run.json` files. Do not run the final benchmark alongside other FONT-04
qualification jobs.

`r2a_prepare_export.py CHECKOUT` installs research-only hooks in an isolated
R1 checkout. Build it separately. `FONT04_R2A_EXPORT=DIRECTORY` writes source
snapshots, observations, planner fits, and exact post-union native
page/occurrence/CID/matrix bindings. The complete output PDF must reproduce its
baseline hash. This instrumented executable is never shipped. The
counterfactual font helper uses the frozen product serializer; its retained
binary is `local/R2a/export/font04_r2a_review` and its research-only source is `r2a_review_font.rs`. Build it as an example in
the isolated instrumented checkout, never on the product branch.

For financial, the original visible-only geometry inference encounters an
invisible earlier union program. The exact binding export comes from a
research off-mode conversion in `local/R2a/financial-binding/`. Its default PDF
and source snapshot are hash-identical to their baselines before
`native-bindings.json` is copied into the financial observations directory.
`r2a_metrics.load_snapshot` attaches those exact identities; `bind` requires a
bijection on page, label, CID and all six matrix values. The other four
corpus documents retain their original successful binding path. No output,
source witness, metric formula, floor or admission rule changes.

`r2a_metrics` takes DEFAULT CANDIDATE SOURCE_SNAPSHOT DESTINATION and scores
isolated available owned-source witnesses, with unavailable draws recorded
explicitly. `r2a_context_metrics` takes ORIGINAL_SCAN DEFAULT CANDIDATE
SOURCE_SNAPSHOT DESTINATION and scores all visible draws in complete page
context. `r2a_save_controls` creates matched deterministic pikepdf saves of
each default and independently audits their transport. All are module commands
under `qualification.font04`.

`r2a_blind_review BASELINE_DIRECTORY` consumes the hash-verified PDFs,
observations, fits and completed isolated scores. It refuses an existing
review/staging/key, generates full-word contexts, and invokes the separate
`r2a_seal_review` process. The README decision rule must exactly match review
condition 4 before sealing. The public package is `local/R2a/blind-review/`;
the separately held key is `local/R2a/blind-private/sealed-key.json`. Do not
read it during authoring. Public arms A/B/C randomize source as well as current
and candidate, as requested for this checkpoint. The independent reviewer
saves and hashes all judgments before using the sealer's guarded `reveal`
command. Post-reveal member adjudication applies the fixed decision rule;
materiality is not inferred from unblinded author diagnostics.

`r2a_finalize` requires all reporting goldens, full optimization byte checks,
final pairs, metrics, save controls and the sealed receipt. It verifies the
README/PDF hashes without reading the key, then writes `r2a-corpus.json`, the
profile, checkpoint and results. Full records, PDFs, private metadata and
large artifacts stay under ignored `local/`.
