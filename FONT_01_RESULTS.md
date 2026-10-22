# FONT-01 — statistical cohorts and learned challengers

## Decision

**Merge useful research infrastructure; activate no classifier in ClearScan.**
The deterministic, linear and convolutional arms all fail the frozen safety
criteria. Higher average ranking accuracy did not produce sufficiently reliable
same-face assignments. Rust model deployment and converter grouping changes are
therefore deferred, rather than shipping an unsafe font merger.

## Publication and product baseline

Approved product PRs [15](https://github.com/mitchins/scanweave/pull/15),
[17](https://github.com/mitchins/scanweave/pull/17) and
[18](https://github.com/mitchins/scanweave/pull/18) were merged in order under the
repository's squash-only policy, without force-push or protection bypass:
`7dc3b5f68e16f44be64d0236d6f0420eb72f349e`,
`fc74b1a5c9c172123b7fa051928fc9acf040fde0`, then
`10b5d9318581717b45b018c3bf51b24525499295`.
Reconciled stacked heads retained exactly the previously accepted trees; effective
diffs and independent reviews were checked after each retargeting. Research
[14](https://github.com/mitchins/scanweave/pull/14) and
[16](https://github.com/mitchins/scanweave/pull/16) closed unmerged with explanatory
comments; their remote evidence branches remain. No rejected experiment entered
production. [Consolidation receipt](https://github.com/mitchins/scanweave/pull/18#issuecomment-6351607293).

A fresh release build reproduced every accepted ACR-05 collection byte-for-byte:
financial3,187,571; historical2,278,050; receipts1,288,188; mixed1,130,058;
forms859,524 bytes; total **8,743,391 bytes**. Synthetic300/600 PDFs were exactly
141,085/189,052 bytes; faithful forms855,127 bytes. Sixteen representative
Poppler/PDFium render hashes matched. All35 frozen source/comparator hashes were
unchanged. Unfiltered139 Rust tests including donor repair passed, as did the
configured denied-warning product Clippy command. A broader optional all-target
Clippy probe found inherited historical harness lints; these were not suppressed
or represented as the configured CI contract passing.

M1 benchmark [PR19](https://github.com/mitchins/scanweave/pull/19) merged to
`e8739e0e7d6a3169b5e2b93061cff81c60d2919a`.
M2 statistical API [PR20](https://github.com/mitchins/scanweave/pull/20) merged to
`9a187132f5ff9d3cf8c1d9e927f8450acfdee57e`, the base of
`research/font01-challenger-results`. Both had successful CI and completed
server-side Sonar gates. PR20 new-code coverage97.9%, duplication0%; its one
CodeRabbit batch-parity finding was corrected. Follow-up rate limits were covered
by independent review, not called automated approval. Sonar S8707 keys
`AaFlmY9OmHtJmemeD8Bs` (M1) and `AaFlydcAIWcgPfQvYnim` (M2) received precise,
independently reviewed and server-verified FALSE_POSITIVE dispositions for the
current operator-selected CLI output roots. They are not code fixes or approvals
of future service/LLM wrappers. Rules and Quality Gates were unchanged.

## Frozen benchmark and method

See [prior art](FONT_01_PRIOR_ART.md),
[benchmark contract](FONT_01_BENCHMARK.md) and
[reproduction instructions](qualification/font01/README.md).
The frozen corpus has5,175 actual-page observations,23 licensed installed faces,
nine pages at200/300/600DPI and D0–D4 degradation. Train/validation/test families
are disjoint; respectively8/7/8 faces and1,800/1,575/1,800 observations. Faces are
interleaved within pages and phrases, sizes and damage vary independently, and
same-face observations recur on distant pages. No font binaries are committed.
The published seed makes this a reproducible development benchmark, not a secret
holdout. The sealed product holdout was not opened.

Inference receives grayscale crops, character identity, source boxes, DPI and
opaque observation IDs. It rejects evaluator-only fields and hash mismatches;
discovered paths must resolve inside the operator-selected corpus. Evaluator
labels enter only an explicit exact-ID/character join. Oracle authoring metrics,
face names, pristine shapes and damage labels are never inference features.
Character labels/bounds are supplied in this controlled arm; it does not measure
real Tesseract recognition accuracy.

The deterministic baseline estimates paper/ink locally, preserves aspect ratio
and uniformly fits observed ink into48×48 comparison frames. It tests rotations
−1.5/0/+1.5°, scales0.97/1/1.03 and translations±2pixels, in both directions.
Eleven features describe grayscale overlap, chamfer distance, area/proportions,
stroke width, topology, registration cost and contrast. This is bounded comparison
registration, **not** a placement estimator or arbitrary shape deformation.
Damage or neighboring ink can bias the observed crop normalization.

Severity-balanced pair sampling requested10,000/6,000/6,000 pairs; available strata
produced9,344/5,701/5,744. The linear arm is L2-regularized logistic regression.
The CPU CNN has63,696 encoder parameters, four small convolutional blocks and a
48-dimensional normalized embedding. Thirty epochs combine face classification
with cross-character supervised contrastive loss. One hybrid adds CNN distance to
registered features; one context challenger adds geometry-derived line evidence
excluding the query character. No oracle line IDs are features. Mixed-face lines
remain in the benchmark. There was no architecture search. The CNN used mixed-face minibatches and competing
related style classes, but no separate nearest-negative mining pass. This bounds
the negative result; it is not evidence that every learned metric will fail.

All thresholds and checkpoint selection used validation only. Model/validation
hashes were frozen before test. The strict packaged baseline reproduced every
feature/target value exactly, and the packaged CNN reproduced all three embedding
arrays exactly. The final research run took51.68s wall time on two CPU threads,
peak RSS773,268KiB; this is research training/evaluation, not converter overhead.

## Pair results

Frozen shortlist: at most0.5% different-face FPR on healthy D0/D1 validation,
at least50% same-face recall. Unseen-font healthy FPR must remain≤1%.
Validation has901 positive/1,200 negative healthy pairs; unseen has944/1,200.

| Arm | Validation AUC | Validation recall @0.5% FPR | Unseen AUC | Unseen recall | Unseen FPR |
|---|---:|---:|---:|---:|---:|
| Deterministic | .76379 | 27.97% | .70994 | 34.32% | 3.83% |
| Linear | .84782 | 28.52% | .76190 | 36.65% | 3.33% |
| CNN | .92925 | 13.87% | .87765 | 12.18% | 1.17% |
| Registered + CNN | .93249 | 25.08% | .88586 | 25.74% | 2.42% |
| Other-character context | .96105 | 32.08% | .91998 | 34.64% | 3.00% |

**No arm passes either combination of gates.** CNN is better at ranking than
hand-selected features, but worse at useful recall in the required low-false-merge
tail. Context improves ranking further, without making the tail safe. No winner
was selected after seeing test. Severe-damage recall is lower. Per-character,
DPI, damage-band, same-family hard-negative, PR-AUC and calibration measurements
are in [results.json](qualification/font01/results.json). Logistic probabilities
are under the training-pair prior, not deployment guarantees. ECE is deliberately
null for deterministic scores and cosine similarity: they are not probabilities.
Pairs share fonts/masters; binomial independence and population-level confidence
are not claimed. Only three held-out families are represented.

## Canonical groups versus font cohorts

Complete-link clustering uses the frozen threshold and character cannot-links;
it avoids single-link chaining. On the full unseen set it finds1,244 canonical
groups for288 true face-character groups: ARI.1458, purity.9272,
completeness.3333,99 contaminated groups and912 singletons. These are not eight
recovered font cohorts.

An actual three-page Rust conversion using only public OCR character boxes emitted
1,600 visible semantic owners, with1,760 bounded observations. The resulting PDF
is1,275,723 bytes and its decoded font319,801 bytes. Compare the same1,760 rows:

| Grouping | Groups | ARI | Purity | Completeness | Contaminated groups |
|---|---:|---:|---:|---:|---:|
| Raw shape key + character | 1,760 | .0000 | 1.0000 | .1631 | 0 |
| Existing accepted prototype or original | 1,506 | .0937 | .9574 | .2489 | 44 |
| Statistical complete-link | 1,212 | .1481 | .9267 | .3381 | 97 |
| CNN complete-link | 1,516 | .0458 | .9534 | .2244 | 71 |

Both renderers completed all three pages and natively found expires and constant
on every page. At300/600DPI PDFium includes one extra edge pixel from fractional
PDF page geometry; this was not resized away or used to improve a score.

Rejected prototype proposals are excluded from the accepted-product row. Forty
unbounded source observations are not silently included in its denominator.
Contamination is disagreement with known face labels, not automatically a visible
character-identity mistake: some fonts are genuinely indistinguishable at this
resolution. Nonetheless these groups do not satisfy the requested safe reuse.

For a separate diagnostic only, transferring the frozen CNN threshold to
cross-character clustering finds1,493 cohorts instead of8 on test: ARI.0021,
purity.9456, completeness.0156,83 contaminated groups and1,270 singletons.
It is an unqualified threshold transfer, not a newly calibrated cohort model.
A character similarity encoder is not established font-cohort intelligence.

## Review and disposition

Independent code review corrected oracle-field rejection, evaluator joins, frozen
input binding and baseline-to-current-fixture binding. Blinded visual review
found one credible numeral donor repair, but healthy punctuation regressions,
cross-style assignments and no justified blanket consensus repair. See
[reconstruction findings](FONT_01_RECONSTRUCTION.md).

No model weights, corpus, font binaries or large PDFs are committed. CPU PyTorch
is separately hash-pinned for research tests, never a Rust conversion dependency.
Python/Rust inference parity and ONNX integration are **not attempted**, because
no model qualifies. No OCR, Unicode, CID/GID, faithful, ownership or ACR-05
composition behavior changed. Useful benchmark/API/research evidence may merge
without activating failed grouping in the product.

The next precise blocker is reliable target-ink evidence plus multi-character
cohort agreement with abstention. Contrast alone mistakes neighboring fragments
for strong glyph witnesses. The next bounded test should freeze source-owned
versus contaminated observations and require agreement across several distinct
characters before proposing a cohort merge; reuse the same family-disjoint gates.
It should not lower thresholds, expand OCR, or assume another CNN will fix the
low-FPR tail. No further mission is launched by this report.
