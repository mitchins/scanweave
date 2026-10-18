# M1-F — Evidence-led page decomposition and compression

## Decision

**Accept F1 lossless resource improvements. Keep F2 disabled and experimental.** Exact image XObjects can be reused across pages, and RGB patches whose samples have `R=G=B` can be stored as one-channel `/DeviceGray`. These changes materially reduce serialized PDFs while preserving extracted text, page geometry, and Poppler/PDFium output. No OCR, reconstruction, font dictionary, or restoration algorithm changed.

The named 300 DPI `8` fallback-render discrepancy remains unresolved: on the saved diagnostic, the source patch and PDF transform are consistent, but the isolated patch renders at IoU 0.732 (Poppler) and 0.768 (PDFium) against truth, versus 0.911 and 0.913 for the whole-page raster. The one-pixel diagnostic improves it but is not part of production. Under the mission gate, I did not run or promote source-ink suppression, whitening, or lower-resolution residual backgrounds. The required hard-negative set was consequently not evaluated. The next conditional step is to isolate that compositing/placement failure, then run a small reversible F2 pilot with explicit protected/unknown regions and hard negatives before any promotion.

## Revisions and frozen inputs

- Repository HEAD: `28c91b12a7212f0ee94daca3bef8c31e4c8044f1` (`main`), unchanged during this work; recorded `origin/main` was `3f0a708`. The prior M1-D commits and unrelated research were preserved.
- Working tree started with no tracked changes. The root M1-F mission/evidence files, Acrobat sandbox and M1-E/M1-C research directories were pre-existing untracked material and were not staged by this task.
- Adobe source manifests and frozen output hashes passed `qualification/experiments/m1f/results/preflight.json`. Input hashes: 300 DPI `069726579bdef9fd4efa96bb8b6b80e4859dc61ccb3c7a1f5013158de3235d2c`, 600 DPI `129a79210a8ef6dc430d349b762873fa2782efe1a93c40b8aef2854dfe026227`, and repeated 12-page `9286edac7fb5881ec5e1c3d1de7ff47c5e49975c443b25b9c39be123717140aa`.
- Frozen Adobe ClearScan output hashes: 300 DPI `6d2150c05e1102cd90a3cdc48f87aeff08af118bf63a5390a787f909589258fb`; 600 DPI `86e26797a02d2e6688c38f8cf6c3f668842da854bcdc177437ce002b3382e6e2`; repeated 12-page `3482de33d73dce352bd5ba9b29afc0f848a1400f4fee43fe3b432c0656246e2d`. Acrobat XI was measured in M1-E as Acrobat Pro 11.0.20 Paper Capture Plug-in under Wine 9.0; these PDFs were treated as frozen references, not quality truth.
- M1-E and the evaluator-only oracle were not modified. All ScanWeave inputs remained the same image/OCR bundles; the converter had no access to the pristine source typography.

## Implementation

`page_pdf.rs` now canonicalizes each patch to its encoded samples, dimensions, bit depth, color model and Flate settings. A SHA-256 digest selects possible matches, then a full key/sample comparison confirms equality before reuse. References are assigned in first-use order. The current patch model has no alpha or soft masks; those properties must enter the key if added later. Equal-channel RGB samples are converted losslessly to DeviceGray after an expansion check. Plain Flate is the default; TIFF predictor and PNG Up are optional controls. The options are passed through both page and document writers and are exposed as CLI `--pdf-image-variant` ablations.

The implementation does not change the input pixels, background patch geometry, semantic text, OCR ownership or font outlines. Faithful mode remains visually and semantically faithful, with a different PDF encoding and smaller repeated-resource PDFs.

## F1 measured results

All byte accounting is from actual serialized PDFs. The reproducible per-object inspector and compact result table are in `qualification/experiments/m1f/measure_pdf.py` and `results/measurement-summary.json`.

