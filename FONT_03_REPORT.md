# FONT-03 — Consensus glyph reconstruction and reuse

## Decision

**Multi-observation fitting is promising; the tested automatic reuse policy is
not qualified for production.** A robust common coverage field improves average
and tail pristine-reference error substantially. Earlier source-only gates admit structural counterexamples. The final directional
49-case blinded review finds no confirmed material canonical defect, but retains
minor contour caveats; a grouping-symmetry defect then requires regeneration. The
conservative real-page
construction control grows the font rather than retiring programs. No converter,
OCR, ownership, font dictionary, faithful or raster-composition behaviour changes
in this research branch.

This is not a rejection of canonical reconstruction. It separates a positive
fitting result from unresolved acceptance and cohort-support problems. It also
measures actual pre-union font construction rather than attributing savings to
post-generation reference edits.

## Baseline and provenance

- Accepted FONT-02 product: `790a2f978af6c01fd699cb74ed05b457488bc3d2`.
- FONT-02 research PR [#23](https://github.com/mitchins/scanweave/pull/23), exact
  reviewed head `37ddcdebb694c62682e7cd805af8aabc6135987a`, was independently
  judged useful evaluation infrastructure and merged normally. Its rejected
  matcher was **not** activated.
- Starting remote main for FONT-03: `c10e3dff93ca12ac410c0f6626a4ef74ce34e0c1`;
  branch `research/font03-consensus`.
- Fresh main [CI](https://github.com/mitchins/scanweave/actions/runs/39894249920)
  and [Sonar workflow](https://github.com/mitchins/scanweave/actions/runs/39894249992)
  passed. Server analysis `e4d3096b-506d-405d-906a-d04f085f2b13` records this exact
  revision and Quality Gate **OK**. Zero open PRs at that checkpoint.
- Frozen financial input and normal 13-page donor context are retained. No
  comparator, historical benchmark or sealed holdout was modified.
- Product financial PDF: **2,849,237 B**, SHA-256
  `74c31136d00a18dbf05fba2d7fba59c85cc201a57ae65d77999a025a692fab0f`.

Compact measurements: [results.json](qualification/font03/results.json).
Exact file identities, tool versions and local artifact paths are recorded in
[manifest.json](qualification/font03/manifest.json). Reproduction instructions:
[research README](qualification/font03/README.md). Large PDFs and native render
arrays remain local and ignored.

## Experiment and coordinate contract

The first experiment uses the actual 42 visible `e` observations on Town
Officers, not independent glyph-box rescaling. Source-owned grayscale coverage
and narrowly supported fringe are mapped to a common 64-pixel frame using line
x-height 32 and baseline 48; original source placement, paper/ink estimates and
transforms remain explicit. The line geometry is estimated from source/production
ownership, not pristine font files.

Healthy-source adjudication yields 33 observations. Two have inherited legacy
repairs and are excluded from ordinary reuse; seven damaged and two uncertain
observations are also excluded. The 31 remaining sources form six complete-link
groups of sizes 13, 6, 2, 7, 1 and 2. Only the three groups with at least three
members are fitted initially: 26 occurrences. These are manually adjudicated
research inputs, **not an automatic production health classifier**.

Arms:

- **A:** existing production outline and placement.
- **B:** a source-supported representative/medoid outline; held-out target is not
  used as its own donor.
- **C:** aligned coverage fitted by 12 Huber IRLS iterations, delta 0.12. Residual
  confidence/uncertainty is retained; no pixel median is used as the outline.
- **D:** robust signed-distance fitting plus limited spatial regularization,
  addressing coverage-fit broadening. This control uses C's target placement,
  so it does **not** establish that every independently registered distance-field
  fitter is inferior.
- **E:** C with bounded translation ±2 grid pixels, rotation ±1 degree and
  independent x/y scale 0.96–1.04; no shear or nonlinear deformation. This was
  motivated by same-face boundary-hit failures and the benchmark's independently
  documented scan transforms. Initial groups and admission threshold remain fixed.

Actual canonical fields are traced using the existing Rust grayscale contour
fitter and font assembler. They are tight-cropped before tracing, with explicit
crop-frame preservation; an early padded-frame probe was discarded because it
misused the tracer's crop-coordinate contract. No reported final comparison uses
that invalid probe. Font-only PDF atlases and complete financial shadow PDFs are
rendered at original physical coordinates through both PDFium and Poppler.

### Clustering and structural evidence (H1)

Same supplied character is mandatory. Deterministic complete-link grouping
requires direct compatibility with **every** member, preventing single-linkage
chaining. Discovery overlap remains 0.76; no global threshold is lowered.
Structural checks cover mass, extents, centroid, elongation/orientation, median
stroke thickness, components and holes. Final refinements add grayscale effective
stroke width, covariance cross-moment, horizontal/vertical cumulative ink profiles
and explicit counter geometry.

The initial structural veto rejects all three FONT-02 flagged substitutions,
including both confirmed dot-to-sliver failures, but also rejects many previously
safe examples: 19/20 in validation and 25/38 in test. It is useful protection,
not a complete or well-calibrated replacement policy.

### Noise calibration and leakage boundary (H3)

Calibration uses **known-consistent training-face groups only**. Mixed-face
training groups are excluded from estimating normal variation; nominal face
labels never select inference donors or rewrite characters. Severity labels
select the D0/D1 healthy evaluation arm. Pristine pixels are opened only after
source decisions/render arrays are saved and hashed.

Initial uniform-registration calibration: 83 leave-one-out source errors,
95th percentile 0.03714814. Affine calibration on the same scope: 83 errors,
95th percentile 0.03322769. A normalized-field allowance alone misses placement
and renderer-phase defects; the next gate therefore also limits native rendered
source error in **each** engine to current error plus the training allowance.

Final structural limits are the fixed 95th percentile of 44 training-only
leave-one-out comparisons with at least three other witnesses:

| Descriptor | Limit |
|---|---:|
| Effective stroke log-ratio | 0.10903095 |
| Covariance cross-moment difference | 0.01793677 |
| Horizontal cumulative profile difference | 0.00662265 |
| Vertical cumulative profile difference | 0.00591026 |
| Counter-region difference | 0.07622799 |

At least three independent **other** healthy witnesses are required. Native
width/height below four pixels, or maximum extent below 0.35 line x-height,
causes abstention; this generic undersampling rule is not a per-character ban.

These refinements were motivated by development failures. The family-disjoint
FONT-01 test families were already inspected in FONT-01/02 and here. They are
**not an untouched holdout**. Hash freezing prevents accidental recomputation
against oracle pixels; it does not make adaptive development an independent test.
Also, the normalized-source error allowance is a heuristic transferred to native
render error, not a validated probabilistic prediction interval.

## Initial directional synthetic results (H2/H3)

These measurements preserve the pre-review experiment. Independent review found
21/247 within-group validation pairs passed only one registration direction.
The original unordered cache incorrectly treated a directional fit as symmetric.
This makes the claimed complete-link safety incomplete, even where actual visual
results are encouraging. `symmetric_compatible` now requires both directions and
uses the minimum score, with an explicit regression test; no threshold changed.
Regenerated results are reported separately below.

The existing 5,175-observation, 23-face corpus remains unchanged. The bounded
study uses six fixed character identities `e1a8.!`, all three source DPIs and
family-disjoint train/validation/test splits. Source extraction yields 546/466/538
usable observations, with 6/17/14 explicit abstentions. D0/D1 healthy eligible
counts are 251/216/244. No claim is made for every character in the full corpus.

There are 81 validation and 136 test targets with sufficient witnesses and an
actual visible production glyph binding. Every fitted synthetic canonical field
excludes its target's pixels. Target source evidence may fit bounded placement;
pristine pixels do not. Each held-out field is a reconstruction test, not a claim
that all leave-one-out outputs are one identical final font program.

Error below is sum of squared coverage difference divided by pristine ink mass,
not ordinary page-wide pixel MSE. Means and 95th percentiles include both engines.

| Arm | Validation mean / p95 | Test mean / p95 |
|---|---:|---:|
| A, existing individual/current production | 0.22693 / 1.02091 | 0.22197 / 0.59567 |
| B, representative | 0.30397 / 1.48907 | 0.21961 / 0.51686 |
| C, robust coverage | 0.10908 / 0.20923 | 0.12189 / 0.24592 |
| D, distance control | 0.17813 / 0.37582 | 0.22005 / 0.46731 |
| E, bounded affine coverage | **0.09786 / 0.20213** | **0.11366 / 0.24994** |

C/E establish a real average/tail fitting opportunity. B does not provide the
same benefit. Neither average error nor a lower point count establishes safety.
FONT-02's frozen per-occurrence diagnostics flag 40/68 C targets and 37/65 E
validation/test targets for review. These are measurement flags, not automatically
adjudicated material visual failures; inherited current-outline defects also exist.

| Acceptance iteration | Validation accepted / flagged | Test accepted / flagged |
|---|---:|---:|
| C normalized source and native geometry | 59 / 28 | 90 / 41 |
| E, same initial gates | 63 / 27 | 101 / 42 |
| E plus native rendered error budget | 44 / 8 | 68 / 9 |
| E plus support, tiny-mark abstention and calibrated structure | **23 / 4** | **26 / 5** |

For those final accepted subsets, baseline→E mean error is 0.16188→0.07134 in
validation and 0.22573→0.08443 in test. Tail p95 improves 0.32708→0.18705 and
0.41938→0.16741. All 49 accepted examples were reviewed, still blinded, in both engines. Four
clear material panel defects map to the **current baseline**, not the canonical
result. Canonical cases 3, 5, 17 and 30 show real but minor counter-rounding and
weight changes; the reviewer found no clear material loss in these views. The
nine numerical flags and four contour caveats remain disclosed. This finite
result does not negate the grouping defect or establish universal safety.

## Corrected symmetric regeneration

The review fix was independently checked and every affected synthetic group,
field, native render and gate was regenerated. All pairwise thresholds are
unchanged; both directional fits must now pass. Train/validation/test healthy
cohort counts become 120/122/107, compared with 99/109/88 previously.

Affine noise calibration now has 79 consistent training comparisons, q95
**0.03084993**. Structural calibration has 43 comparisons. The same fixed q95
policy yields stroke 0.05233308, cross-moment 0.02263815, horizontal profile
0.01320177, vertical profile 0.00939400 and counter difference 0.10762658.
Some learned limits increase and others decrease because the training groups
changed; none was manually adjusted to admit a desired result.

| Corrected arm | Validation mean / p95 (65 targets) | Test mean / p95 (111 targets) |
|---|---:|---:|
| A, current | 0.20705 / 0.47314 | 0.18320 / 0.41905 |
| B, representative | 0.27274 / 1.69801 | 0.19865 / 0.42514 |
| E, robust affine coverage | **0.09194 / 0.19735** | **0.09885 / 0.20532** |

The final source gates accept **24/65 validation and 28/111 test targets**.
Two and five targets respectively retain pristine-reference review flags.
For accepted targets, mean baseline→canonical error is 0.16235→0.07385 and
0.25205→0.08058; p95 is 0.32420→0.19174 and 0.57582→0.16204. C/D in these
regenerated atlases are identical E controls, not independent fitters.

These regenerated arrays supersede the directional safety ledger, not its
historical measurements. The 52 accepted cases received a fresh blinded two-renderer review. No confirmed
material canonical regression was found; cases 7, 5 and 15 retain minor counter/
weight caveats. Case 7 has a gray counter band but remains open in both engines.
All five strong material panel defects belonged to the existing baseline. This
is a limited visual pass, not blanket production qualification.

An independent regeneration audit recomputed all 864 within-group pairs (273/232/359):
every pair passed both directions, with no cross-character merges. Plans and all
source/render hash bindings match. Final accepted-subset measurements filter the
24/28 decision files, not the broader 55/90 initial-gate summaries.

Per-DPI, character and D0/D1 results are retained in `results.json`. These final
acceptances are predominantly `e`; the study does not demonstrate safe healthy
reuse of every tested numeral or punctuation class. No production activation
follows from favourable averages or this finite visual review.

## Actual real-page font construction (H4; pre-review fixed-plan control)

Initial complete financial B/C shadow PDFs retain old programs. Their sizes
(2,849,222/2,851,118 B in the affine trial) are **not font-saving evidence**;
pikepdf serialization and an extra font confound those comparisons.

The pre-review real source-field gates admit 22/26 proposals, but native two-renderer
checks admit only four (`e` indices 7, 8, 9, 36). The others remain individual
exceptions. The ordinary compositor cannot express arbitrary per-occurrence
rotation; the construction control sets rotation to zero, retains bounded
axis scales and rechecks actual native appearance rather than silently expanding
the production geometry API.

An isolated temporary checkout runs the normal PDF-to-PDF CLI on the original
13-page input, with a fixed source-bound scientific intervention **before**
document font union and required-program pruning. It traces three source-derived
common fields, updates four occurrences, then uses the existing font builder,
CID/GID remapping and PDF assembly. Exact source RGB hash, dimensions, symbol IDs
and supplied `e` identity bind the intervention. This is not a deployed automatic
Rust canonicalizer: Python research grouping and manually adjudicated health
remain prerequisites. The patch and generated-plan procedure are reproducible.

| Scorecard | Accepted baseline | Pre-union control |
|---|---:|---:|
| Visible glyph draws | 3,717 | 3,717 |
| Distinct visibly used GIDs | 2,236 | 2,239 |
| Draws per visible design | 1.6623 | 1.6601 |
| Required font slots, including `.notdef` | 2,238 | 2,241 |
| Town visible `e` draws / designs | 42 / 19 | 42 / 22 |
| Encoded font bytes | 727,259 | 727,982 |
| Decoded font bytes | 1,303,200 | 1,304,288 |
| Font outline points | 449,268 | 449,628 |
| Raster stream bytes | 1,973,037 | 1,973,037 |
| Complete financial PDF bytes | **2,849,237** | **2,849,982** |
| Wall seconds | 496.86 reference | 469.90 observed |
| Peak RSS KiB | 1,466,412 reference | 1,489,120 observed |

Visible design counts follow CID-to-GID mappings and graphics-state save/restore;
raw CID counts incorrectly overstate this quantity. The three new canonical
programs do not retire originals still referenced elsewhere. The four old targets
used only two existing GIDs (123 for targets 7/8/36 and 73 for 9); assigning them
to three new source-fit designs can actually split existing reuse. Net result:
**+745 PDF bytes, +723 encoded font bytes, +3 slots**. Successful same-group reuse
of two targets is insufficient to make this document smaller.

The hook runs after individual page tracing but before union, so no tracing-work
saving is demonstrated. Timing is unpaired and overlapped with qualification;
**no speedup is claimed**. Canonical tracing points for the three initial corrected
real fields are 180, 158 and 168. There is no proven compact-font product result.

The actual control PDF is
`qualification/font03/local/financial-preunion.pdf`, SHA-256
`ba0eefad8fda388838e05fe6e06aba23324557e182a2b976b5c42dd557c87e81`.
qpdf and OTS pass. Native PDFium and Poppler text extraction are identical to the
baseline. At 300 DPI, pages 2–13 are pixel-identical in both engines; only the four
intended page-1 glyph regions change. Raster resources are unchanged.

### Other real characters and controls

A read-only CID-to-GID audit covers all 13 financial pages. Visible draws for
`e/a/o/t/1/8/./,` are 291/159/179/149/120/66/24/47. Sums of per-page visibly
used designs are 167/105/109/91/77/47/19/44 respectively; these sums are **not**
global distinct designs. The machine-readable per-page ledger is retained.
No additional real characters are remapped: the first actual construction
control already fails economy. Native extraction and renders outside the four
`e` regions remain unchanged. Numeral/punctuation structural substitutions are
challenged synthetically, not claimed as a successful real deduplication result.

The existing fixed-coordinate `expires`, broken `constant` opening and mixed
historical/illustrated type controls were personally inspected. Their source
identities and inherited irregular typography are retained. No new font-face
labels or prose-derived character corrections are asserted.

## Damaged repair is separate and rejected

A bounded D2–D4 probe selects one source per available character/severity stratum:
17 observations per split. Healthy same-character groups supply common templates;
a one-sided surviving-ink fit, ≥40% survival, ≤10% unexplained source ink and a
best/next margin of 0.015 decide proposals before pristine evaluation.

Two validation and five test proposals pass that source policy. Several recover
missing strokes: validation D3 `e` error 0.08240→0.02820; test D4 `e`
0.19481→0.01113 and D4 `a` 0.20127→0.02515. However validation D2 `1` worsens
**0.02127→0.42643**; test D2 `8` and D3 dot also worsen. Surviving-ink containment
and a score margin do not establish correct design identity. These normalized
coverage comparisons are not native-PDF repair qualification. No repair changes
are promoted, and these outcomes do not change healthy-reuse admission.

The opening of `constant` remains an unreliable OCR label (`‘ronstant`, confidence
31); no `c` is inferred from English prose. Existing proven donor repair remains
unchanged and its unfiltered Rust regression passes.

## Independent review and disposition

Final code and blinded visual review records are retained alongside the report.
Earlier blinded reviews found that coverage fitting often smooths contours, but
also found counter/slant changes in `8`, rounded italic punctuation and a smaller,
rounder `e`. That evidence motivated the final support/structure gates rather than
threshold relaxation. Town repeated-word sheets show no convincing general
reading-size improvement, and inherited broken `s` typography remains untouched.

**Production decision: unchanged.** H1 provides useful but incomplete safeguards;
H2 has positive average reconstruction evidence; H3 has a limited healthy-cohort visual pass, but is not a broadly validated
per-occurrence acceptance model; H4's actual pre-union control fails economy.
No full 32-page rerun is justified for an unqualified, unactivated research arm.

The next focused question is whether a render-grounded structural acceptance
model can retain the demonstrated fitting gain while rejecting counter, terminal
and phase-dependent changes—and whether it supports a sufficiently large shared
cohort to retire existing designs. That must be measured against one common
final outline per cohort, not inferred from favourable leave-one-out averages.
A new OCR/font-recognition architecture is not established as necessary here.

## Validation and limits

The independent [review record](qualification/font03/review.md) and compact
[examples](qualification/font03/examples/) preserve both favourable cases and
remaining counter/repair caveats. Example U/V labels remain the original blind
panels; `review.md` records attribution after judgment.

- 141 unfiltered workspace Rust tests pass, including 300/600-DPI document and
  genuine donor-repair regressions. Fourteen new research unit contracts pass.
- The repository's exact denied-warning Clippy contract passes. An additional
  `--all-targets` run exposes inherited test warnings and two unrelated untracked
  example imports; they are disclosed, not suppressed or fixed in this mission.
- qpdf, OTS, native extraction and both-renderer comparisons validate the actual
  complete construction-control PDF, not merely a glyph atlas.
- No normal converter Rust file changes. Required-glyph pruning, faithful,
  ACR-05 composition, OCR transcription and Unicode contracts remain as on main.
- This finite, development-selected evaluation does not establish zero risk or
  generalization to all glyph classes, severe degradation or unseen scans.
- No model, oracle font or pristine authoring shape enters ordinary conversion.

Practical references: Leptonica's public
[`jbclass.c`](https://github.com/DanBloomberg/leptonica/blob/master/src/jbclass.c)
illustrates size/centroid guards, correlation/rank-Hausdorff classification and
composite templates. Those ideas informed the comparison; no implementation was
copied. This prototype deliberately remains small, inspectable and separate from
production.
