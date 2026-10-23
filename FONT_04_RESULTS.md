# FONT-04 results — Checkpoints A and B1

**Status: discovery checkpoint, unqualified. Stop at B1.** The experimental complete PDF is 175 bytes smaller and uses seven fewer programs, but native financial fidelity is mixed. No product change is promoted, nothing is merged, B2 is not started, and P2 data remains untouched.

Contract: `06f24b122e1cd1cd879880166b8240c7e75747ed`. Product baseline: `c10e3dff93ca12ac410c0f6626a4ef74ce34e0c1`. The preregistration retains SHA-256 `a4f9ccd3a7e51d719946be80f7cc9a297de7ca22285e8755e5e26e415e7db466`.

## Checkpoint A

The forward and reverse controls use actual production A0, fresh native self tracing with floor on/off, crop versus ownership/local normalization, native versus line frame, source-only bounded placement, and independent non-target witnesses. The extra native floor-on self control separates preservation from legacy witness choice. No pristine pixels enter preparation, tracing, candidate ranking or placement.

P1 covers `e1a8.!` plus ten Latin classes `odynstrcul`, across all three development splits and all damage/DPI strata. Eligible targets: train 935/1,056; validation 813/924; test 934/1,056. Every arm uses the same eligible targets; all 354 abstentions are retained by ID. The inherited ownership files held only eight classes; a full production ownership export and separate extension repaired that population defect. Financial causal controls cover all 291 visible `e` across 13 pages; they do not establish a sixteen-class real-document result.

| Population | Renderer | A0 error | A4 error | F-self error | F-medoid error |
|---|---|---:|---:|---:|---:|
| train | pdfium | 0.15106 | 0.14779 | 0.09332 | 0.15448 |
| train | poppler | 0.17325 | 0.12199 | 0.16215 | 0.12575 |
| validation | pdfium | 0.14007 | 0.14632 | 0.09129 | 0.15216 |
| validation | poppler | 0.17209 | 0.12633 | 0.17558 | 0.12664 |
| test | pdfium | 0.14524 | 0.14649 | 0.08809 | 0.15013 |
| test | poppler | 0.16713 | 0.12113 | 0.16088 | 0.11918 |
| financial | pdfium | 0.06991 | 0.10426 | 0.03338 | 0.13910 |
| financial | poppler | 0.15533 | 0.11506 | 0.10804 | 0.13546 |

Error is squared coverage difference normalized by union ink. P1 uses pristine references; P3 uses an ownership-normalized source layer at the original physical transform. The JSON reports each class, p95/worst-ten, DPI/damage strata, area/IoU/contour metrics, and per-toggle explanatory shares. Shape alignment removes centroid translation without rescaling or removing slant. Shares can be negative or exceed 100% because interventions interact and some total gains are near zero; they are not additive.

Placement explains a large share of the PDFium fresh-trace gain, but refitting the existing A0 outline does not transfer reliably to Poppler and worsens financial source error. Simply removing the native preservation floor often worsens quality; crop normalization alone has little effect. F-self and F-medoid are not interchangeable in this all-target source-selected population. The cap is inactive in all evaluated native crops (maximum selected P1 crop: 7,144 samples), so it cannot explain this measured gain.

No mechanism/pair is production-qualified: the financial blind judgments are pending, renderer directions differ, and production P2/P4 qualification is outside this launch. Therefore no individual-reconstruction product branch is prepared. The 87-member/174-panel A review is separate from sharing review. Causal font/atlas bundles are measurement controls, not complete candidate product conversions; their bundle bytes must not be presented as product economy.

Machine-readable result: [checkpoint-A.json](qualification/font04/checkpoint-A.json); concise table: [checkpoint-A.md](qualification/font04/checkpoint-A.md).

## Checkpoint B1

Run `scanweave input.pdf output.pdf --dpi 300 --profile clearscan --glyph-sharing experimental`. The opt-in research mode depends on the checked-out scientific Python environment. It gathers only visible `e`, retains the inherited structural vetoes, adds orthogonal effective-stroke/counter-band checks, and remaps before document font union and required-program construction. Exceptions retain their current outlines. No cross-label merge or damage repair occurs.

