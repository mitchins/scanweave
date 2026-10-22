# FONT-01 independent research

Product baseline and publication receipt: remote main
`10b5d9318581717b45b018c3bf51b24525499295`. Product PRs15/17/18 merged;
research14/16 closed unmerged with pinned evidence and branches retained.
All32 accepted ACR-05 PDFs reproduced exactly (8,743,391 bytes); synthetic300/600
and faithful controls exact. See [the closure receipt](https://github.com/mitchins/scanweave/pull/18#issuecomment-6351607293).

## Reproduce fixtures

Requires Python3.12, NumPy, Pillow and pikepdf from the existing CI requirements.
Install Debian/Ubuntu font packages `fonts-dejavu-core fonts-freefont-ttf
fonts-urw-base35 fonts-liberation`. Font files are not bundled or downloaded.
Their exact paths, hashes and licence-notice hashes are recorded by the generator.

```sh
python -m qualification.font01.benchmark --out qualification/font01/local/corpus-v1 \
  --verify-manifest qualification/font01/fixture-manifest.json
PYTHONPATH=qualification python -m unittest qualification/test_font01_benchmark.py
```

The output directory must not exist: generation never silently replaces evidence.
Strict reproduction fails on changed font/licence-notice hashes, tool versions or
generated document/label/sample hashes. The apt package names install dependencies;
they are not claimed to pin font bytes. An incompatible installation must use the
recorded asset versions rather than silently updating the frozen manifest.
Each split contains a three-page lossless `scan.pdf`, its source PNG pages,
actual-page glyph crops and `observations.jsonl`. Only `oracle/` contains face,
family, pristine or damage labels. `manifest.json` is provenance, not an inference
input. Large generated files stay under ignored `local/`.

The first frozen fixture contains 5,175 observations from 23 faces across 9 pages.
Training/validation/test have 8/7/8 faces in disjoint families. Every face-character
has a D0 and a damaged observation; the CLI fails if this is not true. No classifier result
or production typography improvement is claimed by fixture generation.
This is a reproducible development benchmark: labels can be regenerated from the
published generator and seed. Oracle isolation is an inference API/evaluation
contract, not secrecy or protection against an adversary choosing to read labels.

Review [the prior art](../../FONT_01_PRIOR_ART.md) and
[frozen evaluation contract](../../FONT_01_BENCHMARK.md) before fitting models.

## Statistical baseline (research API only)

SciPy is pinned in CI requirements. After strict fixture reproduction:

```sh
python -m qualification.font01.run_baseline qualification/font01/local/corpus-v1 \
  qualification/font01/local/baseline-v1
PYTHONPATH=qualification python qualification/test_font01_statistics.py
```

The runner checks the frozen three-split manifest before output, before test and
at completion. It fits only on training, selects thresholds only on validation,
and writes model/validation/fixture hashes before opening test pairs. Source-only
loading rejects evaluator labels, validates image hashes and contains discovered
symlinks inside the selected corpus root. Labels enter only the explicit evaluator
join. Outputs include features, pair identities, registration transforms, timing,
thresholds and metrics. Non-probability scores have no claimed calibration error.

Complete-link groups prevent similarity chaining; character cannot-links apply to
canonical glyph groups, not font cohorts. Separate purity/completeness and ARI are
provided. No model or cohort classifier is enabled in Rust or ordinary conversion.
`product_control.make_bundle` supplies only public character labels and page boxes
to the existing converter; it is a controlled OCR-input experiment, not evidence
of real OCR accuracy. The caller must use the verified frozen fixture.
