# M1-C-R — Corrected methodology probe

HEAD/CI: `b882fc7` (CI green after OTS tag fix) → latest `72b7477+`.

## Method changes
1. Real subpixel alignment: phase-correlation integer peak plus local continuous refinement (`phase_shift`), applied as `shift_arr`.
2. No-alignment control retained.
3. Boundary error measured on the same REF_DPI=600 grid against rasterized pristine outlines (vector-ground contour extraction is still follow-up).
4. Independent groups: 10 groups per font/glyph with deterministic seeds; group-median Cmed-vs-B improvement bootstrapped over groups.

## E1 observation count (updated)

| N  | A=... | B       | Cmed (aligned) | Cmed NoAlign | aligned improvement vs B |
|----|-------|---------|----------------|--------------|-------------------------|
| 4  | 1.054 | 0.860   | 1.000          | 0.737        | -16.2%                  |
| 8  | 1.054 | 0.737   | 0.928          | 0.653        | -25.9%                  |
| 16 | 1.054 | 0.735   | 0.892          | 0.615        | -21.3%                  |
| 32 | 1.054 | 0.749   | 0.858          | 0.607        | -14.5%                  |

Aggregate N≥4 Cmed-vs-B with alignment: -3.99% and bootstrap CI
[-9.30%, +1.83%] — zero is inside the interval. The no-alignment arm
remains beneficial (as in M1-C: +14–20%), so the alignment estimator itself
is currently worse than doing nothing.

## H3 safety
Topological checks (component count + aspect ratio + IoU-threshold ≥0.80)
maintain 0 false merges on the preceding PoC; however, the corrected
publication-grade matcher (stroke width) is not yet implemented.

## Decision
CONTINUE RESEARCH. Real subpixel alignment does not yet help; investigate
phase-centering/registration errors before any promotion. Do not integrate.

Reviewer: CONTINUE (independent substitute review).
