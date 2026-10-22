# ACR04 blinded visual review

## Blind protocol

Judged the coded PDFs `A63`, `B17`, `C42`, and `D08` before unblinding. I did not inspect the blind key, probe, setting table, or result table. The comparison used the same source input, Adobe output, and ACR01 product output for context. I rendered the specified pages at 300 DPI in PDFium and Poppler, inspected whole-page sheets at normal viewing scale, and inspected fixed content crops and 2× nearest-neighbour closeups. No pixelwise score was used as a veto.

Reviewed pages:

- Financial: 0, 6, 10
- Historical: 1, 2, 4
- Receipts: 5
- Mixed: 1
- NARA form: 0 as the unchanged control

Rendered pages and comparison crops are in this directory, grouped by engine and page. `render_blind.py`, `build_detail_sheets.py`, `build_resized_contact_sheets.py`, and `build_nearest_zoom_sheets.py` reproduce the local render/crop sheets.

## Judgments

| Blind ID | Visual result | Judgment |
|---|---|---|
| A63 | Text, digits, punctuation, shaded-page detail, receipt totals, and coloured seal edges remain visually intact in the inspected pages. | Acceptable |
| B17 | Same observed preservation and legibility; no distinct blocking defect. | Acceptable |
| C42 | Same observed preservation and legibility; no distinct blocking defect. | Acceptable |
| D08 | Same observed preservation and legibility; no distinct blocking defect. | Acceptable |

I could not make a reliable visual quality ordering among the four candidates. They form a tie in this review. Any finer ranking would overstate differences that were not consistently visible in both renderers.

Financial list pages retained their names and narrow numerical columns; the body/statistics page retained punctuation and small counts. The old book pages retained the selected faded text and shaded lower area; the red stamp boundary on page 4 showed no new seam, halo, or visible colour loss. The receipt page remains intrinsically faint, but its item values and total were no less readable in any coded arm than in the source, Adobe, or ACR01 comparisons. The mixed page's small text and Linn mark remained visually intact. The form control showed no visible change.

PDFium and Poppler gave the same qualitative outcome on the inspected areas. I observed no material codec artifact, lost content, or renderer-specific defect in these selected pages. Adobe and ACR01 remain useful context, but the candidates do not show a clear visual improvement over them.

## Scope limits

This is a visual decision on the eight requested pages plus the form control, not a quality claim for every page in the collections. It does not establish OCR correctness, semantic equivalence, byte savings, or a general-purpose codec policy. It does not imply that the four candidates are equal in measured metrics; those were deliberately not inspected before this blind judgment.
