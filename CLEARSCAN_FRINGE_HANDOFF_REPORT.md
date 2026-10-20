# PR closure and replacement-fringe handoff

## Publication checkpoint completed first

- PR #1: https://github.com/mitchins/scanweave/pull/1 — `0e82e6416a66e94839f52d0a922b02900180d44e`, ready for review; no merge.
- PR #2: https://github.com/mitchins/scanweave/pull/2 — `ecb149fbac3842ea86aa513991f547f27b103af3`, ready for review; no merge.
- Initial heads were the requested `5fe99c1` / `35e2f6d`. Product followups are `aa670ab` and `0e82e64`; PR2 audit fix is `a59d07e` and normal product-branch merges. Existing history was retained.
- CI runs [39377478529](https://github.com/mitchins/scanweave/actions/runs/39377478529) and [39377481897](https://github.com/mitchins/scanweave/actions/runs/39377481897) pass all Rust, Clippy, Python qualification and publication contracts. Local unfiltered workspace tests and all nine Python commands also pass. No skips were added.
- CodeRabbit PR2 `image_resources` finding fixed: two audit regenerations produce identical JSON SHA `b60f329a8fe292968a75dd0441b4289165f23702f97dca1c03baa2ca63890438`, both measured documents contain one image XObject. [Review reply](https://github.com/mitchins/scanweave/pull/2#discussion_r4321883484); thread resolved.
- PR1 CodeRabbit full review is skipped due catch-up size; this is not review approval. Independent donor-fix review completed. PR2 incremental review completed. Neither PR was merged.

### Actual inherited donor failure and correction

The intact ten-witness cohort existed. Candidate discovery compared damaged `e` only with its medoid: IoU .6931, below the unchanged .78 gate. Three actual intact cohort members each score .8368; alternate-face members score .567–.601. A damaged-only fallback now examines actual members of the already-qualified cohort, requires three supporting members under the unchanged gate, and traces the actual selected witness with immutable provenance. Healthy medoid reuse is unchanged. No threshold, Unicode or faithful contract changed. Exactly the required damaged occurrence repairs; original assertions remain and stronger witness-provenance assertions were added.

See `qualification/pr_closure/DONOR_FIX.md`. Final evaluator-only pristine IoU improves .8137 source → .9712 Poppler / .9744 PDFium. The old standalone evaluator's faithful-to-source ordering assertion still fails from source-patch sampling; its failure is retained, not hidden. It is not an unfiltered CI failure. Inherited P01–P08 visual limitations remain recorded in prior reports and are not reclassified as passing by green CI.

## Separate bounded handoff branch

`fix/replacement-fringe-handoff` starts at corrected product `0e82e64`, not the rejected shaded-paper evidence branch. Segmentation and pixel-contact trial patches were reused unchanged: 792 observations, 495,223 foreground pixels, 73 visible occurrence records. The 12 fixed regions are preserved in `qualification/fringe_handoff/regions.json`. Faithful and the sealed holdout were untouched.

### Exact handoff loss

The shaded trial built a smooth p90 illumination grid for segmentation, but retained only its binary foreground decisions. The compositor received `seg.paper`, the old corner-derived value (around 40), rather than the local paper (around 189–197 in the fixed regions). Thus source coverage and donor registration used incompatible illumination estimates. Independently, the fringe path required an independent donor halo. Seven of the twelve fixed local-vector regions lack one; local paper alone cannot satisfy that guard.

### Two corrections tested, no third approach

**A:** Retain the exact existing illumination grid and pass it to source-darkness, registration and fringe-coverage normalization. Independent donor-halo requirements stay unchanged. RGB fill still uses suitable neighboring original samples; if none exist, preserve the original sample rather than importing dark corner colour.

**B:** A plus source-derived evidence when an emitted local glyph has no independent halo and its recorded source-mask agreement satisfies the existing .98 condition. Only a one-pixel, four-connected fringe may qualify: three parallel owned-core → partial-edge → two original-paper rays, per-channel blending consistency, no protected ink or other vector core. No rectangle erasure. Uncertain samples remain raster. See the saved patch for every numerical condition; none were relaxed after observing failure.

Independent review found a B dispatch bug: a present donor record without halo bypassed the source-only predicate. Earlier `b-final`/`b-verified` outputs do **not** establish B effectiveness. Dispatch was corrected within the same B method, then rebuilt and rerun as **`b-active`**. Its log records **27,184 actual predicate invocations and zero passes**. It is byte-identical to A. Provenance is in `b-active-provenance.txt` and `predicate-counts.json`; no third method was introduced.

## Actual completed PDFs and measurements

| Arm | PDF B | Raster B | Font B | Changed core pixels | Changed fringe pixels |
|---|---:|---:|---:|---:|---:|
| Published ordinary product | 5,186,194 | 5,171,835 | — | 0 | 0 |
| Matched shaded control, corrected product fonts | 5,248,323 | 5,163,535 | 70,082 | 16,345 | 0 |
| A | 5,245,351 | 5,160,563 | 70,082 | 16,275 | 2,193 |
| B, corrected active dispatch | 5,245,351 | 5,160,563 | 70,082 | 16,275 | 2,193 |

A/B save **2,972 B** versus the matched control, entirely raster, but remain **59,157 B larger** than ordinary product. All shaded arms retain one native-resolution image. Decoded font programs and full page graphics streams are identical between matched control/A/B; text placements and Unicode therefore stay fixed. Earlier frozen trial B has a different font payload and is explicitly a nonmatched historical reference, not a causal control.

Reported core suppression remains 16,345; actual decoded sample changes are 16,275 because 70 core samples without suitable neighboring RGB evidence are preserved. Do not substitute the reported count for measured changed samples. No changed sample lies outside the one-pixel union around emitted original masks; no protected foreground sample changes. This bounded-footprint test is necessary but does not prove every altered pale sample is obsolete ink.

In five fixed donor-supported regions, fringe changes are 58/56/33/44/52 pixels; seven unsupported regions remain unchanged. For example the `n` region's ring contrast drops 42.48→24.40 levels, while the `G` remains 41.30. These ring statistics include genuine paper texture and are **not** pure ghost-ink scores or pristine error measurements. No original-font ground truth exists for this real page.

A, matched control and B have identical native PDFium and Poppler extracted text within each renderer. Queries `19` and OCR spelling `Geift` remain present in both. This preserves existing OCR, not proof of correct historical transcription. Qpdf checks pass for all actual outputs. Both renderers inspect the same fixed physical regions; no glyph-wise alignment is applied.

B-active wall time **22.93 s**, peak RSS **159,924 KiB**, including verbose predicate diagnostics. It is not a speedup claim. Per-arm timing logs are retained.

## Visual decision: reject both; product unchanged

Actual native full page and twelve enlarged regions were inspected in PDFium and Poppler. The `G` retains a faint raster ring beside a rough stair-stepped vector contour. The `1`/`9` outlines remain visibly stair-stepped; several cleaned letters have heavy stem/edge artifacts. Adobe's corresponding outline is visibly smoother, but is not treated as original-font truth. A cleans some donor-supported pale traces; this does not fix unsupported local-vector quality or the seven no-halo regions.

[PDFium fixed-region sheet](qualification/fringe_handoff/pdfium-twelve.png), [Poppler sheet](qualification/fringe_handoff/poppler-twelve.png), [actual A/B PDF](qualification/fringe_handoff/a.pdf), [vector-only PDF](qualification/fringe_handoff/a-vector.pdf). The B-active PDF is byte-identical to the linked A PDF, SHA `540638347359a1ffb8f5dd6c0665d4db97f91fc432aab3444a881deb7375d585`. Raster-only layers and normal-size full pages are reproducible using `render.py`.

Neither candidate passes the visual/size gate. Source code was restored exactly to corrected product HEAD; rebuilding/running it reproduces the published ordinary history-02 PDF byte-for-byte, SHA `8f14ae1e0831cafced4e9606c5924fd5b2dc1a5a8f09f252ff7ed3302bee072d`. No shaded segmentation/contact/cleanup code is promoted. Conditional history-03/Linn/NARA/synthetic and 32-page runs were not launched after primary rejection; no corpus-improvement claim is made.

Independent review verified matched hashes, corrected active B invocation counts, source ownership accounting and both renderer sheets. It required the dispatch correction and cautioned against treating ring contrast as pure ink or real-page roughness as a proven identity error. Those findings are incorporated.

## Reproduction / evidence

`qualification/fringe_handoff/manifest.json` preserves source/comparator identities and output hashes. `candidate-a.patch.gz` and `candidate-b-active.patch.gz` apply to product `0e82e64` in an isolated checkout; they include the original fixed segmentation/contact trial and diagnostic logging. Run `cargo build --release -p scanweave-cli --bin scanweave`, then the normal `scanweave history-02.pdf output.pdf` command, retaining stderr and its JSON sidecar. Do not apply rejected patches to production. `measure.py` expects the recorded local paths and sidecars; `render.py` creates vector/raster layers and identical-coordinate crops. Python dependencies: pikepdf, pypdfium2, numpy, Pillow; Poppler and existing tools_env qpdf required. Logs, exact timing and hash manifests accompany the result; only one shared completed trial PDF is committed, not every duplicate or corpus output.

**Most important demonstrated blocker:** source-only fringe ownership is not established for the ambiguous local vectors, and those vectors also have visibly unsupported rough/heavy geometry. Passing local illumination fixes one real handoff loss, but cannot safely qualify those edges or justify shipping this shaded-page reconstruction.
