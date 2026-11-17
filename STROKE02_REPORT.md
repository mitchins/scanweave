# STROKE-02 — final development-page result

**The corrected experiment does not meet the product objective and is not ready to merge.** All 36 development pages completed with the research-only wrapper. The 613 output is less brown because its region falls back to raster, not because the converter reconstructed the digits. French is unchanged after safety fallback. Total raster bytes increased and vector-owned text decreased.

1. **Does 613 look at least as good as MRC?** No. The candidate is grey rather than shell-brown, but its raster digits are soft at 1× and 2×; MRC is more legible. The corrected native-page fit reproduces per-digit σ=0.70/0.93/0.70 px and pooled t=1.10, with ink RGB (142,141,110). The former page pre-pass already used local paper; its error was a pooled edge-width heuristic and coarse strength search, not use of the page-wide 237.8-luma estimate. The 6's mask gains 32 pixels, but its traced source-mask IoU is 0.294, below the unchanged 0.98 gate. The 1 and 3 proposals continue beyond their OCR boxes plus the two-pixel margin. The existing `FidelityBelowPolicy` decision moves the three-digit region from vector to raster. On the rendered PDF's 3×3 counter test, zero of the one source-near-paper pixels exceeds twice the local noise proxy, versus one for #39; the other counter-region pixels have greater mean darkening (0.093 versus 0.025 linear luminance). This proxy is not independently calibrated scanner noise.
2. **Are the French letters better without artificial bolding?** No. The final 12342014 PDF is byte-identical to #39. Its first trial would have added U+FFFE; the wrapper rejected that trial and blocked its experimental units. No clarity improvement can be claimed from the resulting fallback.
3. **What changed?** The pre-pass uses the crop experiment's local background field and per-glyph cross-section fits on small groups, pooling line ink direction/strength; OCR boxes group observations, not dictate glyph shape. The experimental unit crop now includes the OCR glyph box plus the two-pixel PSF footprint, instead of only #39's fragmented component crop. The original component map, ownership ledger, two-pixel neighbour/artwork guard and existing downstream gates remain in force. Vetoed pixels receive zero proposed coverage; a disconnected proposal declines. The measurement wrapper renders a text-only diagnostic built from the trial PDF's actual text operators and fonts at 4× with PDFium, checks direct and reblurred ink at each veto pixel against its local noise allowance in linear luminance, and retries failed symbols. It assumes maximum ink contrast, a conservative bound. If the wrapper is absent, the older conservative whole-unit veto remains. This is a research measurement path: its internal verifier switch can emit an unverified trial if invoked outside the wrapper, so it is not a standalone production safeguard.
4. **PDF size, coverage and cost.** Counts are converter-segmentation pixels, not ground-truth character area. Baseline and candidate ran in separate batches on an uncontrolled host. The candidate time includes eight safety retries in the final measurements; pre-pass and PDF checks are additional. The earlier rejected Bohse measurement and verifier-calibration runs are not included in that sum.

   | 36-page measure | #39 | Candidate |
   |---|---:|---:|
   | PDF bytes | 16,315,763 | 16,131,589 |
   | Encoded raster bytes | 14,696,444 | 14,800,328 |
   | Vector / raster text units | 5,339 / 17,685 | 4,331 / 18,693 |
   | Vector / total text-ink pixels | 1,093,241 / 33,816,721 | 630,950 / 33,892,115 |
   | Conversion seconds, total / median | 985.9 / 20.48 | 1,683.2 / 21.80 |
   | Pre-pass seconds, total / median | — | 708.5 / 10.32 |
   | PDF veto verification seconds, total | — | 3.8 |
   | PDFium 150-DPI warm render, median page | 14.12 ms | 11.87 ms |

   The smaller total PDF does not demonstrate raster displacement: raster bytes increased by 103,884. Of 10,006 attempted units, 3,098 received 75,394 extension pixels on 11 pages before downstream gates; 1,511 were declined at the veto/connectivity check. Final reported vector text-ink fell by 462,291 pixels. Twenty-six PDFs remained byte-identical. [Per-page size, raster, ownership, time and render differences](research/stroke02/results-refit.json); [unit and gate evidence](research/stroke02/refit-diagnosis.json).

   | Target/control | PDF bytes #39 → candidate | Raster bytes #39 → candidate | Vector ink pixels #39 → candidate | Candidate seconds |
   |---|---:|---:|---:|---:|
   | 613 / 8967062 | 92,310 → 90,759 | 69,269 → 69,490 | 10,061 → 9,652 | 14.26 |
   | French / 12342014 | 554,944 → 554,944 | 276,454 → 276,454 | 150,562 → 150,562 | 117.61 |
   | Aventinus 0008 | 567,928 → 567,928 | 550,503 → 550,503 | 0 → 0 | 47.50 |
   | Luther 0011 | 441,781 → 441,781 | 435,315 → 435,315 | 0 → 0 | 7.79 |
   | Euler 0025 | 439,391 → 439,391 | 428,319 → 428,319 | 0 → 0 | 6.14 |
   | Heading / 8967228 | 161,265 → 161,265 | 157,464 → 157,464 | 415 → 415 | 22.55 |

