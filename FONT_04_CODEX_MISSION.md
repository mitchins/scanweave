# FONT-04 — Codex mission: reusable reconstructed document fonts

Read `FONT_04_SCIENTIFIC_PLAN.md` first. It holds the hypotheses, controls and
falsification conditions. This file is the engineering contract.

## Objective

Make the real 13-page financial document's reconstructed font **substantially more
reusable** (fewer necessary designs, more draws per design), with typography as good as
or better than current output and a smaller complete PDF. Also find out what actually
makes freshly traced outlines better than current ones, and ship that separately if it
qualifies.

**This mission does not end because a first gate fails.** It ends with a demonstrated
improvement, a falsification that meets the plan's §6 conditions, or an exhausted
bounded alternative space with documented hypotheses.

## Base, branches, Git

- Start from verified remote `main` (`c10e3dff…`, or later if merged work has landed;
  record the SHA).
- Research branch: `research/font04-document-fonts`.
- A product change from Experiment A, if qualified, goes on its own short-lived branch
  from `main` and is merged normally **before** dependent work is stacked. **No new
  stacks of unmerged product PRs.**
- PR #24 stays draft and unmerged until its Sonar failure is resolved (see "Sonar"
  below). Reuse its code by importing or copying it into the FONT-04 branch with
  attribution in the commit message.
- No force-push to `main`, no protection bypass, no weakening of product quality gates.

## This launch

Run **Phase A and Phase B1 only**, then stop at Checkpoint B1 for independent scientific
review. Do not start B2 until the review (`FONT_04_REVIEW_B1.md`) authorizes it.

## Repository hygiene track (parallel; never blocks Phase A or B1)

Run this independently of the discovery work. It must not take up the discovery cycle.
Security triage is **mandatory**, and it must be finished before any product PR merges and
before any decision on #24. It is not a prerequisite for running experiments.

1. Independently triage every Security finding on #24. Fix real issues (path handling,
   subprocess, XML, deserialization). Disposition false positives individually with
   reasons, as in FONT-01. Never in bulk.
2. Propose, in a separate small PR, how research tooling is scoped. For example: move
   research Python under one package (`research/` or `qualification/research/`) with
   `sonar.coverage.exclusions` and `sonar.cpd.exclusions` for that path, and **Security
   and Reliability analysis kept on**. Alternatively, a separate repository. Explain the
   choice. Shipped crates keep the existing gates unchanged.
3. Then decide whether #24 merges as research infrastructure or is closed with its
   branch retained.

## Phase A — causal ladder (scientific plan §3)

Build a harness that can trace any observation through these independently switchable
mechanisms:
- the preservation floor (`preserved_source` / `min_ink_iou`) on or off;
- coverage normalization: production crop p90/p5 (+ Otsu prototypes) versus local
  paper/ink with an ownership halo;
- frame: native crop versus 64-pixel line frame;
- the grayscale size cap (16,384 samples) as-is or raised;
- placement: production versus refitted to the source (same bounds as FONT-03 F);
- witness: self, non-target medoid, or legacy prototype.

Run the forward ladder (A0 → A1 … → F-self) **and** the reverse ladder (F-self minus one
mechanism). Evaluate every arm with the same native two-renderer measurement, plus a
placement-independent shape metric. Populations: FONT-01 synthetic (all splits are
development), the 6 FONT-03 characters plus at least 10 frequent Latin classes, and the
financial document (source error plus blinded review).

**Checkpoint A.** Write `qualification/font04/checkpoint-A.json` and a short markdown
summary:
- each mechanism's share of the A0 → F-self gain, per DPI and damage band;
- F-self versus F-medoid;
- negative-set outcomes.

If a mechanism or pair explains ≥50% of the gain and qualifies, open the small product
PR described in the plan's §8 (individual reconstruction only, no reuse).

## Phase B — document-wide reuse (scientific plan §4)

Implement an experimental mode, for example `--glyph-sharing experimental` (exact name is
your choice). It must produce **complete ordinary PDFs** from the normal PDF-to-PDF CLI.
Default ClearScan must stay byte-identical. That is a test.

In that mode:
1. Gather every visible observation per OCR label across all pages. Never cross labels.
2. Group them using the bounded options (star/medoid; complete-link control; greedy set
   cover over candidate canonicals).
