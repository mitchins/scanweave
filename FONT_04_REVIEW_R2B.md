# FONT-04 R2b review: P2 (single use) — FAIL

Reviewer: Claude, as independent reviewer. Date: 2026-10-31. Codex stop commit: `77c2cbe`.

## Verdict

**P2 fails.** The frozen `cover-2.0` (product `76681da`, binary `85fc1aa6…`) substitutes canonicals from a different
style and, in places, a different face. These are identity-class defects: weight/slant-class changes and wrong
character appearance. The preregistered rule allows zero of them in the accepted sample. They appear throughout the
most-worsened observations, so the material-defect criterion cannot pass whatever the blinded sample shows. The
"pending review" status is therefore moot as a qualification outcome.

P2 is spent. Under the preregistration, any fix is a new method and needs a new holdout (P2′).

## Evidence

**Codex's run is sound as far as it goes.** Every P2 page was converted once in both arms. Determinism holds on all 9
sheets, and extraction, qpdf, OTS and search all pass. The only harness fix allows for PDFium's +1 px page edge, with
hashes unchanged.

**Codex's screen understated the result.** It measured each glyph inside its full observation box, so neighbouring
glyphs fall in the box. Codex flagged this as unvalidated. My reading of its per-observation records (PDFium; Poppler
is equivalent):

- 1,333 of 6,768 observations change between arms. Of those, 948 are worse and 385 better.
- Median change in pristine error is +0.003. The 95th percentile is +0.105.
- The harm is largest at D0 (clean) and at 600 dpi, which is the opposite of the denoising benefit sharing is meant
  to bring.

**Visual check of the 24 most-worsened observations** (`qualification/font04/r2b-evidence/worst-*.png`; columns are
scan, default and cover-2.0). At least 7 are clear identity-class defects:

| Observation | Defect |
|---|---|
| P052-Roman `e` | Drawn as an italic `e` |
| P052-Italic `s` ("ers") | Upright `s` |
| P052-Italic `r` | Upright `r` |
| URWBookman-Light `8` | Italic `8` |
| NimbusSans-Regular `1` | Serif `1` |
| NimbusRoman-Regular `i` | `1`-like glyph |
| NimbusRoman-Bold `n` | Lighter-weight `n` |

The default arm renders every one of these in the correct style. This was not a blinded draw; it is a directed
falsification check. It is enough to establish that the zero-defect rule fails.

## Interpretation

- **Why earlier checkpoints missed it.** The development corpus is dominated by single-typeface financial pages, where
  grouping never sees two styles of the same letter. P2 deliberately mixes 12 faces, including Roman/Italic/Bold
  siblings and Times-metric NimbusRoman. Within one document, cover grouping at multiplier 2.0 admits cross-style
  members. Placement fit and the owned-ink veto do not catch a slant or weight change, because the substituted glyph
  still covers the member's ink box.
- **Why this is not a P2 design artifact.** Bold and italic of the same family are ordinary in real documents. The
  defect is in the method's discrimination, not in P2's layout.
- **The economy cannot buy this back.** These are exactly the "harmful duplication-removal" errors FONT-01 set out to
  avoid.

## Consequences

1. **`cover-2.0` is not qualified.** It must not be merged, even behind the opt-in flag, as a general-purpose option.
2. **Default ClearScan is unaffected.** Sharing is opt-in and `off` is byte-identical to main, so nothing shipped
   changes.
3. **The remaining R2b items (blind package, false rejection, full economy)** no longer decide qualification. They are
   optional diagnostics: P2 data may inform the fix, and any fix then needs P2′.

## Review of S1a and S1b (2026-10-31)

### S1a: substitution census

The census (`s1a-census.json`) was produced by the reviewer, because Codex's join gate tripped on 118 multi-character OCR labels. It covers 473 accepted non-self substitutions:

| Source of the canonical | Count | Share |
|---|---|---|
| Same face | 264 | 56% |
| Different family | 197 | 42% |
| Same family, different style | 5 | 1% |
| Different character (OCR i/l/1 confusion) | 7 | 1% |

- The existing fit error separates visible swaps from same-face swaps at AUC 0.82–0.85.
- Same-face and cross-family fit-error distributions overlap heavily.
- Tightening the multiplier alone therefore cannot fix the defect without losing reuse.

### S1b: per-glyph veto (`30ae13c`)

Verdict: **rejected as a product path.**

