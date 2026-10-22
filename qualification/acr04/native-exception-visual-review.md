# ACR-04 independent native-exception JPEG review

## Scope

Read-only inspection of actual complete derivative PDFs in `native444-95/` and
`native444-90/`, compared with source, frozen Adobe XI and ACR-01. Fixed pages were
financial indices 0, 4 and 10, and receipt index 2. Both PDFium and Poppler rendered
at 300 DPI using the existing fixed physical-coordinate helper. Page overviews and
native-resolution body/number windows were inspected; no glyph registration or
candidate-specific fitting was used. No prototype/product files or holdout were
modified/accessed.

Local views: `native-review/*-{pdfium,poppler}-page.png`, corresponding `r*` detail
sheets, and `receipt2-numerics-pdfium.png`. The temporary read-only rendering script
is `/tmp/acr04-native-review.py`.

Financial windows: `[.10,.24,.48,.39]`, `[.76,.63,.97,.92]`,
`[.15,.40,.55,.54]`. Receipt windows: `[.10,.20,.65,.40]`,
`[.30,.45,.85,.65]`, `[.10,.65,.75,.85]`; supplemental source-selected numeric
window `[.60,.35,.92,.72]` includes the complete amount column and change minus.
Some initial receipt windows show only part of their named lines; the supplemental
view avoids inferring complete number preservation from a truncated crop.

## Findings

**Both Q95 and Q90 are visually defensible on these selected cases under the
permitted lossy ClearScan contract.** Q90 did not exhibit a material readability
regression relative to Q95 or ACR-01 in the inspected regions.

- Financial thin serifs, commas, initials, small marks and the financial digit
  column including 185, 5, 1, 7 and 4 remain readable. Existing rough/damaged
  impressions are not newly claimed repaired.
- Receipt 92,000 / 80,000 / 60,000 / 42,000, subtotal and total 334,000, cash 350,000
  and change -16,000 retain their identities, separators and minus. Thin rules
  and low-contrast surrounding printing remain visible.
- No material new rectangular seam, duplicated edge or halo was identified at the
  inspected retained-patch surroundings. Minor JPEG edge-tone/grain differences
  are permitted and should remain disclosed.
- The block-like bold total glyph rendering visible in ACR-01 persists in the
  candidates; it is not evidence that JPEG newly changed the font program or that
  this raster encoding repaired a preexisting typography defect.
- No conspicuous new colour/posterization change comparable to the rejected palette
  experiments was found. This does not certify every source colour or faint mark
  in unknown documents.

## Decision and limits

Reported complete financial PDFs are 9,018,954 B baseline, 7,887,505 B Q95 and
6,996,071 B Q90. Receipt collection totals are 2,208,177 B baseline, 2,111,377 B
Q95 and 2,094,152 B Q90. These are actual whole-document quantities, not separate
JPEG-file or per-pixel estimates.

Because both pass this selected-case visual gate and no meaningful advantage of
Q95 was established here, **Q90 is a credible candidate for the next already
scoped mechanical/product qualification**. This is not automatic production
approval. Exact placement, ownership, font/Unicode/operator invariants, selected
resource eligibility, deterministic size selection, lossless fallback and faithful
independence require separate code and mechanical evidence. The visual review
cannot prove universal faint-mark preservation or equivalent OCR recognition.
No new raster model, mask, glyph algorithm or extra codec setting is requested.