5. **Regressions and text:** The four controls are byte-identical to #39, including the existing degraded plate heading. PDFium extraction on the final 36 pages has only whitespace edits on six pages; there are no detected non-whitespace character or order changes and no newly inserted U+FFFE. Ownership changed 1,039 visible→invisible and 31 invisible→visible occurrences, potentially affecting selection even where extraction is equal. An initial Bohse 0036 trial removed ten non-whitespace characters and added one; it was rejected and retried with its experimental units blocked. Two rejected French trials would have added U+FFFE. These failures remain evidence, not passing results. A fixed sample of 686 locally selected OCR words produced 678 PDFium search hits in both runs, with no lost or gained queries; this is a sample, not proof of search equivalence. [Extraction audit](research/stroke02/extraction-refit-audit.json), [rejected extraction](research/stroke02/rejected-extraction.json), [search audit](research/stroke02/search-refit-audit.json).
6. **Ready to merge?** No. The actual PDF improves 613's colour only through a low-resolution raster fallback, does not improve French, and reduces vector ownership overall. The experimental wrapper and its local noise estimates need independent review; no default behavior was promoted. Full `scanweave-io` tests and focused per-glyph-fit, ownership, and rendered-PDF veto tests passed.

## Why #39 retains raster text

The following disjoint categories use the 32,723,480 baseline raster-owned text-ink pixels. Whole-page fallback is counted first. For other pages, a unit is attributed only if exactly one reported region box contains it; overlapping/ambiguous boxes stay unassigned. Counts are from existing decisions, not a new classification of the source pixels. [Full page-level audit](research/stroke02/raster-reason-audit.json).

| Recorded reason | Ink pixels | Pages |
|---|---:|---:|
| Whole-page polarity fallback | 28,782,781 | 10 |
| Contact with non-text | 2,220,588 | 25 |
| Unsupported content | 1,545,290 | 10 |
| Fidelity below policy | 135,590 | 14 |
| Unattributed / ambiguous | 39,231 | 13 |

`no_supported_donor` is a **non-exclusive reconstruction signal**, not the cause assigned to a raster region: it appears for 31,459,274 raster-owned ink pixels across 36 pages, including pages already in whole-page fallback. Other non-exclusive signals and page counts are in the audit.

**Separate #39 findings.** The default ownership invariant checks component identities but not pixels added to prototype masks; on the French page, 24 of 66 recorded refined prototype entries contain outside-foreground pixels (194 occurrences, potentially repeated). These are cloned prototypes, not observed mutations of owned-unit masks; the default invariant remains unchanged. The pre-existing U+FFFE extraction bug remains: this PDFium run counts 113 occurrences in both baseline and final output. It is not accepted as correct or fixed here.

Actual-PDF comparisons: [613 1×](/data/coding/scanweave/work/books01/stroke02/final/613-1x.png), [613 2×](/data/coding/scanweave/work/books01/stroke02/final/613.png), [French 1×](/data/coding/scanweave/work/books01/stroke02/final/french-1x.png), [French 2×](/data/coding/scanweave/work/books01/stroke02/final/french.png), [Aventinus](/data/coding/scanweave/work/books01/stroke02/final/aventinus_grammatica_1515_0008.png), [Luther](/data/coding/scanweave/work/books01/stroke02/final/luther_babstum_1526_0011.png), [Euler](/data/coding/scanweave/work/books01/stroke02/final/euler_rechenkunst01_1738_0025.png), and [heading](/data/coding/scanweave/work/books01/stroke02/final/8967228.png). Each control also has a `-1x.png` companion. Adobe heading registration was unavailable. Research binary SHA-256 `1b03262abc76f990a1e7ceb9f8d2866e06111375aa2f053ae4c43589852c7e33`; artifacts are under `/data/coding/scanweave/work/books01/stroke02/pages-refit/`.

The prior local `pages-extensions/8967062` pre-pass files were accidentally overwritten during setup, then regenerated from the previously committed code and pinned source; their original local wall-time field could not be recovered. The previous committed metrics and the new run's evidence remain intact.
