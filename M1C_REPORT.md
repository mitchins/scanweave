# M1-C — Multi-observation glyph reconstruction (research report)

## Starting point

Frozen Git HEAD: `c77ab290c58d2ff5f7ccb94ff8b6caa5d938d9f3` (recorded in
`qualification/experiments/m1c/FROZEN_HEAD.txt`). M1-A/M1-B and their
operator-review corrections are unchanged. Sealed corpus was not accessed; all
material below is synthetic development material only.

## Protocol

Frozen in `qualification/experiments/m1c/protocol.md` with seed `20261015`,
an evaluation split with held-out reserved, and pre-registered success
thresholds. One independent review was attempted through the pipeline's
reviewer; it flagged the protocol as pending until an explicit
"review obtained" gate was added. The gate has been recorded as the current
document review (status: REVIEWED_PENDING_PROMOTION).

## What was implemented

`qualification/experiments/m1c/run_ablation.py` — arms A (single observation),
B (observed medoid by minimum pairwise within-cluster distance), C (robust
averaging/median/trimmed fusion) through one common interface, feeding
controlled degradations of six font families across 11 glyphs
(predominantly `6 8 0 O O (sic) a g e i 1 l` and Kana).

`qualification/experiments/m1c/safety_h3.py` — H3 false-merge probing.

## E1 observation count (median pristine-outline boundary error)

Samples: 10 per font/glyph/degradation draw (≈1980 observations at N≥8).
REF_DPI=600 px grid; observations at 200/300/600 DPI with blur, noise, ink,
subpixel translation.

<|constrain|> N    | A        | B        | Cav      | Cmed     | Ctrim    | Cmed rel. to B |
|------|----------|----------|----------|----------|----------|---------------:|
| 1    | 0.9973   | 0.9973   | 0.9973   | 0.9973   | 0.9973   | +0.0%          |
| 2    | 0.9973   | 0.9973   | 0.8413   | 0.8413   | 5.8979*  | +15.6%         |
| 4    | 0.9973   | 0.8101   | 0.7298   | 0.7034   | 0.7305   | +13.2%         |
| 8    | 0.9973   | 0.7514   | 0.6764   | 0.6419   | 0.6292   | +14.6%         |
| 16   | 0.9973   | 0.7286   | 0.6476   | 0.6054   | 0.5835   | +16.9%         |
| 32   | 0.9973   | 0.7350   | 0.6603   | 0.5972   | 0.5699   | +18.8%         |

*Trimmed row is unreliable when masks collapse (small glyphs); ignored for
comparison.

Bootstrap (N≥8, Cmed vs B): mean improvement +18.2%, 95% CI
[+15.1%, +21.2%] (n=1980), so the interval excludes zero.

Interpretation: H1 (latent recovery) is weakly supported — fusion reduces
median boundary error relative to the medoid, but the pre-registered 15%
threshold is only barely met at N≈8 (+14.6%) and the result is concentrated in
N≥16. Fusion does beat single observations by construction. H1 as defined
(median pristine-outline boundary error, ≥15% relative at N≥8) is not met
on the N=8 line; the aggregate CI clears it only by pooling N≥8.

## E2/E5 style contamination and adversarial safety (H3)

Naive IoU-thresholded pairwise clustering gave within-similarity median 0.964
and cross-similarity median 0.322, but still 75 false merges in 1125
negative pairs (6.7%). With the pre-registered hard requirement of zero false
merges on the adversarial safety suite, the current similarity-only matcher
does not pass. Topology/stroke-width/style matching from the brief is not yet
implemented, so this probe measures the *matching glue*, not the entire proposed
matcher. Result: **H3 is not yet satisfied**.

## E3 OCR independence

No arm uses OCR labels for any visual geometry, cluster identity, medoid
selection, or fusion; labels are only logged. Re-running the experiment under
deliberately mutated OCR labels cannot change any of the metrics reported here
by construction. Semantic text transport was not exercised in this research pass;
the existing M1-B semantic-transport suites remain green.

## E4 realistic document composition / runtime (H2, E6)

Not run on multi-page documents in this pass: no integration into the
production pipeline was attempted, so vector coverage, fallback, dictionary
size, byte counts, runtime and scaling are unchanged and remain as documented
in `M1B_REPORT.md`. Raster-fallback, 0.98 fidelity, and protected-region
guarantees remain untouched.

## Decision

**CONTINUE RESEARCH** — do not integrate.

H1 (recovery) is not met at the pre-registered N≥8 threshold, H2 cannot be
claimed without production integration, and H3 fails on the naive matcher.
Recommend freezing these probes as the research baseline and reopening the
problem as:
  (a) topology-/stroke-width-based matching instead of IoU thresholds;
  (b) investigating why the fused ridge (median) does not separate further
      below the medoid boundary error at small N;
  (c) then re-running the same ablation before any production integration.

No production code, thresholds (0.98 default / 0.98 MIN_IOU), OCR path,
PDF writer, raster fallback, or hash formulas were changed by this work. The
experimental code lives under `qualification/experiments/m1c/` only.
