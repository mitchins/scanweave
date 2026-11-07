# Issue #31: PDFium copy-text repeats (diagnosis and bounded correction)

Reviewer and engineer: Claude. Product PR: #34 (`fix/pdfium-copytext-31`), on main 261c27f. Baseline: the current default output (main d804bb0; the #28 merge does not change default output). Inputs are the fixed real corpus: the five groups plus the single page, 33 pages. All are public or synthetic material already in the repository's qualification sets.

## Mechanism (PDFium source, `core/fpdftext/cpdf_textpage.cpp`)

1. `ProcessTextObject` buffers consecutive text objects as one line. An object stays on the line while its origin y is within half the wider object's PDFium width of the buffer's last object. That width is `GetCharWidth × font size × (XUnit + YUnit) / 2`.
2. Within the buffered line, each object is inserted after the last object whose origin x is ≤ its own. The line is therefore sorted by x.
3. `ProcessTransformedTextObjects` emits a span's `/ActualText` for the first object it meets in that span. It skips the span's later objects only while the previous object belongs to the same marked span (`PreMarkedContent` → `kDone`). Any interleaving re-emits the whole span text.
4. Word spaces come from `ProcessInsertObject`. It measures the gap from the previous `/ActualText` owner object's last item, in that object's text space.

ScanWeave emitted invisible OCR text as one object per OCR character box. `diagnose.py` maps every extracted character to its text object (`FPDFText_GetTextObject`). On main it finds 38 repeats on 8 pages:

| Class | Example | Repeats |
|---|---|---:|
| Duplicate OCR line on the same baseline (both words invisible) | forms p1 "SOLICITATI:" / "SOLICITATION", "OF" / "OF"; historical p3 "ange" / "Yanct-" | 25 |
| Raised mark joins the previous line and is sorted to its front | historical p1 "‘Quoquo" (#31) | 1 |
| Box clamped at the page edge (y = 0) | financial p7 "pe", "xt", "TTNON…" | 4 |
| Invisible word inside a visible word's x-range | forms p0 "BS_AD", "DELIVER", receipts p1 | 5 |
| Visible dash rule spanning two baselines | financial p3, p5 | 3 |

## Variants tried (all invisible-text placement only; visible output pixel-identical in every variant)

PDFium inserted and deleted characters are measured against the `/ActualText` reference. Word tokens are matched out of 5,572.

| Variant | Repeats | PDFium ins/del | PDFium tokens | Poppler tokens |
|---|---:|---:|---:|---:|
| main | 38 | 423 / 104 | 5,382 | 5,173 |
| v2: word as one TJ object, median width | 6 | 132 / 147 | 4,340 | 4,998 |
| v3: per-character objects, shared baseline | 54 | 568 / 135 | 5,383 | 5,161 |
| v4: one object only for overlapping words | 15 | 211 / 115 | 5,245 | 5,135 |
| v5–v13: first character standalone plus a TJ remainder (several sizing rules) | 14–16 | 154–180 / 112–149 | 5,352–5,390 | 4,585–5,173 |
| **v15 (PR #34): one narrow-scale TJ object per all-invisible word; visible baseline for partial words** | **6** | **81 / 96** | **5,463** | **5,166** |

Lessons that fixed the design:
- One object per word removes interleaving. But with a character-sized scale, PDFium measures the real word gap against 0.125 em of that scale, and v2 lost word spaces.
- PDFium previously measured from a one-character object, the word's leftmost character, so it almost always inserted a space. A 0.1× horizontal scale makes any real gap exceed PDFium's threshold. That restores this behaviour without a split object.
- Poppler sizes `/ActualText` words from glyph extents and the last font size. The last character therefore ends at its box edge and sets the vertical scale.

## PR #34 result

- **Real corpus:**
  - Repeats fall from 38 to 6. The 3 visible dash rules are out of scope; 3 forms p0 visible words are split by another span's invisible text.
  - PDFium word tokens rise by 81. Poppler loses 7: joins on historical and forms boxes that span two lines.
  - Reference words absent from text: PDFium 17 → 17, Poppler 0 → 0.
  - Native PDFium search finds fewer hits for 2 more tokens. Both are hyphenated line ends now joined as hyphenation (`accipie￾mus`).
- **Visible output:** 0 changed pixels in PDFium and Poppler, at 150 DPI, on all 33 real pages and all 27 synthetic pages (competitive 300/600, fresh, fresh2, FONT-01 test 0–2).
- **Synthetic text:** 0 repeats in both builds. PDFium tokens are identical; Poppler gains 5.
- **Bytes:** the real total goes from 8,572,386 to 8,499,526.

Files: `measure.py`, `diagnose.py`, `findable.py`, `render_identity.py`, `simulate.py` (an approximate PDFium line model, used only for design), `metrics-*.json`, `repeats.txt`, `pdf-hashes.txt`. PDFs are local only, under `local/copytext/`.
