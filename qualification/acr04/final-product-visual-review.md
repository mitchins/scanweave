# ACR-04 final integrated product: independent visual review

## Decision

**No material visual blocker found in the reviewed final output.** The ordinary-CLI whole-page/native-exception encoding change is visually defensible under the revised ClearScan contract permitting minor tonal/texture losses. This is not pixel-identical preservation, an assertion of improved glyph reconstruction, or a guarantee for every possible source mark.

This review concerns the final progressive-JPEG compatible product, binary SHA-256 `dde0d1da4fc94e69ad291edcc7cc96d9ad52b57b7acbe2e1f9d753b996401556`, not the rejected sequential-decoder outputs. Final PDF identities for all five collections and all four compared arms are bound in `final-visual-review/provenance.json`. The financial PDF is 6,898,862 bytes, SHA-256 `8a8d5d32b710177c37b2fff4b2ad472ffc462f355626b5ac98f10d11bcae4182`. The producer reports a 12,454,682-byte complete corpus; byte accounting and mechanical invariants are separately verified by the parent engineering run, not inferred from these pictures.

## Inspection actually performed

I inspected **all 32 page overviews in both PDFium and Poppler**: ten receipts, five historical pages, thirteen financial pages, Linn and mixed artwork, and two NARA forms. Each overview contains source, frozen Adobe, ACR01, and final output on the same physical canvas. These are normal-view screening sheets rendered at 100 DPI, not detailed certification of every small mark.

I additionally inspected actual 300-DPI source-coordinate details on historical pages 1/2/4; receipts 2/5; financial pages 0/4/6/10; Linn; and both NARA forms. Selected details were checked in both engines, including receipt amounts, financial numerical column, historical seal, serif body text, and form handwriting/rules. The fixed region sheets contain unresized source-pixel crops, not separately normalized glyphs. No perceptual registration was applied.

Reproduction and coordinate evidence:

- `final-visual-review/render_review.py` (independent rendering helper; Python environment `qualification/.venv/bin/python`).
- `final-visual-review/inspection-coordinates.json`: original normalized source boxes, page indices, rounding and 700×450 source-pixel crop cap.
- Rendering implementation: `qualification/residual_resolution/local/qualification/raster_competitors/render_compare.py`, `frame()`. Its common MediaBox canvas retains original CropBox clipping; this avoids the old cross-renderer crop mismatch.
- `final-visual-review/<case>-<renderer>-page.png`: all 64 overview sheets.
- `final-visual-review/<case>-<renderer>-rN-{source,ACR01}.png`: source/Adobe and ACR01/final paired details.

Important source-selected numeric windows include financial `[.76,.63,.97,.92]` and receipt 2 `[.60,.35,.92,.72]`, in normalized full source-frame coordinates before the documented pixel crop cap. The financial examples visibly retain `185`, `5`, `1`, `7`, `4`; receipt 2 retains `92,000`, `80,000`, `60,000`, `42,000`, `334,000`, `350,000`, and `-16,000`, including punctuation/minus. This judgement is from rendered visible marks, not merely the invisible text overlay.

## Findings

