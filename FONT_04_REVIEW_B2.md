# FONT-04 — Independent review of Checkpoints B1′ and B2

Reviewed: `research/font04-document-fonts` at `7576d24`.
Protocol: `FONT_04_REVIEW_PROTOCOL.md`; B1′ authorization: `FONT_04_REVIEW_B1.md` §8.
Reviewer artifacts are in `qualification/font04/review_b1prime/` and `qualification/font04/review_b2/`:
- blind judgments, hashed before the key was opened;
- the decoded keys.

## Verdict

**B1′ is a genuine improvement, and B2 shows that the reuse objective is reachable. The current B2
operating point is limited by transport and over-rejection, not by typography.**

- With placement corrected, shared canonicals fit the source better than today's outlines:
  - `e` substituted subset: analytic 0.060 → 0.039; p95 0.112 → 0.057;
  - all 3,524 frequent draws: analytic 0.0656 → 0.0604.
- No accepted substitution I reviewed was visibly worse.
- The final B2 economy (16–24 net programs) is small for two reasons:
  1. **Text-layout transport:** the complete-output identity veto cut 1,209 → 710 substitutions and
     net retirement from 91 → 24. The 25 sampled vetoed members were all visually indistinguishable
     from today's output.
  2. **Rejections with no demonstrated value:** 0 of 76 sampled members rejected only by:
     - witness/noise support;
     - the functional veto;
     - grouping exception

     were visibly worse than current. Every material defect was caught by a hard structural check.

Classification: **algorithm and measurement limits, not falsification.** Proceed to B2′ (§6).

## 1. Reproduction

