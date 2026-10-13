# ScanWeave — qualification and milestone contract

**Status:** Proposed tests and gates, not benchmark results. Read with `SPEC.md`. All sizes, coverage thresholds and corpus minima below are proposed engineering requirements. No supplied corpus has been evaluated in preparing this handoff.

## 1. Evidence layers

Keep separate evidence for schema/import correctness, geometric/visual correctness, semantic transport, OCR accuracy, font/PDF interoperability, compression and operational behaviour. Passing a unit test or `qpdf --check` cannot prove the higher layers. Passing the same OCR engine on input/output is a diagnostic, not an independent transcription oracle.

Qualification states are `NOT_STARTED`, `IN_PROGRESS`, `HOLD`, `PASS`, `FAIL` and `UNQUALIFIED`. A failed candidate can be safely rejected while a baseline succeeds; report both outcomes. Preserve negative experiments and historical failures.

Every gate records the exact code revision, clean/dirty tree state, toolchain, locked dependencies and models, corpus/split hashes, full resolved policy, commands, exit codes, raw results and reviewer decision. Reviewer approval is separate from the implementer's self-report. `HUMAN_VERIFIED` requires an actual recorded human inspection and a defined scope.

## 2. Corpus and split design

Assume a benign licensed corpus will be supplied. Do not fetch private financial documents from connected accounts, fabricate a corpus availability claim, or upload scans to review services.

Create strata for clean modern text, receipts, bank statements, utility bills/forms, old books/documents, decorative typography, Japanese horizontal, Japanese vertical, and degraded/mixed stress pages. Tags can overlap. Include grayscale and colour, 150/200/300/600-dpi material, camera skew, faint thermal text, transparent stamps, rules touching text, reverse text, JPEG artifacts, paper texture and partially missing OCR.

M0 pilot target: 24 independently sourced documents / at least 60 pages, development data only, covering financial/receipt, book, decorative and Japanese material. A missing category remains unqualified rather than being silently replaced by another English page.

Release qualification target: at least 120 independent source documents / 1,000 pages in total; at least 10 documents per required domain/script stratum; at least one 300-page book for resources; and an adversarial synthetic set separate from the natural-document totals. Set document-level train/development, calibration and holdout partitions at 60/20/20 unless the operator approves another allocation before evaluation. A document can belong to several strata but counts once overall.

Group related scans, pages, originals, degradations, translations from the same template, generated siblings and rescans together. Do not split pages from one book across development and holdout. Preserve a held-out-typeface subset for synthetic tests. A typeface's exact font file and pristine source geometry must be unavailable to the reconstruction engine; they are oracle-only material.

All provenance records include rights, source family, acquisition type, transformations, original hashes and oracle status (`source_generated`, `human_transcribed`, `silver_ocr`, `unlabelled`). Do not call silver OCR ground truth. Only permitted assets go into public fixtures; proprietary fonts remain operator-local and are never packaged in a release.

Before holdout, freeze splits, thresholds, candidate policies, metric code and dependencies. The qualification runner may access holdout oracles; the implementation/tuning agent may not. Report by document/domain/script and include worst cases, not just a pooled page average. Bootstrap confidence intervals by original-document family, not individual correlated glyphs/pages.

## 3. Baselines and experimental comparisons

Use identical source pixels, supplied OCR, geometry and output intent wherever tools permit. Record unavoidable differences rather than claiming paired equivalence.

| Baseline | Purpose |
|---|---|
| Source input | Real operator size/fidelity reference; not automatically a searchable comparator. |
| Lossless searchable raster built with the same OCR | Required safety/control output. Shows how much font reconstruction actually changes. |
| Conservative MRC (Internet Archive PDF Tools or qualified alternative) | Required compression competitor. Its segmentation and codec policy must also pass visual checks. |
| OCRmyPDF lossless-oriented configuration | Practical existing-tool comparator; explicitly specify regular PDF/PDF-A and optimization settings. |
| Scribe digital reconstruction, optional | Useful typography/reconstruction comparator, with its different font strategy declared. |
| Smoothscan, optional | Technique/visual comparator; arbitrary text mapping means it cannot win the searchability gate unchanged. |

