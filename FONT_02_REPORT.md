# FONT-02 — Render-grounded glyph reuse

## Phase 1: required-program construction

Starting product: remote `main` at `6cc38698f94952dbca3ea187dea6ca2892e6eb54`.
Branch: `product/font02-required-glyphs`. No glyph matching, contour tracing,
OCR, raster ownership, repair threshold or composition changes in this PR.
Healthy reuse and damaged repair remain separate subsequent experiments.

### Implemented change

The document union previously included every traced candidate, including rejected
candidates never referenced by emitted text. Before constructing the shared
ClearScan font, collect required visible occurrence shapes/CIDs, whole-span
invisible-owner CIDs and per-character invisible-owner CIDs. Retain their shape
programs in original order, compact both tables and remap every reference.
`.notdef` remains mandatory; owner-only fonts retain their real placeholder.
All outlines are simple TrueType glyphs: there are no composite dependencies.
The reconstructed and raster-baseline candidates use the same remapped tables.

Recompute glyf/loca, hmtx, hhea, maxp, nominal cmap and PDF CID/GID/Unicode tables.
Retain the original conservative **head design bounding box**, which remains
valid for all required glyphs. This is metadata, not an unused outline. The
required-program builder also accounts for mandatory glyph point/contour maxima
and supplies a nominal U+0000→`.notdef` cmap for a textless font. No searchable
PDF character is added. The historical faithful builder is unchanged.

### Why the FONT-01 subset changed Poppler pixels

A controlled FontTools subset retained every used coordinate, endpoint, flag and
advance but tightened `head.yMin` from −31 to −13. Restoring only the original
`yMin` restored every pixel on all 13 financial pages in both renderers at
150 DPI. Restoring hhea, maxp, OS/2 or cmap individually did not fix page 7;
restoring xMin/xMax/yMax individually did not fix it either. Restoring head.flags
alone had already failed in FONT-01. Thus this emitted metadata change is a
reproduced cause; the internal Poppler/FreeType code path is not inferred.
The Rust construction keeps the design envelope while recomputing retained
hhea (descender −13), maxp and other tables. Actual output checks below pass.

### Complete ordinary-CLI result

| Financial document (13 pages) | Baseline | Required programs |
|---|---:|---:|
| Complete PDF bytes | 3,187,571 | 2,849,237 |
| TrueType glyph slots | 3,264 | 2,238 |
| Decoded font bytes | 1,904,648 | 1,303,200 |
| Encoded font bytes | 1,065,434 | 727,259 |
| Visible glyph draws | 3,717 | 3,717 |

Complete-PDF saving: **338,334 B (10.61%)**. Encoded font saving: 338,175 B;
the remaining 159 B is net serialization/table/content cost. No raster savings
are claimed. FONT-01's 1,027 unpainted slots included mandatory `.notdef`;
1,026 unnecessary programs are removed, with `.notdef` retained. This is
required-program elimination, **not additional canonical reuse**.

Baseline PDF SHA-256: `32b7c13e664b32fadeea41b99d9299479f129bfac3bd20debbbf481a6f885e51`.
Candidate: `74c31136d00a18dbf05fba2d7fba59c85cc201a57ae65d77999a025a692fab0f`.
Full PDFs and renders remain under ignored `qualification/font02/local/`.
Machine-readable measurements: [required-glyph-results.json](qualification/font02/required-glyph-results.json).

### Equivalence and qualification

* All 13 pages: PDFium and Poppler pixel-identical at 150 and 300 DPI (52 checks).
* Every visible/invisible Tj: exact Unicode, glyph coordinates, endpoints, flags,
  hmtx and text matrix after CID/GID remapping. Normalized graphics operators match.