3. Trace canonicals with the best available pipeline (Phase A's winner when available;
   otherwise the FONT-03 F path).
4. Test every member at its **real fitted placement**: hard vetoes plus one noise-floor
   error criterion. **Measure before choosing.**
   - Sweep the error criterion and report the reuse/fidelity frontier (designs retired
     versus pristine error versus material defects).
   - Report actual false rejections from the rejected-sample review and from known
     same-design D0/D1 synthetic members.
   - Report each check's unique rejections and the negative-set harm-catch rate.

   Then choose an operating point for the error criterion, aiming at ≤15% family-wise
   false rejection. That target is a calibration objective. **It never justifies
   relaxing or overriding a hard veto.** If the vetoes alone exceed it, report and
   diagnose that.
5. Members that fail keep their current outline as individual exceptions. Damaged or
   uncertain members are never repaired in this mission.
6. Remap **before** document font union and required-program construction. Count
   **retired** programs (zero remaining users), added programs and net change, per class.

Run in stages:
- **B1:** all 291 visible `e` on 13 pages.
- **B2:** the 55 classes with ≥10 draws.
- **B3:** the rest, with abstention.

You may extend the compositor's per-occurrence placement (PDF `Tm` is affine) if the data
shows placement, not shape, blocks sharing. Test it.

**Checkpoint B1** (stop here and wait for scientific review before B2). Produce:
- the full financial PDF in experimental mode, plus the default-mode PDF;
- the `e` scorecard;
- a rejection ledger (member → failing check → value → limit);
- blinded review sheets for a random sample of **accepted and rejected** members,
  repeated words at reading size and 400%, and both renderers;
- negative-set outcomes.

## Scorecard (every checkpoint; machine-readable plus a short markdown table)

Per population and per character class:

| Field | Notes |
|---|---|
| pristine error / IoU / contour distance / area bias | synthetic only; mean, p95, worst 10 |
| error relative to current emitted glyph | all populations |
| material defects (accepted sample, rejected sample, negative set) | from blinded review |
| distinct visibly used designs; draws per design | follow CID → GID; not raw CIDs |
| added / retired / net programs | per class |
| required slots; encoded and decoded font bytes; outline points | |
| complete PDF bytes | experimental and default mode |
| runtime; peak RSS | same machine, paired runs |
| search/extraction equality; qpdf; OTS; determinism | must hold |

## Freedom

- You choose the implementation, data structures and which bounded alternative to try
  next, and you may replace one alternative with a better-justified one. Record why.
- If the evidence says a different mechanism matters (for example outline point budgets
  or serialization once reuse works), you may investigate it within this mission and
  report it.

## Prohibitions

- No damage repair, cross-label merges, OCR/Unicode changes, raster/compositing changes,
  or default-mode output changes.
- No relaxing of hard vetoes to admit candidates.
- No acceptance criterion that requires a canonical to fit one source's noise better than
  that source's own overfitted trace.
- No pristine pixels in any inference or placement step.
- No closing the mission on a first failed gate. Classify the failure (algorithm,
  measurement, data, falsified) and iterate within bounds.
- No full-corpus 32-page production qualification until the method is frozen. Then use
  the fresh P2 held-out set once.
- **P2 is pre-registered** in `qualification/font04/p2-preregistration.json`. Do not
  generate, render or inspect it, and do not change its families, seeds or rules. Implement
  its generator option (`--face-manifest` or equivalent) only behind a check that refuses
  to run without a method-freeze commit referencing the pre-registration SHA-256.
- The plan's 25% retirement threshold is a bounded stopping criterion for this
  experiment's alternatives. Do not present a stop under it as evidence that reuse lacks
  product value. Smaller verified gains are reported as candidates.

## Deliverables

- `FONT_04_RESULTS.md`: checkpoints, scorecards, failure classifications, decisions.
- `qualification/font04/` reproducible harness, ledgers and compact JSON. Large artifacts
  stay local/ignored with hashes in a manifest.
- The experimental-mode PDFs for review (paths in the report).
- Any qualified product PR(s), each small and merged normally, with the final `main` SHA.
- An updated Git receipt: open PRs, merged SHAs, retained branches.
