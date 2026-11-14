# BOOKS-01 Phase 1: Claude's independent review

Reviewer: Claude. Implementation by Codex (`219ce4b`, `b2fa741`). The adjudication in `adjudication.json` (sha256 `a86c55d3…5d8e`) was recorded **before** the blind key was opened, then joined.

## Verified
- **Source PDFs.** Spot checks on aventinus 0008 and benner 0013: decoded Flate samples equal the TIFF, and the page size equals px × 72 / 300.
- **Ground-truth alignment.** Overlays checked on arnold 0114 and trudy 12342014.
- **FineBooks WebP fallback** is the correct decision. The IA original-capture JP2s are uncropped, rotated, slightly skewed camera frames. Using them needs crop and deskew, which the spec forbids.
- **Path equivalence.** `sw-E` and `sw-M` produce byte-identical PDFs on all six pages. The matched-OCR shim runs the stock import path. `build --ocr` remains diagnostic only.
- **Adobe isolation.** Internet sockets were refused (logged); the prefix locale was restored to en-US. A repeat batch gave identical text and sizes within 1 byte.

## Blind adjudication (66 crops: 54 suspected + 12 controls)

| Detector | Crops | False positive | True positive | Other |
|---|---:|---:|---:|---|
| glyph_shape | 12 | 8 | 1 | 1 mixed, 2 minor |
| missing_ink | 12 | 8 | 1 | 1 mixed, 2 minor |
| spurious_ink | 12 | 7 | 2 | 1 mixed, 2 minor |
| illustration_colour | 6 | 0 | 4 (2 on text tiles, mis-scoped) | 2 minor |
| border_inversion | 12 | — | — | **no inversion in any output** |
| controls (random words) | 12 | — | 2 with a confirmed defect | 8 with visible differences |

**Confirmed material defects, after joining with the key:**
- **Adobe XI (3):**
  - luther "was": flat glyphs, with the w broken into fragments;
  - 8967333 "OF": the O is broken into two arcs;
  - 8967333 "THE": the H crossbar and part of the E are replaced by paper.
  - Stroke thickening also appears on aventinus.
- **Archive MRC (9):**
  - luther "was": most strokes lost, reads like "n'a";
  - broken strokes in "ganz" and "grosses" (still readable);
  - woodcut hatching smeared with chroma noise;
  - hand colouring posterised;
  - chroma fringing and blotchy paper on Fraktur text.
- **ScanWeave (sw-E, sw-M, sw-build) and OCRmyPDF: none.** No panel from these rows showed a visible difference at 4×.

## Harness defects found (must fix before the 36-page run)
1. **Adobe deskews.** Adobe rotates the Quiver pages by −0.8° to +0.5° (phase correlation at 75 DPI), with no translation. Its pixel-aligned SSIM, ink recall and detector scores therefore mostly measure rotation. MRC has no global rotation (a 4 px shift on 8967333 only).
   - Fix: register each output to the source before the visual metrics, and report geometric change as its own column.
2. **Glyph and ink detectors.** 8 of the top 12 per detector are 2–10 px OCR noise boxes that saturate at 1.0; the controls found more real defects.
   - Fix: add a minimum box size; rank after registration; scope the illustration detector to GT graphic regions; recalibrate on the registered pilot.
3. **CER mixes reading order with recognition.** Trudy's frozen OCR has CER 0.55 but bag recall 0.64.
   - Fix: add a line-aligned CER, pairing GT and output lines by geometry, alongside the existing measures.
4. **Adobe's OCR is unmatched.** Acrobat ran with its existing default OCR language, and it has no Fraktur model. Its CER is "product as configured", not engine capability. Label it so in every table.
5. **FineBooks line-level coverage** is thin on 8967333 (3 proxies, 32 chars). Report it, and don't rank line F1 on it.

## Observation (not a ranking)
- **Quiver pages:** ScanWeave's output is 97–98% one DCT background, with 0.5–3 KB of fonts. It barely vectorises historical Fraktur, which explains why its fidelity matches the source.
- **Trudy:** 246 KB of its 555 KB is vector fonts.
- **Size comparison:** MRC is 3–5× smaller on every page, but with confirmed visible losses. Adobe is 10–30% smaller on the Quiver pages, with rotation and confirmed glyph defects.
