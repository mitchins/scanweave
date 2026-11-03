# FONT-04 P2″ review: final qualification of `cover-2.0-ceiling-q3`

**Verdict: PASS on every preregistered criterion, with a stated sensitivity caveat.**

Single run, 2026-11-03.
- Preregistration `771bea10…`, approved by the owner (`ab83db9`).
- Candidate `e61c0dc`, binary `8667f6dd…`.
- Evaluation script frozen at `4781da2`, after a dry run on spent P2′.
- Lock receipt: `local/P2pp/OPENED`.
- No code, constant, margin, population or rule changed after opening.

## Numerical findings

| Criterion | Result |
|---|---|
| Functional: extraction in 5 engines, native search, qpdf, OTS, repeat byte-identical (`p2pp-functional.json`) | **PASS**, 9/9 sheets |
| Class non-inferiority against calibrated margins (`p2pp-numeric.json`) | **PASS**, every frequent class in both renderers |
| Tail sign test, τ ≈ 0.22 | **PASS**: 0 worse, 0 better, in both renderers |

**Overall pristine error, candidate vs default:**

| Renderer | Default | Candidate | Δ |
|---|---|---|---|
| PDFium | 0.16931 | 0.16956 | +0.00025 |
| Poppler | 0.18601 | 0.18623 | +0.00022 |

p95 is unchanged in both renderers. No observation exceeded 0.5τ, so the tail stratum of the blind package was empty.

## Visual findings (blind review, `p2pp-grades-blind.json`, committed `e742ca8` before unsealing)

**Package:** 189 rows. Each row shows the source and two arms at 100% and 200%, with arm order randomised.
- 89 rows are every candidate non-self substitution.
- 100 rows are positive controls: reference-arm swaps that the candidate did not admit.

| Arm | Stratum | (i) harmless | (ii) justified restoration | (iii) material |
|---|---|---|---|---|
| Candidate q3 | admitted | 87 | 2 | **0** |
| Default | admitted rows | 89 | 0 | 0 |
| Reference ceiling | controls | 100 | 0 | 0 |
| Default | control rows | 100 | 0 | 0 |

**Material-defect criterion: PASS.** The candidate introduced 0 new class (iii) defects relative to default. The two (ii) restorations fill a notch that a damaged scan had removed:
- a Lato `e`, row 16;
- a Lato `1`, row 179.

### Sensitivity caveat (reported, not a pass criterion)

On P2″ the reviewer flagged none of the 100 positive controls. On P2′, by comparison, the same reviewer flagged 38 of 200.

After unsealing, the oracle shows 8 proxy-visible reference swaps among the controls. Inspected unblinded at native DPI (`p2pp-evidence/controls-proxy-visible-scan-default-ref.png`), none is distinguishable from default at reading size.

The likely explanation is that the P2″ families produce much subtler swaps than P2′ did. However, the review could not demonstrate sensitivity on this population, so a zero-defect result here is weaker evidence than it would be with positive controls that the reviewer caught.

### Oracle census after unsealing (analysis only)

| Arm | Same face | Same family, other style | Different family | Different character | Proxy-visible |
|---|---|---|---|---|---|
| Reference | 242 | 33 | 20 | 4 | 20 |
| Candidate q3 | 70 | 16 | 2 | 1 | 7 |

All 19 candidate swaps that are cross-style, cross-family or cross-character were rendered unblinded (`p2pp-evidence/candidate-cross-style-scan-default-q3.png`). None is distinguishable from default at reading size.

These are predominantly adjacent Lato weights (Semibold ↔ Bold, Regular → Semibold) and the EB Garamond 08 ↔ 12 optical sizes, which are the intended near-sibling stress. The single different-character case (row 5) is a Lato BoldItalic swap labelled `d` ← `a`, an OCR join artefact on a damaged glyph. It renders the same as default.

## Economy and cost (report only)

| Arm | Font bytes | PDF bytes | Substituted | Net outlines retired |
|---|---|---|---|---|
| Default | 932,887 | 5,026,084 | 0 | 0 |
| Reference ceiling | 885,834 | 4,988,508 | 514 | 193 |
| **Candidate q3** | **913,302 (−2.1%)** | **5,009,868 (−0.3%)** | 128 | 85 |

**Runtime and memory, summed over 9 sheets:**
- Default: 396 s; candidate: 620 s (1.57×).
- Peak RSS: 442 MB for default and 441 MB for the candidate.

On real documents (development measurements, `s2a-quorum.json`), q3 saves:
- financial: 64.0 KB of font (net 322 outlines);
- mixed: 7.9 KB.

## Conclusion

`cover-2.0-ceiling-q3` qualifies under the preregistered contract. The candidate made **no material typography regressions** in any evaluated population:
- P2′ and P2 (development, blind-graded);
- P2″ (holdout, blind-graded).

It is now strictly more conservative than the failed variants. The economy is modest on synthetic mixed-face pages and preserved on the real financial document.

**Next, per owner instruction:** a focused product PR with q3 as the sole public opt-in sharing method. Default stays `off`. `cover-2.0` and `cover-2.0-ceiling` are not exposed as supported options. This approval covers the qualification run only, not merging.