| Check | Result |
|---|---|
| B2 default | SHA `74c31136…`, identical to main |
| PV repeat | SHA `97f7e68c…` twice (deterministic) |
| B1′ rescore | Codex's analytic/direct/native tables reproduce my B1 rescore for B1 and match the B1′ PV scorecard |
| Frequent-class aggregates (my sums from Codex's per-class scorecards) | below |

| Arm, 3,524 frequent draws | Analytic mean | Direct mean | PDFium mean |
|---|---:|---:|---:|
| default | 0.0656 | 0.0702 | 0.0762 |
| P-initial (pre-functional) | **0.0576** | **0.0623** | **0.0670** |
| P | 0.0605 | 0.0650 | 0.0703 |
| PV | 0.0604 | 0.0650 | 0.0701 |

The class p95 is worse than default in only 1–3 of 55 classes, depending on the reference (`A`,
`E`, `,`), and by small amounts. Those classes' worst-ten lists should be part of the B2′ sheets.

## 2. The functional veto: real failure, wrong remedy

**I confirmed the failure independently.** P-initial changes Poppler extraction. These are real
regressions, not formatting noise:
- `IPSWICH TOWN` → `IPSWICHTOWN`;
- `83 7` → `837`;
- line regrouping in `-layout` mode.

**Mechanism.** In `font04.rs` `apply()`, each substitution:
- creates a fresh CID;
- replaces the occurrence bbox with the canonical's fitted bbox.

The glyph's text-space origin, advance and apparent font size (`Tm` scale × units) therefore change.
Extractors infer word gaps and lines from exactly those quantities. The visible glyphs carry the
text (`/Span <</ActualText …>>` around `3 Tr`/`0 Tr` runs of one Type0 font).

**Consequence.** Sharing an outline currently also moves the text geometry. Codex's veto preserves
the text contract correctly, but it does so by forgoing reuse.

**Remedy for B2′.** Decouple outline sharing from text geometry. Each occurrence keeps its default:
- CID;
- `Tm`;
- `W` width;
- ActualText.

Only the glyph program changes: it becomes a **TrueType composite glyph** that references the
shared canonical outline through a 2×2 + offset component transform. The fitted placement goes into
that transform. Extraction is then identical by construction, and the outline is stored once.
- Each stub costs about 10–20 bytes, instead of a full outline.
- Stubs may be per design, or per occurrence when transforms differ. Codex chooses, with accounting.

If composites prove unsuitable (OTS, renderer support, F2Dot14 range), the fallback is to preserve
each CID's advance and origin and absorb the placement offset into the canonical's instance. Either
way, the functional veto stays as a **check**, and should then fire on nothing.

## 3. Blind review

**Method.** I graded my own selection, shuffled so I could not see stratum while grading:
- all **192 rejected** B2 panels;
- **150 accepted** panels (my seed 2410);
- the B1′ sheets: 96 accepted, 51 rejected.

PDFium panels at 400%. Judgments were saved and hashed before each key was opened:
- B1′ `81d157ab…`
- B2 `39e0b2aa…`

| Sample | n | Candidate visibly worse | Notes |
|---|---:|---:|---|
| B1′ accepted `e` | 96 | 0 | indistinguishable |
| B1′ rejected `e` | 51 | 51 (41 heavier, 9 material, 1 repair) | identified 51/51; rejections justified |
| B2 accepted, 55 classes | 150 | **0** | one low-confidence note, on the *current* side |
| B2 rejected, 55 classes | 192 | 18 (7 material, 10 minor, 1 repair) | **174 indistinguishable** |

B2 rejected panels by rejection reason:

| Reason | Sampled | Visibly worse | Interpretation |
|---|---:|---:|---|
| Hard structural check (area/centroid/topology/counter/stroke/width…) | 71 | 16 (all 7 material) | Catches all harm; 23% precision |
| Witness/noise only (`insufficient_noise_witnesses`, `noise_floor`) | 33 | **0** | Over-rejection (807 in population) |
| Functional text identity | 25 | **0** | Transport loss (450 in population) |
| Grouping exception | 18 | **0** | Over-rejection (293 in population) |
| Unexplained owned ink | 44 | 2 minor | Fires mostly on immaterial ink; keep, recalibrate |

**Material defects are the same failure every time: a neighbouring glyph is altered.** In each
case the canonical was traced from a crop whose segmentation merged in part of a neighbour, or had
the wrong identity. Examples:
- `m` → `nt` and `w` altered (B1′);
- `s` → `t`, `u` drawn as `U`, `c` → `FI`/`ı`, `m` → `o`, `y` → `n` (B2).

All were caught. But they show that **canonical candidates are not screened for contamination
before they are offered.** That is the gap to close before any soft criterion is relaxed.

**Weight.** In B1′ the rejected `e` attempts were systematically heavier than their sources. These
members are a genuinely lighter design, so the remedy is weight-aware grouping, not admission.

**Limits.** These are one reviewer's 400% PDFium judgments. With 0/76 in the soft-only buckets, the
95% upper bound on the harm rate is about 4%. Poppler panels and repeated-word panels were not
graded this round.

## 4. Other findings

- **Groups that add designs.**
  - Several classes are net negative: `t` +8/−2, `0` +6/−3, `u` +6/−4. A fresh canonical is added
    while the old programs stay alive for other users.
  - These are fidelity substitutions, not reuse. They belong with Experiment A (fresh tracing),
    not in the economy figure.
  - Option: a group is accepted only if it retires at least as many programs as it adds, or the
    canonical is an existing program, so nothing is added.
- **Bytes.** PV retires 16 programs net yet is 2.4 KB larger. Attribute the bytes per added and
  retired program (points per outline), as the plan's serialization row requires.
- **Frontier.** Before the functional veto, complete-link was never net-positive. At error
  multiplier 1.0, star and cover retire 91 and 117. At 2.0–3.0 they retire 337–385 (about 17% of
  all designs), with the direct mean still below default (0.066 vs 0.070). Means hide tails: no
  higher operating point is qualified without blind review of the members it newly admits.
- **Witness eligibility.** 1,523 members have fewer than k = 2 eligible witnesses. The
  current-program exclusion is principled. But witness support has caught no harm in any sample, so
  its role as a hard gate is not earned. It can remain a ranking signal.

## 5. What this review does not establish

- Pristine accuracy on P3, or qualification on P2 (still sealed).
- Poppler-panel and repeated-word materiality for B2.
- That composite transport passes OTS and every renderer; B2′ must show it.

## 6. Direction: B2′

Everything else stays fixed:
- hard vetoes, owned-ink rules (glyph-277 mandatory), the measurement suite, sealed review;
- default byte identity, P2 sealed, no merges.

1. **Composite (or metric-preserving) transport** (§2). Re-emit the P-initial membership with each
   occurrence's CID, `Tm`, `W` and ActualText unchanged. Show:
   - extraction and search identical in both engines **without** the functional veto rejecting
     anything;
   - OTS and qpdf pass;
   - PDFium/Poppler/analytic fidelity equal to P-initial;
   - outline-program, stub, font and PDF byte accounting, reported separately.
2. **Canonical hygiene screen.** A new orthogonal check applied *before* a canonical may be offered.
   Reject canonicals whose ink extends beyond the class footprint, or that contain components not
   supported by their members (neighbour contamination). Mandatory regressions: the 9 B1′ and 7 B2
   material cases listed in `review_*/key-decoded*.json`.
3. **Re-scope soft criteria.** With hygiene and hard checks in force:
   - witness/noise support and grouping exceptions become ranking or diagnostic signals, not gates;
   - measure the frontier with complete outputs at multipliers 1.0 / 1.5 / 2.0 for star and cover.
4. **Weight-aware grouping.** Add a stroke-weight band to the grouping key, so lighter and heavier
   designs get separate canonicals.
5. **Net-retirement rule.** Report fidelity-only substitutions separately. Test the
   "retire ≥ add, or reuse an existing program" constraint.
6. **Owned-ink calibration.**
   - Use the 44 B2 firings (42 judged immaterial) to set the significance threshold.
   - glyph-277, `glyph-3422` and `glyph-1233` must stay vetoed.
   - Dirt not reproduced by default is never preserved.
7. **Byte attribution** per added and retired program, plus the save-only control.

**Checkpoint B2′ deliverables:**
- complete PDFs for each tested point;
- scorecards as in B2;
- sealed sheets that include **every member newly admitted** relative to B2 PV (or a ≥ 200 random
  sample if larger), plus ≥ 150 rejected;
- the frontier with complete-output economy.

**Stop at Checkpoint B2′.** No pre-authorized continuation: the next operating point is chosen
only after the newly admitted members are reviewed.

## 7. B2′ authorization

The project owner accepted this review on 2026-10-24 and authorized B2′ as specified in §6, with
no further refinements. These standing rules carry over unchanged:
- default ClearScan stays byte-identical, and nothing is promoted on B2 or B2′ measurements alone;
- P2 stays sealed;
- no merges, no new product PRs, PR #24 stays draft;
- stage explicit paths only, and never commit untracked ACR-02/03/04 or other local artifacts;
- stop at Checkpoint B2′ for independent review.

**Objective.** The aim is substantially higher document-wide outline reuse, with typography at
least as good as today's output. Passing a gate or saving a few bytes is not the objective.
