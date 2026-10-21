# HIGH maintainability remediation waves

## Frozen intake

Main: `0816d8a229e08838117b1e104a9c005a3d3ba56a`. Both main CI and
Sonar were green; no open PRs. The authenticated, paginated SonarCloud query was:

```
/api/issues/search?componentKeys=mitchins_scanweave&branch=main&issueStatuses=OPEN&impactSeverities=HIGH&ps=500
```

The complete response contains **142 unique keys**, all with HIGH Maintainability
impact, and zero HIGH Security/Reliability findings. This differs from the
operator's earlier 143-key list because the separately approved operator-output
finding is FALSE_POSITIVE, freshly verified as such. It is not a code fix.

The exact source locations, impact objects, current statuses, messages and wave
assignments are in [the baseline CSV](sonar-high-waves-baseline.csv); the
[raw baseline](sonar-high-waves-baseline.json) preserves original issue keys and
server metadata. Baseline measured coverage: overall 43.7%, new code 88.6%;
Quality Gate OK. There are 240 analyzed files and 24,397 non-comment lines.

| Assignment | Unique keys | Boundary |
|---|---:|---|
| Wave 1 | 55 | Qualification utilities only: 47 literal, four correctness/contract and four bounded complexity findings |
| Wave 2 | 9 | Eight near-threshold production parsing/validation/encoding candidates plus explicit wildcard imports |
| Wave 3 | 16 | Four identical auditors, four adjacent comparators and four adjacent stage analyzers (at most three implementation families) |
| Deferred | 62 | Coupled production functions and qualification work beyond this bounded file/family budget |

Assignments are candidates, not advance claims of fixes. Each wave starts from
latest verified main, with only one open PR, independent review, unchanged CI/
Sonar gates, and operator merge approval. Wave 2 has not started. No rules,
severities, source scope or Quality Gate thresholds change.

## Wave 1 implementation

Twenty-three modules replace repeated literal tokens with local constants.
At the **literal-only transformation stage**, before the separately tested
helper extraction in `tonal_raster/compare.py`, expanding constants back yields
**exact original AST equality**, including
PDF operation strings, regex bytes, fixture names, output paths and iteration
order. A [literal contract manifest](sonar-high-wave1-literal-contracts.json)
records original source SHA-256 values and exact constant values. No global
configuration framework or historical data changes.

Two disabled `if False` expressions are removed; neither executed or affected
output. `Pen._endPath` intentionally emits no operator: the eventual PDF `f`
closes open contours. Its contract is documented and tested. The reference
runner's window-search default explicitly continues: unrelated Acrobat windows
are expected. Failing for every nonmatching title would be a behavior change;
unsupported output styles already fail explicitly.

Four small helper extractions preserve:

- Tonal ridge-test contrast, dtypes, thresholds and integer accumulation.
- Alignment y-major candidate order and strict first-best tie-breaking.
- Source-font family sorting and statistics populations.
- Product comparison crop geometry, labels, names and image construction.

Other small complexity candidates are explicitly deferred to keep the review
bounded, rather than expanding into historical geometry changes. Production
Rust, faithful, OCR invocation, font reconstruction, ownership, PDF assembly and
encoding are untouched. Historical P01–P08 visual limitations remain disclosed.

### Executed equivalence

The existing source-font control and product measurement `main()` entry points
ran before/after on the same preserved eight-page PDFs/fixtures in separate
scratch output trees. The product command is the existing interface:

```
qualification/.venv/bin/python qualification/clearscan_product/measure.py \
  --dpi 300 --input-dir qualification/experiments/m1g/fixture/dpi300/input \
  --oracle-dir qualification/experiments/m1g/fixture/dpi300/oracle \
  --pdf qualification/clearscan_product/300/clearscan.pdf \
  --report qualification/clearscan_product/300/report.json --out /tmp/scanweave-wave1-measure
```

Only diagnostic output roots were redirected. No frozen measurement was replaced.
Source-font JSON SHA-256:
`0957fac79e84f47ed9d88b148312b14b55aa63d71c5f9b1b298f3a36f35b157f`.
Product JSON SHA-256:
`91d90a614ba200baa3c8268293827267aa08a90551240d64e59756c0b2265287`.
All 32 source-font and 26 product PNG hashes match, including Poppler/PDFium
renders and 800% labeled crops. JSON structures and numerical values match
exactly. Nine alignment cases have equal arrays and exact floating tuples; 36
tonal cases match exactly, including chunk boundaries at 127/128/129/257 rows.

Ten permanent tests cover local constant values, ties/NaNs, alignment sampling,
ridge preservation, chunk boundaries, ordered family statistics, open contours,
sample-crop pixels and window matching/nonmatching behavior. They preserve an
existing one-row metric exception and tiny alignment/uint8 sampling offset;
neither is silently corrected. Historical scripts execute on import, so unit
controls load actual definition/constant AST nodes without executing their
corpus-writing top-level programs. This is not a claim of executing every
historical entry point.

Independent read-only review found no blocking code difference; it separately
verified literal-stage constant-expanded AST equality, numerical/ordering invariants, shell
search semantics and contour closure. Execution qualification and fresh server
results are recorded on the PR before merge approval.

### Prior-cohort ledger correction

This substantive documentation update records the previously approved PR #10
closure: **27 genuine Sonar-verified code fixes and 28 reviewed false-positive
dispositions**, not 28 code fixes. The genuine filename-only tag improvement
was not evidenced by `AaFbZj2c2TNSduKvuGwI`; that key's flow is deliberately
operator-selected `--out`. No further Sonar dispositions are made in this wave.

## Deferred production complexity

The baseline CSV retains every deferred key and exact reported score. In
particular, do not mechanically refactor `convert_parts` (294),
`clean_replaced_text` (174), visual dictionary `reconstruct` (106),
`emit_text_runs` (100), or `convert_document_with_sources` (96).

Minimum qualification for a dedicated later extraction: explicit ownership and
state-transition contracts, error precedence on malformed inputs, fixed integer/
floating iteration order, exact faithful and synthetic 300/600 PDF bytes,
Poppler/PDFium render hashes, donor repair, Unicode/ActualText/search, native
source-image validation and deterministic serialization. Coupled contour,
mask/units and reconstruction functions also require shape/topology and
compositor invariants; a complexity score alone is insufficient justification.

Wave 2 and Wave 3 outcomes will be appended only after their sequential review,
qualification, operator disposition and fresh main analysis. No fourth wave is
authorized by this plan.

### Local CI receipt

All 17 local contracts passed, including unfiltered workspace Rust tests,
denied-warning Clippy, build, schema/corpus/security boundaries, subpixel and
translation instruments, text search, paint fidelity and document search.
The donor-repair regression passed. Detailed commands/timings and executed
measurement hashes are in [the validation receipt](sonar-high-wave1-validation.json).
Regenerated historical test outputs were backed up outside Git and restored to
their initially clean bytes, rather than replacing published evidence.

Wave 1 PR: https://github.com/mitchins/scanweave/pull/11 . GitHub CI/Sonar
results and review dispositions will be recorded there against the final head.
No merge is authorized without the operator's approval.
