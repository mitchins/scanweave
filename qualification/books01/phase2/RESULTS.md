# BOOKS-01 Phase 2 — development benchmark

36 development pages; 36 ScanWeave, 36 MRC, 36 OCRmyPDF and 30 Adobe outputs scored. Six pilot outputs were reused after source and output hash verification; the hOCR text matches after image-path redaction. Adobe uses default unmatched OCR language, no Fraktur support and deskews; GUI wall times include fixed sleeps and are not comparable to CLI times. Its retry recovered both Estor pages; six GUI-automation failures remain. The last four retries failed in about 52 seconds while the root filesystem was full, a possible contributing cause rather than an established cause (evidence: `$B/runs/adobe-p2-retry2/`). FineBooks are processed lossy-origin derivatives. Line pairing is approximate; matched tracks inherit hOCR boxes and cannot independently measure order. Detector counts are automated suspicions, unreviewed.

## Overall

| Row | Pages | Total MB | Median kB | Text SSIM | Text ink recall | Reading CER / WER | Diplomatic CER / WER | Bag recall | Text present | Literal / diplomatic hits | Median conversion s |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| sw-E | 36 | 16.32 | 419.7 | 0.957 | 0.974 | 0.337 / 0.788 | 0.336 / 0.749 | 0.930 | 36/36 | 340/396 · 394/396 | 20.5 |
| mrc-M | 36 | 4.08 | 99.8 | 0.842 | 0.951 | 0.340 / 0.784 | 0.337 / 0.753 | 0.929 | 36/36 | 339/396 · 395/396 | 3.6 |
| ocrmypdf-E | 36 | 257.24 | 5936.4 | 1.000 | 1.000 | 0.337 / 0.783 | 0.355 / 0.825 | 0.934 | 36/36 | 370/396 · 373/396 | 5.5 |
| adobe-E | 30 | 9.81 | 314.0 | 0.809 | 0.893 | 0.644 / 1.032 | 0.650 / 1.000 | 0.747 | 27/30 | 100/319 · 100/319 | 82.3 |

## Size and aligned fidelity by type and tag

Tag groups use the frozen selection tags; FineBooks volumes have no such tags and are grouped by volume.

