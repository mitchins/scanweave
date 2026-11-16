# BOOKS-01 Phase 2: Claude's spot checks

These are agent observations, not human-confirmed.

## Adobe runs
- Adobe ran network-isolated with the en-US locale. 30 of 36 pages were converted.
- 6 pages failed in GUI automation:
  - failed on both the first pass and the retry: silesius 0423, meyfart 0022, arnold 0115, blumenbach 0047, 8966753, 9684341;
  - the four retries that failed in about 52 s ran while the root filesystem was full.
- The prefix locale is still en-US.

## Visual spot checks
Aligned PDFium renders at source DPI.
- **Fraktur text and woodcuts** (aventinus 0006, luther 0011, euler 0025):
  - ScanWeave is indistinguishable from the source at 2×;
  - MRC shows blotchy paper, dark specks and halos;
  - Adobe has heavier, darker strokes.
- **Colour plates:**
  - 8967062: ScanWeave fragments the faint grey numerals ("613", "628") and recolours them brown; MRC and Adobe keep them whole. **Suspected ScanWeave defect.**
  - 8967228: ScanWeave recolours the faint italic heading brown. MRC smooths the stipple texture, adds dark specks, and loses the faint "3." caption.
- **8966753:** ScanWeave matches the source visually, but the file is 1.47 MB (369-DPI 4:4:4 background, plus 211 KB of foreground images and 214 KB of fonts), 7.9× MRC and 9% of all ScanWeave bytes. This is a size outlier.
- **Clean French print** (12342014): all four converters are visually close.

## Byte attribution (ScanWeave)
- Background JPEG is 88% of all bytes, and 96% on Quiver pages.
- Fonts are 7%, and foreground images 2%.
- On Quiver pages the background is a 200-DPI, 4:2:0 JPEG of 200–920 KB, and fonts are 0.5–3 KB.

Report artifact: the BOOKS-01 Phase 2 results page (private, owner-shared).
