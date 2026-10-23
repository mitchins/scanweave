# FONT-04 discovery (A and B1 only)

Contract baseline: `06f24b122e1cd1cd879880166b8240c7e75747ed`;
product baseline: `c10e3dff93ca12ac410c0f6626a4ef74ce34e0c1`.
P2 preregistration SHA-256: `a4f9ccd3a7e51d719946be80f7cc9a297de7ca22285e8755e5e26e415e7db466`.
P2 is not generated, rendered, inspected, or modified by these discovery tools.

Build: `cargo build --release -p scanweave-cli --bin scanweave -p scanweave-io --example font04_trace`.
Experimental complete-document conversion:

```sh
target/release/scanweave qualification/pdf_packaging/groups/financial-input.pdf qualification/font04/local/financial-experimental.pdf --dpi 300 --profile clearscan --glyph-sharing experimental
```

Omit `--glyph-sharing` for the default. The opt-in CLI requires the scientific
Python environment `qualification/.venv/bin/python` (override with
`SCANWEAVE_RESEARCH_PYTHON`), with NumPy, SciPy and Pillow. Analysis additionally
uses pikepdf, pypdfium2 and fontTools, and Poppler/qpdf/OTS executables.
The experimental planner executes the checked-out `planner.py`; this is a
research dependency, not a distributable product feature. It exports its
source-only snapshot, fitted decisions and rejection ledger alongside the PDF
in `<output>.font04/`. It modifies only visible `e` occurrences, before font
union and required-program construction. Raster and semantic owners are untouched.

`geometry.py` and `pdf_helpers.py` are copied with attribution from FONT-03
`7ebc09ec7ec19d9c4ff260da621fcfbb021d909d`; all other FONT-04 code is new.
The inherited structural veto limits are retained. Added orthogonal checks
cover effective stroke, cross moment and multi-threshold counter topology.
Three grouping alternatives share one source-noise error family.

Large artifacts live under ignored `local/`; compact results and hashes are
committed. Independent blinded judgments remain distinct from automated metrics.

## Checkpoint reproduction

1. Build the CLI plus `font04_trace` and `font04_owned` examples. Run the normal
   default and explicit experimental financial commands above; compare against
   `financial-main.pdf` and the hashes in `manifest.json`. A complete experimental
   repeat was measured byte-identical.
2. `python -m qualification.font04.b1_audit <experimental.pdf>` performs native
   CID/GID/program, source, text and validity measurement. `native_frontier` sweeps
   the recorded sparse candidate matrix; its PDFs are glyph controls, not complete
   document deliverables. `verify_checkpoint` checks the final complete outputs.
3. Phase A freezes source inputs before `causal.py evaluate` opens P1 oracle data.
   The retained FONT-03 eight-class cohort is under `local/causal`; the full-ownership
   eight-class addition is under `local/causal-extension` (`run_extension.sh`).
   `floor_control` adds the fresh native floor-on self trace without reselecting
   cohorts. `causal_financial_native` supersedes nominal-DPI financial atlas
   measurements with the original MediaBox and raster-to-page transform.
4. `checkpoint_a`, `calibration`, `review_sheets`, `negative_review`, `review_a`
   and `finalize` produce summaries and review artifacts. The two negative/style
   populations and all cohort input hashes remain distinct. Raw input freezes,
   trace requests and native control PDFs are retained locally.
5. `review_key.py reveal <directory> <saved-judgments.json>` refuses to reveal
   incomplete judgments. Do not open the sealed key before saving all judgments.

The selected point is an unqualified discovery result. It saves seven net programs
and 175 complete-PDF bytes, but source fidelity directions differ by renderer.
The 24-candidate shortlist and sparse star ordering are explicit limitations;
untested pairs are not rejections. No B2 or P2 generation entry point is present.
The 15% error-only objective is met for `e`; independent visual rejection rates
and material-defect counts are pending review. See `FONT_04_RESULTS.md`.