| Group | Row | n | Total MB | Median kB | Text SSIM | Text recall | Ill. SSIM / recall / ΔE | Paper SSIM / recall |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Quiver fraktur | sw-E | 14 | 6.46 | 440.6 | 0.961 | 0.982 | 0.951 / 0.980 / 2.929 | 0.940 / 0.997 |
| Quiver fraktur | mrc-M | 14 | 1.26 | 88.2 | 0.775 | 0.965 | 0.761 / 0.907 / 4.915 | 0.758 / 0.988 |
| Quiver fraktur | ocrmypdf-E | 14 | 110.75 | 8608.1 | 1.000 | 1.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 |
| Quiver fraktur | adobe-E | 13 | 4.65 | 345.0 | 0.776 | 0.896 | 0.839 / 0.915 / 4.387 | 0.845 / 0.958 |
| tag: illustrations | sw-E | 6 | 1.99 | 344.8 | 0.963 | 0.979 | 0.969 / 0.969 / 2.672 | 0.948 / 0.994 |
| tag: illustrations | mrc-M | 6 | 0.46 | 76.4 | 0.814 | 0.951 | 0.802 / 0.880 / 4.876 | 0.821 / 0.982 |
| tag: illustrations | ocrmypdf-E | 6 | 38.59 | 5501.1 | 1.000 | 1.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 |
| tag: illustrations | adobe-E | 6 | 1.73 | 305.0 | 0.879 | 0.919 | 0.932 / 0.927 / 3.121 | 0.903 / 0.963 |
| tag: marginalia | sw-E | 7 | 3.62 | 355.3 | 0.965 | 0.973 | 0.950 / 0.980 / 3.070 | 0.945 / 0.999 |
| tag: marginalia | mrc-M | 7 | 0.87 | 85.4 | 0.841 | 0.912 | 0.715 / 0.967 / 5.463 | 0.824 / 0.991 |
| tag: marginalia | ocrmypdf-E | 7 | 68.83 | 8421.9 | 1.000 | 1.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 |
| tag: marginalia | adobe-E | 5 | 2.00 | 266.7 | 0.809 | 0.902 | 0.747 / 0.889 / 5.142 | 0.835 / 0.963 |
| tag: tables | sw-E | 3 | 1.51 | 501.5 | 0.950 | 0.989 | 0.951 / 0.983 / 3.076 | 0.931 / 0.998 |
| tag: tables | mrc-M | 3 | 0.27 | 88.5 | 0.741 | 0.965 | 0.720 / 0.973 / 5.535 | 0.688 / 0.986 |
| tag: tables | ocrmypdf-E | 3 | 23.12 | 9915.8 | 1.000 | 1.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 |
| tag: tables | adobe-E | 3 | 1.15 | 379.9 | 0.764 | 0.902 | 0.745 / 0.902 / 5.149 | 0.812 / 0.970 |
| tag: dark border/book edge | sw-E | 5 | 2.17 | 439.4 | 0.971 | 0.990 | 0.995 / 0.998 / 0.563 | 0.961 / 0.997 |
| tag: dark border/book edge | mrc-M | 5 | 0.44 | 87.3 | 0.823 | 0.939 | 0.761 / 0.999 / 4.915 | 0.820 / 0.915 |
| tag: dark border/book edge | ocrmypdf-E | 5 | 32.73 | 7816.5 | 1.000 | 1.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 |
| tag: dark border/book edge | adobe-E | 4 | 1.25 | 307.7 | 0.792 | 0.893 | 0.791 / 0.947 / 4.387 | 0.870 / 0.937 |
| Quiver fontmix | sw-E | 8 | 3.80 | 363.9 | 0.968 | 0.983 | 0.974 / 1.000 / 2.235 | 0.962 / 0.978 |
| Quiver fontmix | mrc-M | 8 | 0.98 | 91.7 | 0.842 | 0.925 | 0.773 / 0.999 / 5.125 | 0.823 / 0.904 |
| Quiver fontmix | ocrmypdf-E | 8 | 71.05 | 6533.7 | 1.000 | 1.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 |
| Quiver fontmix | adobe-E | 6 | 2.30 | 350.3 | 0.820 | 0.927 | 0.962 / 0.999 / 2.154 | 0.888 / 0.936 |
| Quiver antiqua | sw-E | 2 | 0.73 | 365.8 | 0.968 | 0.975 | — / — / — | 0.953 / 0.998 |
| Quiver antiqua | mrc-M | 2 | 0.15 | 74.2 | 0.811 | 0.943 | — / — / — | 0.765 / 0.992 |
| Quiver antiqua | ocrmypdf-E | 2 | 16.21 | 8105.8 | 1.000 | 1.000 | — / — / — | 1.000 / 1.000 |
| Quiver antiqua | adobe-E | 1 | 0.27 | 266.7 | 0.835 | 0.907 | — / — / — | 0.835 / 0.899 |
| FineBooks conchologiaiconi05reev | sw-E | 4 | 1.94 | 188.2 | 0.964 | 0.417 | 0.940 / 0.793 / 1.631 | 0.998 / 0.941 |
| FineBooks conchologiaiconi05reev | mrc-M | 4 | 0.49 | 108.8 | 0.933 | 0.627 | 0.937 / 0.765 / 1.800 | 0.998 / 0.955 |
| FineBooks conchologiaiconi05reev | ocrmypdf-E | 4 | 11.85 | 2708.8 | 1.000 | 1.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 |
| FineBooks conchologiaiconi05reev | adobe-E | 3 | 0.53 | 151.6 | 0.901 | 0.725 | 0.965 / 0.906 / 1.042 | 0.996 / 0.628 |
| FineBooks pisciumquerelaee00sche | sw-E | 4 | 1.71 | 427.6 | 0.944 | 0.954 | 0.866 / 0.992 / 4.488 | 0.988 / 0.921 |
| FineBooks pisciumquerelaee00sche | mrc-M | 4 | 0.70 | 140.9 | 0.883 | 0.964 | 0.873 / 0.971 / 4.250 | 0.981 / 0.914 |
| FineBooks pisciumquerelaee00sche | ocrmypdf-E | 4 | 26.46 | 6222.2 | 1.000 | 1.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 |
| FineBooks pisciumquerelaee00sche | adobe-E | 3 | 1.03 | 367.9 | 0.817 | 0.879 | 0.850 / 0.936 / 4.753 | 0.980 / 0.887 |
| FineBooks trudyrusskagoent161881russ | sw-E | 4 | 1.68 | 416.8 | 0.933 | 0.933 | 0.943 / 0.758 / 1.590 | 0.980 / 0.848 |
| FineBooks trudyrusskagoent161881russ | mrc-M | 4 | 0.50 | 129.3 | 0.912 | 0.964 | 0.933 / 0.843 / 1.841 | 0.956 / 0.852 |
| FineBooks trudyrusskagoent161881russ | ocrmypdf-E | 4 | 20.92 | 5175.9 | 1.000 | 1.000 | 1.000 / 1.000 / 0.000 | 1.000 / 1.000 |
| FineBooks trudyrusskagoent161881russ | adobe-E | 4 | 1.03 | 222.3 | 0.879 | 0.879 | 0.962 / 0.828 / 1.409 | 0.958 / 0.814 |

