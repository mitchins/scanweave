# FONT-02 independent review record

Date: 2026-10-23. Reviewers are separate read-only agents in this session, not
CodeRabbit. These conclusions do not constitute approval of a product matcher.

## Source-health review — `/root/raster_evidence_review`

The reviewer inspected `42-e-source-blind.png` before seeing substitution outcomes.
It adjudicated 33 healthy, seven damaged and two uncertain source impressions.
The frozen list and image SHA are in `source-health.json`. Product repair flags
were subsequently kept as a separate stratum: indices 26/27 were not changed in
the final ordinary-reuse shadow.

## Blinded real-page substitution review — same reviewer

Both PDFium and Poppler sheets included all eight candidate words, repeated
`expires` context, and full pages at identical physical coordinates.

- Rotation arm: **C1 = candidate; C2 = current product**. No material new counter,
  identity, alignment or halo defect found. C2 weakly preferred for consistency.
- No-rotation arm: **Q = current product; R = candidate**. No material new defect
  found; mostly indistinguishable at normal size. Initial weak R preference was
  subjective, not a measured quality benefit.
- The reviewer did not read the blind mapping before returning its judgments.
- An initial claim of improvement in unchanged `Term` index 4 was explicitly
  **withdrawn**. A parse/unparse-only control has zero changed pixels at both
  300/600 DPI in both engines. That preference cannot establish an improvement.
- The final five-change shadow is the no-rotation arm with the two legacy repair
  occurrences left unchanged. The five changed word regions were already covered
  by the seven-change review. It was not claimed as a separate blinded whole-page
  review round.

## Held-out failure review — same reviewer, source/reference labels disclosed

Inspected `hard-negatives/review/validation-0.png`, `test-0.png`, `test-1.png`.
Both test examples exhibit actual geometry failures: compact dots become upright
slivers in both engines. Existing baseline dots are already too wide; this does
not make the new distortion safe. Validation is mixed (closer width but changed
contour/weight), not a clean preservation pass. **The source-accepted substitution
policy fails its safety gate.** Face-label disagreements were not used as failure
criteria.

## Code/evidence review — `/root/independent_review`

Verified the frozen protocol thresholds, all listed local artifact hashes,
source-only measurement separation, and exact test-result reproduction (562 pairs,
48 accepted, 38 relatively safe, eight ambiguous, two material flags).
Confirmed visible dot-to-sliver failures support rejection.

Two evidence clarifications were requested and addressed:

1. Topology in this experiment's gate is **candidate versus current baseline**,
   recorded in source-decision files. Pristine-relative topology was not measured.
   The versioned protocol now explicitly clarifies this limitation without changing
   the original frozen limits, decisions or local pre-oracle protocol artifact.
2. Persist the blind mappings, outcomes and withdrawn `Term` claim in this record.

No general grouping, consensus fitting or damaged repair was approved. Product
matching remains unchanged. Phase 1's separate construction-time pruning review
and qualified merge are documented in `required-glyph-review.md` and PR #22.