| k | P2 caught / 155 visible | P2 same-face vetoed | FONT-01 test caught / 46 | Financial reuse kept |
|---|---|---|---|---|
| 2 | 97 | 83 | 35 | 35% |
| 3 | 60 | 50 | 17 | 60% |
| 4 | 28 | 35 | 4 | 74% |
| 6 | 10 | 14 | 1 | 92% |

- The financial document uses a single typeface, so every substitution its veto removes is a false veto.
- The per-glyph features are weaker than the fit error they would supplement:
  - slant: AUC 0.64–0.84;
  - weight: 0.62–0.68;
  - profile: 0.49–0.77.
- Single-glyph style evidence at scan resolution is noise-dominated. No k gives both defect capture and retained reuse.

### Next: S1c, run-level style evidence

Style is a property of a typographic run, not of one glyph. Pooling slant and weight evidence over an OCR word or line cuts the noise by roughly √n.

S1c should test the following:

1. **Style partition.** Partition each document into style clusters using run-pooled features. A member may then use only a canonical whose source lies in a compatible run cluster.
2. **Confusable characters.** For the confusable labels, test two separate options:
   - an explicit confusable-set restriction, where an i/l/1/I/| or 0/O/o member may share only with a canonical of the same label whose shape passes a structural check;
   - simple exclusion, with its economy cost reported on the financial document.

Calibration stays on FONT-01 train. The metrics and the frontier format are the same as S1b.

## Review of S1c, and the root cause (2026-10-31)

### S1c: run-level style evidence (Codex, rerun by the reviewer after a model-capacity abort)

Verdict: **target not met by any variant.**

- **Best variant: A+C1 at line level, k=2.**
  - P2: 67/155 visible defects caught.
  - FONT-01 test: 27/46 caught.
  - Financial: 97% of accepted substitutions retained.
  - Even on egregious swaps (shape_xor ≥ 0.4), P2 caught only 16/30.
- **B (style clustering):** collapsed to a single cluster per page under single linkage, so it caught almost nothing.
- **C2 (exclude confusables):** caught every different-character case, but cost 30% of financial reuse.

### Root cause

In the frozen product (`plan.rs`), each member's noise floor is the 85th percentile of its errors against its 5 nearest same-label neighbours that pass the hard checks. Admission requires `error / floor ≤ 2.0`.

- **Financial:** a member's neighbours are true repeats of the same design, so the floor measures scan noise.
- **P2:** most face/character designs occur only a few times per sheet. The nearest neighbours are therefore *other designs*, the floor absorbs between-design differences, and a cross-design swap passes as "within noise".

Accepted P2 substitutions, compared:

| Population | Median fit error | Median floor |
|---|---|---|
| Egregious swaps | 0.219 | 0.208 |
| Same-face swaps | 0.048 | 0.125 |

Population-relative floors cannot separate the egregious swaps. The following were also tested and are ineffective (egregious swaps caught ≤ 7/30):

- using the nearest neighbour or a lower quantile as the floor;
- capping the floor at the document median.

The cause is that the document median is itself inflated in a mixed-design document.

### Candidate correction: an absolute ceiling on fit error

A fixed ceiling on fit error, applied in addition to the relative rule, anchors admission to an evidence scale that the document's own population cannot inflate.

- **Calibration:** chosen on FONT-01 train only, as the largest ceiling that catches at least 90% of visible defects there. That gives t = 0.08 (38/41 caught, 12/12 egregious).
- **Results** (offline emulation on the frozen decisions; vetoes only):

| Set | Visible caught | Egregious caught | Different-character caught | Same-face lost | Accepted kept |
|---|---|---|---|---|---|
| FONT-01 train (calibration) | 38/41 | 12/12 | 1/1 | 14/79 | 57% |
| FONT-01 validation | 6/8 | 2/2 | 0/1 | 13/64 | 73% |
| FONT-01 test | 46/46 | 17/17 | 3/3 | 10/59 | 52% |
| P2 (spent) | 138/155 | 29/30 | 6/7 | 67/264 | — |
| Financial | — | — | — | — | **98%** |

The 17 visible P2 defects that remain are mostly near-interchangeable sans pairs, with shape_xor 0.20–0.35:

- NimbusSans ↔ NotoSansMono `a`/`n`;
- Bookman-Demi `s` ← NimbusSans;
- one Times `1` ← `l` (error 0.041).

Same-face members lost to the ceiling fall back to the default reconstruction. That costs only economy, not fidelity.

### Caveats

