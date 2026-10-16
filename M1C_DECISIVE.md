# M1-C — Decisive multi-observation reconstruction test

Baseline for this decision: `work/m1c_r4/decisive_output.txt` and
`work/m1c_r4/decisive.json`.

## 1. Experimental correction

The previous R3 diagnostic failed to establish whether multi-observation recovery worked.
The decisive test corrects two things:

1. **Sampling model:** observations are integrated directly from source vector-glyph pixel
   space at high resolution with independent sub-pixel phases *before* downsampling. This is
   an explicit proper sampling model rather than repeated raster interpolation.
2. **Registration truth sign:** the correction required was later verified by forward/inverse
   MSE. Oracle alignment is now correct.

No production code or fidelity thresholds were changed.

## 2. Conditions tested

- 3 fonts: DejaVu Sans Bold, P052 Roman, IPAGothic.
- 8 glyphs: `a g e 0 6 8 4 ガ`/`パ` (kana).
- 300 DPI, N = 1, 2, 4, 8.
- Boundary / IoU on 300 DPI raster masks, plus topology checks.
- Regimes:
  - repeated identical observations (negative control)
  - independent noise at identical phase (denoising)
  - independent sub-pixel phases with low noise
  - combined phase variation, blur and noise
  - heavy blur / low information

Arms:

A single observation; B observed medoid; C unaligned median; D oracle-aligned median;
E estimated-alignment median; plus direct low-noise control.

## 3. Aggregated results (corrected)

Aggregate values over 72 observed groups per regime, 18 font/glyph cells x 4 repetitions:

| Regime | N=1 D med | N=8 D med | Mean A med | Mean E med | D-A (N=8) | D-E (N=8) |
|---|---:|---:|---:|---:|---:|---:|
| identical (noise approx. 0.08) | 0.108 | 0.123 | 0.108 | 0.103 | +0.002 | +0.011 |
| independent noise | 0.120 | 0.111 | 0.120 | 0.123 | -0.009 | -0.012 |
| complementary phase, low noise | 0.127 | 0.126 | 0.229 | 0.237 | -0.103 | -0.111 |
| combined phase/blur/noise | 0.137 | 0.122 | 0.349 | 0.358 | -0.227 | -0.236 |
| heavy blur | 0.764 | 0.735 | 0.772 | 0.866 | -0.037 | -0.131 |

Read how each row is constructed:
  - D is the *median of aligned* observations mapped back to the source frame.
  - D-N=1 is simply one observation, corrected by its known phase.
  - E is registered using the estimator, followed by fusion.

Interpretation of the row shift:
  - The complementary-phase and combined rows show a large reduction in absolute
    boundary error from 0.229 to 0.127 and 0.349 to 0.137 respectively,
    but most of that occurs already at N=1, i.e. when a **single observation is
    phase-corrected**. N=8 fusion adds only about 0.001-0.034 px in those regimes.
  - The identical-noise row (0.108 single -> 0.123 N=8 D, 0.103 E) is worse
    than single and provides no evidence that repeated observations improve a
    phase-corrected reconstruction beyond one image.
  - Heavy blur improves only modestly (-0.037 / -0.131) and is bounded.

Therefore:
  **Oracle registration produces a strong, large, and repeatable improvement
  relative to an unregistered low-resolution observation.**
  **Multi-observation fusion itself has not yet demonstrated a substantively
  better outline than aligning/using a single complementary observation.**
  **Estimated registration is worse than doing the correction directly.**

## 4. Example evidence

- Improving (phase-complementary): run dirs such as
  `work/m1c_r4/decisive_output.txt` show `a` 0.229 (A) to 0.126 oracle D at 300 DPI.
  Effective improvement there is due to phase recovery, but almost all benefit is
  present in the single phase-corrected image, not uniquely dependent on N.
- Failing (identical noise): repeated observations remain only 1.0-2.4% better at
  most for boundary in some runs and no better on average.
- Failing registration: E/E-ish alignment remains worse than simple alignment and
  shows up to 43 px boundary-registration errors in the earlier diagnostic, and in this
  experiment E-D is +0.007 to +0.024 px (no improvement).

## 5. Ground-truth and estimated registration errors

- Oracle translation residual is ~0 px by construction.
- Estimated arm residual is **materially worse**: overall an E-D penalty of
  0.007-0.024 boundary px and earlier max disp 43.5 px in R3.
- The estimate does not yet beat oracle or single-observation alignment. Failed leaves:
  1. translation estimator design (currently ordinary MSE phase-correlation) 
     under varying noise and a 300 DPI glyph observation scale.
  2. mathematical fusion objective beyond median.
  3. robust safety against confusable fonts and topology.

## 6. Remaining threats to validity

- Multi-DPI (200, 600) and larger N (16/32) have not been included.
- Only one evaluator mask threshold (300 DPI >= 0.5) was counted; grayscale contour
  comparison was planned but is not in this committed result.
- Median fusion only; joint high-resolution reconstruction is currently a stub
  (`F_unused`) and does not add a new result.
- Observation phases were uniformly spaced (0.23, 0.37), not independent random in
  every generated cell; per-glyph random seeds were created but not applied.
  This overestimates complementary-phase improvement somewhat.
- The 72 groups are paired over font/x glyph x repetition but only 4 glyph families are represented.
- CI does not execute the decisive experiment (runtime too high); the first 3 instrument
  tests do run now.

All artifacts used for this report are derived from a command whose output is preserved in
`work/m1c_r4/decisive_output.txt`; the exact arrays in `work/m1c_r4/decisive.json`
are present locally but not committed due size. A small visual gallery is present under
`qualification/experiments/m1c_r4` scope only for testing, not as a permanent artifact.

## 7. Exact tests, output and CI

- `qualification/.venv/bin/python qualification/experiments/m1c_r4/instrument_test.py` (PASS).
- `qualification/experiments/m1c_r3/{test_translation.py, generator.py, test_diagnostic_modes.py}` (PASS).
- CI job `Instrument correctness tests (M1-C-R3)` passed at HEAD `13bc273`.
- New experiment produced:
  - `work/m1c_r4/decisive_output.txt`
  - `work/m1c_r4/decisive.json` (local evidence)
- No production code, thresholds, PDF assembly, OCR or hash formulas changed.

## 8. Decision

**Instrument gate: PASS on the narrow instrument tests, with noted defects.**
**A limited reconstruction improvement is present only when the registration
truth is available.**
**Multi-observation fusion itself has not yet demonstrated statistically new
information beyond aligned single observations.**
**Production promotion: NO — registration plus safe matching are unsolved
and an estimated reconstruction is worse.**

Per the governing M1-C success gate for justified research:
- **Pursue (continue): registration** because the phase-corrected oracle case is good.
- **Do not integrate** until a validated estimator attains oracle parity.
- **Revisit sampling/fusion** before claiming true multi-image detail recovery.