* Encoded image resources unchanged. Native extraction identical in both engines.
* qpdf and OTS pass. Explicit empty and owner-only PDFs pass OTS and qpdf.
* Synthetic 300 DPI: **141,085 B**, byte-identical; both engines checked at 300 DPI.
* Synthetic 600 DPI: **189,052 B**, byte-identical; both engines checked at 600 DPI.
* Faithful forms: **855,127 B**, SHA-256
  `5f17cd97caa7caa79f931edc63692fe2551235f4aa658072cf24482f0f78188c`, byte-identical.
* Final unfiltered workspace tests: **141 passed**, zero failed; configured denied-warning Clippy passed;
  final clean-build CI and Sonar status will be recorded in the PR closure.
* Independent code review found a mandatory-glyph maxp edge case; it was fixed
  and covered by empty/owner-only table tests. No remaining mapping/bounds blocker.

The first financial CLI run took 496.86 seconds, peak RSS 1,466,412 KiB.
This is an operational measurement, not a speedup claim. A final-binary repeat
produced the exact same PDF hash. Executable SHA-256:
`43a61c3eb68c2d719680f79decf9ff4b0537484a970c21ca8fcb7f2f199e1483`.

### Reproduction

```sh
cargo test --workspace --locked
cargo clippy --locked -p scanweave-core -p scanweave-io -p scanweave-cli -- -D warnings
cargo build --release --locked -p scanweave-cli
mkdir -p qualification/font02/local
target/release/scanweave qualification/pdf_packaging/groups/financial-input.pdf qualification/font02/local/financial-required.pdf
# Existing matched synthetic bundles, with their document-wide donor context:
target/release/scanweave build --bundle qualification/experiments/m1g/fixture/dpi300/input/document.json --profile clearscan --output synthetic-300.pdf --report synthetic-300.json
target/release/scanweave build --bundle qualification/experiments/m1g/fixture/dpi600/input/document.json --profile clearscan --output synthetic-600.pdf --report synthetic-600.json
```

Local read-only verification scripts, table-isolation controls, exact commands,
logs and render hashes are preserved in `qualification/font02/local/`.
Historical inputs/comparators and sealed holdout are unchanged. Rust tests write
legacy evidence locations; those generated changes were copied locally and the
tracked historical evidence restored before publication.

## Phase 1 publication checkpoint — complete

