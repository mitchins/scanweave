# BOOKS-01 Phase 1: six-page pilot

The six frozen pilot pages were run. Holdout and other dev pages were not run. Existing Adobe files were ingested only. See `track-matrix.md`, `versions.json`, `methodology.md` and `results/` for methods, versions and machine-readable rows. No final smallest-acceptable ranking is made.

## Size (bytes)

| Pilot page | src | sw-E | sw-M | sw-build | ocrmypdf-E | mrc-M | adobe-E |
|---|---:|---:|---:|---:|---:|---:|---:|
| aventinus_grammatica_1515_0008 | 10289513 | 567928 | 567928 | 576609 | 10301842 | 103604 | 509174 |
| luther_babstum_1526_0011 | 9377387 | 441781 | 441781 | 441781 | 9385962 | 98623 | 345022 |
| arnold_ketzerhistorie01_1699_0114 | 17138441 | 927973 | 927973 | 927973 | 17161011 | 246622 | 794311 |
| benner_herrnhuterey04_1748_0013 (low DPI confidence) | 7805527 | 420009 | 420009 | 424393 | 7816515 | 100806 | 322434 |
| 8967333 | 611306 | 215146 | 215146 | 226174 | 618300 | 91088 | 63983 |
| 12342014 | 4955345 | 554944 | 554944 | 637972 | 4972564 | 137040 | 396265 |

## OCR versus extraction

Reading CER uses known-character denominator with U+FFFD wildcards, and includes reading-order errors. It does not measure visual reconstruction. Frozen hOCR is the matched pre-PDF OCR.

| Pilot page | Known chars | U+FFFD | Frozen hOCR CER | sw-M PDFium CER | Adobe PDFium CER |
|---|---:|---:|---:|---:|---:|
| aventinus_grammatica_1515_0008 | 1453 | 0 | 0.555 | 0.559 | 0.806 |
| luther_babstum_1526_0011 | 600 | 0 | 0.227 | 0.227 | 0.643 |
| arnold_ketzerhistorie01_1699_0114 | 5918 | 0 | 0.376 | 0.375 | 0.851 |
| benner_herrnhuterey04_1748_0013 (low DPI confidence) | 879 | 0 | 0.402 | 0.398 | 0.730 |
| 8967333 | 322 | 0 | 0.019 | 0.019 | 0.267 |
| 12342014 | 3327 | 0 | 0.554 | 0.555 | 0.373 |

## Visual fidelity at source DPI, PDFium

Values are text-region SSIM / ink recall; a dash means no measurable denominator. These are automated measurements, not confirmed defect counts. Full renderer, resolution, class, ΔL, colour and precision data are in `results/visual.json`.

| Pilot page | sw-E | OCRmyPDF | MRC | Adobe |
|---|---:|---:|---:|---:|
| aventinus_grammatica_1515_0008 | 0.951 / 0.986 | 1.000 / 1.000 | 0.745 / 0.962 | 0.349 / 0.557 |
| luther_babstum_1526_0011 | 0.977 / 0.966 | 1.000 / 1.000 | 0.802 / 0.897 | 0.198 / 0.210 |
| arnold_ketzerhistorie01_1699_0114 | 0.978 / 0.970 | 1.000 / 1.000 | 0.845 / 0.866 | 0.262 / 0.362 |
| benner_herrnhuterey04_1748_0013 (low DPI confidence) | 0.968 / 0.989 | 1.000 / 1.000 | 0.845 / 0.937 | 0.500 / 0.635 |
| 8967333 | 0.975 / 0.981 | 1.000 / 1.000 | 0.947 / 0.857 | 0.899 / 0.720 |
| 12342014 | 0.932 / 0.884 | 1.000 / 1.000 | 0.894 / 0.696 | 0.843 / 0.784 |

## Conversion wall time (seconds)

Adobe timing includes GUI sleeps and startup and is not comparable to CLI times. Per-row CPU, peak RSS and renderer timing distributions are in `results/performance.json` and `results/render-costs.json`.

| Pilot page | sw-E | sw-M | sw-build | OCRmyPDF | MRC | Adobe GUI |
|---|---:|---:|---:|---:|---:|---:|
| aventinus_grammatica_1515_0008 | 45.2 | 41.6 | 37.8 | 5.5 | 3.5 | 101.3 |
| luther_babstum_1526_0011 | 4.6 | 3.7 | 1.6 | 4.8 | 3.3 | 82.3 |
| arnold_ketzerhistorie01_1699_0114 | 23.8 | 9.2 | 3.4 | 22.0 | 6.4 | 82.3 |
| benner_herrnhuterey04_1748_0013 (low DPI confidence) | 16.0 | 14.3 | 10.2 | 6.4 | 3.2 | 82.3 |
| 8967333 | 9.1 | 8.6 | 8.0 | 2.0 | 2.3 | 82.3 |
| 12342014 | 53.7 | 45.8 | 44.0 | 10.5 | 3.7 | 82.3 |

## Path comparison

