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

## S2a reviewer diagnosis (2026-10-31): pair groups

Codex's S2a run stopped partway (`a0a5f0a`). Its partial prototype could not test A or B, because its smoke groups had fewer than 3 witnesses. The reviewer checked group sizes in the frozen P2′ candidate.

**P2′ candidate groups (accepted members, including the canonical):**

| Group size | Groups |
|---|---|
| 2 (pairs) | 150 |
| 3 | 33 |
| 4 | 11 |
| 5 | 5 |

**The 7 graded P2′ candidate defects by group size:**
- **Pair groups (5):** panels 207 (Plex Bold `o`), 819 (Plex Sans `e`), 951 (Gothic `1`), 267 (Charter `.`) and 1040 (Plex Mono `T`).
- **One 5-member group:** panels 425 and 1131, both URW Gothic `e` with canonical 228.

**Consequence.** In a pair there is no third witness, so cross-witness agreement (A) and consensus (B) cannot decide which witness is contaminated. The defensible rule is a **witness quorum**: share only when at least 3 compatible witnesses support the shape. A or B then applies within groups of 3 or more, where it can actually adjudicate.

**Upper bound on the economy cost of a quorum of 3**, from the frozen ceiling outputs. Each pair group retires at most one outline net.

| Document | Pair groups | All groups | Net retired | Maximum loss |
|---|---|---|---|---|
| Financial | 67 | 267 | 318 | 67 (21%) |
| Mixed | 22 | 55 | 82 | 22 |

**Redirected S2a plan:**
1. Arm Q: the ceiling plus a quorum of 3 or more admitted witnesses.
2. Arm QA: Q plus the cleanest supported witness as canonical within each group.
3. Arm QB, the consensus canonical, follows only if QA leaves the 5-member Gothic `e` group defective.

Evaluation is as briefed: all confirmed defects, a blind sample, pristine quality split into clean and restoration cases, economy and functional checks.

## S2a result: witness quorum (reviewer implementation and evaluation, 2026-10-31)

**Implementation:** `exp/canonical-witness` `e61c0dc`, flag `cover-2.0-ceiling-q3`.
- A shared canonical needs at least 3 distinct source designs (shape keys).
- Grouping, the 0.08 ceiling, placement and every veto are otherwise unchanged.
- 73 `scanweave-io` tests pass, including a new quorum test, plus the CLI flag test.
- `cover-2.0-ceiling` and `off` are byte-identical to the R2c outputs on P2′ sheet 0.
- Binary: `local/S2/scanweave`.

**All 7 graded P2′ candidate defects are removed.** Every one of those members now falls back to default reconstruction.

**Oracle census, analysis only** (`s2a-quorum.json`; ceiling → q3):

| Set | Visible (proxy) | Egregious | Different-character | Net retired | Font bytes saved |
|---|---|---|---|---|---|
| P2′ | 12 → 4 | 1 → 0 | 1 → 1 | 182 → 78 | 48.1 → 19.1 KB |
| P2 | 21 → 10 | 2 → 0 | 1 → 0 | 172 → 61 | 39.1 → 14.2 KB |
| FONT-01 test | 0 → 0 | 0 → 0 | 0 → 0 | 53 → 14 | 13.9 → 3.1 KB |
| **Financial** | — | — | — | **318 → 322** | **61.6 → 64.0 KB** |
| **Mixed** | — | — | — | 82 → 81 | **5.1 → 7.9 KB** |

**Economy.** On the real documents the quorum is *more* economical. Pair groups each paid for an added canonical while retiring at most one outline, so dropping them saves bytes. Synthetic economy falls, as expected, because those pages are dominated by pairs.

**Remaining proxy-visible cases.** The reviewer rendered each at native DPI: none is distinguishable from default at reading size.
- The P2′ "different-character" case is the "amount" `o`. The scan is damaged into a `c` shape; default renders the identical `c`, so sharing did not introduce it.
- The other cases are near-interchangeable sans `a`/`n`/`r` and bold `e`.

**Blind review of every q3 non-self substitution on P2′ and P2: 153 rows.**
- Format: source | X | Y, with default and q3 order randomised per row and the key sealed at `local/S2/sealed/key.json` (`e1bc89c7…`).
- Grades were committed before unsealing (`8a0acb0`).
- **Result: 0 material defects in either arm.** Two harmless dash notches were noted. Because no row was flagged, there is nothing to attribute to an arm.

**Pristine reconstruction on P2′, isolated observation boxes, against default:**

| Renderer | Arm | Mean | p95 | Observations worse by >0.05 | Better by >0.05 |
|---|---|---|---|---|---|
| PDFium | ceiling | +0.00010 | −0.00096 | 19 | 20 |
| PDFium | q3 | +0.00014 | ±0 | 7 | 2 |
| Poppler | ceiling | −0.00006 | −0.00050 | 14 | 19 |
| Poppler | q3 | +0.00009 | ±0 | 3 | 1 |

**Arms A and B.** With the quorum in place there is no confirmed residual for A or B to fix:
- every remaining substitution is in a group of 3 or more;
- no blind-graded defect remains.

Adding either would add complexity without a demonstrated benefit, so neither is recommended.

**Recommendation.**
1. Freeze `cover-2.0-ceiling-q3`: ceiling 0.08 (calibrated on FONT-01 train) and quorum 3 (from the pair-group mechanism; not tuned).
2. Finalise the P2″ contract with the corrections below.
3. Then preregister and run P2″ once.

### Review of the contract draft (`P2DOUBLEPRIME_CONTRACT_DRAFT.md`)

1. **Margin formula.** Drop R(c,s), the PDFium-vs-Poppler difference.
   - It measures the offset between renderers, about 0.016 in mean error here, not sampling noise. It would accept regressions roughly 8 times larger than anything seen.
   - Use N(c,s) only: the 95th percentile of |stat(default, seed A) − stat(default, seed B)| over independent FONT-01-train-face generations with fresh seeds, per renderer.
   - Add a **tail rule**: the count of observations worse than default by more than a fixed per-observation threshold, calibrated in the same way, must not exceed the default-vs-default replicate count.
2. **Zero tolerance.** Keep it for newly introduced class (iii) defects, judged against default.
3. **Fonts.** List candidates whose ancestry is genuinely unseen and which have style siblings, for example:
   - EB Garamond (serif, roman/italic/bold);
   - Lato or Cabin (sans, weight and italic siblings);
   - Inconsolata or Fira Mono (mono).

   Avoid Hack, which derives from DejaVu, and Carlito/Caladea, whose metrics were seen in Liberation. Audit ancestry before selection.
4. **Freeze before opening.** The contract must reference the frozen q3 binary hash, and the guard must refuse to open otherwise.
