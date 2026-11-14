# Pilot track matrix

| Row | Path | Track | OCR |
|---|---|---|---|
| sw-E | Stock ScanWeave PDF import, default clearscan | E | Internal Tesseract |
| sw-M | Same PDF import, strict Tesseract shim | M | Frozen psm 3 and retry psm 6 hOCR |
| sw-build | `build --ocr --profile clearscan` | M diagnostic only; never ranked | Selected frozen hOCR |
| ocrmypdf-E | OCRmyPDF `--output-type pdf` | E | Internal Tesseract |
| mrc-M | Archive `recode_pdf`, CCITT, one thread | M | Externally supplied selected frozen hOCR; not an independent OCR engine |
| adobe-E | Existing Acrobat XI 11.0.20 output | E | Adobe default OCR language, unmatched; Fraktur unsupported |
| src | Image-only lossless PDF | Reference | None |

The PDF-import and `build` paths are distinct and must not be assumed equivalent. The former uses source-image handling and visual glyph dictionary in its clearscan path; the latter invokes single-page conversion without source images and defaults to faithful unless overridden. Adobe timing includes GUI waits and startup and is not comparable to CLI timings.
