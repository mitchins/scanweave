# M2 — Ownership-protected residual compaction

**Negative result: no product promotion.** Candidate A preserved the matched PDF
through unchanged whole-page fallback and saved **zero bytes**. Candidate B was
not run: the frozen protection map did not establish a sparse packing opportunity.
No protection thresholds were relaxed, glyph/OCR logic changed, or new mode shipped.

## Branch and review boundary

Fetched product main: `0ca94aecd74c35ea1b28bcebe7e11e863aae7f08`.
Trial branch: `product/ownership-protected-residual`, directly from main.
[PR14](https://github.com/mitchins/scanweave/pull/14) remains open/unmerged at
`ffa604ebd4ab47a6af67d2696a5c8fc15fbf3f2e`, with passing CI and server Quality Gate,
nine original CodeRabbit findings resolved, and independent evidence review finding
no blocker. Its final incremental bot review was rate-limited, not approved.
No merge was performed. This report alone is published; detailed negative artifacts
remain local rather than adding another large evidence-only PR.

## Matched trial

The ordinary CLI converted the **unchanged five-page historical document**, retaining
document-wide donor context. Only history-04/01 received candidate representation
changes. An earlier standalone diagnostic changed that context; it is preserved
locally but superseded, not used for qualification.

- Input SHA-256: `53276a63753bba7801c73c8d91e2e52d310a70ca16efb93c1d69f52c462fce6f`.
- Baseline and A complete PDF: **24,637,206 B**, byte-identical to frozen Q100.
- Output SHA-256: `5919f6159ef6d26ec65abfc766ce98b03477f40ce6eb7db89aaa0a2ca2f5ea11`.

| Measurement | history-04 | history-01 |
|---|---:|---:|
| Source dimensions | 1757 × 2440 | 1116 × 1835 |
| Initial native rectangles | 7,521 | 127 |
| Initial union coverage | 92.21% | 93.37% |
| Baseline final coalesced coverage | 100% | 99.40% |
| Pixels added by initial-to-final rectangle expansion | 333,772 | 123,517 |
| A protected pixels | 4,081,528 | 1,897,553 |
| A protected fraction before tiling | 95.205% | 92.660% |
| A native tile coverage | 100% | 95.934% |
| Final emitted coverage, baseline and A | 100% | 100% |
| Native raster bytes, baseline and A | 8,318,245 | 4,047,178 |
| Existing visible-owned occurrences, unchanged | 36 | 25 |

The ownership counts are **telemetry, not validated readable typography**. Vector-only
views contain sparse pale marks while almost all body text remains raster. That is
preexisting behavior outside this raster milestone.

## Cause and candidate

Large `Mixed / ContactNonText` components generate initial native rectangles
`[92,42,1757,2367]` and `[0,25,1069,1800]`. Touching artwork/weak-rule protection and
transitive bounding unions expand them. This is not evidence that every enclosed
paper pixel is printed ink. The final coalescer leaves one rectangle, exceeding
the existing 60% native-area fallback guard. The fragmented-cost branch requires
more than 32 rectangles and **never runs here**; no encoded-cost estimate influenced
selection. Actual stream bytes above are measured, not apportioned by area.

Candidate A reused existing background, native patches, lossless encoding and PDF
assembly. Protection used retained raster-unit/artwork **masks**, explicit caller
regions, every source/150-DPI-restored channel residual >3, short dark/light extrema
>=2 in horizontal/vertical/diagonal directions, page boundaries, 2px margins and
8px native tiles. This supplements the existing long horizontal/vertical detector;
it is not a semantic guarantee for weaker marks.

A preflight exposed another issue: the old proposed paper base clears all recognized
component masks, including the page-sized unresolved component. Within A we corrected
the handoff to derive the base from source cleaned **only beneath emitted vectors**.
The superseded preflight also fell back unchanged and is retained locally.
Even after correction, retained raster-unit masks cover 78.65%/83.91% of the pages;
source residuals and fine extrema make protection still denser. Distinguishing that
uncertain paper/texture from meaningful detail is not established by current ownership.

**B: NOT RUN.** Under the same frozen tile map, history-04 has no unprotected area
and history-01 only 4.066%. No evidence-supported sparse representation was found.
Area is not entropy: this does not prove another packing could never save 10%.
Changing classification to manufacture sparsity would violate B's contract.

## Verification and costs

PDFium and Poppler independently rendered source, baseline, Adobe, O3 and candidate
at fixed physical coordinates. Twenty region records cover PR14's seal, bleed-through,
printing, ornament, paper damage, plus baseline-selected vector boundaries and page
edges. Baseline/A complete renders and all region pixels are identical. No new
halos, seams, colour damage or missing marks were introduced **through fallback**;
the un-emitted compact layer is not qualified.

Native cleaned samples, decoded image samples, occurrences, cleanup counts, regions
and semantic ownership are unchanged. Native extraction matches within each renderer.
Complete PDF identity preserves glyph programs, placement, ToUnicode and ActualText.
Pikepdf/qpdf-library syntax checks and fontTools TrueType parsing passed; standalone
`qpdf` is unavailable and its CLI validation is not claimed.

Collection byte breakdown, unchanged: raster **24,557,201**, font programs **15,428**,
page content **60,428**, other streams **2,081**, serialized remainder **2,068**.
Each primary page emits one whole-page image and zero reduced-paper/exception images.
Inspection-only extracted page PDFs are 8,359,500/4,075,670 B; they retain shared font
resources and are not separate native CLI benchmark documents or additive page costs.

One instrumented **whole-collection** run per arm: baseline **65.137 s / 755,272 KiB**
peak RSS; A **39.342 s / 738,344 KiB**. Audit I/O, cache order and run variance are
uncontrolled. These receipts do not qualify a product speedup or per-page timing.

## Evidence, review and stop

Detailed local deliverables are under `qualification/residual_resolution/`:
`ownership-audit.json`, `protection-summary.json`, `document-results.json`,
`region-results.json`, `inspection-regions.json`, `artifact-manifest.json`,
`run-manifest.json`, `README.md`, reproduction scripts and archived scratch patches.
`local/DETAILED_REPORT.md` retains the extended report; `local/{baseline,candidate-a}/`
contains actual native PDFs, per-stage maps/rectangle lists, source/cleaned rasters,
font-only/non-font PDF derivatives and logs. `comparison/` contains compact sheets;
full physical-resolution renders remain local. These are intentionally not in Git.

Independent read-only review checked actual PDFs, matched hashes, maps, native samples,
both-renderer sheets, accounting and final conclusions. It found **no blocking
unsupported claim**, supported the bounded stop, and did not approve future ownership
methods. Detailed review is retained locally in `INDEPENDENT_REVIEW.md`.

Temporary production edits were reverted and the prior product binary restored.
Faithful, reconstruction, Unicode, source handling and deterministic serialization
remain unchanged. Historical sources, frozen results and sealed holdout are preserved.
The 10% primary gate failed, so no secondary/adversarial, synthetic, full Rust/CI or
32-page promotion rerun was started or claimed. The frozen corpus baseline remains
45,453,391 B; there is no newly measured corpus saving and no implementation PR.

**Remaining blocker:** current evidence does not establish a sparse, source-preserving
native-detail set on these historical pages. Broad unresolved component ownership and
conservative fine-detail protection precede rectangle expansion. Repacking alone has
no measured qualifying opportunity; erasing uncertain marks is not an acceptable fix.
