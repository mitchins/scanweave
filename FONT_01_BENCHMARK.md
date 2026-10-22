# FONT-01 frozen benchmark specification v1

Frozen before feature/model fitting. This is a development benchmark, **not** the
sealed product holdout. No files from that holdout are opened.

## Identity and inference boundary

Family is a design relationship; face/cohort is compatible design, weight and slant;
canonical glyph is one character design within a cohort; observation is a particular
impression with nuisance geometry and degradation. Size is recorded separately.
No model may rewrite the supplied character identity. Same-character similarity
alone does not establish cross-character face identity. Indistinguishable designs
at scan resolution require abstention.

`observations.jsonl` and `images/` are inference inputs: opaque observation IDs,
character identity, scan DPI, page geometry and grayscale samples. The separate
`oracle/` directory contains font/style/family, pristine shape, damage mask,
transform, document/line/word identity and split labels. Training/evaluation joins
labels explicitly; the inference API never opens `oracle/`.

## Faces and splits

Use manifested installed DejaVu, GNU FreeFont, URW Base35 and Liberation files,
with exact names, hashes and local licence notices. No font binaries are committed.
DejaVu is Bitstream Vera/public-domain additions; FreeFont is GPL-3+ with font
exception; URW Base35 is AGPL-3 with document embedding exception; Liberation is
SIL OFL1.1. Rendered document fixtures do not redistribute the font software.
The manifest records the exact notice as well as each font hash.

Training: eight DejaVu/FreeSerif faces. Validation: six C059/NimbusMono faces.
Unseen test: eight Liberation Serif/Sans/Mono faces. All styles of a family remain
in one split. Test fonts, documents and pristine source identities never appear
in training or threshold calibration. A further related-face stress arm may be
reported separately, never relabelled family-disjoint evaluation.

Each split creates a separate multi-page document, with similar faces on one page,
interleaved lines, within-line alternating faces, and repeated distant-page faces
under different degradation. Page position cannot predict cohort. Include:
`expires`, `Term expires 1921`, `constant use were after`, common body words,
upper/lowercase, punctuation and financial numerical strings. Identical strings
appear in different faces; different strings appear in each face.

## Geometry and damage

Record subpixel translation/baseline jitter, rotation up to 1.5 degrees, bounded
scale (0.96–1.04), anisotropy (0.97–1.03), shear up to 0.025, varied spacing and
nominal point sizes (10/12/15) at 200/300/600 DPI. Geometry and damage are sampled
independently from a seeded generator. Oracle is the correctly transformed pristine
glyph, not a separately resized candidate bounding box.

| Band | Explicit mechanism |
|---|---|
| D0 | Pristine printing, geometry variation retained |
| D1 | Mild blur, grayscale noise and small density variation |
| D2 | Uneven density, mild bleed and structured stroke loss |
| D3 | Missing contiguous stroke segments and substantial fading |
| D4 | Severe contiguous removal/occlusion, deliberately ambiguous cases |

Each face/character has clean and damaged independent observations. Damage masks
identify changed ink, including interrupted crossbars/arcs/terminals; they are
not inference inputs. Report generator limitations: raster simulation is not a
complete physical printer/scanner or a substitute for genuine pages.

## Frozen evaluation

Split before augmentation by family and document. Master identity is face-file
hash + character + rendering source; all descendants remain in one split. No random
instance split. Pair sampling balances same/different faces *within character*,
includes close serif/style hard negatives and keeps D0–D4 strata visible.

Report ROC/PR AUC, precision/recall, false merges at 50/80% same-face recall,
calibration error for probabilities, and fixed validation-selected threshold
results on untouched test. Report by character, DPI, severity and related-face
negative. Fix threshold using validation only; no test-score tuning.

Report canonical-template clustering separately from face-cohort discovery:
ARI, purity, completeness, cohort counts, over/under-splitting, contamination,
canonical groups/character and abstentions. Complete-link clustering must reject
an incompatible pair even if an intermediate observation connects them.

Recovery uses medoid/consensus and strongest donor, compared to held-out pristine
oracles at fixed geometry. Never infer missing strokes from expected words.
Compare actual ScanWeave shape-key behavior via the existing Rust path, not a
Python approximation labelled as product equivalence.

## Conditional deployment gate

Default: research only. No normal PDF change. A candidate must reduce redundant
groups without material cross-style contamination, outperform its simpler arm
on unseen families, and pass independent failure-case review. Claimed probability
requires calibration. Rust parity and real-PDF visual/Unicode tests are separate
gates, not implied by benchmark accuracy. No forced CNN or forced glyph merge.

Real checks: Town Officers page marked5 (`expires`), page105 (`constant`), and one
existing mixed historical page. No authoritative font labels are invented. Report
adjudicated examples separately from synthetic exact-ground-truth metrics.