- **Decoder correctness:** no green cast, corrupt JPEG blocks, missing strips, or gross new page-geometry defect observed in any final page overview in either engine. This supports the compatibility correction on these real outputs; it is not exhaustive decoder portability testing.
- **Whole-page detail:** final output sometimes looks slightly softer and less textured than ACR01, especially thermal receipts and shaded historical paper. Paper grain and some tiny edge noise change. Under the authorized readability/functional-content objective these are acceptable in the inspected regions; no visible number, meaningful punctuation, rule, or marginal mark was identified as newly disappearing.
- **Thermal receipt amounts:** dotted/faded financial digits remain readable. On cord-05 the amounts `45,000`, `55,000`, `47,000`, `33,000`, and `39,000` retain their structure and commas. Existing blur/fading is not repaired by this codec. Receipt 2's bold total has a pre-existing rough/blotted font appearance in ACR01; the new encoder does not establish a typography fix and that inherited defect must not be advertised as newly corrected.
- **Historical paper:** blackletter and italic/serif text remain usable; fine paper texture and show-through are somewhat softened. The history-04 red seal remains red, its circular edge and readable wording survive. No ACR02-like brown palette substitution or conspicuous flattened-paper rectangle was seen. Large shadow/corner gradients remain recognizable.
- **Financial fine print and numbers:** body serifs, small names, commas, and selected narrow digits remain readable. Minor edge/raster variations exist but no material ringing, block boundary, doubled edge, or newly broken counter was found in the inspected windows. Adobe can look smoother because it reconstructs different content; that does not demonstrate that the present codec changes glyph outlines.
- **Linn and mixed artwork:** page graphics and text remain coherent. The selected Linn body/bullet region did not reveal new visible patch seams or text overlap. Existing reconstruction variation is inherited.
- **NARA:** faint typewritten letters, horizontal rules, printed form labels, handwriting and signature remain visible. The selected signatures and faint body lines show no new meaningful deletion. These pages largely retain the fallback representation; no compression benefit is inferred merely from their visual agreement.
- **Ownership/font separation:** this review did not identify a new cleanup halo or duplicate-source-ink problem caused by the encoding change. It does not prove all existing fringes are eliminated. Fonts, ownership and search invariants must remain the separately checked mechanical contracts; codec pictures alone cannot prove those invariants.

## Limitations and disposition

All 32 pages received two-renderer normal-view screening; only the listed representative fixed regions received detailed inspection. This is not an exhaustive reading of every word or a statistical proof of safety on unseen scans. No pristine typography truth exists for these genuine pages. Comparisons use source readability and functional content, not an invented ground truth, and do not impose pixel equality. The review did not rerun OCR or Rust tests; those results belong to the engineering verification, not this visual finding.

**Independent visual disposition: pass for the tested integrated candidate, with disclosed minor softness/texture changes and inherited typography limitations.** No further codec candidate or imaging method is requested by this review. Production review, CI and operator publication/merge decisions remain separate.

## Supplemental OCR-disagreement check

The completed rerender-OCR diagnostic (`local/rerender-ocr.json`) is not identical between codecs. This must not be reported as unchanged optical recognition merely because embedded PDF text is unchanged.

- **Financial page index 6:** ACR01 OCR reads the second cents token `75`; final OCR reads `15`. I located the final Tesseract TSV box `(1327,1406,52,39)` and independently rendered the surrounding source-coordinate crop **`(1150,1330,1450,1530)` at 300 DPI**, with no resizing/registration, from source, ACR01 and final in **both PDFium and Poppler**. The relevant row visibly reads **`33 75` in all three arms**, with the row above `32 75` and below `22 00`. The final `7` retains a visible top bar and diagonal; I do not find a material human-readable numeral change in this crop. This is nevertheless a measured optical-recognition regression (`75`→`15`), not an improvement or perfect OCR equivalence. Sheets: `final-visual-review/financial-6-75-disagreement-{pdfium,poppler}.png`.
- **Receipt 2:** baseline rerender OCR `- 36,000` versus final `-16,000` is consistent with the independently inspected visible **`-16,000`**. That particular final OCR token agrees better with the visible amount; it must not be counted as content deletion or numerical corruption solely because the strings differ.
- **Receipt 5:** baseline token `70` and final tokens `0`, `017` arise in largely nonsensical OCR lines rather than reliable extraction of the actual visible amount column. The inspected source-supported amount column remains readable, but these OCR outputs do not demonstrate numeric recognition improvement or reliable numeric equivalence. Treat the page as an unresolved OCR limitation, not permission to discard its visible text.

The financial crop adds no material visual blocker to the prior disposition. It does narrow the claim: readable visible numbers survived the inspected codec change, **while rerender OCR is not invariant** and the specific financial substitution must remain disclosed.