## Size–fidelity comparisons

A competitor matches when its text SSIM and ink recall are each no more than 0.01 below ScanWeave, and it is smaller. “ScanWeave better” requires both measures above the competitor by more than 0.01; these automated metrics do not establish visual defects.

| Competitor | Valid comparisons | ScanWeave better | Smaller competitor matches |
|---|---:|---:|---:|
| mrc-M | 36 | 21 | 0 |
| ocrmypdf-E | 36 | 0 | 0 |
| adobe-E | 28 | 25 | 1 |
- mrc-M, ScanWeave better: estor_rechtsgelehrsamkeit02_1758_0819, luther_babstum_1526_0010, luther_babstum_1526_0011, aventinus_grammatica_1515_0006, aventinus_grammatica_1515_0007, aventinus_grammatica_1515_0008, benner_herrnhuterey04_1748_0013, benner_herrnhuterey04_1748_0014, alberti_pictura_1540_0008, silesius_seelenlust01_1657_0010, silesius_seelenlust01_1657_0021, bohse_helicon_1696_0009, bohse_helicon_1696_0036, meyfart_rhetorica_1634_0021, meyfart_rhetorica_1634_0022, arnold_ketzerhistorie01_1699_0114, arnold_ketzerhistorie01_1699_0115, luther_auszlegunge_1520_0003, blumenbach_anatomie_1805_0047, 8966753, 12342014.
- mrc-M, smaller competitor matches: none.
- ocrmypdf-E, ScanWeave better: none.
- ocrmypdf-E, smaller competitor matches: none.
- adobe-E, ScanWeave better: estor_rechtsgelehrsamkeit02_1758_0007, estor_rechtsgelehrsamkeit02_1758_0819, euler_rechenkunst01_1738_0025, euler_rechenkunst01_1738_0031, luther_babstum_1526_0010, luther_babstum_1526_0011, aventinus_grammatica_1515_0006, aventinus_grammatica_1515_0007, aventinus_grammatica_1515_0008, benner_herrnhuterey04_1748_0013, benner_herrnhuterey04_1748_0014, alberti_pictura_1540_0008, silesius_seelenlust01_1657_0010, bohse_helicon_1696_0036, arnold_ketzerhistorie01_1699_0114, luther_auszlegunge_1520_0003, luther_auszlegunge_1520_0029, 8967333, 9684355, 9684335, 9684354, 12341923, 12342014, 12341934, 12342041.
- adobe-E, smaller competitor matches: bohse_helicon_1696_0009.

## Opportunity examples

Largest ScanWeave/MRC ratios; background attribution uses the largest non-mask image and DPI assumes page fill. Semantic-owner visible fraction is a vector-word proxy.

| Page | SW / MRC | SW background kB | SW font kB | MRC background + mask kB | SW visible fraction |
|---|---:|---:|---:|---:|---:|
| 8966753 | 7.89 | 984.9 | 213.6 | 134.4 | 0.392 |
| euler_rechenkunst01_1738_0031 | 6.33 | 453.2 | 0.5 | 50.9 | 0.000 |
| euler_rechenkunst01_1738_0025 | 5.90 | 428.3 | 0.5 | 52.4 | 0.000 |
| silesius_seelenlust01_1657_0021 | 5.74 | 336.5 | 2.7 | 41.6 | 0.000 |
| aventinus_grammatica_1515_0007 | 5.66 | 490.2 | 2.0 | 60.5 | 0.000 |
| luther_auszlegunge_1520_0029 | 5.60 | 585.6 | 3.8 | 76.9 | 0.000 |
| alberti_pictura_1540_0008 | 5.50 | 326.5 | 0.5 | 41.1 | 0.000 |
| luther_auszlegunge_1520_0003 | 5.50 | 679.8 | 0.5 | 94.5 | 0.000 |
| aventinus_grammatica_1515_0008 | 5.48 | 550.5 | 3.0 | 74.0 | 0.000 |
| aventinus_grammatica_1515_0006 | 5.41 | 576.3 | 2.2 | 79.6 | 0.000 |

## Render latency at 150 DPI

| Row | PDFium median s | Poppler median s | MuPDF median s |
|---|---:|---:|---:|
| sw-E | 0.014 | 0.612 | 0.015 |
| mrc-M | 0.040 | 1.295 | 0.052 |
| ocrmypdf-E | 0.020 | 0.565 | 0.017 |
| adobe-E | 0.024 | 0.992 | 0.018 |

## Anomalies

Per-page anomaly details and local example paths are in `results.json`. Crops show the same region across rows; low-text-SSIM cases target a difference, while other cases use page-centre context. A source has no text layer by design; source emptiness is excluded.

