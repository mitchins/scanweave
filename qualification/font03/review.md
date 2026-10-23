# Independent review record

## Code review

An independent read-only reviewer identified a genuine flaw in the initial
complete-link implementation: its unordered pair cache stored one directional
registration result. Recomputing validation within-group pairs found 21/247
asymmetries. The source-frame fit could pass one direction while the reverse
failed coverage or stroke width.

The correction requires both directional comparisons and uses the minimum
score. A new asymmetric-pair unit test proves a one-way pass cannot join a group.
The independent reviewer verified this correction and all 14 focused tests;
no other code blocker was identified. All affected groups, fields, source gates,
render arrays and pristine evaluations were regenerated. Old artifacts remain
under `local/directional-before-review/`, never silently replaced as equivalent.

The reviewer also confirmed that pristine pixels are read after source decisions
freeze, severity labels define evaluation strata, and the real pre-union hook
is described as a fixed-plan construction intervention rather than a deployable
Rust canonicalizer.

## Blinded visual review — directional iteration

All 49 final-source-accepted cases were reviewed in PDFium and Poppler using
source/pristine/U/V panels. U/V were randomized per case. The reviewer reported
panel defects before attribution; the implementation agent then mapped keys.
An attempted reviewer key read was blocked by automatic approval review; root
mapping allowed the task to continue without bypassing the blind boundary.

Four clear material defects belonged to the **current baseline**:

- 43 U: strongly narrowed `e`.
- 35 U: narrowed counter and distorted crossbar.
- 40 V / 41 U: noticeably thinned and narrowed `1`.

Canonical panels 3 V, 5 V, 17 V and 30 U show actual counter-rounding and weight
changes, but no clear material loss was established in these views. The reviewer
classified them as minor enlarged-view differences or uncertain materiality,
not evidence that every canonical result improves fidelity. All nine metric
flags remain disclosed. This finite visual result did not override the grouping
bug or establish promotion readiness.

## Real construction examples

The four completed-PDF source/baseline/candidate comparisons were reviewed in both
engines. No obvious material regression was found. Targets 7, 8 and 36 show a
small consistency gain; target 9 is nearly indistinguishable. The reviewer did
not consider this sufficient for a general product-quality claim. Font growth
and fixed-plan limitations independently prevent production promotion.

The opening of `constant` and the mixed-style control were personally reinspected
using existing fixed-coordinate comparisons. No missing character identity was
inferred from expected prose; inherited typography defects were kept separate.

## Symmetric regeneration audit

The independent reviewer recomputed every within-group pair: **0 failures across
273 train, 232 validation and 359 test pairs**, with no cross-character merges.
Plans match all 65/111 regenerated targets; all 24/28 accepted decisions have
at least three other witnesses. Source hashes, render freezes and all 110 then-
recorded manifest files match. The evaluated summary describes the broader
55/90 initial source-gate set; final oracle reporting must filter by the separate
final decisions. `results.json` does this explicitly (2/24 and 5/28 flags).

## Fresh blinded review — symmetric iteration

All 52 final accepted cases were reviewed afresh in both engines, with fresh
case ordering and per-case U/V mapping. Root unblinded only after panel judgments.
All five material panel concerns (43 U, 38 V, 39 U, 49 U, 34 V) map to the current
baseline. Candidate cases 7 V, 5 V and 15 V have minor counter/weight differences.
Case 7's upper counter remains open; the gray lower-counter band is darker in
Poppler. No disappeared stroke, counter closure or identity failure was found.

Final independent visual judgment: **no confirmed material canonical regression
in this finite 52-case healthy cohort**. Limited visual pass with explicit
counter-rounding/weight caveats; not a pristine-accuracy win in every example,
not blanket production qualification and not damaged-repair approval.

## Post-decision contour diagnostics

The independent reviewer verified half-coverage boundary extraction, symmetric
native-pixel distances and the linear `300/source-DPI` aggregation. No empty
contours occurred in either arm. Saved values match the report. The optional
source-decision hash check was added before oracle access, alongside the existing
native-array binding check. No acceptance thresholds or decisions changed.
