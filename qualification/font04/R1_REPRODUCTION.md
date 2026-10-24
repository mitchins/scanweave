# FONT-04 R1 native checkpoint

Product branch: `feat/glyph-sharing`. The qualified executable is retained in
`local/R1-native/scanweave`; its source/build commit and SHA-256 are in
`r1-native-build.json`. Later product commits add tests/documentation only;
the runtime source equality is recorded in `r1-git-receipt.json`.

The four deliverable PDFs and logs are in `local/R1-native/`. The native flag is:

```sh
scanweave input.pdf output.pdf --dpi 300 --profile clearscan --glyph-sharing cover-2.0
```

Use `cover-1.5` for the fixed comparison. Supply the installed PDFium shared
library using `SCANWEAVE_PDFIUM_LIBRARY` if it is not on the system loader path.
The shipping converter never starts Python; qualification deliberately set
`SCANWEAVE_RESEARCH_PYTHON=/nonexistent-font04-python` during both opt-in runs.

The research oracle, method freeze, dependency inventory and 23 safety cases are
committed on this research branch. The native decision ledger records all 3,524
members. `r1-parity.json` enumerates all decision/canonical divergences, and
`r1-numerical-source-audit.json` localizes preparation differences without changing
thresholds or trying fallback canonicals. `native_probe.rs` and
`probe_native_fit.py` are research-only probe sources; they are absent from the
product branch. Their large inputs/results remain in `local/native-fit/`.

`qualify_r1.py` checks the explicit four native outputs, independently scores every
native draw using `r1_class_metrics.py`, audits actual owned ink, checks exact
raster/text/program invariants, and runs `r1_compatibility.py --native-final`.
The source/default fidelity controls are reused only after exact snapshot and
PDF-hash checks; candidate pixels are always measured. These scripts never take
P2 as input and do not run corpus qualification.

The 12-panel review is in `local/R1-blind-review/`, with blank judgments. It
includes the one Rust-only acceptance and the other five divergent members, in
both PDFium and Poppler, at 100%/400%, in identical default context. Its separate
key is in `local/R1-blind-private/`. Do not reveal it before saving all judgments.
The sealer refuses to overwrite an existing review. No judgments were made here.

Reader is BLOCKED-ON-OWNER: provide the official **Windows x64** Reader installer
for owner build **26.00221.901** (`.exe` or matching `.msi`). The root's incomplete
macOS DMG is not a Wine installer. No Wine prefix or Xvfb display was touched.
The PDFKit kit is in `pdfkit/`; owner execution is deferred to R3.

**Stop at Checkpoint R1.** No P2, R2 corpus, product PR or merge is authorized by
this receipt. CI/Sonar server acceptance and independent judgments remain pending.