A tool being installable or advertising compression is not a benchmark result. Record attempted routes, configuration and blockers. No baseline may silently use lossy symbol substitution, hidden downsamples or different page cropping. A visually invalid baseline is reported as invalid, with raw size still visible; do not cherry-pick which failures to show.

Run ablations: no dictionary vs dictionary; unique glyphs vs shared medoids; reconstruction vs MRC; symbol-level vs word-only OCR; wrong OCR labels with fixed geometry; simple vs textured backgrounds; faithful vs compact; one worker vs multiple workers; fresh vs resumed jobs.

Compression denominators are explicit. For output O, source S and searchable baseline B, report `source_ratio = O/S` and `baseline_ratio = O/B`. Lower is smaller. For paired external MRC compare with its independently validated output, not an arbitrary JPEG scan. Report median/p95/worst document ratios, totals and per-domain breakdown, plus PDF-only and package sizes separately.

## 4. Visual metrics and operating policy

### 4.1 Reference and canonicalization

A source raster's canonical decoded samples are the reference for source-faithful claims. A pristine digital source is an additional oracle for synthetic reconstruction detail, not the runtime input. Record colour handling, resolution, resampling and any deliberate deskew separately. Do not align away a placement bug with unconstrained image registration before scoring.

Render source baseline and final PDF with the same independent renderer at a fixed physical size/resolution. Repeat in a second independent PDF engine. Compare at native scan DPI and 2x native DPI; inspect thin-feature crops at high zoom. Two wrappers around the same underlying PDF renderer are not independent.

For native-resolution crop acceptance, use the same source-derived foreground threshold(s) on source and candidate. Never tune the candidate threshold separately to make it resemble the source. Include surrounding context so removed decimals, underline damage and crop seams cannot escape the mask.

### 4.2 Defined metrics

- **Ink IoU:** intersection / union of foreground masks; treat an empty/empty mask as 1 and empty/nonempty as 0. Compute per occurrence and protected critical crop, not only per page.
- **Edge error:** symmetric nearest-boundary distance, measured in source pixels. Record p95 and maximum with a defined pixel-edge contour method. Do not discard isolated marks as distance outliers.
- **Coverage/topology:** source component ownership, connected components and holes at fixed threshold offsets. Dots, accents and dakuten have no blanket minimum-area exemption. A component that could be a mark is preserved or causes fallback.
- **Local colour error:** mean absolute channel error on a padded comparison crop with defined normalized channel values; report an ink-weighted error separately from background error.
- **Global diagnostics:** page SSIM/PSNR, colour/background differences, and high-zoom inspection. They can reveal problems but cannot override a failing local-content gate.

Initial development policy: ink IoU ≥0.98; symmetric boundary p95 ≤0.5 source pixel and maximum ≤1.0 pixel; normalized local MAE ≤0.02; no unexpected component/hole changes at threshold offsets -0.05/0/+0.05; no unowned source mark. These are deliberately conservative **starting values**, not demonstrated universal perceptual thresholds.

M0/M1 may calibrate numeric operating thresholds on development/calibration material with independent review and an explicit policy revision. Freeze them before holdout. Changing thresholds in response to holdout failure invalidates that run; label it development and create a new sealed evaluation. Never weaken a behavioural invariant or hide an entire failing class to make the numbers green.

Exact mode compares decoded image samples losslessly and verifies that adding invisible text does not change the baseline render in the same renderer. It does not claim different PDF renderers produce identical pixels to one another. Protected patches must preserve source samples and compositing, not merely satisfy a high SSIM score.

### 4.3 Content-critical errors