Stock PDF import uses internal OCR and `convert_document_with_sources_and_sharing` with source images; `build --ocr --profile clearscan` calls single-page `convert` without source images and is diagnostic only. All six sw-E and sw-M PDF bytes match. Raw hOCR differs on all six only because the input image path embedded in hOCR differs; after redacting that field, all match. PSM 3 and PSM 6 frozen OCR were each deterministic in repeated runs. The shim checks pixel hash, exact arguments and call order. All three negative tests rejected their input and produced no PDF.

| Pilot page | sw-M bytes | build bytes | PDF bytes equal? | Extracted text equal? | Changed rendered pixels at 150 DPI |
|---|---:|---:|---|---|---:|
| aventinus_grammatica_1515_0008 | 567928 | 576609 | False | True | 0.000000 |
| luther_babstum_1526_0011 | 441781 | 441781 | True | True | 0.000000 |
| arnold_ketzerhistorie01_1699_0114 | 927973 | 927973 | True | True | 0.000000 |
| benner_herrnhuterey04_1748_0013 (low DPI confidence) | 420009 | 424393 | False | True | 0.000000 |
| 8967333 | 215146 | 226174 | False | True | 0.000000 |
| 12342014 | 554944 | 637972 | False | True | 0.000000 |

## Alignment and triage

FineBooks has no GT TextLines. Single-line TextRegions are proxies only; their coverage is reported below, with region-level metrics for the remainder. OCR overlap uses word-box centres. Alignment overlays and the blind pack are local under `$B/qa/pilot-alignment/` and `$B/pilot/blind/`.

| Pilot page | GT geometry | Lines / proxies | Known chars covered | OCR word centres inside |
|---|---|---:|---:|---:|
| aventinus_grammatica_1515_0008 | TextLine | 54 | 1414 | 0.971 |
| luther_babstum_1526_0011 | TextLine | 19 | 580 | 0.972 |
| arnold_ketzerhistorie01_1699_0114 | TextLine | 159 | 5807 | 0.967 |
| benner_herrnhuterey04_1748_0013 (low DPI confidence) | TextLine | 44 | 866 | 0.950 |
| 8967333 | single-line TextRegion proxy | 3 | 32 | 0.089 |
| 12342014 | single-line TextRegion proxy | 107 | 3166 | 0.978 |

The blind pack contains 66 crops; top candidates and random controls are identified only as suspected or controls. Per-page 99.5th-percentile score distributions are in `results/triage.json`; raw scores are local. Confirmed defects are **not yet adjudicated**, rather than zero.

The first OCRmyPDF attempt on Luther failed because the isolated Tesseract directory lacked its `txt` config; the unchanged system config was added, hashed, and that page was retried successfully. The Adobe repeat PDFs have identical Poppler-extracted text on all six pages and size differences of at most one byte. The GUI wall times are not CLI benchmarks. Claude’s offline logs record 104 and 198 refused Wine service-thread internet-socket attempts in the current and superseded batches respectively; no Adobe process was started here.

## Costs and readiness

Logical disk bytes by pilot stage: {'ocr-frozen': 44960818, 'pilot/runs': 94969091, 'pilot/renders': 742240684, 'pilot/blind': 3078359, 'qa/pilot-alignment': 35955825, 'runs/adobe': 2600426}. Renderer timings use five warm runs after a warm-up; p95 is nearest-rank, hence the maximum of five. GNU time records CPU and peak RSS for commands. Poppler uses CropBox where the PDF has a distinct CropBox; the other PDFs have equal page boxes. Earlier abandoned MediaBox and CropBox rerender attempts are not completely attributed in the per-row cost totals.

The six-page sequential CLI totals by row are {'sw-E': 152.39423341630027, 'sw-M': 123.30645191506483, 'sw-build': 104.97759772092104, 'ocrmypdf-E': 51.26848350535147, 'mrc-M': 22.382319086929783}; multiplying these measured values by six gives {'sw-E': 914.3654004978016, 'sw-M': 739.838711490389, 'sw-build': 629.8655863255262, 'ocrmypdf-E': 307.6109010321088, 'mrc-M': 134.2939145215787} seconds. This is a linear projection, not a runtime guarantee; Adobe is excluded.

Recommendation: **not ready to run all 36 pages yet**. Claude must adjudicate the blinded candidates and the owner must review the proposed acceptance thresholds. FineBooks proxy coverage varies; the simple PDFium line grouper can merge columns; exact-text Kendall tau excludes unmatched lines; byte attribution leaves dictionary/xref/other bytes in a reconciled residual and cannot isolate compressed text-layer bytes from other page-content bytes. OCRmyPDF’s lossless source retention is a control, not proof that other rows preserve visible glyphs.

Open items: the reading-normalization rules follow the approved spec but were not independently checked against the external FineBooks evaluator; the Phase 0 low-confidence DPI remains accepted for this pilot, not validated; some tool and measurement startup/aborted-attempt costs are not fully captured. No Adobe or Wine process was run.
