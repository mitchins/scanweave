# Checkpoint A — causal ladder

Classes: `e1a8.!odynstrcul`. Both native renderers; all three P1 splits remain development data.

| Population | Renderer | Targets | A0 | A1 | A4 | F-self | F-medoid |
|---|---|---:|---:|---:|---:|---:|---:|
| train | pdfium | 935 | 0.15106 | 0.12097 | 0.14779 | 0.09332 | 0.15448 |
| train | poppler | 935 | 0.17325 | 0.16975 | 0.12199 | 0.16215 | 0.12575 |
| validation | pdfium | 813 | 0.14007 | 0.12394 | 0.14632 | 0.09129 | 0.15216 |
| validation | poppler | 813 | 0.17209 | 0.19106 | 0.12633 | 0.17558 | 0.12664 |
| test | pdfium | 934 | 0.14524 | 0.12044 | 0.14649 | 0.08809 | 0.15013 |
| test | poppler | 934 | 0.16713 | 0.17066 | 0.12113 | 0.16088 | 0.11918 |
| financial | pdfium | 291 | 0.06991 | 0.11166 | 0.10426 | 0.03338 | 0.13910 |
| financial | poppler | 291 | 0.15533 | 0.17682 | 0.11506 | 0.10804 | 0.13546 |

Error is coverage squared error normalized by union ink, measured against pristine in P1 and source-owned coverage in P3. Each arm uses the same targets. The JSON includes per-class mean/p95/worst-ten, DPI/damage strata, reverse effects and explanatory shares. Shares are not additive.

No mechanism is production-qualified: independent blinded financial review is pending and renderer directions differ. No product branch or merge is justified by a ≥50% explanatory share alone.

The independent reviewer must assess renderer disagreement, the shape metric, rejected candidates, and source-frame accuracy. This checkpoint does not authorize a product promotion or B2.
