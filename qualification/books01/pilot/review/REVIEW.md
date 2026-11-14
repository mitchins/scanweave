# BOOKS-01 Phase 1: Claude's independent review

Reviewer: Claude. Implementation by Codex (`219ce4b`, `b2fa741`). The adjudication in `adjudication.json` (sha256 `a86c55d3…5d8e`) was recorded **before** the blind key was opened, then joined.

## Verified
- **Source PDFs.** Spot checks on aventinus 0008 and benner 0013: decoded Flate samples equal the TIFF, and the page size equals px × 72 / 300.
- **Ground-truth alignment.** Overlays checked on arnold 0114 and trudy 12342014.
- **FineBooks WebP fallback** is the correct decision. The IA original-capture JP2s are uncropped, rotated, slightly skewed camera frames. Using them needs crop and deskew, which the spec forbids.
- **Path equivalence.** `sw-E` and `sw-M` produce byte-identical PDFs on all six pages. The matched-OCR shim runs the stock import path. `build --ocr` remains diagnostic only.
- **Adobe isolation.** Internet sockets were refused (logged); the prefix locale was restored to en-US. A repeat batch gave identical text and sizes within 1 byte.

## Blind adjudication (66 crops: 54 suspected + 12 controls)

**Status: AI-assessed, provisional (not human-adjudicated).** Per the owner's Phase 1 review, these verdicts are an AI assessment by Claude and need human confirmation (blinded panel, Phase 1b) before any count becomes a benchmark result. Zero visible differences in sampled ScanWeave/OCRmyPDF crops does not establish a defect-free converter.

| Detector | Crops | False positive | True positive | Other |
|---|---:|---:|---:|---|
| glyph_shape | 12 | 8 | 1 | 1 mixed, 2 minor |
| missing_ink | 12 | 8 | 1 | 1 mixed, 2 minor |
| spurious_ink | 12 | 7 | 2 | 1 mixed, 2 minor |
| illustration_colour | 6 | 0 | 4 (2 on text tiles, mis-scoped) | 2 minor |
| border_inversion | 12 | — | — | **no inversion in any output** |
| controls (random words) | 12 | — | 2 with a confirmed defect | 8 with visible differences |

**Provisionally assessed material defects (AI, pending human confirmation), after joining with the key:**
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

## Addendum after Phase 1b (`b7b3235`, `f222252`)
- **Geometry.** Global registration now precedes the pixel metrics. Adobe rotation is −0.50° to +0.82°. Adobe text SSIM went from 0.20–0.50 native to 0.76–0.81 aligned on the Quiver pages; the native and aligned scores are both reported.
- **MRC shift on 8967333.** Claude's "4 px" was one quantisation step of a 4×-downsampled phase correlation, not a measured shift. Codex's near-zero estimate is accepted.
- **Line-level OCR.** The earlier rise from frozen to extracted line CER was a grouping and parsing artefact. After the correction, the matched rows agree with frozen OCR within 0.0032 CER.
- **Detectors.** Calibration is in-sample (16 labelled crops for glyph/ink), and the full triage flags 21% of word boxes (2,504 of 12,030). The suspicion rate is too high to serve as a review queue at 36 pages. Precision outside the calibration sample is unknown.
- **Human panel.** Now one output per distinct converter (4), with fresh labels and a sealed key. Pixel-identical source-preserving outputs may still be recognisable.

## Addendum after Phase 1c (`3b7519a`)
- **Search audit accepted.** All 40 ScanWeave/MRC conditional-search misses are long-s query normalisation (the reading-form query against the diplomatic ſ in the text layer); PDFium finds the diplomatic form. No ScanWeave text-layer defect.
- **Queue coverage check (Claude, diagnostic only; not calibration).** For the four locations the human questioned, the best rank of the concerned output on its page:

| Known location | Output | Rank by raw score | Rank by contrast against other outputs |
|---|---|---|---|
| 0018 | MRC | 58 of 432 | 39 |
| 0018 | Adobe | 48 of 432 | 31 |
| 0055 | Adobe | 17 of 336 | 46 |
| 0056 | Adobe | 8 of 336 | 5 |
| 0014 | MRC | 47 of 432 | 48 |

  - A source-identical output (OCRmyPDF) scores exactly 0 on all 3,978 boxes, so the scores carry no renderer noise.
  - For MRC and Adobe, many words on a page change to a similar degree, so no instance-level ranking with a cap of 10 per page will reliably surface specific known instances.
- **Implication.** The review question should be decided per page × output ("does this output show material damage anywhere on this page?") by stratified sampling: top-k by raw score plus random word crops per distinct output, plus all illustration and border candidates. Instance-level coverage is the wrong yardstick. This is a proposal for the owner and has not been implemented.
