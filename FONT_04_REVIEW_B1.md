# FONT-04 — Independent review of Checkpoints A and B1

Reviewed: `research/font04-document-fonts` at `2e6402f` (results `cc6e10d`).
Protocol: `FONT_04_REVIEW_PROTOCOL.md`. Reviewer scripts, blind judgments and the opened key are in
`qualification/font04/review_b1/` (run from the repository root against the local B1 artifacts).

## Verdict

**B1 is a failed measurement of a promising result, not a mixed result.** The
"PDFium worse / Poppler better" pattern comes from a **systematic half-canvas-pixel
placement bug** in the research planner's inverse mapping, together with Poppler's
glyph-position snapping. Once the bug's constant offset is removed, the shared
canonicals fit the source **better** than the current per-occurrence outlines. A
blinded visual review of the accepted substitutions found **no material defect** and
one minor ink-deletion case that points to a missing veto.

Classification: **measurement failure (placement inverse) plus one missing veto.**
Not falsified. Fix, re-run B1 once, then proceed to B2 under the conditions in §6.

## 1. Reproduction

- Re-scoring all 291 `e` from the shipped PDFs reproduces Codex's native numbers exactly:
  - PDFium: 0.06991 → 0.09275;
  - Poppler: 0.15533 → 0.13518.
- Program accounting (29 added / 36 retired / net −7) and the 175 B PDF saving were not
  disputed and were not re-derived beyond the scorecard.

## 2. The renderers disagree more than the arms do

A control probe used 30 production glyphs × 4 subpixel offsets on a white page, against a
4× supersampled analytic reference.

| Comparison (identical outlines) | Union-normalized squared error |
|---|---:|
| PDFium vs analytic | 0.026 |
| Poppler vs analytic | 0.049 |
| **PDFium vs Poppler** | **0.092** |

- Poppler compresses edge coverage: analytic 0.6–0.8 renders at 0.57.
- PDFium tracks subpixel origins with a constant offset of about +0.22 px vertically.
- Poppler's error drifts −0.42 → −0.67 px vertically, and −0.12 → −0.46 px horizontally,
  as the requested offset goes 0 → 0.75 px. **Poppler quantizes glyph origins.**

**Consequence.** Native single-renderer error cannot rank arms whose differences are
below about 0.09. Subpixel placement fitting is honoured by PDFium and partly discarded by
Poppler.

## 3. A renderer-neutral reference (PDFium at 1200 DPI, box-averaged to 300) agrees with PDFium, not Poppler

| Accepted members (124) | PDFium | Poppler | Analytic |
|---|---:|---:|---:|
| Default → experimental error | 0.060 → 0.113 | 0.157 → 0.110 | 0.060 → 0.103 |
| Members worse / better | 110 / 14 | 20 / 104 | 107 / 17 |

The sign of change agrees between analytic and PDFium for 86% of members, and between
analytic and Poppler for only 28%. So the shipped experimental PDF really does fit the
source worse. The question is why.

## 4. Root cause: half-pixel edge/centre mismatch in the planner inverse

Analytic reference, accepted members:

| | Default | Experimental |
|---|---:|---:|
| Raw error | 0.060 | 0.103 |
| Error after best translation (±1.5 px, 0.25 px steps; both arms) | 0.034 | **0.022** |
| Centroid offset vs source (dy, dx) | (−0.11, +0.04) ± 0.2 | **(+0.41, +0.41) ± 0.19** |
| Ink mass ratio | 1.002 | 1.000 |

**The bug.** `planner.source_frame` samples the 64-pixel canvas with
`ndimage.map_coordinates`, where canvas index *i* is a pixel **centre**. The bbox inverse
in `planner.py` (the assignment loop: `left=32+s*(x-32)+dx`, `top=48+s*(y-48)+dy`) and
in `causal.py` (the `bb=[f['cx']+(x-32)/f['scale'], …]` lines for the `line-*` arms) treats
the crop origin `x, y` as a pixel **edge**.

- The predicted displacement is `+0.5 / frame.scale = 0.5·xheight/32`. The prediction is
  0.404 px; the observed displacement is 0.412 (dy) and 0.409 (dx); the residual is
  0.008 ± 0.19 px.
- Poppler's own −0.4 to −0.6 px snapping cancels the bug, which is the entire reason
  Poppler "improved".

**Scope.** Every line-frame arm in Phase A (A4, F-self, F-medoid, the floor controls) and
B1 emits glyphs with this offset. These Phase A conclusions are therefore **confounded and
must be re-measured**:
- "F-self and F-medoid are not interchangeable";
- "placement does not transfer to Poppler";
- the frame-mechanism shares.

The native-crop arms (A0–A3) are unaffected.

## 5. Blinded visual review

**Method.** I composed my own panels: source | U | V at 400%, U/V randomized with
seed 731, and the key sealed until all judgments were saved. Coverage: 84 of 92 accepted
PDFium members, plus the repeated words.

**Result.** There were **0 material defects** (identity, counter, stroke, weight-class).
U and V `e` shapes are visually equivalent at 400%. One uncertain case:

- **glyph-277:** a small stray mark above `h e` is present in the source and the current
  output, but **absent in the candidate**. The default outline had absorbed the speck into
  the `e` program, and substituting the canonical deletes owned ink. This is minor here.
  It is the failure class that matters on financial documents (decimal points and marks
  touching digits). **Missing veto.**