Examples: 6↔8, 0↔O, 1↔l, rn↔m, deleted decimal point, dropped minus sign, moved superscript, merged diacritics, removed dakuten/handakuten, changed small kana, eroded barcode module, shifted table amount, duplicated text, or lost figure/marginalia.

The admissible count is zero for the explicit adversarial safety suite and zero newly introduced known critical errors on holdout. No finite corpus or metric set proves a universal zero-error rate; report exposure counts and confidence bounds. A single discovered content-changing reconstruction blocks promotion and gets a permanent regression fixture.

Barcode checks include source patch preservation; unchanged decode results alone cannot prove a barcode's visual fidelity. For financial fields report exact oracle match where a reliable oracle exists. Do not change visible content to make it agree with OCR or a checksum.

## 5. Semantic and font tests

Run an independent font parser/OTS on generated fonts and render/extract the final PDFs with pinned Poppler and PDFium. Add the host's renderer as a consumer test, not as a replacement for independent validation. Desktop viewer checks cover at least browser PDFium and macOS Preview where available; manual platform claims require actual execution.

The primary semantic metric is **transport**: the emitted semantic spans must reproduce admitted normalized OCR text in declared logical order without additions, deletions, duplicate layers or normalization. Compare by span/region as well as whole-document extraction. Separators introduced by an extractor's documented layout formatting are handled through a preregistered mapping; never normalize away numeric punctuation or content errors.

OCR accuracy is measured separately against generated or human transcription oracles. Wrong-label injection must demonstrate that the visual source survives while the wrong supplied text remains explicitly unreviewed. Do not mark that case semantically correct merely because the transport worked.

Required fixtures: two GIDs for the same Unicode; one GID for two distinct semantic strings/CIDs; `fi` ligature; combining mark sequence; supplementary-plane scalar; full-width digits; horizontal kana; vertical Japanese; multi-component `ガ` and `パ`; ordinary word-only OCR; unrecognized raster text; Arabic/RTL fallback without transliteration; mixed visible and invisible spans; font subset boundary at 60,000 entries; and repeated text that must extract once per occurrence, not once per dictionary symbol.

For visible vector proof, inspect the final PDF resource/paint graph. Confirm accepted text is painted by embedded outline fonts and is not still backed by a full-resolution scan or per-character bitmap. Remove/hide raster operations in a diagnostic copy and demonstrate that the claimed reconstructed text remains. This is diagnostic tooling, not the user output. Report any retained full-page image by disposition.

## 6. Named behavioural tests

Implement tests first using stable IDs and Given/When/Then descriptions; no special Gherkin framework is required.