| Quantity | Default | Experimental |
|---|---:|---:|
| Visible glyph draws | 3,717 | 3,717 |
| `e` draws / designs | 291 / 155 | 291 / 148 |
| `e` draws per design | 1.877 | 1.966 |
| All visible designs | 2,236 | 2,229 |
| Required font slots | 2,238 | 2,231 |
| Encoded font bytes | 727,259 | 725,422 |
| Decoded font bytes | 1,303,200 | 1,299,032 |
| Outline points | 449,268 | 447,873 |
| Complete PDF bytes | 2,849,237 | 2,849,062 |
| Added / retired / net programs | — | 29 / 36 / −7 |

The selected point is star grouping, fresh source-witness canonicals, noise multiplier 1.0: 124 remapped members and 167 exceptions. Retirement means zero remaining users. Independent CID→GID/compiled-program accounting confirms 36 retired and 29 added programs; no old `e` program has invisible or cross-label users, and all non-`e` visible programs and placements are identical.

The 3 grouping alternatives × 7 error multipliers are all measured in both native renderers. The candidate search is bounded to 24 source-shortlisted witnesses per member (6,984 directed pairs); 77,406 other pairs are untested, not rejected. The sparse star uses support-first ordering and is not a complete-matrix medoid search: missing comparisons can make median priorities infinite. This coverage-oriented replacement targets economy directly, but its ordering and shortlist remain algorithm limitations, not grounds for falsification. The selected point was retained after calibration: on 193 known-design D0/D1 `e` comparisons, error-only rejection is 13.47% (within the 15% objective), hard-only rejection is 4.15%, and family-wise rejection is 16.58%. Other class support is explicitly recorded; sparse classes do not inherit the `e` calibration claim. No hard veto was relaxed. The real rejected ledger contains 88 insufficient-noise-support cases; these remain exceptions.

| Native source error | Default mean | Experimental mean | Default p95 | Experimental p95 |
|---|---:|---:|---:|---:|
| pdfium | 0.06991 | 0.09275 | 0.14708 | 0.17684 |
| poppler | 0.15533 | 0.13518 | 0.21402 | 0.20000 |

**This is mixed fidelity, not a safe improvement.** All measured positive-net-saving frontier points worsen PDFium mean source error; Poppler improves. The analytic fitted-source criterion does not transfer reliably to actual native drawing. Larger savings exist on the curve (up to 56 net programs), but they are not qualified operating points. There is no P3 pristine reference, and material-defect fields remain null pending blind judgments.

[Native frontier data](qualification/font04/reuse-fidelity-frontier.json), [PNG plot](qualification/font04/local/frontier/frontier.png), [SVG plot](qualification/font04/local/frontier/frontier.svg), [rejection ledger](qualification/font04/rejection-ledger.json), [scorecard](qualification/font04/checkpoint-B1.json). Frontier PDFs are glyph measurement controls; the two deliverable financial PDFs below are complete ordinary documents.

## Complete PDFs and checks

- Default: `qualification/font04/local/financial-default.pdf` — SHA-256 `74c31136d00a18dbf05fba2d7fba59c85cc201a57ae65d77999a025a692fab0f`. Byte-identical to the independently run current-main binary.
- Experimental: `qualification/font04/local/financial-experimental-v2.pdf` — SHA-256 `1020b7dd78e69afbf3659d14cb11169426c315c588bcd5792fe2dfe03cbbfca4`. The complete CLI repeat has the identical hash.

Both complete PDFs pass qpdf and OTS. PDFium native extraction and all extracted-word Find counts agree exactly; Poppler extraction agrees exactly (literal search on that equal extraction also agrees; the CLI has no separate Find API). Save-only serialization controls separate repackaging effects; the primary byte comparison uses the same normal Rust serializer in both modes. All image/compositing inputs and non-`e` draws remain unchanged. Eighty-four relevant crate tests pass.

| Run | Wall time | Peak RSS (KiB, `/usr/bin/time -v`) |
|---|---:|---:|
| main | 7:45.10 | 1,488,760 |
| default | 7:48.95 | 1,459,020 |
| experimental | 9:46.70 | 1,494,436 |

