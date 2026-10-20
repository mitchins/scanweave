# ClearScan residual background reconstruction

**Review the [completed 600 DPI PDF](qualification/clearscan_background/600/final.pdf), [300 DPI PDF](qualification/clearscan_background/300/final.pdf), and [1600% paper/vector/final comparison](qualification/clearscan_background/300/background-context-1600pct.png).** The same coordinates are shown at [100%](qualification/clearscan_background/300/background-context-100pct.png) and [800%](qualification/clearscan_background/300/background-context-800pct.png).

The ordinary `--profile clearscan` now reconstructs paper outside source fringes, removes additional donor-supported weak impressions, and serializes a smaller paper layer with native exceptions. Faithful PDF behaviour, OCR, canonical dictionary, font programs and text placement remain unchanged. There is no new public mode.

## Revision and reproducibility

Actual starting HEAD was `9cce714c5236abf026cb24ac47fe5c72d7fed418`, with no tracked modifications. This is the contour evidence commit after the requested `ac977ff8f60ce965f64353cff0affb818e4d2a01`; the conversion implementation and frozen baseline PDFs are the accepted contour baseline. Untracked research, prior outputs and Wine automation were preserved. [Starting state](qualification/clearscan_background/starting-state.json.gz).

Implementation commits: `a79dc87`, `ca9a5e8`, `732ce82`, `5042c03`. The last is the frozen runtime source for these outputs. [Run manifest](qualification/clearscan_background/run-manifest.json) binds full revisions, Rust source hashes, unchanged scan/OCR inputs, separate evaluator oracles, PDF hashes and tool versions. [Commands](qualification/clearscan_background/commands.json) and `/usr/bin/time -v` records preserve execution details.

Both documents have eight pages, 552 non-space instances, identical 432×216 pt pages, and genuine 1800×900 / 3600×1800 scans. Acrobat XI 11.0.20 / Wine 9.0 outputs are the frozen same-input references; no Adobe program or font asset enters inference.

## Completed document scorecard

Glyphs use exact-position, fixed-size comparisons against pristine typography: no per-candidate bounding-box normalization. Poppler uses integer physical DPI; PDFium uses `nextafter(dpi/72,0)` to avoid canvas ceil drift. Source glyph IoU is 0.94516 / 0.97807. The existing Adobe renderer disagreement is retained rather than averaged away.

| Metric | Baseline | New | Adobe XI |
|---|---:|---:|---:|
| 300: PDF bytes | 711,770 | 257,972 | 37,100 |
| 300: Raster bytes | 615,829 | 118,980 | 17,411 |
| 300: Font bytes | 25,340 | 25,340 | 5,963 |
| 300: Vector occurrences | 531 | 531 | 544 |
| 300: Distinct painted outlines | 52 | 52 | 27 |
| 300: Pristine glyph IoU, pdfium | 0.95633 | 0.95669 | 0.90255 |
| 300: Local ghost contrast, pdfium | 3.50607 | 0.43783 | 0.36836 |
| 300: Paper MAE, pdfium | 2.43279 | 0.76130 | 1.23394 |
| 300: Pristine glyph IoU, poppler | 0.94994 | 0.94973 | 0.75066 |
| 300: Local ghost contrast, poppler | 3.60217 | 0.42379 | 0.36827 |
| 300: Paper MAE, poppler | 2.50292 | 0.77556 | 1.23329 |
| 600: PDF bytes | 1,308,145 | 326,692 | 50,779 |
| 600: Raster bytes | 1,158,885 | 218,200 | 30,036 |
| 600: Font bytes | 32,536 | 32,536 | 5,880 |
| 600: Vector occurrences | 517 | 517 | 544 |
| 600: Distinct painted outlines | 57 | 57 | 21 |
| 600: Pristine glyph IoU, pdfium | 0.96772 | 0.96827 | 0.94155 |
| 600: Local ghost contrast, pdfium | 2.38880 | 0.28922 | 0.23846 |
| 600: Paper MAE, pdfium | 1.35844 | 0.67842 | 1.11964 |
| 600: Pristine glyph IoU, poppler | 0.96178 | 0.96245 | 0.88319 |
| 600: Local ghost contrast, poppler | 2.36897 | 0.28922 | 0.23846 |
| 600: Paper MAE, poppler | 1.55814 | 0.67842 | 1.11964 |

