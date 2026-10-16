# M1-C-R3 — Instrument validity repair

Baseline after instrument work: same revision as M1-C-R, plus uncommitted repair artifacts.  
Current HEAD before this report: `40ce12f` plus prior pushes.

## What was validated

- `qualification/experiments/m1c_r3/test_translation.py` (v2): 50 random fractional-shift trials,
  independent BICUBIC generation (generator path) vs the estimator's BILINEAR affine path.
  Report: `work/m1c_r3/instrument_translation_v2.json`
  - max displacement error: 0.2015 px
  - mean bias x/y: -0.0081, -0.0270 px
  - SD displacement error: 0.0467 px
  - max post-registration residual MSE: 0.0110 pixels-space
  → alignment displacement accuracy vs analytic truth is demonstrated in a narrow
    synthetic regime.

- Appropriate tolerances, stable SHA-256-derived seeds, deterministic generator.

- H3 topology filter still 0 false merges at ≥0.80 IoU.

## What is NOT validated

- `max_res` is the estimator's own objective; it is circular and must not be cited as
  independent evidence.
- Phase sensitivity and degradation coverage are narrower than the advertised ranges.
- End-to-end, M1-C-R's aligned fusion still loses to no-alignment:
  +0.0 (N=1) to –25.9% (N=8) on boundary error; bootstrap CI [–9.30%, +1.83%] includes
  zero. The M1-C-R evidence does not support integration.

## Independent review

glm-reviewer: CONTINUE — partially validated; residual-MSE gate circular; no promotion.
No production changes, no PDF, no font matching, no fidelity threshold change.

## Disposition

CONTINUE RESEARCH / no integration. The next milestone must (a) replace the residual gate
with independent statistics, (b) embed richer degradation and glyph coverage, and
(c) only re-run the N=1–32 ablation if the aligned arm beats no-alignment.