| Page | Anomalies | Local example |
|---|---|---|
| 8966753 | conversion_time_over_2x_median ×1, missing_or_failed ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/8966753.png |
| 8967228 | document_cer_above_hocr_by_0.05 ×1, registration_unaccepted ×1 | /data/coding/scanweave/work/books01/phase2/examples/8967228.png |
| 8967333 | twice_competitor_size ×2 | /data/coding/scanweave/work/books01/phase2/examples/8967333.png |
| 9684335 | conversion_time_over_2x_median ×1, text_ssim_below_0.80 ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/9684335.png |
| 9684341 | missing_or_failed ×1 | /data/coding/scanweave/work/books01/phase2/examples/9684341.png |
| 9684354 | conversion_time_over_2x_median ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/9684354.png |
| 9684355 | conversion_time_over_2x_median ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/9684355.png |
| 12341923 | twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/12341923.png |
| 12341934 | conversion_time_over_2x_median ×1, twice_competitor_size ×2 | /data/coding/scanweave/work/books01/phase2/examples/12341934.png |
| 12342014 | conversion_time_over_2x_median ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/12342014.png |
| 12342041 | conversion_time_over_2x_median ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/12342041.png |
| alberti_pictura_1540_0008 | text_ssim_below_0.80 ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/alberti_pictura_1540_0008.png |
| arnold_ketzerhistorie01_1699_0114 | conversion_time_over_2x_median ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/arnold_ketzerhistorie01_1699_0114.png |
| arnold_ketzerhistorie01_1699_0115 | conversion_time_over_2x_median ×1, missing_or_failed ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/arnold_ketzerhistorie01_1699_0115.png |
| aventinus_grammatica_1515_0006 | conversion_time_over_2x_median ×1, text_ssim_below_0.80 ×2, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/aventinus_grammatica_1515_0006.png |
| aventinus_grammatica_1515_0007 | conversion_time_over_2x_median ×1, text_ssim_below_0.80 ×2, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/aventinus_grammatica_1515_0007.png |
| aventinus_grammatica_1515_0008 | conversion_time_over_2x_median ×1, text_ssim_below_0.80 ×2, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/aventinus_grammatica_1515_0008.png |
| benner_herrnhuterey04_1748_0013 | twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/benner_herrnhuterey04_1748_0013.png |
| benner_herrnhuterey04_1748_0014 | twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/benner_herrnhuterey04_1748_0014.png |
| blumenbach_anatomie_1805_0047 | missing_or_failed ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/blumenbach_anatomie_1805_0047.png |
| bohse_helicon_1696_0009 | empty_text_layer ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/bohse_helicon_1696_0009.png |
| bohse_helicon_1696_0036 | text_ssim_below_0.80 ×2, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/bohse_helicon_1696_0036.png |
| estor_rechtsgelehrsamkeit02_1758_0007 | twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/estor_rechtsgelehrsamkeit02_1758_0007.png |
| estor_rechtsgelehrsamkeit02_1758_0819 | text_ssim_below_0.80 ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/estor_rechtsgelehrsamkeit02_1758_0819.png |
| euler_rechenkunst01_1738_0025 | text_ssim_below_0.80 ×2, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/euler_rechenkunst01_1738_0025.png |
| euler_rechenkunst01_1738_0031 | text_ssim_below_0.80 ×2, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/euler_rechenkunst01_1738_0031.png |
| luther_auszlegunge_1520_0003 | twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/luther_auszlegunge_1520_0003.png |
| luther_auszlegunge_1520_0029 | text_ssim_below_0.80 ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/luther_auszlegunge_1520_0029.png |
| luther_babstum_1526_0010 | text_ssim_below_0.80 ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/luther_babstum_1526_0010.png |
| luther_babstum_1526_0011 | text_ssim_below_0.80 ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/luther_babstum_1526_0011.png |
| meyfart_rhetorica_1634_0021 | empty_text_layer ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/meyfart_rhetorica_1634_0021.png |
| meyfart_rhetorica_1634_0022 | missing_or_failed ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/meyfart_rhetorica_1634_0022.png |
| silesius_seelenlust01_1657_0010 | text_ssim_below_0.80 ×2, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/silesius_seelenlust01_1657_0010.png |
| silesius_seelenlust01_1657_0021 | empty_text_layer ×1, registration_unaccepted ×1, text_ssim_below_0.80 ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/silesius_seelenlust01_1657_0021.png |
| silesius_seelenlust01_1657_0423 | missing_or_failed ×1, text_ssim_below_0.80 ×1, twice_competitor_size ×1 | /data/coding/scanweave/work/books01/phase2/examples/silesius_seelenlust01_1657_0423.png |

All page × row metrics, byte attribution, opportunity inputs, anomaly details and scatter data are in `results.json`; renderer peak RSS and individual timing samples are included per row.
