# BOOKS-01 Phase 1b — six-page corrected re-score

**Recommendation: keep Phase 2 on hold.** The geometry correction exposes useful differences, but detector calibration remains sparse, some controls exhibit changes the detectors missed, and PDF character grouping produces uncertain line matches. The owner should review the local blinded panel, resolve the proposed acceptance rule, and validate line grouping and detector calibration on an adequately labelled sample before expansion. All crop verdicts in this report are **AI-assessed, provisional (not human-adjudicated)**. No new benchmark conversions, OCR runs, source substitutions, holdout access or Acrobat/Wine execution occurred.

All 252 output × renderer × resolution cells met the predeclared global registration test, including exact identity cases. The source-to-output page geometry remains separately reported; only a global output-to-source similarity was used for alignment. For Adobe, native and aligned text-region scores below are PDFium at source DPI. Rotations, translations and fit errors are PDFium at 150 DPI; translations are pixels and fit error is 95th-percentile displacement at 150-DPI equivalent. These inverse-map rotation signs differ from output straightening signs.

| Page | Adobe rotation ° | scale | translation x,y | outside source grid | residual p95 px | text SSIM native → aligned | ink recall native → aligned |
|---|---:|---:|---:|---:|---:|---:|---:|
| aventinus 0008 | +0.372 | 0.99952 | +4.67, −3.05 | 1.31% | 1.78 | .349 → .764 | .557 → .902 |
| luther 0011 | +0.821 | 1.00024 | +9.12, −6.60 | 1.61% | 1.59 | .198 → .800 | .210 → .890 |
| arnold 0114 | −0.501 | 1.00004 | −8.46, +3.86 | 1.35% | 2.24 | .262 → .809 | .362 → .880 |
| benner 0013 | +0.364 | 0.99961 | +4.35, −2.54 | 1.41% | 1.89 | .500 → .809 | .635 → .902 |
| 8967333 | +0.102 | 1.00001 | +1.02, −1.41 | 0.72% | 1.31 | .899 → .924 | .720 → .766 |
| 12342014 | −0.011 | 1.00022 | +0.12, −0.31 | 0.78% | 1.65 | .843 → .891 | .784 → .875 |

Every Adobe page box differs from source. Outside-grid percentages are sampling-based possible coverage loss, not proven content loss. Registration cannot repair real damage; resampling itself affects aligned scores. The complete scorecard records transforms, page boxes, residuals and native/aligned region metrics for every row, renderer and DPI. An independent high-pass phase-correlation check of MRC versus source on 8967333 at 75 DPI found a [0,0] integer-pixel displacement, versus the review's approximately four-pixel estimate; the 150-DPI SIFT translation is near zero. Claude accepts the near-zero MRC shift on 8967333; the earlier ‘4 px’ came from phase correlation on a 4× downsampled render, one quantisation step of a coarse method, and is not a measured shift.

Adobe throughout means **Acrobat default OCR language (not matched); no Fraktur support; page straightened (deskew)**. The original native Adobe renders are retained. In the first batch, 2026-11-14, host `LANG=en_GB.UTF-8` led Wine to resynchronise the prefix international locale to en-GB, including keyboard preload and codepage; the repeat with `LANG=en_US.UTF-8` restored en-US. Text was identical and sizes differed by at most one byte. Wine also auto-registered newly installed host fonts and Acrobat changed its recent-files list; Acrobat OCR/output settings did not change. Registry evidence hashes and isolation details are in `results/adobe-isolation.json`.

## OCR and search

**Correction:** The previous table used a PDFium grouping that split and mispaired lines, and the hOCR parser omitted captions, headers and floating text. The matched-track score now partitions actual PDFium text by a monotonic character alignment to frozen hOCR line boundaries, with hOCR boxes for GT matching. Six examples with the GT, frozen-hOCR, previously grouped PDFium and corrected PDFium texts are stored locally at `$B/pilot/phase1b/line-diagnosis-examples.json`; text-free line indices and edit counts are in `results/phase1b/line-diagnosis.json`. For example, old PDF-to-frozen character edit counts for three Aventinus lines were 95, 71 and 55; the corrected counts are 0, 1 and 0. Three Luther examples changed from 29, 28 and 3 to 0, 0 and 0. Text and GT remain local.

The table shows `sw-M` on the same GT lines as frozen hOCR. CER and WER are frozen → PDFium; ΔMRC is the absolute change in MRC PDFium CER relative to frozen on the same GT lines. Unmatched GT is unmatched by the frozen-box matcher, not confirmed missing text. PDF line geometry and order are not independently assessed by this matched-track procedure, so Kendall τ is unavailable for these rows. Search is hits among GT words recognised in frozen OCR. The complete scorecard retains all rows, document-level scores and search controls. FineBooks uses single-line region proxies only: 8967333 covers 3 proxies / 32 known chars; 12342014 covers 107 / 3,169.

