# FONT-04 — Independent review protocol

How each FONT-04 checkpoint is examined before the next direction is set. The
reviewer is adversarial toward favourable metrics and toward premature closure alike.

## 1. Reproduce before reading conclusions

- Rebuild from the recorded SHA. Regenerate at least one complete experimental-mode
  financial PDF and confirm its hash, along with the default-mode byte identity.
- Recompute headline numbers from the ledgers, not the markdown: designs, draws per
  design, retired/added programs, font and PDF bytes.
- Count designs by following CID → GID mapping and graphics state, not raw CIDs.

## 2. Challenge favourable metrics

For every improvement claimed, check:

- **Population drift:** are the arms compared on the same targets? Look for filtered
  subsets, accepted-only populations, and denominators that change between tables.
- **Placement leakage:** is any placement, frame or crop derived from pristine data,
  or from an evaluator-only field?
- **Metric-frame coupling:** does an arm win only because its placement was fitted in
  the frame the metric uses? Require the placement-independent shape metric to agree
  in direction.
- **Tail versus mean:** p95, the worst 10 per class, and per-DPI/damage strata, not only
  the mean.
- **Gaming of economy:** a draws-per-design gain must come with no rise in material
  defects and no fall in pristine quality. Check whether the gains are concentrated in
  rare classes or in punctuation.
- **Byte attribution:** compare against a save-only serialization control. Separate
  font bytes from content and other bytes. Retired programs must be truly absent from
  the font.
- **Renderer split:** PDFium and Poppler are judged separately. A gain in one with a
  loss in the other is reported as mixed.

## 3. Hunt for unsafe substitutions

Construct the review set independently of Codex's selection:

1. **The worst 10 accepted members per frequent class**, under each of the following:
   error relative to source, change in area, change in elongation, and counter
   difference.
2. **A stratified random sample** of accepted members: at least 3 per frequent class,
   and at least 100 in total for B2.
3. **A random sample of rejected members**: at least 50 for B1, at least 150 for B2. This
   measures over-rejection and is mandatory.
4. **The complete curated negative set.**
5. **Repeated words across distant pages** (for example "expires", amounts, dates) at
   reading size and 400%.
6. **Cross-style probes:** every star/group with members on pages or lines of visibly
   different weight or style.

Blinding:
- Panels show the source plus two randomized candidates (U/V: current versus
  experimental), in both renderers at fixed physical coordinates.
- The reviewer records judgments before the key is revealed.
- The mapping is held by a separate process and revealed only after all judgments are
  saved.

Each panel is classified as one of:
- material defect (identity, closed/opened counter, missing or added stroke, wrong
  weight or slant class, dot/sliver),
- minor (counter rounding, slight weight change),
- indistinguishable,
- improvement.

The result is tabulated by arm, class and sample type.

## 4. Decision matrix

| Observation | Interpretation | Next direction |
|---|---|---|
| Accepted sample: 0 material defects; rejected sample mostly fine; economy small | Measurement failure: gates over-reject | Recalibrate the joint criterion; inspect unique rejections per check |
| Accepted sample has material defects concentrated in one check's blind spot | Missing veto | Add one orthogonal veto targeted at that defect; never loosen the others |
| Rejected sample genuinely different; few designs retired | Design multiplicity is real for this document | Check sizes/weights; consider placement API; if the plan's §6 conditions hold, falsified |
| Economy good, but bytes flat | Serialization cost (point count) | Point budget or CFF follow-up; reuse not falsified |
| One placement mechanism explains the Phase-A gain | Fix individual reconstruction | Small product PR first; re-trace canonicals with it |
| Star groups leak styles | Grouping failure | Switch to set cover or add a style veto; re-test the negative set |
| Defects appear only at one DPI or size | Stratum-specific | Abstain in that stratum; continue elsewhere |

## 5. Output of each review

A short `FONT_04_REVIEW_<checkpoint>.md` containing:
- reproduction status;
- the metrics challenged and their outcome;
- the panel classification table;
- failure classification (algorithm, measurement, data, falsified);
- the **specific next experiment**, with any bounds changed and why.

Positive and negative examples are both kept.

Production qualification (plan §8) uses the same protocol on the fresh P2 held-out set
and all P3/P4 pages, with the operating point frozen beforehand.
