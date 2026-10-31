# FONT-04 R2c review: P2′, single use — FAIL under the preregistered criteria

Reviewer: Claude, independent and blind. Date: 2026-10-31.

- Preregistration: `fd8d69e3…`. Candidate: `cover-2.0-ceiling`, binary `d3a26c6d…`.
- The grades were committed blind as `e08287f`, before unsealing. The key and census hashes match the commitments in `r2c-seal.json`.

## Verdict against the preregistered criteria

| Criterion | Result |
|---|---|
| Functional: text, search, qpdf, OTS, determinism | **PASS** on all 9 sheets |
| Pristine quality: candidate mean and p95 ≤ default for every frequent class, in each renderer | **FAIL**: 61 of 86 class×renderer cells. Largest mean excess +0.0019; largest p95 excess +0.0002. Overall mean is equal to default within ±0.0001 (PDFium 0.16346 vs 0.16336; Poppler 0.17987 vs 0.17993) |
| Material defects: zero identity-class defects in the accepted sample | **FAIL**: 6 admitted members, 12 arm-grades across both renderers |
| Material defects: candidate rate ≤ default | PASS: candidate 12 arm-grades vs default 18 (14 of them in the admitted stratum) |

**P2′ fails.** Under the single-use rule, `cover-2.0-ceiling` is not qualified and cannot be merged. This is reported as measured, with no post-result tuning.

## Blind grading (1,158 panels × 3 arms)

| Arm | Identity-class defects | Materially worse | Breakdown |
|---|---|---|---|
| Default ClearScan (`off`) | 18 | 8 | stroke 11, weight 5, slant 2 |
| Frozen `cover-2.0` (reference) | **68** | 12 | stroke 26, slant 18, weight 12, counter 6, dot 4, wrong character 2 |
| `cover-2.0-ceiling` (candidate) | **12** | 2 | stroke 7, wrong character 2, slant 2, weight 1 |

**Sensitivity.** The reviewer flagged 38 of the 200 positive-control panels on the reference arm. These are substitutions that the ceiling removed. Many controls are interchangeable shapes, so this sets a floor, not a measured recall.

**Candidate defects, unsealed and joined to the oracle.** Five of the seven graded panels are **same-face** substitutions. The canonical is the same font and character, but is traced from a different scanned occurrence.

| Panel | Glyph | Source of canonical | Fit error | Observed defect |
|---|---|---|---|---|
| 207/208 | Plex Sans Bold `o` | same face | 0.038 | rendered with a zero-like inner mark; materially worse |
| 425/426 | URW Gothic `e` | same face | 0.035 | terminal shape from another occurrence |
| 1131 | URW Gothic `e` | same face | 0.021 | terminal shape from another occurrence |
| 819/820 | Plex Sans `e` | same face | 0.076 | hooked tail |
| 951/952 | URW Gothic `1` | same face | 0.065 | flag restored where the scan's flag was damaged away |
| 267/268 | Charter `.` | Plex Sans Italic `.` | 0.042 | slanted full stop |
| 1040 | Plex Mono `T` | Plex Sans `T` | 0.051 | heavier stem; one renderer only |

## Interpretation (not used to change the verdict)

**The diagnosed failure is fixed.** In the oracle census:
- Cross-family admissions fell from 178 to 34, and same-family different-style from 24 to 5.
- Egregious substitutions fell from 59 to 1, and proxy-visible ones from 155 to 12.
- Blind identity-class grades fell from 68 to 12.

**The residual failure is a different mechanism: same-face shape transport.**
- A canonical traced from one damaged occurrence carries that occurrence's local shape, such as a terminal notch, an inner mark or a restored flag, into members whose own scans differ there.
- These substitutions have very low fit error (0.02–0.08), so no fit-error ceiling or style check can exclude them.
- The defect is identity-preserving but visible at 200%.
- The candidate's rate (12) is below the reviewer's flag rate on the default arm (18). Default ClearScan shows comparable differences from damaged sources.

**The pristine criterion is effectively unattainable as written.**
- It requires per-class ≤ default with no tolerance, so any substitution method fails it on noise-level changes. Here the excess is 0.002 at most.
- This should be fixed by preregistration before any future holdout. It is noted here and not applied post hoc.

## Options for the owner

1. **Stop FONT-04 sharing here.** Default ClearScan is unaffected. Record the ceiling candidate as the best non-qualified result, and keep the research artifacts.
2. **One further iteration, under a new holdout (P2″).** It would address same-face transport and fix the criterion design in advance:
   - **(a)** A canonical-selection change: build the canonical as a consensus over its group's member traces, rather than one occurrence's trace. Or admit only when the canonical's own source is among the cleanest (lowest-damage) members.
   - **(b)** Preregister a pristine tolerance tied to measured renderer and reconstruction noise, plus the identity rule as used here. Do not tune it to P2′.

   This needs new fonts, or at least a new seed and layout, plus the same blind protocol.
3. **Ship nothing** until a P2″ pass, whatever the choice. P2′ is spent.

The reviewer's recommendation is option 2a with a consensus canonical. It is the only mechanism aimed at the observed residual, and it would make sharing a denoiser rather than a copier. Option 1 is also defensible, given the remaining effort and the modest economy on mixed documents.
