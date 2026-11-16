# STROKE-01 — offline stroke reconstruction proof of concept

**Verdict: not ready for converter integration.** Local fractional coverage recovers much of the faint “613” that the existing global mask omits, but the local ink estimate remains brown and the resulting strokes are not demonstrably correct. All three tested methods add substantial false ink to synthetic ground truth; the energy and geometry variants can join distinct components. A better simulated-scan fit alone cannot establish stroke identity. No converter, glyph sharing or output PDF was changed.

## What was tested

Five native image crops were extracted losslessly from the dev source PDFs with `pdfimages` 24.02.0; each includes surrounding local context. The source PDF, existing baseline, MRC and Adobe outputs were reused. Adobe's heading registration fails the BOOKS-01 gate and is unavailable in that panel. Euler and Luther are controls. This crop PoC does **not** identify the physical page edge, classify illustration or show-through, or process a whole page.

In linear-light RGB, the prototype estimates a slowly varying background from a downsampled local 80th percentile, and estimates one crop-level ink colour from the darkest 4% of background-subtracted observations. It projects each observation onto the paper–ink colour vector to estimate fractional coverage. The sigmoid probability map and a contrast/noise confidence score are **heuristics, not calibrated probabilities**. A low-contrast crop is marked for raster fallback; diagnostic masks are still computed to expose the consequences of a missed refusal.

The four comparisons are: (0) the existing corner-paper, 60-luma foreground mask, not the entire ScanWeave renderer; (1) local fractional coverage, thresholded at .5 for mask metrics; (2) an edge-weighted unary/pairwise label energy solved by iterative conditional modes; (3) a skeleton and local-width field seeded by (2), with a bounded global width scale and Gaussian PSF jointly fitted against the observation, penalising unsupported ink. Width expansion can join skeleton components; topology is measured, **not guaranteed**. The fitted PSF is an effective parameter, not an independently measured scanner PSF. The geometry candidate is tested on all crops for diagnosis: a trajectory/width representation is plausible for engraved strokes, while the printed serif and Fraktur examples require contour-preserving treatment of corners, branches and counters before deployment. This PoC does not yet implement that class-specific representation or infer reliable class labels.