| Arm | PDF bytes | Images used / unique XObjects | Encoded image streams | Font program | Content | Remaining PDF structures |
|---|---:|---:|---:|---:|---:|---:|
| A — frozen ClearScan 300 | 1,097,352 | 107 / 107 | 987,055 | 60,468 | 18,480 | 31,349 |
| B — exact reuse, ClearScan 300 | 1,097,352 | 107 / 107 | 987,055 | 60,468 | 18,480 | 31,349 |
| C — reuse + Gray, ClearScan 300 | 767,158 | 107 / 107 | 656,768 | 60,468 | 18,480 | 31,442 |
| A — frozen ClearScan 600 | 3,536,068 | 100 / 100 | 3,354,071 | 133,848 | 18,377 | 29,772 |
| C — Gray re-encode, ClearScan 600 | 2,469,094 | 100 / 100 | 2,291,066 | 133,848 | 18,377 | 25,803 |
| A — frozen faithful, repeated 12 pages | 4,206,711 | 400 / 400 | 3,888,728 | 142,836 | 73,864 | 101,283 |
| B — reuse, repeated 12 pages | 1,227,630 | 400 / 100 | 972,182 | 142,836 | 73,864 | 38,748 |

At 300 DPI, C saves **330,194 bytes (30.1%)** from A. The prior pixel-count estimate expected 331,636 bytes of raster savings; the actual stream reduction is 330,287 bytes, with the small difference explained by final PDF/object accounting. At 600 DPI, the independent grayscale rewrite saves **1,066,974 bytes (30.2%)**. Its image streams shrink by 1,063,005 bytes, 73,804 bytes more than the prior 989,201-byte estimate; another 3,969 bytes of final-PDF savings come from PDF overhead. The 600 DPI case was not emitted by the Rust CLI: its ClearScan reconstruction run failed to complete within the bounded attempt, consuming about 1.48 GB RSS. Therefore the 600 DPI PDF is an actual lossless PDF-level rewrite of the frozen ScanWeave output, not a fresh ScanWeave conversion.

The repeated 12-page faithful fixture had 400 references but only 100 unique decoded sample keys in the frozen file. F1 emits 100 image XObjects for those 400 references. It removes **2,916,546 duplicated encoded image bytes** and reduces total PDF size by **2,979,081 bytes (70.8%)**. This matches the previously measured duplicate-stream total. It does not claim that four repeats predict reuse on unrelated pages.

The M1-E prior estimate for grayscale was ~332 KB at 300 DPI and ~989 KB at 600 DPI; actual savings are shown above. I also re-encoded the actual 300 DPI gray image resources with predictor 1, TIFF predictor 2, and PNG Up, without rerunning OCR or reconstruction. All three versions are pixel-identical to each other in Poppler and PDFium. Predictor 1 used 655,419 image-stream bytes and a 761,516 B PDF in the PDF-level rewrite; TIFF used 704,855 stream bytes and an 818,190 B PDF; PNG Up used 781,389 stream bytes and an 894,831 B PDF. Thus predictors 2 and 12 cost 49,436 B and 125,970 B more image data, respectively. The rewriter changes PDF overhead slightly, so compare predictor variants to its own predictor-1 output; the production Rust PDF remains 767,158 B. Per-resource samples, filters and hashes are in `results/dpi300/predictor-variants/`. Tiny serialized Rust control PDFs with gray and two distinct color patches are in `results/encoding-controls/`; their Poppler/PDFium checks also passed.

### Render and semantic equality

- At 300 DPI, all three ClearScan pages render pixel-identically between the frozen A and F1 output under Poppler and PDFium. The gray-versus-RGB comparison is also pixel-identical in both engines.
- At 600 DPI, all three pages of the rewritten PDF render pixel-identically to frozen A under both engines.
- All 12 repeated faithful pages render pixel-identically to frozen A under both engines.
- The 12-page output is 612 × 792 points per page. The 3-page 300/600 PDFs are also letter-size at 612 × 792 points. `pdfinfo`, `pdffonts` and `pdftotext` succeeded on representative PDFs; outputs have one embedded CID TrueType `ScanWeaveDoc` font. `qpdf` was unavailable. The xref streams/images and both renderer parses provide independent structural checks.
- Extracted text SHA-256 is unchanged for each lossless comparison: 300 DPI `6c593cceb82d30f887f55d927710f25a7bdcf701769857c417ffed48b758b62d`; 600 DPI `5279beb2c3ced83b427627ef6483118eb8e9982db03eac0a3ebe47c6fa9fc474`.
- The 12-page faithful coverage counters are 62,116 text-ink pixels vectorized of 826,372 total (7.5%), 764,256 retained as raster, 164,928 other-ink pixels, and zero unowned or multiply-owned ink. F1 changes storage, not this low reconstruction coverage. Pristine-relative quality is therefore unchanged from the frozen M1-E candidate; this work makes no new claim of glyph repair quality.
- Control PDFs include genuinely colored RGB samples plus gray samples. The negative control remains RGB and distinct content is not deduplicated. Unit tests also check dimension/sample-length rejection and deterministic serialization.

