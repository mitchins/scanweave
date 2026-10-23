# FONT-04 — Independent review of Checkpoint B2′

Reviewed: `research/font04-document-fonts` at `5e8bb6f`, under contract `9c2e996`.
Protocol: `FONT_04_REVIEW_PROTOCOL.md`. Direction: `FONT_04_REVIEW_B2.md` §6.

Reviewer artifacts are in `qualification/font04/review_b2prime/`:
- my own selection and strata;
- blind judgments, hashed before the key was opened (`d8c0d520…`);
- the decoded key;
- an independent rescore and its scripts.

## Verdict

**B2′ meets the objective for the frequent classes: outline reuse is much higher, and typography is
at least as good as today's output.**

- **Transport is solved.** Composite stubs keep every occurrence's CID, `Tm`, `W` and ActualText.
  - Extraction and search are identical to default in PDFium and in Poppler's three modes. I
    checked this myself.
  - The functional veto now rejects nothing.
- **Reuse is up roughly twentyfold.** At cover-2.0:
  - **327 primitive outlines are retired net**, against 16 at B2 PV. That is about 15% of the
    document's 2,236 programs.
  - Stored outline points fall 13.8%.
  - Font bytes fall 7.5%, from 727 KB to 673 KB.
  - The complete PDF is 45 KB smaller.
- **Typography is not worse.** In my sample, **0 of 244** newly admitted or worst-case accepted
  substitutions were visibly worse than current output. Every material defect sat in the rejected
  stratum, and a hard check caught each one. Source fit improves at every tested point, both in
  Codex's analytic reference and in my independent full-page rescore.

Classification: **qualified research success for the frequent classes.** Nothing is promoted. The
next step is an owner decision (§6).

## 1. Reproduction

| Check | Result |
|---|---|
| Default | `74c31136…`, 2,849,237 B, identical to main |
| Repeats | cover-2.0 and star-1.5 are byte-identical to their `-repeat` files; the manifest hashes match the files on disk |
| Extraction (mine) | cover-2.0, star-1.5 and star-2.0 match default in `pdftotext` default, `-layout` and `-raw`, and in PDFium page text |
| Third renderer (mine) | MuPDF renders the composite stubs. Total ink ratio against default is 0.9997, and no glyph vanished |
| Scope of changes | 82 files, all under `qualification/font04/` plus `FONT_04_RESULTS.md`. No untracked ACR or local artifacts were committed |

## 2. Fidelity

Codex's analytic reference, all 3,524 frequent draws:

| Point | Mean | p95 |
|---|---:|---:|
| default | 0.0656 | 0.1327 |
| star-1.5 | 0.0564 | 0.1132 |
| cover-1.5 | 0.0566 | 0.1136 |
| cover-2.0 | 0.0574 | 0.1139 |

My independent rescore uses full-page renders, so neighbouring glyphs are included and harm to
neighbours is counted. It is comparable only as a change from default.

| Point | All: mean / p95 change | Substituted subset: mean / p95 change | Subset members worse / better by > 0.02 |
|---|---|---|---:|
| star-1.0-net | −0.0028 / −0.0040 | −0.0106 / −0.0181 | 10 / 201 |
| star-1.5 | −0.0039 / −0.0053 | −0.0085 / −0.0142 | 25 / 310 |
| star-2.0 | −0.0035 / −0.0054 | −0.0073 / −0.0126 | 40 / 299 |
| cover-1.5 | −0.0039 / −0.0054 | −0.0082 / −0.0143 | 31 / 311 |
| cover-2.0 | −0.0035 / −0.0054 | −0.0072 / −0.0132 | 44 / 306 |

Both measures agree on direction at every point. The regression tail grows slowly from 1.5 to 2.0.
I sampled the 24 largest cover-2.0 regressions blind, and none was visibly worse.

## 3. Blind review

**Method.**
- I drew my own selection (seed 20261024) from the sealed 17,440-panel set, and never looked at
  stratum while grading.
- Panels show source, U and V, upscaled from the sealed assets.
- I saved and hashed my judgments before opening the key.

| Stratum (my sample) | n | Candidate visibly worse |
|---|---:|---:|
| Newly admitted, cover-2.0 (PDFium) | 80 | 0 |
| Newly admitted, cover-2.0 (Poppler) | 40 | 0 |
| Newly admitted, star-1.5 | 60 | 0 |
| Newly admitted, star-2.0 | 40 | 0 |
| Worst 24 regressions from my rescore, cover-2.0 | 24 | 0 |
| Repeated words, cover-2.0 | 20 | 0 (one minor note on the *current* side) |
| Mandatory-regression and owned-attempt panels | 34 | 0 (all retained default) |
| Rejected | 80 | 9 material, 2 minor, 69 indistinguishable |

