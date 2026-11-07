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

The real financial document saved about 64 KB of font with a net 322 outlines retired; the mixed document saved about 7.9 KB. Cost is larger on real documents: in a paired serial run the 13-page financial document took 14:02 against 7:31 for default (1.86×), with peak RSS 1.76 GB against 1.47 GB (+20%); the mixed document took 3:18 against 1:46 (1.86×). A missing or unusable PDFium library is reported before rasterization, OCR, and planning, so a q3 run fails fast (exit 2, no output written).

q3 passed all preregistered P2″ criteria, with zero detected new material defects among the 89 blinded admitted substitutions.

The blind positive controls did not demonstrate sensitivity on the P2″ population. The numerical non-inferiority margins were relatively permissive. Overall pristine accuracy was at parity with default, not superior. Documents without enough repeated glyph evidence may see little or no benefit. q3 is opt-in and ordinary ClearScan is unchanged. There is no claim of zero-risk typography or universal visual improvement.

Research evidence: [`FONT_04_REVIEW_P2PP.md`](https://github.com/mitchins/scanweave/blob/research/font04-document-fonts/FONT_04_REVIEW_P2PP.md) and [`FONT_04_REVIEW_R2C.md`](https://github.com/mitchins/scanweave/blob/research/font04-document-fonts/FONT_04_REVIEW_R2C.md) on `research/font04-document-fonts`.

## Safety corrections after qualification

Review after P2″ qualification found two defects: the owned-ink crop was correct only at 300 DPI, and the witness quorum was not rechecked after owned-ink exceptions. The frozen legacy crop check remains as a qualification-compatibility veto, while a corrected DPI-aware check adds protection; a substitution is rejected if either check reports an exception. The final three-distinct-design quorum is applied after both checks. These corrections are strictly subtractive: they can only reject substitutions accepted by the qualified build. The P2″ qualification applies to the original build; the corrected build is verified as a subset of it, not re-qualified.

Subset verification (independent reviewer, 41 documents: P2, P2′ and P2″ at 200/300/600 DPI, FONT-01, and the five real development documents):

- 0 added substitutions, groups or canonicals; 0 changed canonical shapes or placements. 108 of 1,853 qualified substitutions are removed: 0 at 200 DPI, 14 at 300 DPI, 94 at 600 DPI.
- 0 final groups with fewer than three distinct design witnesses (the qualified build emitted 11).
- Every pixel of every changed output equals either the qualified output or default ClearScan. Outputs whose substitution set did not change are byte-identical, and default and faithful outputs are byte-identical to `main`.
- Real documents: the financial document drops 7 of 1,336 substitutions (`final_witness_quorum` and `final_canonical_rejected`); mixed, forms, receipts and historical are unchanged.
- The second crop check adds about 0.9 s to the owned-ink stage on the 13-page financial document (1.15 s → 2.01 s). Total wall time and peak RSS changed within run-to-run noise.
- At 600 DPI the legacy crop window falls outside its own render for most glyphs. Under the combined rule this counts as an exception, so most 600 DPI substitutions are now rejected. This is conservative by design.