The original whole-document renderer harness retained all rendered pages; its first 12-page comparison completed pixel-identically but reached approximately 14 GB RSS. I changed it to compare one page at a time and reran the comparison; the bounded-memory rerun is recorded separately. This high memory was in the measurement harness, not the converter. The converter run log measured 329.558 seconds and 1,376,312 KiB peak RSS on its first full run. Stage timing around the document conversion region measured 169.423 seconds: donor collection 54.524 s, page conversion 90.630 s, font union 0.002 s, font build 0.041 s, reconstruction PDF assembly 1.692 s, raster-baseline preparation 0.218 s, and raster-baseline PDF assembly 22.312 s. The remaining 4 ms is selection/report preparation inside that region. The difference between the end-to-end 329.558 s and this instrumented region is outside `convert_document` and remains unprofiled. The repeat peaked at 1,383,596 KiB RSS and serialized the same PDF hash. The pipeline is CPU/memory-heavy despite the PDF size reduction.

## Source fidelity and comparison with Adobe

F1 is exactly lossless relative to each frozen ScanWeave PDF in both tested renderers and preserves extracted text. It does not alter any pristine-relative glyph result: it serializes the same reconstruction and fallback layers. Adobe ClearScan measured 46,213 bytes at 300 DPI and 51,429 bytes at 600 DPI (M1-E), so ScanWeave remains substantially larger. The present result attributes a large, demonstrated part of the gap to duplicated raster data and three-channel encoding; it does not attribute all of Adobe's advantage to glyph reuse. Adobe uses lower-resolution backgrounds and different reconstruction/font serialization, which F1 deliberately does not imitate.

No quality-based tradeoff was accepted. Source noise was not whitened, text pixels were not erased, and protected artwork was not downsampled. Adobe remains a comparative measurement, not the quality oracle.

## Ablation status and F2 gate

`results/ablation-results.json` records the requested A–G arms. A, B and C have actual output PDFs as described. The 600 DPI C output is explicitly marked as a PDF-level grayscale rewrite rather than a new conversion. D (background normalization), E (replaced-text suppression), F (adaptive background resolution), and G (combinations) were **not run** because the `8` compositing discrepancy remains unresolved and the required targeted hard-negative inputs were not assembled. There are no claims for background/noise savings or information preservation. Under the mission's stop condition, F1 is independently accepted; irreversible page restoration is not promoted.

The conditional next branch is:

1. Isolate the fallback `8` rendering discrepancy across source crop, transform, clip, paint order and renderer.
2. If resolved, build one small reversible F2 pilot with explicit replaced-ink/fringe/background/native/unknown ownership and the specified faint text, punctuation, kana, rules, barcode, artwork, handwriting, aged texture and ambiguous-mark hard negatives.
3. If faint information is lost or placement remains uncertain, retain only F1 and stop the restoration path. If a bounded F2 layer passes the negatives and both renderers, qualify it separately before release.

Do not begin a font-format project from this result: raster resources remain the largest cost on these ScanWeave outputs, and vectorized text coverage is still low enough to leave glyph reconstruction as a separate programme.

## Reproduction and files

From the repository root:

```sh
qualification/.venv/bin/python qualification/experiments/m1f/preflight.py
cargo test -p scanweave-io
cargo build -p scanweave-cli
qualification/.venv/bin/python qualification/experiments/m1f/summarize_measurements.py
```

`qualification/experiments/m1f/` contains the image/accounting/render scripts, preflight hashes, run records, compact measurement table, control PDFs, serialized output PDFs and renderer comparisons. The three-page source images and frozen Adobe/ScanWeave baselines remain in `qualification/competitors/adobe_xi/`. Independent review findings are in `qualification/experiments/m1f/independent-review.md`.
