# STROKE-01 — corrected local ink experiment

**Verdict: the corrected local model is promising on synthetic faded strokes, but is not ready for converter integration.** Claude identified the original crop-wide darkest-4% estimate as a calibration error: sparse glyph pixels were diluted by paper and antialiasing, making ink too light and masks too thick. Replacing it with component-local stroke-centre estimates largely removes that defect and reverses the earlier negative synthetic conclusion. It does not yet establish safe page-level reconstruction, especially for small details and illustration boundaries. No converter was changed.

## Method and calibration

Local paper is the same smooth percentile field as before. A residual threshold relative to measured background variation proposes connected components; their skeleton centres with strong residuals provide per-component RGB ink estimates. Components with fewer than four core samples can borrow from a nearby sufficiently sampled component. A size bound excludes a large contiguous illustration from text-core estimates. This is **not** a semantic text/illustration classifier: small illustration fragments and text touching artwork remain unresolved. The estimated ink is an effective observed stroke colour, not proof of the underlying physical ink. Its uncertainty is robust core-residual dispersion divided by contrast, not a calibrated confidence interval.

Method 1 projects each observation onto its local paper–ink vector. Method 2 uses the same edge-weighted label energy as before, optimized by ICM from method 1; ICM is a weak local optimizer, not an exact graph cut or Howe's full method. Method 3 fits skeleton widths and an effective Gaussian PSF; it does not guarantee topology. In displayed images, unsupported regions retain source raster. The baseline below is ScanWeave's existing **foreground mask**, not its complete PDF rendering.

The decline gate was calibrated only on DejaVu Serif and Liberation Serif Regular synthetic cases. A “correct” accepted method-1 case requires boundary F1 ≥ .90, missing and false ink each ≤ .20 of GT ink, and zero false joins. A finite grid maximised coverage at ≥90% training precision; it chose **component-weighted contrast/noise ≥4 and relative core dispersion ≤.20**, plus the proposal's basic low-contrast refusal. This is a crop-level experiment, not a per-glyph guarantee. On training, **49/54 accepted** met that criterion; on the held-out Liberation Serif Italic font, **26/27 accepted** met it, including all 26 cases that met the criterion. The italic font appeared in the prior experiment and aggregate development results were inspected, so this is not an independent test of model selection. No-evidence cases were all declined. A single wrong accepted case and real-image component merging are material limitations.

## Synthetic ground truth

105 cases: seven glyph or adjacent-glyph shapes in three system fonts, with clear, faded, broken, no-evidence and two-ink conditions. The new two-ink case puts a grey glyph near a large brown illustration blob; text scores exclude the separate blob region for every method, and blob classification is reported separately. Existing 300/500-DPI blur, texture, noise and JPEG simulation is unchanged for the original cases. Results do not establish performance on unseen historical images.

Each raw row has 21 cases. Entries are mean **boundary F1 / missing ink / false ink**, with ink areas divided by GT ink area. After-gate entries score **accepted cases only**; declined cases retain the raster and have no invented binary-mask score. A `—` therefore means every case declined, not zero error. False-join totals are raw / accepted.

| Condition | Method | Raw F1 / missing / false | After gate F1 / missing / false | False joins raw / accepted |
|---|---|---:|---:|---:|
| clear (21/21 accepted) | baseline | 0.993 / 0.090 / 0.011 | 0.993 / 0.090 / 0.011 | 0 / 0 |
| clear (21/21 accepted) | local | 0.990 / 0.020 / 0.116 | 0.990 / 0.020 / 0.116 | 0 / 0 |
| clear (21/21 accepted) | energy | 0.990 / 0.008 / 0.207 | 0.990 / 0.008 / 0.207 | 0 / 0 |
| clear (21/21 accepted) | geometry | 0.979 / 0.157 / 0.154 | 0.979 / 0.157 / 0.154 | 0 / 0 |
| faded (21/21 accepted) | baseline | 0.000 / 1.000 / 0.000 | 0.000 / 1.000 / 0.000 | 0 / 0 |
| faded (21/21 accepted) | local | 0.993 / 0.029 / 0.090 | 0.993 / 0.029 / 0.090 | 0 / 0 |
| faded (21/21 accepted) | energy | 0.986 / 0.012 / 0.201 | 0.986 / 0.012 / 0.201 | 0 / 0 |
| faded (21/21 accepted) | geometry | 0.987 / 0.073 / 0.117 | 0.987 / 0.073 / 0.117 | 0 / 0 |
| broken (18/21 accepted) | baseline | 0.876 / 0.315 / 0.010 | 0.921 / 0.242 / 0.011 | 0 / 0 |
| broken (18/21 accepted) | local | 0.933 / 0.205 / 0.082 | 0.952 / 0.155 / 0.083 | 0 / 0 |
| broken (18/21 accepted) | energy | 0.940 / 0.186 / 0.155 | 0.959 / 0.135 / 0.159 | 0 / 0 |
| broken (18/21 accepted) | geometry | 0.914 / 0.315 / 0.095 | 0.930 / 0.272 / 0.098 | 0 / 0 |
| no_evidence (0/21 accepted) | baseline | 0.000 / 1.000 / 0.000 | — | 0 / — |
| no_evidence (0/21 accepted) | local | 0.086 / 0.939 / 0.013 | — | 0 / — |
| no_evidence (0/21 accepted) | energy | 0.082 / 0.938 / 0.016 | — | 0 / — |
| no_evidence (0/21 accepted) | geometry | 0.075 / 0.942 / 0.017 | — | 0 / — |
| two_inks (21/21 accepted) | baseline | 0.992 / 0.091 / 0.012 | 0.992 / 0.091 / 0.012 | 0 / 0 |
| two_inks (21/21 accepted) | local | 0.998 / 0.024 / 0.074 | 0.998 / 0.024 / 0.074 | 0 / 0 |
| two_inks (21/21 accepted) | energy | 0.999 / 0.010 / 0.167 | 0.999 / 0.010 / 0.167 | 1 / 1 |
| two_inks (21/21 accepted) | geometry | 0.988 / 0.163 / 0.124 | 0.988 / 0.163 / 0.124 | 1 / 1 |

