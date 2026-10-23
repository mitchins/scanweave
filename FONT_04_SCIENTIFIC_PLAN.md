# FONT-04 — Scientific plan: reusable reconstructed document fonts

**Status:** Plan. No implementation or result is claimed.
**Product baseline:** remote `main` `c10e3dff93ca12ac410c0f6626a4ef74ce34e0c1`.
**Evidence base:** FONT-01 (#19–#21), FONT-02 (#22, #23), FONT-03 draft #24 (`7ebc09e`).

## 0. The question

Can ScanWeave build a document-specific font in which **few, genuinely necessary
outlines are reused by many compatible occurrences**, with typography that is at
least as good as today's, and with smaller complete PDFs?

Success is measured on the real 13-page financial document and confirmed on synthetic
pristine references. Merging by face identity, consensus averaging, model
architecture and particular thresholds are possible means. None of them is the goal.

Current real-document position (Phase 1 product, `790a2f9`):

| Quantity | Value |
|---|---:|
| Visible glyph draws | 3,717 |
| Distinct visibly used designs | 2,236 |
| Draws per design | 1.66 |
| Character classes | 173; the 55 classes with ≥10 draws cover 3,524 draws (95%) |
| Encoded font bytes | 727,259 (≈325 B per design) |
| Complete PDF | 2,849,237 B |
| Runtime / peak RSS | 497 s / 1.47 GB |

For scale only, not as a target: a 13-page document in a few faces needs a few
designs per frequent class. Even 600 designs would be a 3.7× reduction and save
roughly 500 KB of font, about 18% of the PDF. The experiment must find out how
much of that space is safely reachable.

---

## 1. Independent reassessment of FONT-03

### 1.1 Directly demonstrated

| # | Result | Source |
|---|---|---|
| D1 | On all held-out synthetic targets (no acceptance filter), fresh line-frame tracing roughly halves pristine error compared with current output. Test: A 0.183 → E 0.099 → F 0.100. Validation: 0.207 → 0.092 → 0.092. | FONT-03 corrected tables |
| D2 | A **single fresh witness (F)** matches multi-observation fitting (E) to within 1%. Renderer directions are mixed. | Matched control |
| D3 | In the 52 accepted cases, blinded review found **0 material canonical defects and 5 material baseline defects**. | `review.md` |
| D4 | The final source gates accept 24/65 (validation) and 28/111 (test) targets. | Corrected tables |
| D5 | The real construction control remapped 4 occurrences on one page to 3 new designs. The old GIDs 123 and 73 stay referenced elsewhere. Result: +3 slots, +745 B. | H4 scorecard |
| D6 | Structural vetoes catch both FONT-02 dot-to-sliver cases and the `8` counter changes. | H1 |
| D7 | Damage repair produced real recoveries but also identity failures (`1` 0.021 → 0.426). | Repair probe |

### 1.2 Verified in code for this plan (not stated in the FONT-03 report)

- **The contour fitter is not the difference.** The F/E arms call the production
  `trace::trace_shape_clearscan` (`qualification/font03/experiments/canonical_tracer.rs`).
  Any explanation of D1 that credits "a better fitter" is wrong.
- The **inputs** to that fitter differ between production (A) and F:
  1. **Preservation floor.** Production passes `preserved_source = (source, policy.min_ink_iou)`
     (`convert.rs` ≈ line 965) for every outline that is not reused. A candidate curve is
     rejected unless its *binary* ink IoU against the source's own thresholded mask stays
     at or above min(0.98, the old trace's IoU), on top of a 0.90 trace gate. F passes `None`.
     Production is therefore constrained to stay close to the binarized scan, noise
     included.
  2. **Coverage normalization.** Production estimates paper and ink from crop
     percentiles (p90 / p5) of the observation's own crop, which can include neighbouring
     ink. Prototypes are additionally Otsu-thresholded (`visual_dict::refine_observed_mask`).
     F uses a local paper/ink estimate plus an ownership-assigned halo.
  3. **Frame and resolution.** F traces a resampled 64-pixel line frame (x-height 32,
     baseline 48). Production traces the native crop. Grayscale fitting is skipped for
     crops over 16,384 samples, which falls back to the binary trace and can affect large
     glyphs at 600 DPI.
  4. **Placement.** E/F placement is fitted to the target's source (bounded
     translation/scale). A uses production placement. FONT-03 reports A's p95 absolute
     ink-area bias at 32% versus 6.5%, which is consistent with systematic size or
     placement error.
  5. **Witness.** F uses a non-target medoid. A uses the observation itself or a legacy
     prototype.

### 1.3 Interpretations (plausible, not demonstrated)

- **I1. The gain comes from the pipeline, not from sharing.** F beats the target's
  *own* outline while being traced from a *different* observation. So witness choice
  cannot be the main factor. Placement (4) and the preservation floor (1) are the
  leading suspects, because both produce systematic area/shape bias. **No control has
  separated them yet.**
- **I2. Multi-observation ≈ single because the population is healthy.** In D0/D1,
  per-witness noise is small compared with the systematic errors that both arms share
  (placement, normalization, fitter smoothing). Averaging can only remove independent
  noise. Prediction: any multi-witness advantage shows up only at D2/D3, 200 DPI, or
  small sizes. Either way, economy does not need consensus.
- **I3. The gates stack conservatism.** About eight checks, each at the 95th percentile
  of 43–79 training comparisons, would pass about 0.95⁸ ≈ 66% of genuine members if
  independent (less loss if correlated). With 43 samples, a q95 is the 2nd–3rd largest
  value, so each limit is itself noisy. Add complete-link grouping (31 healthy Town `e`
  observations split into 6 groups: 13/6/2/7/1/2) and ≥3-witness support. Low acceptance
  is the expected result. **However, nobody reviewed the rejected candidates.** "The
  gates reject good candidates" is so far *my* inference. FONT-04 must measure it.
- **I4. The real-PDF growth was guaranteed by the test design.** A design can only be
  retired when *all* of its users are remapped. A 4-occurrence, single-page, fixed-plan
  intervention cannot retire anything. It says nothing about document-wide economy.

### 1.4 What FONT-01 to FONT-03 do *not* support

No experiment has yet:
- remapped a whole character class across the document,
- counted designs retired,
- used the improved pipeline for canonicals in a full conversion,
- reviewed what the gates rejected,
- or measured the false-rejection rate of each gate.

**No broader negative conclusion about document-wide reuse is supported.**

### 1.5 Challenging my own earlier recommendations

| Earlier advice | Assessment now |
|---|---|
| "Fit one outline from all members" (multi-witness super-resolution) | Overweighted. D2 shows healthy reuse does not need it. Keep it only as a secondary hypothesis for degraded strata. |
| "Not measurably worse than its own trace" | Implemented as zero tolerance (FONT-02) and still partly present as "current error + allowance" (FONT-03). The reference should be the noise between independent impressions, not an overfitted self-trace. |
| "One combined gate instead of eight" | Too blunt as stated. Keep the **orthogonal hard vetoes** (topology, area, elongation/orientation, counters, small marks): they carry the demonstrated safety. Replace only the stacked *error-type* checks with one jointly calibrated criterion, and calibrate the false-rejection rate **for the whole gate set (family-wise)**, not per check. |
| "Harm relative to current output" | Necessary but not sufficient. Current output has its own defects, so "no worse than current" could admit bad outlines. Add an absolute check: the candidate must stay within the source noise floor and pass blinded review on its own merits. |
| "Star grouping around a medoid" | Still recommended, but untested. Risk: a style leak (bold or a related serif joining a regular star) that only member-versus-canonical checks would catch. It must be tested against curated hard negatives. |
| "Draws per design as the headline" | It can be gamed by over-merging. Report it only together with defect rate and pristine error. |
| "Exclude research code from Sonar" | Only partly right. Coverage and duplication rules may be scoped away from unshipped research code. Security analysis must stay on. |

---

## 2. Hypotheses and competing explanations

| ID | Hypothesis | Competing explanations | Discriminating evidence |
|---|---|---|---|
| **H1** | One or two input mechanisms (§1.2) explain most of the A → F gain, and adopting them improves *individual* reconstruction. | (a) gain is evaluation geometry (placement fitted in the same frame as the metric); (b) gain spread thinly over many mechanisms; (c) gain is witness selection | Causal ladder, Experiment A |
| **H2** | Within each class, most healthy occurrences can be drawn by a few canonicals at their real placement, with source error within independent-impression variation and zero material defects. | (a) genuine design multiplicity (sizes, weights, faces) needs many designs; (b) placement/compositor limits, not shape, prevent sharing; (c) gates over-reject | Document-wide reuse, Experiment B, plus rejected-sample review |
| **H3** | Document-wide remapping retires enough programs to reduce encoded font bytes and complete PDF bytes materially. | (a) canonicals cost more points than retired programs; (b) retirements concentrate in rare classes; (c) serialization noise | Retired/added/net accounting on full conversions |
| **H4** *(secondary)* | Multi-witness fitting helps where single impressions are degraded (D2/D3, 200 DPI, small sizes). | No independent noise left to average; fitter broadening dominates | Stratified E versus F |

Experiment A comes first because its winning pipeline should trace the canonicals in B.
B can start on the current pipeline in parallel.

---

## 3. Experiment A — explain and exploit the fresh-tracing advantage

**Design: a two-way causal ladder.** Effects can interact, so run both directions:

- **Forward, from A0:** add one F mechanism at a time.
- **Reverse, from F-self:** remove one at a time.

| Arm | Outline source | Preservation floor | Coverage normalization | Frame | Placement |
|---|---|---|---|---|---|
| A0 | production, own or legacy prototype | on | crop p90/p5 (+ Otsu for prototypes) | native crop | production |
| A1 | A0 outline | — | — | — | **refitted to source** (same bounds as F) |
| A2 | fresh self-trace | **off** | crop | native | production |
| A3 | fresh self-trace | off | **local paper/ink + ownership halo** | native | production |
| A4 | fresh self-trace | off | local + halo | **64-pixel line frame** | production |
| F-self | fresh self-trace | off | local + halo | line frame | refitted |
| F-medoid | fresh non-target medoid | off | local + halo | line frame | refitted |

Also include the 16,384-sample grayscale cap (raised versus current) as a separate
toggle at 600 DPI.

**Evaluation hygiene:**
- Placement refitting uses target source pixels only. Using pristine pixels at any
  stage is leakage.
- Every arm is evaluated with **the same measurement procedure**: native renders in
  both engines at original physical coordinates.
- Placement is also evaluated with a placement-independent shape metric (symmetric
  contour distance after rigid alignment). This separates "better shape" from "better
  position".

**Populations:**
- All FONT-01 synthetic splits, all 6 FONT-03 characters, plus at least 10 further
  frequent Latin classes. These are development data.
- The financial document: there is no pristine reference, so use source error within
  the noise floor plus blinded review.

**Outcome rule:**
- If a mechanism (or a pair) accounts for **≥50% of the A0 → F-self gain**, keeps the
  real-document blinded review neutral or better, and does not change text, search,
  raster or compositing, it may become **its own small product PR**, qualified
  independently of reuse.
- If F-self ≈ F-medoid, sharing costs nothing in quality for healthy members. That is
  direct evidence for H2.

---

## 4. Experiment B — document-wide canonical reuse

**Scope:**
- **B1:** every visible `e` on all 13 pages (291 draws).
- **B2:** all 55 classes with ≥10 draws.
- **B3:** remaining classes, with explicit abstention where support is thin.

**Bounded algorithm space.** Codex picks among these and may replace one with
justification, but the space stays small:

- **Grouping:**
  - star groups around a medoid (each member tested against the canonical),
  - complete-link (control),
  - greedy set cover over candidate canonicals (choose the fewest designs such that
    every accepted member has a valid one).
- **Canonical:**
  - fresh medoid trace on the best Experiment-A pipeline,
  - the best-of-k fresh traces by member-aggregate error,
  - robust consensus (only if H4 shows a benefit in that stratum).
- **Acceptance:** for each member at its *real fitted placement*:
  - **Hard vetoes** (kept, never relaxed to admit candidates): component and hole
    count; ink-area ratio; bounding-box aspect; second-moment elongation and orientation;
    effective stroke-width ratio; counter presence and openness; centroid relative to
    baseline and x-height; the small-mark class (punctuation, i/j dots, `'`) handled
    separately, by moments or no sharing.
  - **One jointly calibrated error criterion:** source-coverage error must not exceed the
    member-to-member variation of independent impressions in that group (leave-one-out).
  - **Calibration, measure first:** before choosing any operating point, measure:
    - the **reuse/fidelity frontier**: designs retired versus pristine error and versus
      material defects, swept over the error criterion;
    - **actual false rejections**: the rejected-sample review (§5), and family-wise
      rejection of known same-design D0/D1 synthetic members;
    - the **harm-catch rate** on the curated negative set;
    - each check's *unique* rejections, meaning rejections no other check would make.
  - **≤15% family-wise false rejection is a calibration objective for the error
    criterion only.** It never justifies relaxing, overriding or removing a hard veto.
    If the hard vetoes by themselves reject more than 15% of genuine members, report that
    as a finding and diagnose which veto is responsible. Change a veto only if review shows
    it rejects visually equivalent members *and* it stays effective on the negative set.

**Not allowed:**
- requiring a canonical to fit one source's scanning noise better than that source's own
  overfitted trace,
- relaxing hard vetoes,
- cross-label merges,
- damage repair. Damaged or uncertain members stay exceptions on their current outlines.

**Placement.** PDF text matrices express full affine transforms. If bounded per-occurrence
rotation or anisotropic scale is needed, extend the compositor's placement API rather
than abandoning the share. That decision belongs to Codex, with a test.

**Construction:**
- Remapping happens **before document font union and required-program construction**.
- A program is **retired** only when it has no remaining visible or invisible user.
- Report added, retired and net designs per class.
- Old shared GIDs must not be split without counting the cost.

**Output:**
- An explicit experimental mode (for example `--glyph-sharing experimental`) that
  produces complete ordinary PDFs.
- Default ClearScan stays byte-identical.

---

## 5. Evaluation design

**Populations:**
- **P1 — development synthetic.** The FONT-01 corpus (5,175 observations, 23 faces). All
  splits are now *development*, because each has been inspected.
- **P2 — fresh held-out synthetic.** **Pre-registered now**, before any FONT-04 result
  exists, in [`qualification/font04/p2-preregistration.json`](qualification/font04/p2-preregistration.json),
  which is committed with this plan. That file freezes:
  - 5 families / 12 faces never used in FONT-01 to FONT-03, with file SHA-256: P052, Nimbus
    Roman, Nimbus Sans, URW Bookman, Noto Sans Mono. These include a related-serif pair, a
    regular/bold pair at each family and a monospace;
  - seeds, DPIs, damage plan and phrases;
  - the evaluation rules and pass criteria.

  Nobody may generate, render or inspect P2 before a commit that freezes the method and
  operating point and references the pre-registration hash. P2 is evaluated once. Any
  code change after that evaluation needs a new pre-registration (P2′) before
  re-qualification. P2 is required for production qualification only.
- **P3 — the real financial document** (13 pages). The primary product population.
- **P4 — the other ACR-05 real collections** (historical, receipts, mixed, forms;
  32 pages in total). Used for regression and generalization.
- The sealed holdout stays sealed.

**Curated negative set** (kept for the whole mission, never pruned after results):
- FONT-02 dot-to-sliver cases; FONT-03 `8` counter and slant changes; the rounded italic
  punctuation; the smaller rounder `e`; the `1` repair failure;
- regular/bold, roman/italic and related-serif pairs for each tested class;
- close numerals: `3/8`, `5/6`, `1/7`, `0/O`;
- grayscale counter bands.

**Scorecard.** Every checkpoint reports all of these, per population and per class:
1. pristine error, IoU, contour distance and area bias (P1, P2);
2. relative error versus current emitted glyphs (all populations);
3. material per-character defects from blinded review, **including a random sample of
   rejected candidates**;
4. distinct visibly used designs;
5. visible draws per design;
6. required font slots, encoded and decoded font bytes, and outline points;
7. complete PDF bytes;
8. runtime and peak RSS;
9. search/extraction equality and qpdf/OTS validity.

Do not report aggregate means without the per-class tail (p95, worst 10 per class) and
the negative-set outcome.

---

## 6. Falsification and diagnosis

After each checkpoint, classify each failure as exactly one of these:

| Class | Meaning | Required next step |
|---|---|---|
| **Algorithm failure** | A bounded alternative was not yet tried, or a tried one has a diagnosed fixable defect | Try the next alternative, or fix the defect |
| **Measurement failure** | Rejected-sample review finds most rejected substitutions visually fine, or a metric disagrees with review | Recalibrate or replace the criterion; re-run |
| **Inadequate data** | Too few healthy witnesses in a class or stratum | Report coverage; abstain for that class; continue elsewhere |
| **Falsified opportunity** | See below | Close with evidence |

**The broader healthy-reuse opportunity is falsified for this document only if all of
the following hold:**
1. Over the bounded alternatives, with the best Experiment-A pipeline, the substitutions
   that pass blinded review with **zero material defects** retire **< 25% of designs in
   the 55 frequent classes**.
2. A random-sample review of rejected candidates confirms the rejected members differ
   visibly and genuinely from their canonicals (so the gates are not what blocks reuse).
3. Placement/compositor extensions were tested and do not change (1).

**Scope of this criterion.** The 25% retirement threshold is a **bounded stopping
criterion for this experiment's alternative space**, and nothing more. It does **not**
establish that:
- smaller verified improvements lack product value (a safe 10% font reduction or a
  quality gain remains a promotion candidate in its own right);
- other reconstruction methods cannot succeed;
- reuse fails on other documents.

A stop under this criterion is reported as "the bounded FONT-04 alternatives did not
reach 25% on this document". It is never reported as "glyph reuse does not work".

**H1 is falsified** if no mechanism or pair explains ≥50% of the A0 → F-self gain *and*
the full F-self pipeline does not improve P1 pristine error while staying neutral on P3
review.

**H3 can fail while H2 holds** (for example, canonicals carry more points). That is a
font-serialization problem: simplification budget or CFF. It is not falsification of
reuse.

---

## 7. Iteration rules

- **A failed gate is a diagnosis input, not a closure condition.** Each checkpoint ends
  with a classified diagnosis (§6) and a stated next iteration.
- **Closure requires** either the falsification conditions in §6, or exhaustion of the
  bounded alternative space with the remaining hypotheses written down.
- **Bounds:** at most 3 grouping × 3 canonical choices × 1 acceptance family; at most 4
  iteration rounds before a mandatory scientific-review checkpoint.
- **Discovery** may freely trade quality against economy and report the curve.
  **Production** uses one frozen operating point.

## 8. Production qualification (separate, after discovery)

To promote anything into default ClearScan:
- freeze method and operating point;
- evaluate once on P2;
- run all P3 and P4 pages in both renderers;
- blinded review under `FONT_04_REVIEW_PROTOCOL.md`;
- exact text/search equality; qpdf and OTS pass; deterministic repeat;
- no material defect in the negative set;
- runtime and memory reported;
- a small, separately reviewable PR merged normally into `main`.

Experiment-A pipeline changes and Experiment-B reuse qualify **separately**.
