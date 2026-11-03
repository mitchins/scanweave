# Glyph sharing

Glyph sharing is opt-in: `--glyph-sharing cover-2.0-ceiling-q3`. The default is `--glyph-sharing off`. It is available only with the ClearScan profile and requires PDFium; set `SCANWEAVE_PDFIUM_LIBRARY` to the native library path.

The cover planner accepts a relative fit error at most 2.0 times the member noise floor and an absolute fit error at most 0.08. A group requires at least 3 distinct default-emission design witnesses. Existing structural and owned-ink checks also apply. The converter deterministically falls back to the default output when sharing cannot safely or economically improve the document.

On the P2″ qualification population, measured costs and savings were:

| Metric | Default | q3 |
|---|---:|---:|
| Font bytes | 932,887 | 913,302 |
| PDF bytes | 5,026,084 | 5,009,868 |
| Runtime | 396 s | 620 s (1.57×) |
| Peak RSS | 442 MB | 441 MB |

The real financial document saved about 64 KB of font with a net 322 outlines retired; the mixed document saved about 7.9 KB.

q3 passed all preregistered P2″ criteria, with zero detected new material defects among the 89 blinded admitted substitutions.

The blind positive controls did not demonstrate sensitivity on the P2″ population. The numerical non-inferiority margins were relatively permissive. Overall pristine accuracy was at parity with default, not superior. Documents without enough repeated glyph evidence may see little or no benefit. q3 is opt-in and ordinary ClearScan is unchanged. There is no claim of zero-risk typography or universal visual improvement.

Research evidence: [`FONT_04_REVIEW_P2PP.md`](https://github.com/mitchins/scanweave/blob/research/font04-document-fonts/FONT_04_REVIEW_P2PP.md) and [`FONT_04_REVIEW_R2C.md`](https://github.com/mitchins/scanweave/blob/research/font04-document-fonts/FONT_04_REVIEW_R2C.md) on `research/font04-document-fonts`.