- **Harm in admitted members.** 0 of 244 accepted panels were worse. The 95% upper bound on the
  harm rate is about 1.2%.
- **Material defects caught by rejection.**
  - Five are registered regressions: `u`→`U`, neighbour `l` erased, `s`→`t`, `c`→`FI`, `l`→`t`.
  - Four are new, unregistered cases, all caught by hard checks: member 3013 (`e` erased), 2466
    (`w`→`y`), 63 (`e`→`c`) and 1450 (`o`→`r`). Add them to the regression set.
- **glyph-277 / member 3422.** The rejected attempt deletes the owned mark. The veto is correct, and
  the final output keeps default.

**Rejected members by reason** (cover-2.0 ledger):

| Reason | Population | Sampled | Visibly worse |
|---|---:|---:|---:|
| Hard structural check | 1,200 | 53 | 9 material + 1 minor |
| Ranking/economy exception | 315 | 11 | 0 |
| Canonical hygiene | 114 | 7 | 0 |
| Stroke-weight band | 98 | — | — |
| Unexplained owned ink | 47 | 9 | 1 minor (glyph-277) |

**The binding constraint is now the hard checks.**
- They reject 1,200 members. About 81% of those sampled are visually indistinguishable from current
  output, so precision is about 19%.
- But every material defect in this review and in the B1′ and B2 reviews was caught by a hard check.

## 4. Economy

| Point | Net outlines retired | Points saved | Font bytes | PDF change |
|---|---:|---:|---:|---:|
| star-1.0-net | 138 | 30,235 | 709,069 | −12.1 KB |
| star-1.5 | 235 | 47,218 | 695,783 | −22.1 KB |
| star-2.0 | 292 | 56,013 | 681,808 | −36.1 KB |
| cover-1.5 | 286 | 56,012 | 681,154 | −36.8 KB |
| **cover-2.0** | **327** | **61,989** | **672,845** | **−45.1 KB** |

- Moving from 1.5 to 2.0 adds only 41 retirements under cover. The soft error criterion is no longer
  the bottleneck.
- The complete PDF changes by only about 1.6%, because the raster background (1.97 MB) dominates
  the file. Font economy is the right measure for this mission.
- Accounting is honest:
  - 1,746 stubs are counted separately;
  - the literal "stubs count as programs" rule admits nothing, and is reported;
  - the `support-initial` sweep, which left 378 members without a floor, is disclosed and retained.
- The 25% stopping criterion is not reached (about 15%). That criterion is bounded, so this is not
  evidence against the value of reuse.
- B3, the classes with fewer than 10 draws, covers only 193 draws. It cannot add much.

## 5. Risks and limits

- **Renderer coverage.** Composites use `ROUND_XY_TO_GRID | UNSCALED_COMPONENT_OFFSET`. They are
  verified in PDFium, Poppler, MuPDF and OTS, but **not yet in Acrobat or Apple PDFKit**. Both are
  required before any product qualification.
- **12 font resource variants.** These are needed when one CID needs different stubs in different
  places. Extraction is unaffected. The content stream grows by 3.7 KB.
- **Single reviewer.** These are one reviewer's judgments on upscaled 300 dpi crops. Poppler is
  covered only for the cover-2.0 newly admitted members.
- **No pristine truth on P3.** P2 is still sealed.

## 6. Decisions for the project owner

The research question for frequent classes is answered. What remains are choices that belong to
you.

1. **Candidate operating point.** I recommend **cover-2.0**. It has the most reuse and fidelity
   equivalent to 1.5, and no newly admitted member was harmed. cover-1.5 is the conservative
   fallback, with 41 fewer retirements and a slightly smaller regression tail.
2. **The next economy lever is hard-check precision. The hard checks themselves stay unchanged.**
   Two options do not relax any veto:
   - **(a) Alternate canonicals.** When a member fails a hard check against its group canonical, try
     the next-best canonical, or split the group. The hard checks stay exactly as they are.
   - **(b) A measurement study only.** Calibrate each hard check against known-design synthetic truth
     and the blind judgments, then report which checks fire on scan noise. No veto changes without
     your explicit approval.
3. **Method freeze, then P2.** If you want this toward product, the path is:
   - freeze the method at the chosen point;
   - run the Acrobat and PDFKit renderer checks;
   - run the single-use P2 qualification;
   - only then open a small product PR, with default unchanged until it is qualified.

Until then: default stays byte-identical, P2 stays sealed, there are no merges, and PR #24 stays
draft.