| ID | Given / when | Required outcome and forbidden effects |
|---|---|---|
| IN-01 | Matching image and hOCR | Real geometry imports; no OCR invocation. |
| IN-02 | Same dimensions, different image hash | Binding rejection; no output publication. |
| IN-03 | OCR uses stale crop/rotation | Reject unsupported binding/mapping; never silently shift text. |
| IN-04 | Word-only hOCR/TSV | Word-level mapping or raster fallback; no equal-width invented characters. |
| IN-05 | Absent DPI and physical extent | Explicit geometry error, not a guessed page size. |
| IN-06 | Malformed XML/oversized image/path escape | Bounded rejection; no external entity or network access. |
| VS-01 | Observed `8`, OCR `6` | Original `8` remains visible; supplied `6` retained as unreviewed text. |
| VS-02 | Label-only mutation, fixed geometry/protection | Identical visual plan and render; semantic mapping changes only. |
| VS-03 | A≈B, B≈C, A≉C | C cannot enter A's cluster through transitivity. |
| VS-04 | Same label in bold/italic/different family | Distinct shapes retained unless actual visual equivalence passes. |
| VS-05 | Dot, minus, accent, dakuten, barcode edge | No missing source mark; preserve or fall back. |
| VS-06 | `O` / `8` on coloured paper | Real compound-contour holes; no white-painted counters. |
| VS-07 | Text touches table rule/stamp/photo | Non-text unchanged; conservative fallback if inseparable. |
| VS-08 | Unknown OCR region / handwriting | Visual content retained, no invented semantic label. |
| VS-09 | Protected amount or identifier | Original samples retained including adjacent punctuation. |
| VS-10 | Two overlapping replacement candidates | Resolve/merge/fallback ownership; no doubled paint or missing ink. |
| TX-01 | Same outline, different text mappings | Distinct CIDs/extraction; no majority-vote substitution. |
| TX-02 | Ligature/combining/supplementary character | Exact string transport and correct visible shape. |
| TX-03 | Mixed vector and raster text | Every span extracts exactly once. |
| TX-04 | Kana and full-width characters | No normalization, transliteration or generic-font replacement. |
| TX-05 | Vertical columns with ruby/inline numbers | Qualified appearance, extraction/order and coarse/fine selection claims. |
| TX-06 | Historical hyphens and long-s | Preserve supplied strings and shapes; no modernization. |
| PF-01 | Reconstructed clean text | Actual embedded TrueType outlines paint it; no hidden full-resolution copy. |
| PF-02 | Native digital or mixed page | Pass through intact; no flattening to raster. |
| PF-03 | Signed/unsupported structured PDF | Explicit rejection/authorized derivative policy; no false preservation. |
| PF-04 | 60,001 glyph/CID candidates | Deterministic split/fallback before format cap, valid output. |
| SZ-01 | Small receipt; font makes PDF larger | Auto selects measured valid baseline; honest no-vector result. |
| SZ-02 | Repeated multi-page text | Dictionary reuse measured, actual full-file bytes counted. |
| SZ-03 | Impossible target size | No safety downgrade; predicate failure without rejected output. |
| SZ-04 | Lossless mask codec enabled | Decode round trip exact; lossy-symbol mode rejected. |
| OP-01 | Source/output hard-link or symlink alias | Reject; original bytes unchanged. |
| OP-02 | Crash/cancel at each stage | No corrupt published PDF; valid checkpoint rules on resume. |
| OP-03 | Changed source/OCR/config/tool version | Stale cache not reused. |
| OP-04 | One worker vs many; fresh vs resumed | Deterministic final PDF on the pinned environment. |
| OP-05 | Font/curve/bucket/memory budget exceeded | Safe fallback or typed resource failure, not a hang or downsample. |
| OP-06 | Missing requested validator | NOT_RUN/failure, not PASS. |
| OP-07 | Report publication fails | Commit state is explicit; no fake atomic two-file claim. |

Property tests cover transform round trips, clipping/coverage accounting, UTF-8 ranges, deterministic dictionary keys, font/CID allocation and monotone safety under stricter policies. Fuzz parsers and untrusted dimensions/paths. Mutation tests must deliberately break protection, font holes, ownership, Unicode maps, cache keys and output publication to prove the suite notices.

## 7. Anti-vacuity and product gates

Hard invariants cannot be traded for size. Release gates require all required safety/semantic/operational fixtures, zero known newly introduced critical errors, and independent final-output validation.

A reconstruction milestone also needs **real vector coverage**. On a preregistered clean printed-text subset, target median vectorized text-ink coverage ≥80%, reported both over all text and over independently defined eligible text. A safe all-raster build fails this reconstruction gate. The eligible mask must be established before examining system output. Measure coverage separately for `auto` and `reconstruct`; the reconstruction-coverage gate uses explicit `reconstruct` mode. Never present forced-reconstruction coverage as an observed `auto` result.

For auto mode, final PDF size must not exceed the utility's fully serialized valid searchable baseline on the same input/policy, except an explicitly chosen output feature with reported overhead. This is a selection invariant, not proof of superiority to another tool. When the original is already a smaller valid output candidate, include it.