Ghost contrast is a gray-level measurement over **common vectorized ASCII** on page 0, after subtracting each glyph's surrounding-paper residual median. It measures text-shaped contrast, rather than treating a different paper tone as ghost ink. Kana is excluded from this comparator because Adobe legitimately retains it as raster. Paper MAE uses the same common footprint against paired no-text paper. Raw all-owned measurements, including kana, remain in [background-metrics.json](qualification/clearscan_background/background-metrics.json). These populations differ from the 552-instance glyph evaluation and must not be combined into an additive error budget.

PDF bytes fell **63.8% / 75.0%**; raster bytes fell **80.7% / 81.2%**. Local PDFium ghost contrast fell **87.5% / 87.9%**. The new documents remain 6.95× / 6.43× Adobe's size. Geometry changes in final IoU are small and renderer-dependent; they are composition effects, **not improved outlines**.

## A — What the oracle established

The generator did not persist a separate no-text paper layer. `oracle.py` replays the original random draws, deposition, texture, fading and scanner blur; it asserts that the regenerated **original scan is pixel-identical** before constructing the paired no-text surface. Genuine degraded artwork remains. The same font, placements and Unicode are copied into all arms. A1 keeps the baseline native resource footprints and lossless grayscale Flate level 6; unvectorized text remains in those native crops. This is not a blank white counterfactual.

| Page-0 arm | PDF bytes | Raster bytes | Raw ink-band contrast | Paper MAE |
|---|---:|---:|---:|---:|
| A0 | 136,141 | 116,060 | 4.096 | 2.583 |
| A1-native | 518,067 | 497,976 | 0.007 | 0.011 |
| A1 | 131,501 | 111,412 | 0.546 | 0.755 |
| A2 | 56,044 | 33,004 | 1.060 | 0.999 |

A0 is the frozen current page; A1-native retains the actual high-resolution paper noise; A1 is its 150 DPI representation; A2 is the final ordinary converter. All three use the same vector program and text geometry. The native oracle is expensive because noise remains. Cleaning alone at the same reduced representation saves only **4,640 B (3.4%)** of this page's PDF, below the mission's 10% branch. Therefore the substantial byte opportunity is representation, not sophisticated texture synthesis. A2 saves **80,097 B** over A0 and 83,056 raster bytes. The oracle does establish a useful visual cleanup opportunity: most of the initial source-shaped darkness is absent from actual paired paper.

The oracle comparison is one-page synthetic evidence, not a universal inpainting guarantee. Its font/oracle data is used only by the evaluator.

## B — Integrated paper reconstruction

The old local median could sample unresolved fringes near the same ink it was filling. The new bounded estimate excludes vector ink, its surrounding edge band, all non-vector/artwork masks and caller-protected regions before taking a per-channel paper median. The neighbourhood is 8 source pixels at 300 DPI and 12 at 600. Protected content is excluded over the entire sampling radius. Aged/coloured paper therefore supplies its own colour; it is not thresholded to white. The pre-existing page-paper fallback remains for a neighbourhood with no usable samples; strong local illumination discontinuities remain a limitation outside these tested pages.

For accepted canonical occurrences, an independent donor's grayscale halo is registered within ±1 source pixel, using only owned source-mask samples. Bilinear coverage models edge phase; a half-pixel envelope requires support at three donor sampling positions. These are **three samples of one independent donor**, not three independent witnesses. Weak dropout pixels inside a strongly supported donor stroke also belong to superseded printing. Local-only glyphs without an independent donor retain the conservative fringe path.

A first permissive self-halo rule was rejected after review: an unknown mark could validate its own deletion. It is absent from the final implementation. A crossing-rule test then exposed real losses (20 / 90 samples outside the vector). Coherent weak horizontal/vertical rules are now protected independently of segmentation: at least eight physical 300-DPI pixels of ridge support, at most four pixels of weak non-ridge gap, with dark source cores allowed to bridge. Their weak samples are stored in padded native strips from the **cleaned** source. This prevents coalescing from repainting original vector-owned cores.

A genuinely faint rule can itself be claimed by a binary glyph mask. The rule classification deliberately takes precedence in that ambiguous weak band; excluding such pixels reproduced two lost rule samples at 600 DPI. This can conservatively retain a faint typographic stroke that resembles a rule. It is not a claim that every gray pixel beneath a glyph has disappeared. The measured synthetic audit still finds **zero retained dark cores and zero dark raster/vector double paint** at both DPIs. Superseded source-mask pixels are 126,838 / 518,716; additional bright samples suppressed are 81,865 / 275,068.

