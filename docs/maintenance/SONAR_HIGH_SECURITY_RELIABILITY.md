# HIGH Security / Reliability remediation

Baseline: `e8c0a652637cff4349d00b98609fef83a98f9da7` (`main`).
Branch: `fix/sonar-high-security-reliability`; [PR #10](https://github.com/mitchins/scanweave/pull/10).

## Exact intake

Authenticated SonarCloud API, project `mitchins_scanweave`, branch `main`:

```
GET /api/issues/search?componentKeys=mitchins_scanweave&branch=main&issueStatuses=OPEN&impactSeverities=HIGH&impactSoftwareQualities=SECURITY,RELIABILITY&ps=500
```

The response contained 55 unique keys. Each also has a **single impact** whose
severity is HIGH and whose software quality is SECURITY or RELIABILITY. No
Maintainability-only finding was admitted. Credentials were read privately and
never printed, persisted in these records or committed.

| Rule | Findings | Treatment |
|---|---:|---|
| python:S6729 | 12 | Nine index calls corrected; two duplicate calls share the existing renderer; one unused index calculation removed |
| shelldre:S7688 | 11 | Bash `[[ ]]`, with operands and quoting preserved |
| pythonsecurity:S8707 | 31 | Five code fixes under the operator-adopted containment/tag contract; 26 reviewed false positives |
| pythonsecurity:S8705 | 1 | Independently reviewed false positive |

All keys, original locations/status and dispositions are in
[sonar-high-security-reliability.csv](sonar-high-security-reliability.csv).
The 27 initial per-key false-positive reasons and three PR-only follow-ups are in
[sonar-high-reviewed-paths.json](sonar-high-reviewed-paths.json).
The initial transitions and comments were verified on Sonar; they are **not code fixes**.
The other 28 findings must not be represented as fixed on `main` before merge
and fresh analysis. No manual closure of the five containment findings was made.

## Reliability changes

One-condition NumPy index lookups use `np.nonzero`; three-argument `np.where`
still selects samples. Index order, empty results, crops and histogram
classification are preserved. The two identical historical `render_glyph`
implementations now reuse the existing M1-C helper. The unused counter-coordinate
calculation is removed; actual boolean counter-sample selection is unchanged.

The reference runner already requires Bash. All eleven tests now use `[[ ]]`.
Literal string right-hand operands stay quoted; numeric and file operators stay
unchanged. Wine automation, sleeps, conversion settings and reference PDFs do
not change. No Acrobat reconversion was needed.

Nine focused tests exercise boundary coordinates, blank/nonblank crops through
both callers, actual outline bounds, oracle ink coordinates and emitted oracle
paths using a tiny generated test font. Donor-only scikit-image imports are lazy,
so those independent index helpers can be tested without a new dependency.
Runner tests check syntax, early errors and actual late conditions, including
wildcard-like titles/styles, output-size equality and numeric stability. They do
not claim a full Wine-GUI run. Existing analytical subpixel tests are instrumented
too; histogram entry points are source-reviewed but not fully integration-tested.

## Adopted corpus and tag contracts

The initial review found five boundary questions rather than an established
containment contract. The operator explicitly chose the following requirements
before implementation:

- `--corpus` is operator-selected and may itself resolve through a symlink.
  Its canonical destination becomes the authorized source root.
- Discovered directories, raster files and OCR files may follow symlinks only
  when the resolved target remains inside that root. Reject external targets
  explicitly, including during byte-only holdout sealing.
- `--tag` is a nonempty filename component, never a path. `--out` remains an
  arbitrary operator-selected destination.

`corpus_path()` checks canonical path ancestry before enumeration, raster decode,
OCR existence checks/reads, and direct `seal_material()` reads. It rejects
prefix-sibling escapes, dangling external links and resolution errors instead
of silently skipping them. OCR companion names are exact filenames, not glob
patterns. Files opened in this path now have explicit lifetimes.

Internal aliases into canonically named holdout documents are rejected from
ordinary development materialization unless `--include-holdout` is given.
Ordinary named holdouts still receive source-byte hashing only; they are not
parsed, decoded or copied. All boundary tests use synthetic temporary material,
not the real sealed holdout.

Tag validation runs both in argparse (before creating output directories) and
at the direct `run()` entry point. It rejects empty/dot/dotdot labels, separators,
absolute/drive-qualified paths and NUL. Ordinary spaces, Unicode and punctuation
remain supported. Output-directory ownership is still the operator's concern.

**Limit:** resolve/check/use is not protection against concurrent malicious
symlink replacement. Corpus trees must remain stable during ingestion. This is
bounded source containment, not a general filesystem sandbox.

The genuine Security code-fix keys are:

- `AaFbZj2c2TNSduKvuGwI` — diagnostic tag.
- `AaFbZj512TNSduKvuG0r`, `AaFbZj512TNSduKvuG0n`,
  `AaFbZj512TNSduKvuG0o`, `AaFbZj512TNSduKvuG0s` — corpus/holdout reads.

Seventeen boundary tests cover canonical root aliases, internal/external
symlinks at each input layer, byte-only sealing, external holdout rejection,
internal aliases into holdouts, direct seal calls, intelligible CLI errors,
exact OCR names and both tag entry points. Negative holdout tests forbid opening
the external target, rather than merely checking the eventual return code.

## Separately reviewed false positives

Parent tracing and a fresh independent investigation examined all 32 Security
keys, their direct callers and the actual probe argument parser. No applicable
`SECURITY.md` was present. Two zoom utilities parse integer DPI before forming a
path component. Other reviewed paths implement explicit CLI input/output
selection. No repository-provided HTTP/LLM file service or independently
privileged caller was found. Corpus normalization invokes a fixed probe with an
argv list; joined paths cannot equal exact option tokens and DPI is a float.

A fresh analysis identified three PR-only repetitions at explicit output writes
and rereads after context-manager changes. Independent review traced their
constructed paths and both OCR branches: no OCR data chooses an output path.
They have separate keys/reasons in the JSON ledger, not extra claims against the
original 55-finding cohort. The new repeated OCR suffix literal also uses one
constant rather than adding duplicated configuration.

The individually reasoned false-positive transitions leave the five genuine
containment findings untouched. No Accepted transition, rule/severity change,
`NOSONAR` or analysis-scope exclusion was used. A future service accepting
adversarial paths would need its own authority and argument boundaries; these
verdicts do not certify such a service.

## Validation and product scope

The first PR analysis correctly failed its unchanged Quality Gate: new coverage
41.7%, new duplication 3.9%, with no new Security/Reliability findings. Tests were
extended to the actual index/geometry helpers, identical rendering code was
shared, and the subpixel tests were added to coverage. No threshold was weakened.

Local unfiltered Rust tests (116 passed), denied-warning Clippy, existing Python
qualification and the 26 focused tests pass. A diagnostic server analysis measures new
coverage 91.8% and duplication 0.4%. GitHub CI and server-side Sonar for the
final follow-up are pending at this write-up; final per-head results
will be recorded on PR #10. Upload success alone is not a Quality Gate result.

Independent patch review found no source-backed regression in the reliability
changes; late Bash condition tests addressed its coverage concern. A fresh
independent containment review found no blocking bypass or compatibility defect,
under the documented stable-filesystem assumption. CodeRabbit's validation-wording
comment was addressed; its follow-up was rate-limited, not an approval.

No Rust product, faithful-profile, OCR engine/invocation, glyph reconstruction,
font, Unicode, PDF writer or image encoding changes. Historical P01–P08 visual
limitations remain. No full 32-page regeneration is necessary for these
qualification utility changes.
