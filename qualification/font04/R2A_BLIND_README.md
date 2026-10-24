# FONT-04 R2a sealed blind review

Save all judgments before requesting the separately held key. The author has
not graded this package. Materiality is unknown until independent review.

Each panel shows the complete OCR word with surrounding page context, at 100%
and 400%, in PDFium or Poppler. Source, current and candidate are independently
permuted into A/B/C on each panel. Opaque IDs reveal neither document nor stratum.
For individual substitutions only the target glyph changes in default context;
repeated-word panels compare complete final output crops. Registered fixtures
use their original page/symbol identities, including mixed member 518.

Record a grade for each arm (material defect, minor, indistinguishable, or
improvement), plus notes identifying any affected letter. Save and hash the
completed judgments before unsealing. After decoding, independently adjudicate
whether each candidate substitution is materially worse than current relative
to source, reconciling its two renderer panels into one member judgment. Retain
all panel grades and the adjudication. Count unique substitutions, not panels.
Every mixed substitution is included so the first rule has its full denominator.

The tail definition is source-normalized squared ink error for each of the
three isolated measurements: analytic, PDFium and Poppler. A substituted draw
enters the stratum when candidate error minus current error exceeds 0.02 in
any of those measurements. The same definition and measurement code select
both documents. The financial stratum is an equal-sized random sample without
replacement of its eligible tail; selection is held with the private evidence.
Other strata include at least 300 random accepted members, stratified by
document, at least 150 random rejected members, repeated words, cross-style
probes, and registered regression fixtures. Rejected counterfactuals are
diagnostic proposals, not admitted output.

The following decision rule is copied verbatim from
FONT_04_REVIEW_R2A_STOP.md, condition 4, before sealing:

4. **Decision rule, fixed now, before grading.** The reviewer grades blind. The mixed
   document is a **concrete problem** if either of these holds:
   - more than 5% of all its substitutions are graded materially worse;
   - its materially-worse rate in the >0.02 stratum exceeds financial's in the same stratum
     by more than 10 percentage points.

   If neither holds, the tail is accepted as immaterial. A concrete problem goes to the
   owner, with candidate remedies, as a method change requiring a new freeze.

P2 remains unopened. Adobe Reader remains BLOCKED-ON-OWNER. No product PR or
merge is part of this checkpoint.
