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