## C — Compact paper and accountable native content

The existing 150 DPI cleaned layer is tested against a 75 DPI candidate. Exposed sample differences above three channel levels receive native cleaned-source exceptions; candidate mean error must be ≤0.5 and exception area ≤5%. Existing opaque native interiors are excluded, while their boundaries remain tested. Exceptions use four reduced samples per tile (8 / 16 source pixels), avoiding the measured 32px inflation around sparse errors. If gates fail, 150 DPI remains. The existing original-source residual-detail pass still runs afterward. All eight matched pages select 450×225 paper images.

This bound is against the previous **150 DPI samples**, not the original scan or final renderer. Existing bounded JPEG, lossless grayscale/native encoding and exact resource reuse remain active. No new codec or general MRC system was added. A coherent rule is retained natively even if OCR missed it; an isolated unknown mark already lost by the older 150 DPI representation is not magically recovered by this change.

| Document / arm | Raster | Font | Content | Other streams | Overhead |
|---|---:|---:|---:|---:|---:|
| 300 / previous | 615,829 | 25,340 | 54,567 | 1,383 | 14,651 |
| 300 / final | 118,980 | 25,340 | 61,332 | 1,383 | 50,937 |
| 600 / previous | 1,158,885 | 32,536 | 62,816 | 1,431 | 52,477 |
| 600 / final | 218,200 | 32,536 | 56,233 | 1,431 | 18,292 |

Paper backgrounds alone fall from 583,698→46,532 B at 300 and 412,049→50,479 B at 600. At 300, remaining native resources comprise 18,249 B artwork/mixed, 11,364 B vector surroundings, 10,054 B fallback, 934 B mixed fallback/surroundings and 31,847 B other detail. At 600 they comprise 76,781 B artwork/mixed, 31,684 B vector surroundings, 53,954 B fallback, 1,298 B mixed and 4,004 B other detail. Labels describe whole encoded resources; a mixed rectangle also contains paper. We do not invent entropy-byte allocations for individual pixel meanings. Geometric vector overlap is not proof that every retained sample is obsolete ink. [Full inventory](qualification/clearscan_background/resources.json) includes dimensions, filters, resource references and actual bytes; per-image encoded/decoded hashes are in the renderer metrics.

The remaining Adobe gap is concrete: at 300, raster costs 101,569 B more, font 19,377 B more, content 59,785 B more and remaining streams/overhead 40,141 B more. At 600, the respective differences are 188,164, 26,656, 54,731 and 6,362 B. Fine native exceptions increase 300-DPI object/content overhead while reducing image bytes far more. Native fallback/artwork, conservative detail retention, TrueType payload and text/resource serialization remain costs; they are not all irreducible. This round does not start a CFF or MRC rewrite.

## D — One bounded contour refinement, rejected

The one extra candidate refit grayscale curves for canonical `8`, `0`, `g` at a 0.30-pixel tolerance. On 187 common accepted occurrences, **actual vector-only PDF** IoU changed 0.96339→0.95677 in PDFium and 0.96191→0.95778 in Poppler. PDFium family means regressed for all three; 15 individual cases improved, which does not justify the broader regression. Existing outlines were retained. [Paired measurements](qualification/clearscan_background/contour-trial.json) and the rejected patch/PDF preserve the negative result.

The final 531 / 517 vector occurrences include 511 / 502 canonical replacements using 37 / 43 accepted prototype identities. The embedded font programs and all text/placement operations are hash-identical to baseline. Actual painted outline count remains 52 / 57, with continued cross-page sharing. Unsupported text remains raster.

## Faint lines, renderers and genuine documents

