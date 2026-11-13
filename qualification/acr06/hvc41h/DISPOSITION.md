# HVC-41H independent disposition (Claude)

**Economic result: FAIL, far from break-even. Phase D is not built.** HVC-41G remains the proven representation technique. #41 stays open.

## Verified independently
- The #39 p1 `/Im0` embedded stream is 451,336 bytes, DCT, 1158×1569, sha256 `4f5734599b697f9b…`. It is identical to Codex's `original-39.jpg` and `control.jpg`, so the encoder control is byte-exact.
- Variant sizes on disk: B-pre 448,450 bytes (−2,886) and B-native 451,757 bytes (+421).

## Judgement
- **B-pre** saves 2,886 bytes against about 59,473 bytes of vector cost: **4.9% of break-even**. The predicted net is +56,587 bytes. It also has decoded changes beyond the touched 16×16 MCUs (2,293 pixels, max |ΔL| 14.5). In the ghost panels it leaves a faint pale outline of the removed glyph.
- **B-native** makes the JPEG larger and leaves dark contour ghosts at partially owned cells (2,261 dark-proxy pixels).
- The owner's stop rule applies ("nowhere near break-even"). Quality, coverage and geometry were not changed to rescue the result.

## Why it fails
At Q85 / 200 DPI, an average glyph's ink costs about **76 JPEG bytes**. A unique traced vector outline costs about **1,565 bytes** per glyph. The ratio is roughly 20:1 against the vectors, independent of coverage. More coverage at the same per-glyph cost scales the loss linearly; the projection is about +1.5 MB at full proxy coverage.

## Recommendation
- **Park** per-instance vector reconstruction as a compression strategy. Keep HVC-41G as evidence that a faithful, renderer-consistent, semantics-neutral historical-vector overlay is feasible.
- **Do not pursue broader coverage with this architecture.** The economics change only with an architectural shift, each part of which needs separate authorisation and its own fidelity criteria:
  1. shared glyph definitions, where each instance costs only a placement, about 20–40 bytes, instead of its own outline. This changes per-instance shape fidelity, which is ClearScan's own trade-off;
  2. a background whose resolution or quality is chosen *because* text is vector.
  Neither was tested here, and both were expressly out of scope.
