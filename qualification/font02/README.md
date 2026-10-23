# FONT-02 evidence

The construction-time font pruning is product code, merged in PR #22.
The registered matcher is a rejected research result. Nothing here enables it in
ordinary conversion. See [the report](../../FONT_02_REPORT.md).

## Compact checked-in evidence

- `required-glyph-*`: successful Phase 1 product verification and review.
- `42-e-observations.json`, `42-e-matrices.json`: original visible ownership,
  reconstruction decisions and current/registered pair matrices (unrounded).
- `matcher-source-binding.json`: exact production private-function source hashes.
- `source-health.json`: independent source-only adjudication, before substitutions.
- `reuse-protocol.json`: pre-oracle rendered-quality limits.
- `reuse-results.json`: family-disjoint results, per-character outcomes and actual
  material-regression records. Face labels are diagnostic, not the decision target.
- `healthy-shadow-results.json`: final five-change arm excluding legacy repairs.
- `reuse-manifest.json`: versions, local artifact identities and hashes.
- `examples/`: fixed-coordinate real-word and rejected punctuation comparisons.

## Local reproduction

Use the existing FONT-01 corpus and frozen financial document/comparators; do not
open the sealed holdout. Large source pages, PDFs, native coverage arrays and
individual render logs remain in ignored `local/`.

`local/rendered-reuse-reproduction.tar.gz` preserves the exact experiment scripts,
Rust read-only probe and closure scripts. Its hash and all required frozen output
hashes are recorded in `reuse-manifest.json`. The archive contains no fonts,
credentials or third-party implementation. Extract into a scratch directory to
inspect it, not over frozen outputs. The probe's Cargo path is checkout-specific;
change only that path for another checkout. Its source-binding hashes must still
match before comparing private production functions.

The archive's `reuse-study/` scripts run in this order: `register.py`,
`substitute.py`, `measure_substitutions.py`, `complete_candidate.py`,
`comparison_sheets.py`. They intentionally use fixed experiment paths under this
checkout; they are not a supported public API. The individual-trace comparator
was built in `/tmp/scanweave-font02-trace-probe` with visibility-only exports of
existing tracing/font functions, and its original source binding remains there.
Do not describe this diagnostic build as normal converter behavior.

For hard negatives: `prepare.py` reads public observations/source imagery with
separate evaluator sampling labels; `probes.py` binds actual emitted Rust glyphs
and creates native-position PDFs; `measure.py` freezes source-only decisions and
coverage arrays. Only then does `rendered_reuse.py` read pristine oracle pixels.
`validation` and `test` remain family-disjoint. D2–D4 are not scored as healthy
reuse. No thresholds were selected using test oracle outcomes.

Recompute evaluation without rerunning OCR or registration:

```sh
qualification/.venv/bin/python -m unittest qualification.font02.test_rendered_reuse
qualification/.venv/bin/python -m qualification.font02.rendered_reuse \
  --artifacts qualification/font02/local/hard-negatives \
  --corpus qualification/font01/local/corpus-font01-v1 \
  --split validation --output /tmp/font02-validation.json
qualification/.venv/bin/python -m qualification.font02.rendered_reuse \
  --artifacts qualification/font02/local/hard-negatives \
  --corpus qualification/font01/local/corpus-font01-v1 \
  --split test --output /tmp/font02-test.json
```

Both recomputations reproduce every first-run per-pair numerical result exactly.
The evaluator refuses changed source-decision/coverage artifacts. This is an
integrity check, not a filesystem sandbox or protection against malicious
concurrent changes. Pristine images belong only to evaluation.