| Page | GT lines/proxies | shared | CER | WER | unmatched GT / char share | extra | recognised-word search | ΔMRC CER |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| aventinus 0008 | 54 | 33 | .636 → .639 | 1.226 → 1.207 | 21 / 23.2% | 0 | 6/7 | −.0009 |
| luther 0011 | 19 | 17 | .172 → .172 | .677 → .677 | 2 / 7.0% | 0 | 7/9 | .0000 |
| arnold 0114 | 159 | 150 | .189 → .191 | .533 → .544 | 9 / 1.7% | 16 | 9/12 | +.0014 |
| benner 0013 | 44 | 35 | .282 → .285 | .648 → .656 | 9 / 11.2% | 1 | 9/13 | +.0013 |
| 8967333 | 3 | 3 | .031 → .031 | .200 → .200 | 0 / 0.0% | 6 | 18/18 | .0000 |
| 12342014 | 107 | 103 | .456 → .459 | .774 → .775 | 4 / 2.6% | 56 | 15/15 | .0000 |

Across the six pages the maximum absolute `sw-M` CER difference is 0.0032 and the maximum for `mrc-M` is 0.0014. These residuals reflect the actual extracted characters and line partition; non-space PDFium characters are accounted for. The procedure does not prove text identity or remove the need to inspect reading order.

These line scores must be interpreted cautiously: non-matched rows use sequential PDFium grouping, while matched rows inherit frozen hOCR boxes; fragmented boxes, one-to-one IoU pairing and different line segmentation can create apparent omissions or additions. FineBooks region text is not invented as lines. French page 12342014 has frozen OCR known-character bag recall approximately 64.5%, a recognition limitation independent of whether the raster is visually preserved. Benner's DPI has low confidence and is flagged on every result row.

## Defect calibration

Reference: 66 prior crops, with AI-assessed provisional labels joined to the old key. The in-sample calibration is not independent validation. Minimum dimension separates <10 source px from ≥10 px; tiny content is not suppressed. P/R are precision/recall; — means undefined for that sample.

| Detector | positive / negative | P / R, all | P / R, <10 px (positive/negative) | P / R, ≥10 px (positive/negative) |
|---|---:|---:|---:|---:|
| glyph shape | 8 / 8 | .800 / 1.000 | — / — (0/2) | .800 / 1.000 (8/6) |
| missing ink | 8 / 8 | .727 / 1.000 | .000 / — (0/2) | .800 / 1.000 (8/6) |
| spurious ink | 0 / 7 | — / — | — / — (0/1) | — / — (0/6) |
| illustration colour | 2 / 0 | — / 1.000 | — / — (0/0) | — / 1.000 (2/0) |
| border inversion | 0 / 12 | — / — | — / — (0/0) | — / — (0/12) |

The fresh fixed-seed sample contains 36 page × output controls, assessed nonblind by an AI: among labelled glyph examples, P/R were .50/1.00 (one positive, 22 negatives); for missing ink 1.00/1.00 (one positive, 22 negatives). There were no labelled positive tiny examples, so tiny-defect recall is unknown. Correctly flagged examples include Luther MRC crops 0014, 0016, 0017 (strokes) and 0019/0020 (artwork); false positives include 8967333 Adobe crops 0045/0046 (glyph) and Luther Adobe 0015 (missing ink). Fresh controls `fresh-029` (8967333 MRC) and `fresh-035` (12342014 MRC) exhibit provisionally assessed texture/colour changes not flagged by text detectors. They do not establish a human-confirmed defect. Text-only crops 0007/0008 were excluded from illustration-colour calibration. No in-sample labelled glyph/missing positives were missed, but the sample is far too small to infer general recall.

Full aligned triage examined 12,030 word candidates and flagged 2,504 glyph and 2,248 missing-ink suspicions; illustration and border triage flagged 10 and 3. These are candidate counts, not defect counts. Raw scores are kept locally and calibration scores are committed; review, not an automated IoU threshold, determines material defects.

## Human panel and decisions

A local self-contained 20-crop panel uses the same crop locations with fresh anonymous per-crop labels and four outputs: ScanWeave sw-E, OCRmyPDF, Archive MRC and Adobe. It shows source and outputs at 4× nearest-neighbour, with a response taxonomy, free-text notes and JSON export. Source-preserving outputs can still be visually recognisable by their identical pixels; eliminating duplicate ScanWeave tracks does not guarantee perfect blinding. Its committed index and HTML hash are in `results/phase1b/human-panel-index.json`; the mapping remains sealed locally. The proposal in `acceptance-proposal.md` separates visual, OCR/search, geometry and human confirmation, and includes conditional examples. It is not frozen and no size ranking is computed. FineBooks access images remain `lossy-origin` and `processed-derivative`; Quiver pages use original TIFFs.