Local-mask exact component-and-hole counts were **19/21 clear, 21/21 faded, 1/21 broken and 21/21 two-ink**; recovering a plausible faded shape is not a guarantee of repairing a broken one. Across 105 cases local produced **zero false joins**; energy and geometry each produced one in the two-ink condition. The synthetic blob contributed 0% of core and supported pixels on average, but it was one large connected, separated shape and does not validate exclusion of fragmented illustrations. [Two-ink panel](/data/coding/scanweave/work/books01/stroke01/corrected/panels/synthetic-6-two_inks.png), [faded adjacent glyphs](/data/coding/scanweave/work/books01/stroke01/corrected/panels/synthetic-rn-faded.png), and [broken numeral](/data/coding/scanweave/work/books01/stroke01/corrected/panels/synthetic-6-broken.png) show the actual masks.

## Real dev crops

For each crop the table gives the calibrated gate decision and **baseline → local** source-ink recall / mean ΔE2000 over source pixels at least 20 luma below local paper. These are visual diagnostics, not glyph ground truth; local output includes preserved source pixels outside accepted component support. Source/ScanWeave/local/energy/geometry/rescan-residual/MRC/Adobe panels are linked. Adobe's heading registration fails the existing gate and is unavailable.

| Crop | Gate | Baseline → local: recall / ΔE | Observation |
|---|---|---:|---|
| [8967062](/data/coding/scanweave/work/books01/stroke01/corrected/panels/8967062-gated.png) | accept | 0.857 / 6.96 → 0.986 / 1.95 | Grey and more continuous than baseline; two numeral regions are merged in the proposal, so identity is unproven. |
| [8967228](/data/coding/scanweave/work/books01/stroke01/corrected/panels/8967228-gated.png) | raster | 0.795 / 8.89 → 0.991 / 2.65 | Raw local result is less orange, but high dispersion causes raster fallback. |
| [12342014](/data/coding/scanweave/work/books01/stroke01/corrected/panels/12342014-gated.png) | accept | 0.932 / 6.54 → 0.994 / 2.50 | Local view is close to source; unsupported dots remain raster. No proven legibility gain. |
| [euler_rechenkunst01_1738_0025](/data/coding/scanweave/work/books01/stroke01/corrected/panels/euler_rechenkunst01_1738_0025-gated.png) | accept | 0.996 / 0.69 → 1.000 / 0.73 | Local view resembles source; exact Fraktur topology is unverified. |
| [luther_babstum_1526_0011](/data/coding/scanweave/work/books01/stroke01/corrected/panels/luther_babstum_1526_0011-gated.png) | accept | 0.895 / 9.75 → 0.991 / 7.21 | Local view resembles source, but colour and fine stroke changes need validation. |

The heading's local numbers above are **raw**, although its displayed gated panel retains the source. For 613, the two numerically dominant numeral proposals have sRGB `K` **[174,172,143]** (relative core dispersion .124) and **[184,183,151]** (.263); the first proposal spans parts of more than one digit. These are estimates in the local crop, not the true inks. A separate nearby [shell ROI](/data/coding/scanweave/work/books01/stroke01/corrected/shell-roi.png) has median sRGB **[145,120,87]** among its darkest 10% of observed pixels. The shell is multicoloured; that measurement is a reference, not a fitted single shell ink. The 613 text crop does not contain the whole shell, so the two-ink synthetic case, rather than this colour comparison, exercises their proximity.

The original [Gatos](https://users.iit.demokritos.gr/~sper/PAPERS/2006J-GatosPratikakisPerantonis-PR39.pdf), [Howe](https://www.science.smith.edu/~nhowe/research/pubs/icdar11.pdf), [Epshtein et al.](https://iacl.ece.jhu.edu/proceedings/cvpr2010/papers/1509.pdf), [Sober–Levin](https://arxiv.org/abs/1602.07038), and [Hanif et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC10032482/) motivate the modelling choices; this prototype does not implement those complete methods. No OCR-based repeated-letter prior or glyph-sharing change is used.

Synthetic evidence now supports further study, but the real images lack latent GT, per-component confidence is not validated, and strong PDF/compression/readability gains have not been demonstrated. No PDF was generated, so output size, PDF render time, OCR/search and ownership changes are not measured. Five focused tests passed. Reproducible code, exact versions, font hashes, aggregated scores and calibration details are in [research/stroke01](/data/coding/scanweave/work/stroke01/research/stroke01/README.md); original and corrected local evidence are both preserved under `$B/stroke01/`.