Runs overlapped other discovery work; these wall times are not an isolated speed benchmark. The paired commands, stage reports and logs remain local and hashed.

## Blind review and negatives

The B1 set has 324 lossless panels: 92 accepted members (random, worst-error/area/contour/elongation/counter and cross-page probes), 50 random rejected members, and repeated words from distant pages, in both renderers at 100% and 400%. Rejected panels show the attempted substitution, not the unchanged exception in the complete PDF. Blinding is performed in a separate process; keys stay local and unrevealed.

- [B1 blind sheets](qualification/font04/local/review/blinded-review.pdf)
- [Phase A blind sheets](qualification/font04/local/review-A/blinded-review.pdf)
- [Original negative/style sheets](qualification/font04/local/review-negatives/blinded-review.pdf)
- [Additional Latin style sheets](qualification/font04/local/review-negatives-extension/blinded-review.pdf)

All 74 retained FONT-02 source-accepted controls are kept, including known dot/sliver, counter and italic cases. Hard vetoes catch all three previously material cases. The two negative sets include 112 style probes across all 16 tested characters. The prior `1` repair failure and its exact artifact hashes remain in the negative ledger; FONT-04 has no repair operation, so that operation is prohibited rather than rerun. Cross-label numeral controls are blocked before grouping. These are automated outcomes, not a claim of zero independently reviewed defects. Actual visual false-rejection and harm-catch rates require the sealed judgments.

To reveal a key, first save a complete copy of `judgments-template.json`, then run `review_key.py reveal <review-directory> <saved-judgments.json>`. The tool refuses incomplete judgments.

## Failure classifications and next experiment

| Failure | Class | Disposition / next step |
|---|---|---|
| Grouping counted canonicals later rejected at self-admission | algorithm | Fixed; exact complete-PDF accounting now agrees. |
| Two far-away OCR line baselines | algorithm | Fixed with local source vertical support; all 291 frames available. |
| Page-local OCR IDs collided in the initial financial causal export | algorithm | Fixed with page-scoped keys before final native measurements. |
| Eight-class inherited ownership cache | measurement | Fixed by full ownership export and the retained eight-class extension. |
| Gray-paper/neighbour contamination and nominal-DPI financial atlas mapping | measurement | Superseded by normalized source/glyph layers at the exact original MediaBox/transform. |
| Analytic accepted candidates disagree with native renderer fidelity | algorithm | Unresolved: fit/evaluate placement through the actual native compositor, then recalibrate one joint error family; retain every hard veto. |
| No independent materiality/visual rejection judgments yet | data | Review the sealed accepted/rejected/negative sets before selecting another operating point. |
| Sparse independent real witnesses / some synthetic class strata | data | Abstain and report coverage; do not impute support from other classes. |

No broader reuse opportunity is falsified: B1 covers only `e`, not the 55 frequent classes; native placement and independent rejection review remain unresolved. The plan’s 25% criterion is not applied. The small measured economy is retained as evidence, not rejected for missing an arbitrary size target.

## Hygiene and Git receipt

All 15 distinct Security findings from the two PR #24 snapshots were individually statically triaged (28 snapshot rows retained). Dispositions are not actionable under the documented local researcher trust boundary; no live Sonar states were changed. Independent acceptance and refreshed live analysis remain outstanding, so #24 remains draft/unmerged.

Draft [PR #25](https://github.com/mitchins/scanweave/pull/25), commit `480a281e780d28827e9ee8bd950fd0fb71a41da1`, proposes staged research coverage/CPD scoping only. It changes documentation, not active analysis settings; Security/Reliability and shipped-crate gates stay on.

Research implementation increments: `1ab7f83`, `62d63e2`; final evidence commit follows this report. No product branch qualified and no merge occurred. See [git-receipt.json](qualification/font04/git-receipt.json) and [manifest.json](qualification/font04/manifest.json). Existing local research files were preserved.

**Reviewer decisions requested:** assess the sealed materiality/false-rejection results; explain the native renderer/placement discrepancy; choose whether to resolve native placement in B1 before authorizing B2. Nothing here authorizes B2, P2 generation, a product merge, or a default-mode change.
