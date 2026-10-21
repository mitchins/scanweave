# HIGH Security / Reliability remediation

Baseline: `e8c0a652637cff4349d00b98609fef83a98f9da7` (`main`).
Branch: `fix/sonar-high-security-reliability`.

## Exact intake

Authenticated SonarCloud API, project `mitchins_scanweave`, branch `main`:

```
GET /api/issues/search?componentKeys=mitchins_scanweave&branch=main&issueStatuses=OPEN&impactSeverities=HIGH&impactSoftwareQualities=SECURITY,RELIABILITY&ps=500
```

The response contained 55 unique keys. Each was also checked for a **single impact**
with severity HIGH and software quality SECURITY or RELIABILITY; no HIGH-only
Maintainability finding was admitted. Credentials were read privately, never
printed, persisted in these records, or committed.

| Rule | Findings | Treatment |
|---|---:|---|
| python:S6729 | 12 | Replace one-condition `np.where` with `np.nonzero` |
| shelldre:S7688 | 11 | Use Bash `[[ ]]`, preserving operands and quoting |
| pythonsecurity:S8707 | 31 | 26 independently reviewed false positives; 5 unresolved boundary questions |
| pythonsecurity:S8705 | 1 | Independently reviewed false positive |

The complete keyed inventory, original status and reasons are in
[sonar-high-security-reliability.csv](sonar-high-security-reliability.csv).
Reviewed path dispositions are in
[sonar-high-reviewed-paths.json](sonar-high-reviewed-paths.json).
Code fixes are not represented as fixed on `main` before merge and fresh analysis.
False-positive dispositions are **not code fixes** or scope exclusions.

## Small reliability changes

Only the twelve one-argument NumPy calls change. Three-argument `np.where` remains
unchanged; it selects samples rather than returning indices. Ordinary ndarray
index order, empty results, crops and histogram classifications are preserved.

The reference runner already requires Bash. All eleven conditional tests now
use `[[ ]]`. Literal string right-hand operands stay quoted, and numeric/file
tests retain their operators. Wine automation, sleeps, output settings and
reference PDFs do not change. This is not an Acrobat reconversion.

Six focused unittest methods exercise boundary coordinates, blank/nonblank crops
in both historical reconstruction scripts, runner syntax and early errors, and
actual extracted late runner conditions (literal title/style equality, output
size equality and numeric stability). They do not exercise every NumPy site or
run the Wine GUI. The existing subpixel/corpus/search tests additionally exercise
the modified `checks.py` paths. Source review establishes the unchanged index
semantics at the remaining sites; a new fixture/corpus is unnecessary for these
primitive substitutions.

Both normal CI and instrumented Python coverage run the new tests. No test,
source scope, rule, severity or Quality Gate is weakened.

## Security boundaries and unresolved findings

Parent source-to-sink review and an independent fresh read-only investigation
examined all 32 security keys, direct callers and the actual probe argument
parser. No applicable `SECURITY.md` was found. These are standalone qualification
CLIs, not a repository-provided LLM tool or HTTP file service. An explicit input
or output filename is generally the utility's intended authority. Restricting it
to the current directory would silently change legitimate workflows.

Two zoom scripts parse DPI as an integer before using it as a path component.
The corpus adapter's subprocess uses a fixed probe executable and an argv list;
joined paths cannot equal the exact option tokens parsed by `arg_of`, and DPI
passes through Python `float`. No shell injection was established.

Five findings remain OPEN/needs-review, without suppression or an Accepted
transition:

- `AaFbZj2c2TNSduKvuGwI`: `diagnostic.py --tag` can escape `--out`. Both values
  come from the same CLI caller. A filename-only contract or independently
  lower-trust tag source must be established before restricting it.
- `AaFbZj512TNSduKvuG0r`, `AaFbZj512TNSduKvuG0n`,
  `AaFbZj512TNSduKvuG0o`, `AaFbZj512TNSduKvuG0s`: corpus enumeration follows
  symlinks outside the selected root. The adapter promises pixel binding,
  document splits and holdout sealing, not a filesystem sandbox. External
  symlinked datasets may be legitimate. Decide the supported corpus trust and
  symlink contract before changing those reads. No sealed real holdout was opened.

A future service accepting adversarial paths must define and enforce its own
filesystem/option boundary. The reviewed false positives do not certify such a
service or imply that all local invocations are trustworthy.

## Product and review scope

No Rust product, OCR invocation, glyph reconstruction, font, Unicode, PDF writer,
image encoding or faithful-profile code changes. Historical P01–P08 visual
limitations remain. Local unfiltered Rust tests (116 passed), denied-warning Clippy, and the existing
Python qualification contracts passed. GitHub CI and server-side Sonar are still
pending at this write-up; their final per-head results will be recorded on PR #10.
Independent patch review found no source-backed regression and identified test
coverage gaps; late Bash condition tests were added in response. No broad style
cleanup or reconstruction refactor is included.