- The emulation removes accepted members from the frozen plan. Natively, cover grouping may then select different canonicals, so full native PDF runs are required.
- The ceiling is scale-free only if the fit error is resolution-independent. That must be confirmed across DPI natively. Same-face error is somewhat higher at 600 dpi.
- The confusable guard (C1 or a stricter variant) should be re-tested on top of the ceiling for the residual i/l/1 case.

### Direction: S1d

1. Implement the ceiling natively on `exp/style-compat`, created from `76681da`, under a new flag value. Frozen `cover-2.0` and `off` must stay unchanged.
2. Measure actual full PDFs on P2, FONT-01 (all splits), financial and mixed.
3. Then return to Checkpoint S1 review.

## Review of S1d: native absolute ceiling (2026-10-31)

**Implementation.** Commit `3370de3` on `exp/style-compat`, branched from `76681da`. Binary sha256 `d3a26c6d…`.

- The new opt-in flag value is `cover-2.0-ceiling`. A pair must satisfy both the existing `error/floor ≤ 2.0` and `error ≤ 0.08`. Nothing else changes.
- Tests pass.
- The `off` and `cover-2.0` outputs are byte-identical to the frozen outputs:
  - Codex's smoke check: P2 sheet 0;
  - reviewer re-check: all 9 FONT-01 pages.

**Native full-PDF results.** Full PDFs were run by the reviewer; the census and evaluation script is `s1d_eval.py`, with results in `s1d-results.json`.

| Set | Arm | Visible¹ | Egregious (xor ≥ 0.4) | Different-character | Substituted | Net outlines retired |
|---|---|---|---|---|---|---|
| P2 (spent) | cover-2.0 | 155 | 30 | 7 | 753 | 327 |
| | **ceiling** | **21** | **2** | **1** | 513 | 172 |
| FONT-01 train (calibration) | cover-2.0 | 41 | 12 | 1 | 242 | 83 |
| | ceiling | 5 | 2 | 0 | 153 | 44 |
| FONT-01 validation | cover-2.0 | 8 | 2 | 1 | 130 | 57 |
| | ceiling | 2 | 0 | 1 | 97 | 38 |
| FONT-01 test | cover-2.0 | 46 | 17 | 3 | 217 | 96 |
| | **ceiling** | **0** | **0** | **0** | 156 | 53 |

¹ "Visible" uses the font-outline proxy: a different character, or shape_xor > 0.2.

**Real corpus.** Default ClearScan is unchanged throughout.

| Document | cover-2.0 | ceiling |
|---|---|---|
| Financial | 1,750 substituted, net 326, font −62,710 B | 1,736 substituted, net **318 (97.5%)**, font −61,586 B; PDF +1.2 KB vs cover-2.0 |
| Mixed | net 88 | net 82 |
| Forms, receipts, historical | economy guard or no groups (unchanged) | same |

**Residual check** (`s1d-evidence/residual-scan-default-ceiling.png`). This covers every remaining case with a different character or xor ≥ 0.3. The reviewer rendered each at native DPI, with columns scan | default | ceiling. **None is distinguishable from default at reading size.** The cases are:

- NotoSansMono `a` ↔ NimbusSans `a`;
- Bookman-Demi `s`/`t`;
- DejaVu Mono/Sans `s`/`r`;
- Times `1` ↔ `l`;
- NimbusMono-Italic `l`.

The outline-xor proxy overstates these as defects. At scan resolution they are interchangeable shapes, which the owner explicitly allows. This check was unblinded; the P2′ blind review is the qualifying test.

**Verdict.** The correction addresses the diagnosed failure without weakening any safeguard:

- it removes all egregious cross-style substitutions on held-out FONT-01 test;
- on spent P2 it removes 28 of 30 egregious substitutions, and the 2 that remain look indistinguishable from default at reading size;
- it keeps 97.5% of the financial net outline retirement.

It is suitable to freeze as the next candidate.

**Before P2′, the freeze package needs:**

- determinism repeats;
- qpdf, OTS, and text-extraction/search equality on the ceiling outputs;
- paired runtime and RSS;
- the method-freeze record with the ceiling constant and its calibration provenance;
- a fresh P2′ preregistration:
  - new families with related style siblings (Roman/Italic/Bold/Light/Demi);
  - a new seed;
  - the v1.1 sheet layout;
  - the same pass criteria and blind protocol.

P2′ stays ungenerated until the reviewer has checked the preregistration.
