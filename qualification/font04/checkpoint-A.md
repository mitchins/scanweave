# Checkpoint A — causal ladder

Classes: `e1a8.!odynstrcul`. Analytic primary reference plus both native renderer screens; all three P1 splits remain development data.

| Population | Renderer | Targets | A0 | A1 | A4 | F-self | F-medoid |
|---|---|---:|---:|---:|---:|---:|---:|
| train | analytic | 935 | 0.15209 | 0.12125 | 0.09066 | 0.09320 | 0.09781 |
| train | pdfium | 935 | 0.15106 | 0.12097 | 0.09054 | 0.09302 | 0.09768 |
| train | poppler | 935 | 0.17325 | 0.16975 | 0.16099 | 0.15047 | 0.15841 |
| validation | analytic | 813 | 0.14072 | 0.12444 | 0.08913 | 0.09263 | 0.09392 |
| validation | pdfium | 813 | 0.14007 | 0.12394 | 0.08970 | 0.09306 | 0.09457 |
| validation | poppler | 813 | 0.17209 | 0.19106 | 0.17254 | 0.16250 | 0.16720 |
| test | analytic | 934 | 0.14610 | 0.12078 | 0.08556 | 0.08808 | 0.08794 |
| test | pdfium | 934 | 0.14524 | 0.12044 | 0.08559 | 0.08796 | 0.08772 |
| test | poppler | 934 | 0.16713 | 0.17066 | 0.15770 | 0.14759 | 0.15179 |
| financial | analytic | 291 | 0.06530 | 0.09613 | 0.03898 | 0.03867 | 0.06222 |
| financial | pdfium | 291 | 0.06991 | 0.11166 | 0.03631 | 0.03893 | 0.06358 |
| financial | poppler | 291 | 0.15533 | 0.17682 | 0.12477 | 0.10675 | 0.13199 |

Error is coverage squared error normalized by union ink, measured against pristine in P1 and source-owned coverage in P3. Each arm uses the same targets. The JSON includes per-class mean/p95/worst-ten, DPI/damage strata, reverse effects and explanatory shares. Shares are not additive.

Corrected independent blinded financial review is pending. No product promotion is qualified by these causal measurements alone.

The independent reviewer must assess renderer disagreement, the shape metric, rejected candidates, and source-frame accuracy. This checkpoint does not authorize a product promotion or B2.
