# P2″ contract — DRAFT for reviewer and owner

This is a proposal, not an authorization to generate or open a holdout. No font, seed, candidate arm, margin value, or test population is selected here. The P2′ FAIL stands. Freeze the final protocol, implementation, numerical margins, populations, sampling and analysis before opening any future holdout.

## Independent calibration and numerical criterion

Use isolated-glyph error, separately by renderer and frequent character class. Define frequent classes, eligibility, class sample minima, error metric, cropping and aggregation before calibration; classes without sufficient independent calibration support are unresolved, not automatic passes. Keep FONT-01 train and default-versus-default renderer variation as the only margin calibration sources. No P2, P2′, S2a or other development outcome may set, adjust or select a threshold.

Proposed fixed recipe, subject to reviewer acceptance before calibration: for each class c and statistic s in {mean, p95}, compute R(c,s) as the absolute difference between the statistics for the same default outputs rendered by PDFium and Poppler on the independent calibration corpus. Compute N(c,s) as the 95th percentile of absolute paired differences in statistic s across predeclared independent FONT-01 train reconstruction-noise replicates (paired resampling units are pages, retaining within-page dependence). Set margin Δ(c,s) = max(R(c,s), N(c,s)). Use the same fixed protocol for each renderer; do not use future holdout data to choose a margin. If replicates or calibration support do not exist, report margins as undetermined and do not run a qualifying test until a reviewer accepts a valid independent calibration. Record all input hashes, software versions, replicate definition, values and code before holdout opening.

For a future holdout, let E(c,s,r,arm) be the class statistic of isolated-glyph error under renderer r. The proposed non-inferiority rule requires E(c,s,r,candidate) − E(c,s,r,default) ≤ Δ(c,s) for both statistics, every eligible frequent class, and both renderers. Report the paired differences and margins, not just pass/fail. The p95 is computed across eligible observations, not as a percentile of class summaries. This is a descriptive margin rule; it does not claim a confidence-bound non-inferiority test. The reviewer must approve any inferential uncertainty rule and multiplicity treatment before calibration and holdout opening.

Report IoU, contour distance and signed area bias as well as error, mean and p95 by class and DPI × damage band, separately for D0–D1 clean and D2–D4 restoration cases. Fix contour distance units and the direction of signed area bias in the final protocol. Do not retrofit limits from development results.

## Blind visual review

Randomize the arm labels independently per row; retain scan and witnesses as evidence while preventing the reviewer from identifying output arms. Seal the mapping and any information that identifies arms; commit grades before unsealing. Specify sampling and inclusion of accepted, rejected and positive-control cases in the final preregistration. Review at reading size and at 200%. Record the evidence and classify each arm's visible differences as:

1. Harmless visual difference.
2. Justified restoration: ink missing from a damaged scan, supported by other source witnesses. Record the witness evidence; do not classify unsupported additions as restoration.
3. Material change: wrong character or numeral, opened or closed counter, style, slant or weight-class change, or unsupported added or removed stroke.

Zero newly introduced class (iii) defects are permitted in the candidate relative to default in the reviewed population. A restoration is not a defect merely because it differs from a damaged member. Ambiguous support requires an explicit unresolved grade and independent adjudication under the preregistered rules, not an assumed pass.

## Population and independence

The holdout must use genuinely unseen font families with competing style siblings within documents, including weight and slant siblings. Audit design ancestry and hashes against all development families, not just names. Candidate packages for later investigation in the official Ubuntu Noble archive, **not selections**, include [fonts-cabin](https://packages.ubuntu.com/noble/fonts/fonts-cabin) (1.5-3, universe), [fonts-cantarell](https://packages.ubuntu.com/noble/fonts-cantarell) (0.303.1-1, universe), and [fonts-ebgaramond](https://packages.ubuntu.com/noble/all/fonts/fonts-ebgaramond) (0.016+git20210310.42d4f9f2-1, universe). Archive availability does not establish unseen design ancestry or sufficient sibling coverage; verify those properties and actual package contents before any future selection. No package is installed by this draft.

The final contract must also preregister functional equality, qpdf, OTS, determinism, actual CID→GID outline and byte accounting, runtime and peak RSS. Development measurements cannot set any threshold. No future holdout is generated or opened by this draft.