For a production-value claim, preregister one of two hypotheses at M0: **compression benefit** (at least 10% median size reduction against the best fidelity-qualified external MRC comparator on a stated clean-text subset, while meeting safety and vector coverage) or **vector benefit at near-parity** (at least 80% median vector coverage with no more than 15% median size overhead against that comparator in explicit reconstruction mode, plus independent zoom/readability evidence). Report all domains either way. These are proposed product thresholds, not promised achievable outcomes.

Neither hypothesis permits hiding receipt/statement/Japanese regressions. If neither holds, report the negative result and stop generic infrastructure expansion. The operator can approve a narrower product with explicit limits; the agent cannot rename failure to success.

## 8. Milestones and stop points

| Milestone | Bounded deliverable | Gate / stop |
|---|---|---|
| M0 — feasibility and contracts | Pin dependencies/toolchain; import/geometry schemas; baseline pilot; tiny scanned-shape → compound outline → embedded TrueType → PDF probe, including `8`/`6`, a kana mark and multi-codepoint text; inspect holes on coloured background | Independent review of actual artifacts. Stop with a concrete blocker if an upstream API/interoperability route fails. Do not build CLI breadth or a generic pipeline yet. |
| M1 — useful one-page slice | Image+hOCR input, binding, original-shape fonts, supplied text, unique-glyph path, raster fallback, candidate render verification, distinct output | Real Latin + decorative + horizontal-kana pages; adversarial wrong OCR; no hidden full-resolution text copy. Stop for review. |
| M2 — safe hybrid documents | Protected financial regions; faint receipts; segmentation/ownership; non-text preservation; word-only input; mixed visible/invisible semantics | Receipt/statement/bill/book examples and all small-mark/overlap regressions; original never modified. Stop for review. |
| M3 — dictionary and economical output | Bounded cross-page dictionary, medoid checks, internal raster/MRC/hybrid candidates, actual byte selection, resumability/resource limits | Repeated-text real signal, short-receipt no-gain, 300-page memory run and deterministic replay. Stop for review. |
| M4 — script/PDF interoperability | Vertical Japanese, ruby/mixed orientations, Unicode edge cases; scan-PDF import and native/mixed passthrough; opaque document-feature policy | Independent rendering/extraction on declared support matrix. No universal-script claim from fallback alone. Stop for review. |
| M5 — qualified CLI/library release candidate | Frozen holdout, platform packaging, consumer example, documentation, reports, dependency notices | Complete evidence bundle and independent release review. No automatic publish/merge/release without operator authorization. |
| Optional host integration | PdfCraft optimized-export adapter, using existing library contract | Separate upstream change; not allowed to delay CLI qualification or couple core to UI. |

At each milestone: plan → independent plan review → failing behaviour tests → smallest implementation → complete relevant suite → independent artifact/code review → minimal repairs → ledger. Run the configured independent reviewer; where the usual `deepseek-reviewer` is available it fits minor gates, with a separate PR review for major changes. Do not fabricate reviewer availability or approval.

## 9. Performance evidence

Record named CPU/OS/RAM/storage, thread settings, dependency versions, page dimensions, pixel counts and font dictionaries. Separate source decode, OCR, segmentation/matching, tracing/font compilation, PDF assembly, validation and IO times. Report cold/warm caches and median/p95 page latency, maximum RSS, scratch peak and final size. A conversion benchmark excluding OCR says so prominently.

Initial resource target: 1,024 MiB managed memory and 4,096 MiB scratch on the declared ordinary-document workload, with long-document spool support and no unbounded growth. Large/complex inputs may explicitly require a larger budget or return ResourceLimit. Do not fabricate a throughput target from README claims; M0 measurements establish a budget before the performance gate is frozen.

User-visible runtime verification must be practical but mandatory for reconstructed output. M0 measures its cost. Release qualification uses two independent engines even if the runtime uses one pinned, qualified renderer plus structural checks. A production host may supply the renderer, but must identify it and cannot report unavailable checks as passed.