The targeted controls contain 330 / 1,306 added faint-rule pixels, including 41 / 192 in the source-mask fringe. **All are stored natively with unchanged samples; none is erased.** Stream exactness is not rendered exactness: a whole-page raster control and the native-background/final controls isolate attenuation from patch sampling. The attenuation is already present without vector text; adding the unchanged font changes these mean errors by at most 0.004 gray levels. Whole-page source controls give PDFium MAE 0 / 0 and Poppler 1.29 / 0.48; native-background controls give PDFium 4.67 / 2.18 and Poppler 4.12 / 2.16 at 300 / 600 DPI. Two samples exceed luma 252 in each native-background and final Poppler control; the source-raster Poppler control has none. None exceeds that value in PDFium. Both renderers' means, maxima, lightening counts and full images are recorded in [patch-sampling-control.json](qualification/clearscan_background/patch-sampling-control.json) and [hard-negative-audit.json](qualification/clearscan_background/hard-negative-audit.json). One-pixel rules can lose contrast, particularly at 300 DPI. Dark outliers near fallback are not reported as deleted line pixels. The named `8` source-patch sampling finding remains; this is not a claim that it has been fixed.

| Genuine page | Vector occurrences | Baseline PDF | New PDF | New raster bytes |
|---|---:|---:|---:|---:|
| cord-02 | 58 | 371,283 | 419,570 | 369,487 |
| history-01 | 17 | 5,098,148 | 5,098,148 | 5,035,593 |

[CORD comparison](qualification/clearscan_background/real/final/cord-02.comparison.png) and [historical comparison](qualification/clearscan_background/real/final/history-01.comparison.png) retain full pages. Receipt paper tone, rules, blurred source regions and financial text remain; it **grows 48,287 B** because conservative native detail is retained. Some bold receipt vector digits remain visually rough: this background change does not repair their contours. Historical paper colour, stains, decorative initial and marginal detail remain; the document is byte-identical to baseline. There is no demonstrated real-document compression gain here. Both pages have actual vector replacements. Real conversion uses nominal 300 DPI; dataset capture DPI is unknown. Seven original-OCR financial queries succeed in native PDFium search. Historical renderer text-order/hyphen differences remain inherited. No pristine truth is invented for real scans. [Attribution and derivative licences](qualification/clearscan_background/real/ATTRIBUTION.md).

## Runtime, validation and review

Observed conversion wall time/RSS: 45.60 s / 190.2 MiB at 300 and 99.43 s / 712.0 MiB at 600, against baseline 37.94 s / 197.2 MiB and 80.83 s / 723.6 MiB. CPU is 41.91 / 90.28 s; these single runs show a time cost, not a speedup. Frozen Adobe's valid repeat was 97.91 s at 300, 98.82 s at 600; its process peak memory was not recorded.

**93 Rust tests pass**, with two previously documented inherited failures explicitly skipped (`regress_auto_reports_the_selected_candidate`, `clearscan_repairs_a_damaged_glyph_from_same_document_donors`). E0–E7 pass; inherited P01–P08 visual/native-cardinality failures remain in the saved result. Final ScanWeave PDFs pass qpdf and OTS, actual CID Unicode ownership and native search. Raw/layout/PDFium extraction matches supplied OCR on all 16 synthetic pages. The supplied OCR's existing `c` for pristine `e` is preserved (551/552 known labels correct), not silently repaired. A second ordinary 300 DPI conversion is byte-identical. Frozen Adobe 600 retains its prior qpdf linearization warnings.

[Independent review](qualification/clearscan_background/independent-review.md) found the self-halo erasure risk, missing caller protection in sampling and the need to test rendered weak-line contrast. These led to concrete corrections and the source/patch control. It also records the conservative weak-rule/glyph ambiguity and renderer attenuation; native sample preservation is not presented as a blanket visual guarantee.

## Reproduce and conclusion

```sh
cargo build --release -p scanweave-cli
python qualification/clearscan_background/run.py --repeat
python qualification/clearscan_background/contour_trial.py
python qualification/clearscan_background/summarize.py
python qualification/clearscan_background/manifest.py
```

Use the established qualification environment (NumPy, Pillow, pikepdf, PDFium, FontTools, Poppler, qpdf, OTS). `--measure-only` on this **qualification script** remeasures saved outputs; it is not a product conversion mode. Archived JSON hydrates automatically. Native/high-zoom renders at 100%, 300%, 800%, 1600% and hashes are preserved, with selected full-page images committed.

The faint patterns were substantially obsolete ink/fringe and contaminated fill, with some legitimate/ambiguous material mixed in. Simple local paper reconstruction plus bounded representation removes most of the measured pattern and most raster bytes while keeping the source-matched canonical font intact. The finished PDFs are materially smaller and visibly cleaner. Remaining limitations are renderer-specific native patch sampling, conservative native content cost, and the already-known vector contour defects. No further programme is begun in this round.