[PR #22](https://github.com/mitchins/scanweave/pull/22) merged normally,
with squash commit **790a2f978af6c01fd699cb74ed05b457488bc3d2**. Its tree
matches reviewed head `43bb81575e32fb07e8619db6ab72f6a9070ea7a8`.
Fresh main [CI](https://github.com/mitchins/scanweave/actions/runs/39882703745)
and [Sonar workflow](https://github.com/mitchins/scanweave/actions/runs/39882703717)
passed. Completed server analysis `5a2b5ab0-1e2d-4ab1-aeb2-a18c53cb0252`
was attributed to that exact revision: Quality Gate **OK**, new-code coverage
96.7%, duplication 0.3%. The PR's implementation received independent review
and CodeRabbit review; its reproduction-path comment was fixed. CodeRabbit's
last documentation-only follow-up was rate-limited, not counted as approval.

## Phase 2 — 42 real `e` observations

Research branch: `research/font02-rendered-reuse`, from the merged Phase 1
product. No matching, grouping, repair, OCR or raster policy changed in production.
The original **13-page financial document** supplies all existing canonical fonts;
these are actual full-document outputs, not isolated-page conversions.

Town Officers, PDF page 1 / printed page 5, has 74 bounded `e` observations,
of which **42 have visible ToUnicode ownership**, using 19 GIDs. Their 41 distinct
source shape hashes exactly match the existing production report. The study
retains source bounding boxes, OCR boxes, hOCR baselines/x-heights, source scale,
source-owned binary masks and locally normalized grayscale coverage. See
[observation provenance](qualification/font02/42-e-observations.json),
[matrices](qualification/font02/42-e-matrices.json) and
[private-function source binding](qualification/font02/matcher-source-binding.json).

### What the current gates actually mean

The read-only Rust probe uses production segmentation/ownership and byte-identical
extracted comparison functions. It records normalized binary IoU, style compatibility,
cohort bucket equality, 0.78 and 0.96 score gates. Existing full-document occurrence
records retain actual decisions and downstream rejection reasons.

The 0.96 fallback is **not** a universal production reuse threshold: ClearScan's
broader cohort branch can reuse healthy glyphs at 0.78. Candidate discovery also
requires compatible aspect/density/topology, bucket/cohort support and medoid
selection. Downstream tracing requires 0.90 prototype trace fidelity; healthy
ClearScan reuse has its existing 0.80 source-IoU condition. The 0.98 preservation
condition for unreused/unrepaired sources remains unchanged. We did not lower any
of these thresholds. Pairwise probe scores do not reconstruct the whole document's
candidate search or constitute full production acceptance decisions.

The 861 distinct real-page pairs have current binary-IoU median **0.75316**;
340 meet 0.78 and 19 meet 0.96. The corresponding grayscale registered median is
**0.83953**, but these are different metrics: the numerical rise does not prove
better discrimination.

### Registered source comparison

Coverage uses local paper/ink estimates and a narrow halo assigned to the owned
core only where closer than competing source ink. Coordinates are normalized by
line x-height and baseline, not by each glyph's bounding-box dimensions. The fit
permits translation ±2 grid pixels (32 pixels per x-height), uniform scale ±2%,
and initially rotation ±1 degree. There is no anisotropic shape warping.
277/861 fits touch a translation/rotation bound; fitted nuisance geometry is not
assumed to be typographic truth.

Independent source-only adjudication, frozen before substitutions, found 33
healthy, seven damaged and two uncertain observations. Two source-healthy instances
(26 and 27) are nevertheless **legacy product repairs**. They remain untouched
in the final ordinary-reuse arm, giving 31 eligible healthy occurrences. The
frozen source adjudication was not rewritten to match product decisions.

Eleven already-emitted outline designs were rendered at each of the 42 original
placements. Each candidate is compared with both the current emitted glyph and
an independently reconstructed individual source trace. Source-coverage MSE must
be no worse than either comparator in **both** renderers, with topology retained.
Per-occurrence added/missing-ink arrays are retained locally. An exact finite
set-cover diagnostic selects among eligible donors; unchanged occurrences can
keep their original design. This is a research selection exercise, not a proposed
production optimizer or a single-linkage grouping algorithm.

### Actual complete PDFs

| Arm | Eligible healthy designs | All 42 `e` GIDs | Complete PDF bytes |
|---|---:|---:|---:|
| Merged Phase 1 native converter | 10 | 19 | 2,849,237 |
| pikepdf save-only control | 10 | 19 | 2,848,780 |
| Initial rotation arm, 33 source-healthy occurrences | 11 → 6 | 19 → 15 | 2,849,041 |
| No-rotation control, same 33 | 11 → 7 | 19 → 16 | 2,848,946 |
| Final no-rotation ordinary-reuse arm, 31 occurrences | 10 → 7 | 19 → 17 | **2,848,921** |

The final arm changes only **five** occurrences: indices 5, 19, 24, 31 and 40.
It leaves damaged, uncertain and legacy-repaired occurrences unchanged. Its
font programs are unchanged: this trial demonstrates **no font-byte saving**.
It is 141 bytes larger than the save-only control; the apparent 316-byte saving
against native output is serialization, not glyph economy. Unreferenced programs
would need a correctly integrated construction-time remap before savings could
be claimed. There is no reason to integrate that additional matcher complexity
on the strength of this selected page alone.

Full shadow PDF SHA-256:
`ca105ba6cabb1a619d65c019903e04fcde0de203cf89691e2c13c4e9f3825100`.
Only five `Tm`/`Tj` pairs on page 1 change. All image samples, font programs,
ToUnicode and other normalized operators remain identical; both engines' native
extraction hashes match their own baseline. qpdf passes; the font is the exact
previously OTS-validated program. A parse/unparse-only control changes **zero
pixels** at 300 and 600 DPI in either renderer.

The [persisted independent review](qualification/font02/reuse-review.md) records
blinded independent review finding no material regression in the inspected real-page
substitutions. The rotation arm weakly favored the baseline; the no-rotation arm
was mostly indistinguishable with weak subjective preferences. A claimed improvement
in unchanged `Term` was explicitly withdrawn after the control established equality.
These preferences are not evidence of a general visual gain. The inherited broken
`s` adjacent to one `expires` remains unchanged and is not repaired by sharing `e`.

## Held-out substitution gate — failed

FONT-01 family-disjoint validation and test sets are retained. Public geometry
provides controlled OCR for this experiment; these are not Tesseract recognition
claims. One observation per face/character/severity is selected before scoring,
with characters `e`, `1`, `a`, `8`, `.`, `!`. D0 donors and D0/D1 healthy targets
are separate from D2–D4 damage. Face labels stratify the evaluator's sample only;
source registration and rendered quality decisions do not use them. Different
font labels are not themselves a wrong-merge outcome.

The normal Rust control documents provide real emitted donors and placements.
The benchmark arm uses zero rotation, the same bounded translation/scale fit,
and source-derived line metrics. It renders each substitution at original page
coordinates and native 200/300/600 DPI using both engines. ROI geometry is the
union of public and assigned ownership boxes plus four pixels, so neither gets
silently cropped. This source-only ROI correction preceded any oracle-pixel
inspection; old artifacts remain archived locally.

Source decisions and coverage arrays were SHA-frozen **before** reading pristine
images. The [evaluation protocol](qualification/font02/reuse-protocol.json) was
also fixed first. A relative safe result requires both renderers' pristine-error
increase ≤0.002, core-IoU decrease ≤0.01 and absolute ink-area-bias increase ≤0.02.
A material-review flag is pristine-error increase >0.02 or core-IoU decrease >0.05
in either renderer. Intermediate cases abstain. Topology is candidate-versus-baseline in the frozen
source decision; pristine-relative topology was not measured. Absolute baseline and candidate
errors are retained: improving a poor baseline does not make the result pristine.

| Family-disjoint arm | Rendered pairs | Source gate accepts | Safe relative | Ambiguous | Material-review flags |
|---|---:|---:|---:|---:|---:|
| Validation | 279 | 26 | 20 | 5 | 1 |
| Test | 562 | 48 | 38 | 8 | 2 |

Independent inspection confirms **both test flags are real geometry failures**:
compact dots become upright slivers in PDFium and Poppler. The baseline itself
has over-wide dots; the candidate is wrong differently. Validation's flagged dot
is mixed, not a clean preservation pass. See the
[actual rendered counterexample](qualification/font02/examples/rejected-punctuation.png).
A favorable source-MSE comparison cannot establish safe substitution here.

The problem is broader than excluding punctuation: among the four source-accepted
validation `1` pairs only one meets the frozen relative-safe criterion. The only
accepted validation `e` pair is ambiguous; test `e` has two safe and one ambiguous
accepted pairs. No hard-negative case was removed after seeing its result.

Diagnostic ROC-AUC for predicting the frozen relative-safe rendered outcome:

| Arm | Current binary score | Registered grayscale score |
|---|---:|---:|
| Validation | 0.8556 | 0.7668 |
| Test | 0.6766 | 0.6920 |

This is not a head-to-head comparison of complete production matchers: all candidate
placements use the experimental registration, and raw production-score thresholds
omit cohort support and downstream checks. Nevertheless there is **no consistent
ranking improvement** supporting the proposed score. Python's diagnostic 32×32
score matches all 199,395 pairs exported by the exact Rust function, with maximum
absolute difference zero. The [per-character results](qualification/font02/reuse-results.json)
include safe, ambiguous and flagged cases separately.

## Phases 3–5 disposition

**Stop this approach at the initial go/no-go gate.** Real-page sharing can look
acceptable, but registration plus nonworse source-coverage error is not a reliable
healthy-substitution policy on unseen controls. No threshold adjustment, trained
model, generalized grouping, multi-witness outline fit or new Rust matcher is shipped.
The individual-source trace and strongest emitted-donor arms were compared; they
do not establish that fitting a consensus would cure the observed safety failure.

Damaged-glyph recovery remains separate and unchanged. The requested `constant`
opening on PDF page 11 / printed page 105 was personally inspected with source,
Adobe and current product at fixed coordinates. The frozen OCR word is **`‘ronstant`**
(confidence 31), not a `c` observation. Replacing its opening with a `c` inferred
from prose would violate the character-identity constraint. Both Adobe and current
output retain a visibly broken opening. We abstain; we do not report it repaired.
The mixed typography/artwork page was also inspected against source and Adobe;
no substitutions were made there. Existing donor-repair regression successes
remain covered by the 141 passing Phase 1 workspace tests. No new D2–D4 repair
trial is claimed, because the prerequisite healthy-reuse gate failed.

## Reproduction, evidence and remaining limitation

[Manifest](qualification/font02/reuse-manifest.json) records versions, exact local
paths, SHA-256 hashes, complete PDFs, matrices, source decisions and coverage maps.
Large artifacts remain ignored. The local hash-addressed research archive retains
the exact source-extraction, registration, substitution, rendering and closure
scripts; it includes the read-only Rust probe, not a product branch. Its private
function extraction is bound to the recorded production source hashes. Existing
FONT-01 corpus and comparator assets remain required; none are downloaded or
regenerated during normal conversion.

The maintained read-only evaluator reproduces the first oracle run exactly:

```sh
qualification/.venv/bin/python -m unittest qualification.font02.test_rendered_reuse
qualification/.venv/bin/python -m qualification.font02.rendered_reuse \
  --artifacts qualification/font02/local/hard-negatives \
  --corpus qualification/font01/local/corpus-font01-v1 \
  --split test --output qualification/font02/local/hard-negatives/test-reproduced.json
```

The seven evaluator tests cover identity, a dot-to-sliver regression, geometry
mismatch, two-renderer agreement and tamper detection. Source-fitting and rendered
probe generation are more expensive than this read-only scoring step: the frozen
validation and test render measurements took approximately 48 and 70 seconds,
respectively; these are not ordinary CLI or Rust-inference timings. No claimed
product matcher performance improvement exists. Phase 1's actual CLI RSS/time
measurements remain above; matcher-research peak RSS was not instrumented.

**Product outcome:** construction-time unused-program elimination is shipped;
experimental reuse is rejected and preserved as evidence. Faithful, donor repair,
OCR, geometry and ACR-05 composition remain unchanged. Historical P01–P08 visual
limitations are not reclassified by green CI.

**Specific remaining blocker:** a source-error fit can reward a geometrically
inappropriate donor when the source/individual rendering is already imperfect,
particularly at tiny marks. A next method must independently constrain actual
stroke shape and scale under native sampling, and demonstrate held-out rendered
non-regression; nominal font labels or a higher normalized similarity score do
not supply that evidence. This report does not authorize another model search.

### Research closure checks

The final research tree passes 141 unfiltered workspace Rust tests, configured
Clippy with denied warnings, the existing Python qualification workflow commands,
and seven new evaluator tests (86% measured statement coverage of the evaluator).
Validation and test re-evaluation exactly reproduce every first-run per-pair
numerical result. Independent code/evidence review found two documentation gaps
(topology scope and archived blind judgments); both were corrected and the reviewer
reported no remaining blocker. GitHub CI, Sonar and CodeRabbit status are recorded
in the research PR; none is substituted for the failed visual safety gate.
