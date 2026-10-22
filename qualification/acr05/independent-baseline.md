# ACR-05 independent baseline diagnosis (before candidate inspection)

Read-only visual diagnosis of the actual ACR04 financial collection, page indices **0,1,10,12**, controls **5,6**. No production change, candidate output, OCR relabelling or sealed holdout was used.

## Evidence and fixed windows

`baseline-review/pN-{pdfium,poppler}.png` compares source, complete ACR04 and font-suppressed raster-only derivative on a common physical canvas. All six pages have both-engine sheets. Derivatives suppress font shows through the existing `anatomy.derivative` helper; they are not reconstructed by adding independent RGB layer images. `baseline-review/regions.json` freezes the following normalized source boxes before candidate evaluation:

| Page index | Fixed source boxes (left, top, right, bottom) | Purpose |
|---|---|---|
| 0 | [.20,.20,.78,.31]; [.10,.32,.92,.40] | Heading/retained versus replaced text; witness rows |
| 1 | [.55,.42,.94,.57] | Amounts, subtotal, thin rule, adjacent paper |
| 10 | [.08,.20,.92,.34]; [.25,.47,.91,.58] | Body paragraph, near rules and paragraph transitions |
| 12 | [.10,.39,.94,.50] | Child-welfare heading/body transition |
| 5 control | [.50,.32,.93,.46] | Totals and paper around ruled groups |
| 6 control | [.25,.21,.80,.33] | CEMETERIES heading, rule and retained source edges |

Detailed sheets render at 300 DPI without registration or independent normalization. Coordinates are rounded against the full source-frame width/height; each crop is capped from its top-left to **900×400 source pixels**. The original uncapped boxes and cap contract are frozen, not retuned after candidates. `render-baseline.py` and `render-crops.py` preserve reproduction. Source `qualification/pdf_packaging/groups/financial-input.pdf`; product `qualification/acr04/local/product/financial.pdf`.

## Supported diagnosis

1. **Faint glyph-shaped remnants exist in the raster-only layer.** Clear examples are page 0's TOWN OFFICERS heading, page 10's missing body words, page 1's replaced amount digits and page 12's heading/body. These are weak edge patterns, not a second full-strength complete text layer. Existing unsupported words/numerals remain strongly painted in raster and must not be erased to make this ablation blank.
2. **These sheets do not establish that a conspicuous broad rectangle is duplicated dark ink.** Complete ACR04 is readable and broadly coherent at normal scale. Any proposed rectangle correction must distinguish low-amplitude paper/patch colour disagreement from actual superseded edges; a font-suppressed word is not by itself evidence of an output defect or permission to remove its whole bounding rectangle.
3. **Paper mismatch/patch boundary is plausible but not yet proven as the unique mechanism.** Some surrounding paper appears smoother or slightly different in tone around repaired text, particularly near headings. To attribute a rectangular discontinuity, overlay exact emitted image-placement boundaries and sample paper-only edge profiles across those boundaries, retaining the same source coordinates. I cannot honestly designate a large unmistakable cleanup rectangle from these unenhanced overview sheets alone. Do not manufacture a stronger visual defect to justify the intervention.
4. **Control heading caution:** page 6 CEMETERIES shows a pale border/halo in the source itself and residual pattern in the nonfont layer. Source lighting/scanned edge contrast must be subtracted before calling all pale surrounding pixels a new compositor halo. The rule below remains real content.
5. **No demonstrated wholesale duplicated ink or geometry shift.** Native glyph edges, thin rules and subtotal content remain present in the selected full renders. Faint edge redundancy is narrower than the larger retained-raster cost and should be measured separately from source-paper tonal seams.

## Acceptance implications

Keep these windows fixed for candidate comparison, including paper outside glyphs and rules/numerals that cross native regions. Require explicit image-boundary alignment to support a paper-seam claim and source-relative evidence before deleting edge pixels. A compositor correction may address paper continuity without changing fonts or asserting new vector coverage. This baseline review is not candidate approval; finer quantitative boundary attribution remains with the engineering audit.
