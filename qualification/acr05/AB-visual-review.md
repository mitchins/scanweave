# Blinded completed-PDF X/Y review

Judgement recorded without reading `visual-candidates/key.json` or candidate implementation. Source, ACR04, frozen Adobe and completed X/Y financial PDFs were rendered at identical physical coordinates in both PDFium and Poppler using the existing MediaBox/CropBox contract. No size information was used to rank the candidates.

## Fixed evidence

`ab-review/render-review.py` reproduces the sheets. Original baseline windows remain frozen in `baseline-review/regions.json`. Additional supplied worst-patch source-pixel boxes at 300 DPI were page0 `[430,1862,461,1904]`, page1 `[1256,1526,1308,1566]`, page10 `[1623,1874,1648,1915]`, page12 `[332,1467,412,1494]`, each displayed with 100 pixels horizontal and 75 pixels vertical context. No individual-arm resizing or registration was used. Full source-coordinate crops are stacked rather than resized into a wide overview.

Reviewed all four worst-patch windows and the source-selected fixed context windows, spanning both renderers. Especially diagnostic sheets: `p10-poppler-fixed0.png`, `p1-pdfium-fixed0.png`, `p0-poppler-fixed0.png`, `p12-pdfium-fixed0.png`, and the worst-patch sheets.

## Blinded result

**Y is visually preferable to X, but no unconditional product approval follows from these four pages.**

- **X fails the paper-coherence purpose.** On page10 fixed0, small source specks acquire noticeable rectangular light/dark surrounds, and the thin rule has block-like paper transitions near its left portion. On page1 fixed0 there are visible small rectangular backgrounds around the `4` and one upper `15`, and a pale rectangular edge around the horizontal rule. These are more readily visible in the enlarged actual-context crops than in an isolated tiny worst patch. They are not supported by equivalent rectangular source marks. Source text remains readable, but these rectangles are a negative compositor result rather than an improvement to paper continuity.
- **Y avoids the conspicuous X rectangles in those windows.** Amounts (`15 00`, `4 00`, `$295 00`; page10 `185`, `5`, `1`) and surrounding body text remain readable. No meaningful punctuation or nearby line was observed disappearing. Paper appears more coherent than X.
- **Y is not visually identical to ACR04/source.** Some retained thin raster edges, notably the horizontal subtotal rule on page1, look slightly softer/spread compared with ACR04. This is not a demonstrated missing rule, but should be disclosed and measured separately from paper continuity. Do not claim Y sharpens all content.
- The four supplied worst-patch boxes show relatively subtle differences without surrounding context; they alone do not establish a large readability improvement. The fixed contextual windows are more informative about X's boundary artifacts.
- Adobe often has smoother glyphs and broad paper changes; that does not make its output an exact preservation reference or excuse X's newly rectangular paper.

This is a comparative visual judgement on the completed blinded derivatives, not approval of inference-time ownership, font changes or all-page compositing. Any integrated candidate still needs the declared accounting, unchanged glyph/Unicode contracts and normal-size completed-page controls. No third method was requested or evaluated by this review.
