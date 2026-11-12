# HVC-41G independent disposition (Claude)

**Disposition: standalone historical-vector representation feasible; not compression-positive.** This is research only, not a product qualification. #41 stays open. The 38 visible glyphs are path-only Form XObject graphics, **not embedded-font glyphs**; the unchanged invisible OCR layer holds all text semantics.

The frozen PDF reviewed was `local/hvc41g/historical-frozen.pdf`, sha256 `e408daab686fd47f05451627620a79dc8770e5c299654eba4f76bb5454ef7a4b` (Codex evidence `3e6a3ef`, code `fb7c8c0`).

## Checks Claude re-ran independently
- **Hash:** the PDF hash matches the freeze record.
- **Poppler `pdftotext` (plain, `-layout` and `-raw`):** byte-identical to #39 on all 5 pages.
- **MuPDF extraction:** `get_text()` and `rawdict` are identical to #39 on all 5 pages.
- **p1 original content stream:** byte-identical (40,446 bytes).
- **New overlay operators:**
  - patch stream: `q Q rg m l h f*`;
  - invocation stream: `q Do Q`;
  - `/ResearchPaths` Form: `q Q cm rg m l c h f`, with empty Resources.
  - There are no text operators and no new font; the page Font resources are unchanged (`/F1` only).

## Visual review
All 38 glyphs were reviewed at 300 DPI in PDFium, Splash-AA, Cairo and MuPDF, at 4× nearest-neighbour scale, plus contrast-stretched (L 170–235) views of #39 and the candidate. Context strips were reviewed at 300 DPI and at 96 DPI reading size.
- **Renderer consistency:** acceptable. None of the four renderers shows jagged contours, including Splash, which was HVC-41E's defect.
- **Character shape:** all 38 match the frozen review. No counter closes, and no doubled strokes appear.
- **Halo:** none visible at reading size or at 4× natural contrast. In the contrast-stretched views, the pale rim around replaced glyphs looks the same as the rim the #39 background already has around unchanged neighbouring glyphs. Codex's measured boundary-to-ring ΔL (PDFium 300 DPI mean 6.79, max 10.30; other engines 14–21, which includes antialiased edge pixels) is a residual measurement, **not** an eliminated difference.
- **Streak at 243 `t`:** the light diagonal streak by the adjacent `f` is present in #39. The difference map is confined to the `t`, so it was not introduced.
- **Remaining appearance limitation:** glyph tone is flat. Replaced glyphs lack the scan's stroke texture and are browner or flatter than their dark neighbours at enlargement. 207 `a` and 208 `l` (`alſs`) read slightly heavier than their neighbours at 300 DPI. These follow the frozen HVC-41E colour decisions and are not halos.

## Beyond-band exceptions (judged)
There are none at 300 DPI in any renderer. At 96 DPI:

| Renderer | Pixels (glyph, ΔL) |
|---|---|
| Splash | (110, −1.0), (110, −2.4), (207, −6.9), (207, −3.0) |
| Cairo | (110, −4.6), (207, +1.0) |
| PDFium | (110, −6.5) |
| MuPDF | (110, −4.8), (207, −4.2), (207, −2.0) |

All are |ΔL| ≤ 6.9 and adjacent to the band of the glyph's own owned footprint. At 96 DPI one render pixel covers about 3 source pixels, so antialiasing coverage of an owned-edge source pixel can spill across one more render pixel. **Judged acceptable:** imperceptible, with no foreign ink involved. Source-space ownership violations: 0. Foreign-ink deletion: 0.

## Cost
- Complete historical PDF: 2,319,452 bytes, +72,062 against #39. This is 59,174 vector Form, 12,589 patch, 29 invocation and 270 structural bytes.
- The append-only overlay cannot deliver net source-raster compression.
