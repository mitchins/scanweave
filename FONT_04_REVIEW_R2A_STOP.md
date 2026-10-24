# FONT-04 — Reviewer decision on the R2a stop (member 518, mixed document)

Reviewed: research `d2d8f1e` (stop receipt), product `62c833d` (reporting only).

## Verdict

**The stop was correct, and the defect is real.**
- The `w` in "with" (mixed page 2, member 518) renders visibly smaller in both PDFium and
  Poppler.
- The default glyph follows the source closely: analytic error 0.019. The substitution does
  not: 0.139, with area bias −13.7 points.

**It is not yet established that this is a method failure.** It is the single worst case of
a tail, and it was found unblinded. Whether that tail is *material* is exactly what the sealed
blind review is for. R2a therefore **resumes as evidence gathering only**, with the method
frozen. No method change is authorised.

## What the mixed document shows (my reanalysis of Codex's records)

There are 326 substituted draws.

| Metric (isolated) | Worse than default by >0.02 | Better by >0.02 | Mean Δ | p95 Δ | Max Δ |
|---|---:|---:|---:|---:|---:|
| Analytic | 52 | 173 | −0.029 | +0.046 | +0.120 |
| PDFium | 41 | 161 | −0.030 | +0.047 | +0.098 |
| Poppler | 37 | 170 | −0.032 | +0.032 | +0.078 |
| PDFium, in context | 55 | 152 | −0.023 | +0.055 | +0.129 |

- **On average, substitutions on this document improve fidelity.** 233 of 326 have lower
  analytic error than default.
- **The worse-than-default tail is heavier than on the financial document.** Financial B2′
  rescore (PDFium crop): 44 of 1,750 worse by >0.02, which is 2.5%. Mixed: 12–17%,
  depending on metric. The metrics are not identical, so this is indicative, not a measured
  ratio.
- **Member 518 is the largest outlier.** Next are 644 `t` (+0.086), 1093 `t` (+0.070) and
  1242 `n` (+0.068). Most of the tail is thinner or lighter strokes, not changes of form.
- **Member 518's planner decision:**
  - error 0.09066 against its own floor 0.09083, the most permissive floor in the document;
  - scale pinned at the 1.02 upper bound.

  Bound-pinned scales are common on both documents (mixed 100/326, financial 396/1,750), and
  financial passed blind review. Bound-pinning alone is therefore not diagnostic.
- **Other corpus documents:**
  - **forms**: the economy guard correctly emitted default. The attempt was net −8 outlines,
    and the font would have grown 41,147 → 46,879 B.
  - **receipts** and **historical**: no surviving groups.
  - Text, qpdf and OTS pass on all five documents.

## Conditions for resuming R2a

1. **Method frozen.**
   - No threshold, floor, scale-bound, guard or membership change.
   - Member 518 is not to be "fixed".
2. **Complete the remaining R2a items** listed under `incomplete_due_to_stop` in
   `checkpoint-R2a.json`:
   - financial golden reruns;
   - profiling and byte-identical optimization;
   - financial all-draw fidelity;
   - save-only controls;
   - paired runtime and RSS;
   - repeats.
3. **Sealed blind package.** In addition to the R2a strata, include:
   - **every** mixed substituted draw that is worse than default by >0.02 on any isolated
     metric;
   - member 518 as a registered fixture;
   - an equal number of **financial** substitutions that are worse by >0.02 on the same
     metric definition, so both documents are graded on one scale.

   Panels show the full word in context, with source, current and candidate in randomised
   order.
4. **Decision rule, fixed now, before grading.** The reviewer grades blind. The mixed
   document is a **concrete problem** if either of these holds:
   - more than 5% of all its substitutions are graded materially worse;
   - its materially-worse rate in the >0.02 stratum exceeds financial's in the same stratum
     by more than 10 percentage points.

   If neither holds, the tail is accepted as immaterial. A concrete problem goes to the
   owner, with candidate remedies, as a method change requiring a new freeze.
