# FONT-03 research controls

No converter imports this package. No fitted outline or acceptance policy is
activated in ClearScan. See [FONT_03_REPORT.md](../../FONT_03_REPORT.md).

Run from the repository root with the existing qualification environment:

```sh
PYTHONPATH=. qualification/.venv/bin/python -m unittest qualification.font03.test_consensus
```

## Reproduction and prerequisites

The frozen FONT-01 corpus, FONT-02 source-owned observations and full-document
controls are prerequisites, not new downloadable datasets. Their locations and
hashes are recorded in `manifest.json`. Large outputs remain under ignored
`qualification/font03/local/`. Do not replace historical evidence when running
these commands; use a separate checkout with the same local inputs.

`experiments/` preserves the concrete development sequence. Scripts use explicit
repository-relative paths, not their own directory, and are invoked as
`PYTHONPATH=. qualification/.venv/bin/python qualification/font03/experiments/SCRIPT.py`.
They use NumPy, SciPy, Pillow, fontTools, pikepdf and pypdfium2 from the existing
qualification environment, plus Poppler. No training or new OCR engine is used.

1. Prepare the production ownership exports for all six characters `e1a8.!`,
   using the FONT-02 Rust matcher probe and FONT-01 public-geometry bundles.
   `prepare-source-all.py` records source-owned coverage, line geometry and
   independent evaluator labels. Its corrected selection description means
   **all** available observations of these characters, not one per stratum.
2. Run `group_synthetic.py`, `calibrate_uniform.py`, `bindings.py` and
   `synthetic_templates.py`. Character/severity labels select the healthy
   evaluation arm; face labels only reject contaminated *training calibration*
   groups. Pristine pixels do not participate in grouping or fitting.
3. Trace each `SPLIT-trace-input.json` with `canonical_tracer.rs`, using the
   FONT-02 scratch probe build. Only visibility exports differ from production:
   make `trace`, `glyphs`, `fontbuild` modules and `trace_shape_clearscan` public
   **in the temporary source copy**. The binary takes input JSON and an existing
   output directory. `Cargo.toml` dependencies are the existing workspace
   `scanweave-io`, `scanweave-core`, `image` and `serde_json`. Keep the probe out of
   the production workspace. Its tracing and font builder are otherwise unchanged.
4. Run `synthetic_pdfs.py`, then `synthetic_measure.py validation` and `... test`.
   Only after the source decisions and rendered coverages are frozen, run
   `synthetic_evaluate.py validation` and `... test` to read pristine references.
5. Run `affine_refinement.py`; trace its inputs into `local/affine-refinement/`.
   Repeat step 4 with that directory as the optional root argument. In this
   refinement **C and D are identical controls**, not independent candidates.
   Run `native_budget.py` and `structural_calibration.py` for the final gates.
6. `repair_probe.py` uses frozen source-only groups in `repair-control.json`
   for the separate, rejected pre-review damaged-ink experiment. Its
   normalized comparisons are not complete-PDF repair qualification.
7. `prepare_town.py` produces the frozen **three-parameter uniform** source
   groups and fields; trace that input into the local root before `town_pdf.py`.
   `town_affine.py` separately produces **five-parameter** records under
   `town-affine/`; trace there and use `town_affine_pdf.py`. Never interchange
   the two formats. `town_pdf.py` and the `town_affine*` scripts generate source-bound real-page
   probes from the existing Town Officer coverage, group and placement records.
   Full shadow PDFs retain original fonts and cannot demonstrate font savings.
   `construction-control.json` freezes the pre-review real intervention. Run
   `town_native_budget.py` after its native rendering to reproduce the exact
   four source-bound targets; do not substitute regenerated symmetric limits.

The original initial real cohort record and adjudicated source health are kept
in the hash manifest. Their manual health decisions are not an automatic
classifier. All family-disjoint evaluation was previously inspected in
FONT-01/02 and remains development evidence, not a pristine final holdout.

## Pre-union construction control

This is a **fixed-plan scientific intervention**, not product inference.
`preunion_plan.py` generates the four accepted source-bound real substitutions.
Apply `construction-control.patch` using `git apply --unidiff-zero` in a detached
temporary checkout of `c10e3df`,
copy the generated plan to `crates/scanweave-io/src/font03_plan.json`, build its CLI,
and convert the original 13-page financial input normally. The hook checks the
exact source RGB hash, size, supplied `e` identities and symbol IDs, then inserts
canonical shapes/remaps before document union, required-font pruning and font
assembly. The plan is derived from source evidence, not pristine typography.

Never ship this fixed plan or describe its result as a standalone Rust
canonicalizer. It tests construction causality only. Normal ClearScan and
faithful are unchanged. The phase-2 source/native decisions and hashes must be
retained with any rebuilt output.

To reproduce the original **rejected directional discovery** controls, apply
`experiments/directional-discovery.patch` with `git apply --unidiff-zero` only
in a temporary checkout, then rerun the original uniform/affine sequence. This
intentionally fails the new symmetry regression and must never replace the
maintained grouping implementation. It explains the historical tables rather
than providing a second supported policy.