**Defects in Codex's review sheets:**
- **All 100 rejected-sample panels are unblinded.** The attempted substitution is drawn
  isolated on white, while the current output is drawn in page context. The
  over-rejection measurement therefore cannot be made from these sheets.
- **Repeated-word panels mostly contain no lowercase `e`** (TOWN, IPSWICH, John,
  DEPARTMENT), so U and V are identical. They are useful as null controls only. The
  repeated-word sample must be drawn from words containing the target class.

## 6. Direction: B1′, then B2

Codex should make these changes, keeping everything else (plan, vetoes, operating point
1.0, star grouping) fixed:

1. **Fix the inverse.** Map crop origins as `x − 0.5`, `y − 0.5` in canvas centre
   convention, in both `planner.py` and `causal.py`. Add a round-trip test: frame → bbox →
   emitted PDF → analytic render, with |centroid offset| < 0.05 px on synthetic glyphs.
2. **Primary fidelity metric = the analytic reference** (supersampled PDFium, or direct
   outline coverage). Report both native renderers as secondary screens, each alongside
   the measured renderer-vs-analytic floor. Never rank arms by a native difference smaller
   than that floor.
3. **New hard veto, "unexplained owned ink".** Before substitution, any source-owned
   connected ink outside the canonical's rendered footprint plus a halo, above a small area
   or contrast, makes the member an exception (or the residual is retained as raster; the
   choice is Codex's, with a test). glyph-277 is the regression case.
4. **Fix the review sheets.**
   - Rejected panels show the attempted substitution composited in page context, exactly
     like current output.
   - Repeated words are sampled from words that contain `e`.
   - Re-issue sealed sheets.
5. **Re-run Phase A** (the line-frame arms) and **B1** with the fix. Report the frontier
   again: with correct placement the error criterion may admit more members. The 88
   insufficient-noise-support rejections are the next economy lever. Report how many
   have fewer than k witnesses versus failing calibration.

**B2 authorization (pre-committed, so no extra stop is needed).** Codex may proceed
directly from B1′ to B2 if B1′ shows all of the following:
- (a) analytic mean **and** p95 source error of the experimental PDF ≤ default, on all 291
  `e`;
- (b) net programs retired > 0;
- (c) the corrected review sheets are issued sealed, and the B1′ checkpoint records the
  reviewer-pending state.

B2 then runs on all 55 frequent classes, and **stops at Checkpoint B2** for independent
review. If (a) fails, stop at B1′ for review.

## 7. What this review does not establish

- Pristine accuracy on the real document. P3 has no pristine reference; the analytic
  source fit and visual review are the evidence.
- Over-rejection. It cannot be measured until rejected panels are re-issued blind.
- Font-economy scale. B1 is one class; B2 measures it.

## 8. B1′ authorization (accepted by the project owner, with three refinements)

The review is accepted. B1′ runs as specified in §6, with the conditional B2 authorization
unchanged, plus the refinements below. Where they add to §6, they govern.

**R1. Isolate the coordinate fix from any change in acceptance.** Report these arms on the
same 291 `e`, each as a complete financial PDF:

| Arm | Placement | Membership / vetoes |
|---|---|---|
| B1 (as shipped) | buggy inverse | B1 acceptance |
| B1′-P0 | fixed inverse | **B1's accepted set, frozen** (pure placement effect) |
| B1′-P | fixed inverse | B1 vetoes re-applied, no new veto |
| B1′-PV | fixed inverse | B1 vetoes + ownership-aware unexplained-ink veto |

Test the pixel-centre convention against **independently established physical
coordinates**, not against the planner's own frame. Use synthetic outlines placed at known
PDF coordinates, at 200/300/600 DPI, at least four x-heights, and subpixel offsets
{0, 0.25, 0.5, 0.75} px on both axes. Run frame → bbox → emitted PDF → analytic render, and
require |centroid offset| < 0.05 px in every cell. Also show that the old inverse fails the
same test by the predicted 0.5/scale.

**R2. The unexplained-ink veto is ownership-aware.**
- Ink the current default output does not reproduce is never newly preserved. Unrelated
  scanner dirt is not promoted into glyphs.
- Significant source ink that the current output reproduces, and that this draw owns, must
  not vanish silently. Either keep the member as an exception or retain the residual; the
  choice is Codex's, with tests.
- Ambiguous components (detached specks inside the ownership halo) are logged in a
  component ledger: member, area, contrast, distance, decision. Every firing appears in the
  blinded sheets.
- glyph-277 is a mandatory regression test: its mark must survive.

**R3. Report fidelity separately** for all 291 `e` **and** for the actually substituted
subset. For each arm, give mean, p95 and the worst 10 regressions with member IDs, under:
- PDFium;
- Poppler;
- the supersampled analytic reference;
- a direct-outline coverage reference.

Report each renderer-vs-reference floor alongside.

**Also:**
- The rejected-sample review stays **unresolved** until the corrected, genuinely blinded
  sheets have been assessed. B2 condition (c) requires only that they are issued.
- Re-run the affected Phase A line-frame arms.
- Default ClearScan stays byte-identical. Nothing is promoted on pre-fix measurements.
- Stage only explicit paths. Untracked ACR-02/03/04 and other local artifacts must never be
  committed.
- If B2 runs, it **stops at Checkpoint B2** for independent review.

**Objective.** The aim is substantially higher document-wide outline reuse, with typography
at least as good as today's output. Passing a gate or saving a few bytes is not the
objective.
