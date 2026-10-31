# R2c P2′ measurement receipt

P2′ was opened and converted by the reviewer at `c77b893`; preserve both
existing `OPENED` locks. Do not rerun the generator or conversions. The
preregistration SHA-256 is `fd8d69e3b941740f6360b6abb38e53068de7b90db3694f148748d933155666ce`;
the ceiling binary SHA-256 is `d3a26c6d0677563858f2c57e393ec538d0395335a7460f960ef228705aee4177`.
`sha256sum -c qualification/font04/local/P2prime/SHA256SUMS` verifies the
retained PDFs, including the nine byte-identical candidate repeats.

With `PYTHONPATH=qualification/font04/local/R2a/pdfium-python:.`, use
`qualification/.venv/bin/python -m qualification.font04.r2c_pristine` and
`qualification/.venv/bin/python -m qualification.font04.r2c_checks`, followed
by `qualification/.venv/bin/python -m qualification.font04.r2c_report`.
The pristine program carries over the R2b composite page, original boxes,
measure and summary functions, and adds the reference arm. Per-observation
records stay under `local/P2prime`; the committed output contains aggregates.
It is a full-context screen including overlapping neighbours, as in R2b.
Functional checks use R2a extraction and font checks plus the same PDFium
native word-search check used for S1e. GNU time results are retained per sheet
in the economy output; timings reflect the reviewer's original runs.

The blind package and sealed material are local. The package builder refuses to
overwrite an existing package. The committed seal is a commitment, not a
release of the key or census. Reviewer grades must be saved and committed
before unsealing. Material-defect results remain pending blind review.

The package contains 1,158 renderer panels in 97 contact sheets; all structural
checks passed. Sampling is shuffled with a seed retained in the sealed key,
round-robin by sheet; all eligible admitted non-self decisions are included,
with at least 150 rejected decisions and 100 positive controls, plus cross-run
and repeated-word probes. Two renderer panels are produced for each sampled
member. The manifest hashes every review file. `r2c_census.py` recomputed the
complete S1d-style oracle census and its outline proxy; the correction and
before/after PDF hash checks are recorded in `r2c-harness-fixes.json`.

Rejected-member panels show the retained final output arms. They do not show
R2a's rejected counterfactual proposals: the P2′ conversion artifacts do
not contain the exported planner observations and native bindings needed to
construct those proposals. Consequently these panels cannot establish whether
rejected proposals would have looked acceptable. The oracle false-rejection
measurement remains sealed; blind review cannot adjudicate over-rejection from
these panels alone.
