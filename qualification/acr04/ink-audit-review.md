# ACR-04 independent retained-ink audit

## Method and bounds

Read-only Phase A / Hypothesis B inspection of eight fixed pages: financial
indices 0, 6 and 10; historical 1, 2 and 4; receipts 5; mixed 1 (Linn).
Existing reviewed ablation helpers generated font-only and non-font derivatives
of the actual ACR-01 collection PDFs and frozen Adobe PDFs. Original documents
were not overwritten. The fixed physical rendering contract preserves MediaBox
canvas and original CropBox clipping. Both PDFium and Poppler were rendered at
300 DPI. Local sheets retain nearby source content, not independently normalized
glyphs. No OCR, ownership, font or segmentation changes were made; no holdout was
accessed. Paintable Unicode counts were not used as equivalent coverage.

Evidence: `local/ink-audit/<group>-<index>/` contains page and fixed-region sheets,
actual derivative PDFs and `regions.json` source coordinates. Temporary read-only
render script: `/tmp/acr04-ink-audit.py`. These are selected regions, not an audit
of every source mark.

## Exact resource examples

Numbers below count each image object once within the selected page; they do not
allocate compressed bytes between text and paper inside an image. A full-page
placement is not necessarily a native-resolution page image.

| ACR-01 page | Image objects referenced | Exact encoded image bytes | Representative object |
|---|---:|---:|---|
| financial 0 | 214 | 609,539 | 35 0: 453x664, 93,675 B reduced full-page paper; 36 0: 1536x104, 47,406 B native strip |
| financial 6 | 1 | 334,130 | 975 0: 1813x2655 full-page native raster |
| financial 10 | 255 | 630,995 | 1288 0: 453x664, 91,810 B reduced paper; 1309 0: 1504x104, 38,597 B native strip |
| historical 1 | 1 | 849,913 | 20 0: 1116x1835 full-page raster |
| historical 2 | 1 | 531,744 | 21 0: 1676x2287 full-page raster |
| historical 4 | 1 | 1,205,699 | 23 0: 1757x2440 full-page raster |
| receipts 5 | 1 | 766,574 | 55 0: 2305x4096 full-page photographic receipt |
| mixed 1 / Linn | 454 | 253,967 | 32 0: 1330x434, 31,059 B native patch; 14 0: 638x826, 8,763 B reduced paper |

These bindings come from the current ACR-01 `local/inventory.json`, not the older
pre-ACR-01 resource sizes. Representative Adobe contrasts, from the frozen PDF
inventory: financial 0 object 277 0 is about 150 DPI / 4,189 B, accompanied by
300-DPI objects; financial 6 object 80 0 is 300 DPI / 48,067 B; financial 10 object
133 0 is about 150 DPI / 4,944 B with native patches. Historical 2 uses 31 0
(150 DPI / 18,874 B) and 32 0 (300 DPI / 69,695 B). Linn's only indirect raster
is 13 0, 150 DPI / 569 B. Inline stencils/content-stream costs are separate and
must not be inferred absent merely from this indirect-image table.

## What the actual isolated layers show

- **Financial 0**, upper body `[.10,.24,.48,.39]`: ACR-01 visibly fonts the B in
  Eben B Moulton, A Brown, and John H, while substantial adjacent names/words
  remain native raster. Non-font content is complementary rather than a second
  complete dark copy of the vector text. Faint scattered residuals exist around
  some cleaned positions. Adobe fonts nearly the entire inspected lines.
- **Financial 6**, same window: ACR-01 fonts Jewett, C, N and selected other text,
  retaining Chas, Edward, Brooks and Martel as raster. Faint glyph-shaped traces
  remain at some replaced positions, but dark source cores are largely absent.
  Adobe fonts nearly all inspected print and leaves the rule/marks in non-font
  content. ACR-01 still needs a whole-page resource for its substantial fallback.
- **Financial 10**, numeric column `[.76,.63,.97,.92]`: ACR-01 vectors Town Clerk,
  several 1s, 7 and 204, but retains 185, 5 and 4 in raster. The rule remains
  raster. Adobe fonts all inspected digits while retaining its rule. Tiny marks
  around replaced digits are not evidence that the whole source glyph remains.
- **Historical 1**, body `[.15,.37,.55,.48]` and ornament `[.05,.24,.40,.43]`:
  ACR-01's selected body font-only view is blank; actual printed body remains in
  raster. Adobe font-only view carries the body and its non-font view removes it.
- **Historical 2**, body `[.13,.18,.71,.225]` and punctuation `[.30,.30,.80,.35]`:
  ACR-01 body is raster. Adobe font-only view carries the visible blackletter;
  its non-font layer retains faint text-shaped patterns. Bleed-through versus
  obsolete ink cannot be determined for every such pattern from these images.
- **Historical 4**, body `[.09,.25,.50,.39]` and seal `[.37,.74,.64,.91]`:
  ACR-01 font-only view contains sparse pale marks, not readable reconstructed
  body text. Its printed body and red seal remain raster. Adobe reconstructs
  substantial body print while retaining seal/background content. Do not call
  pale ownership marks validated text coverage.
- **Receipt 5**, words `[.19,.32,.58,.42]` and amounts `[.64,.32,.81,.42]`:
  amounts remain visible in the non-font raster for both converters. ACR-01
  font-only view is blank in the inspected amount crop. Adobe fonts a few nearby
  dot-like features, not the amount column itself. The page image also contains
  photographed surroundings and paper, not only unsupported text.
- **Linn**, body `[.11,.35,.55,.52]` and right column `[.56,.64,.90,.79]`:
  ACR-01 vectors some words (Sequence, selected short words and phrases), leaving
  many complementary words in native patches. Adobe font-only view carries
  nearly the entire inspected body; its non-font view is essentially blank there.
  Erasing ACR-01 patches simply because they sit near vectors would remove valid
  unsupported words.

Selected particularly informative visuals are `financial-00/pdfium-r0-ACR01.png`,
`financial-06/pdfium-r0-{ACR01,Adobe}.png`,
`financial-10/poppler-r1-{ACR01,Adobe}.png`,
`historical-01/pdfium-r1-{ACR01,Adobe}.png`,
`historical-04/pdfium-r0-{ACR01,Adobe}.png`,
`receipts-05/pdfium-r1-{ACR01,Adobe}.png`, and
`mixed-01/pdfium-r0-{ACR01,Adobe}.png`, relative to `local/ink-audit/`.

## Hypothesis B conclusion

**No low-risk cleanup defect capable of explaining the dominant raster cost was
established.** Small residual fringes/ghosts around some emitted vectors are
visible, especially financial text. Their exact ownership and independent byte
cost are unmeasured. They are not evidence that dark complete source glyphs
universally remain underneath vector replacements.

The larger demonstrated difference is unsupported/unconverted printed text:
whole historical/receipt body lines and many financial/Linn words remain raster
in ACR-01 while Adobe often paints those as fonts. Paper/texture and meaningful
non-text content are jointly encoded alongside that print. These observations
explain why removing raster wholesale would be unsafe; they do not authorize
changing OCR, font acceptance, or ownership in this mission.

No semantic byte apportionment, equivalent-coverage claim, safe-erasure claim or
new production correction follows from this read-only audit. Codec probes can
be evaluated independently under the current permitted lossy-quality contract;
ink cleanup should not be credited with savings it has not actually demonstrated.