[Gatos et al.](https://users.iit.demokritos.gr/~sper/PAPERS/2006J-GatosPratikakisPerantonis-PR39.pdf) motivates spatial background estimation; [Howe](https://www.science.smith.edu/~nhowe/research/pubs/icdar11.pdf) motivates edge-aware label energy, but our ICM approximation is **not** Howe's Laplacian/graph-cut algorithm. [Epshtein et al.](https://iacl.ece.jhu.edu/proceedings/cvpr2010/papers/1509.pdf) motivates local width consistency, not stroke-restoration accuracy. [Sober and Levin](https://arxiv.org/abs/1602.07038) fit variable-width splines using manually supplied points; our automatic skeleton model is not their method. [Hanif et al.](https://pmc.ncbi.nlm.nih.gov/articles/PMC10032482/) motivates colour-based component modelling; this PoC does not implement their GMM or component taxonomy. Repeated-letter priors were not implemented: OCR labels and genuine type variation could encourage invented strokes.

## Synthetic ground truth

84 cases: seven glyph or adjacent-glyph shapes from three locally installed regular/italic serif fonts, each with clear, faded, deliberately broken, and almost invisible conditions. Shapes are rasterized at 300 or 500 DPI; degradation includes smooth stain and paper shading, Gaussian blur, noise and JPEG 4:2:0. Seed and font hashes are recorded. Cases are simple rendered fonts, not a representative sample of historical print, and parameter choices have not been validated on independent data.

Each row is 21 cases. Values are mean **boundary F1 / missing ink / false ink**, with ink areas normalised by GT ink area (so false ink can exceed 1), followed by exact component-and-hole counts / 21 and total false joins. F1 uses a one-pixel boundary tolerance. Scores are raw proposed outputs, including cases flagged for fallback; the fallback would retain the raster, not output the mask.

| Degradation | Mask | Boundary F1 | Missing | False ink | Exact topology | False joins |
|---|---|---:|---:|---:|---:|---:|
| clear | baseline | 0.993 | 0.090 | 0.011 | 20/21 | 0 |
| clear | local | 0.890 | 0.000 | 0.614 | 18/21 | 2 |
| clear | energy | 0.859 | 0.000 | 0.679 | 18/21 | 2 |
| clear | geometry | 0.909 | 0.031 | 0.493 | 16/21 | 2 |
| faded | baseline | 0.000 | 1.000 | 0.000 | 0/21 | 0 |
| faded | local | 0.594 | 0.001 | 0.776 | 12/21 | 2 |
| faded | energy | 0.487 | 0.000 | 0.873 | 13/21 | 2 |
| faded | geometry | 0.440 | 0.009 | 0.925 | 8/21 | 3 |
| broken | baseline | 0.876 | 0.315 | 0.010 | 2/21 | 0 |
| broken | local | 0.801 | 0.049 | 1.158 | 2/21 | 2 |
| broken | energy | 0.759 | 0.040 | 1.311 | 4/21 | 2 |
| broken | geometry | 0.782 | 0.088 | 1.070 | 4/21 | 2 |
| no_evidence | baseline | 0.000 | 1.000 | 0.000 | 0/21 | 0 |
| no_evidence | local | 0.032 | 0.541 | 16.183 | 0/21 | 3 |
| no_evidence | energy | 0.027 | 0.535 | 17.349 | 0/21 | 3 |
| no_evidence | geometry | 0.038 | 0.565 | 15.581 | 0/21 | 3 |

The proposed fallback declined **21/21 no-evidence**, **2/21 faded**, **1/21 broken**, and **0/21 clear** cases. It correctly recognises the extreme blank examples but does not guard against false ink or joins in accepted cases. Faded-case mean linear-light simulated-rescan RMSE is baseline/local/energy/geometry **.0302/.0137/.0169/.0171**: the improved fit coexists with excessive false ink. The local method partially fits the observations it directly projects, so its fit advantage is not independent evidence of a correct latent shape. [Synthetic faded adjacent-glyph panel](/data/coding/scanweave/work/books01/stroke01/panels/synthetic-rn-faded.png) and [broken numeral panel](/data/coding/scanweave/work/books01/stroke01/panels/synthetic-6-broken.png) include clean GT, observation and masks.

## Real crops

Observation fit below is linear-RGB RMSE after simulating the fitted blur over the context crop, using one estimated background and ink model per crop. Baseline is its global mask rendered through that same model, not its PDF. Lower is better fit, **not** ground-truth stroke accuracy. All five confidence scores saturated at 1.0 and all were accepted by the heuristic; the synthetic failures show these scores are overconfident.

| Dev crop | Rescan RMSE: baseline / local / energy / geometry | Visual observation; topology and false ink |
|---|---|---|
| 8967062 | 0.075 / 0.035 / 0.038 / 0.045 | Local model connects faint numerals more than baseline, but ink colour remains brown; energy/geometry remove and thicken details. No latent GT to verify loops or invented ink. |
| 8967228 | 0.056 / 0.036 / 0.037 / 0.040 | Local coverage removes much of the orange but becomes pale; binary variants drop fine italic strokes. No GT for continuity or topology. |
| 12342014 | 0.060 / 0.031 / 0.048 / 0.058 | Binary variants make lettering stronger but alter serifs and dot shapes; clear reading benefit without false strokes is unproven. |
| euler_rechenkunst01_1738_0025 | 0.225 / 0.031 / 0.072 / 0.085 | Global baseline mask includes gutter shading; geometry changes fine Fraktur detail. Lower fit does not establish preserved characters. |
| luther_babstum_1526_0011 | 0.516 / 0.046 / 0.069 / 0.074 | Baseline mask is inverted by corners; geometry alters the complex branches and texture. No claim of protected fidelity. |

Inspect the 3× source / baseline / local / energy / geometry / 5× residual / MRC / Adobe panels: [613](/data/coding/scanweave/work/books01/stroke01/panels/8967062.png), [italic heading](/data/coding/scanweave/work/books01/stroke01/panels/8967228.png), [French](/data/coding/scanweave/work/books01/stroke01/panels/12342014.png), [Euler](/data/coding/scanweave/work/books01/stroke01/panels/euler_rechenkunst01_1738_0025.png), [Luther](/data/coding/scanweave/work/books01/stroke01/panels/luther_babstum_1526_0011.png). Full-context local background/ink distribution, alpha, probability, core and skeleton diagnostics are under `$B/stroke01/` (`$B=/data/coding/scanweave/work/books01`); native pixels and images are not committed.

**Six criteria:** observation fit improves under the assumed model, and the 613 crop suggests better continuity; neither establishes true topology or absence of invented strokes. Synthetic GT directly exposes both false joins and missed/extra ink. Some binary French lettering appears stronger, but synthetic errors and altered details prevent a readability-preservation claim. No reconstruction PDF was made, so compression and PDF render time are **not measured**; no new OCR/search or ownership changes exist to classify. Crop reconstruction took about .02–.12 s per crop in this run, excluding source extraction and panels; that is not a full-page performance projection.

Reproduction and exact Python, library and local-font hashes are in [research/stroke01](/data/coding/scanweave/work/stroke01/research/stroke01/README.md) and its aggregate JSON. The three focused tests pass (forward model endpoints, missing/false-join metrics, no-evidence refusal). This evidence supports further research into calibrated uncertainty and topology/contour constraints, **not** integration or a claim that latent reconstruction materially beats the baseline safely.
