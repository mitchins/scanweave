# M0-Q Q1 — Independent reproduction record

Date: 2026-10-14. Method: fresh `git clone` of the repository into
`/tmp/opencode/repro`, from-source build of the probe, full committed suite executed
in that clean checkout. This closes the ledger distinction left by the restricted-shell
final review ("re-parsed but did not execute").

## Reproduction checkout

- Frozen baseline tag `m0-provisional-baseline` → commit `3172a32` (operator-accepted).
- Final-tree reproduction checkout: `597386f` (M0-Q REVISE repairs). The subsequent
  commit `9c28819` adds ONLY the committed digest record
  (`qualification/repro_hashcheck.json`) produced by this reproduction — no code.
- Scope: 8 gate pages; 32 acceptance artifacts (8 × out.pdf / out.ttf / b0_raster.pdf /
  b0_notext.pdf).

## Environment (recorded)

| Component | Version |
|---|---|
| rustc/cargo | 1.99.0 (b940084d7 2026-09-28) via rustup, `rust-toolchain.toml` pinned |
| OS | Ubuntu 24.04 x86_64, Linux 7.0.0-31-generic |
| qpdf | 12.4.2 (tools/dist, source tarball sha256 8a58af5b…) |
| ots-sanitize | 9.3.0 (upstream release, zip sha256 1caab403…) |
| Poppler | 24.02.0 |
| fontTools | 4.46.0 |
| Python | 3.12 (qualification/.venv: pypdfium2, jsonschema, numpy, pillow, fonttools) |
| PDFium | via pypdfium2 bundled build |

Environment tooling (`tools/`, `.venv`, `target/`) is NOT committed; it is pinned by the
hashes/versions in `TOOLCHAIN.md` + `UPSTREAMS.lock.toml`. The clone's `tools` was a
symlink to the canonical pinned tools; the probe binary was REBUILT FROM SOURCE in the
clone (`cargo build` after clean clone; target/ is gitignored).

## Executed commands and outcomes (clone checkout)

| Command | Outcome |
|---|---|
| `cargo build -p m0-font-pdf` | success (29.8 s, from source) |
| `cargo test` | **36 passed, 0 failed** (incl. `e0_four_part_key_property`) |
| `qualification/validate_fixtures.py` | 3 positive pass / 6 negative rejected — all ok |
| `qualification/checks.py` | **8 pages** verified; **8/8 E-proofs PASS**; visual gates as in probe_results.json (p08 pdfium transport-order exception recorded; see M0_Q_REPORT §5) |
| `qualification/measure.py` | all B0 checks (chars/neutral/qpdf) true; p09 external comparison executed (IA MRC / OCRmyPDF / ours — numbers committed in measurements.json); ratios reproduced |

## Cross-checkout determinism (final tree)

All **32** acceptance artifacts (8 pages × out.pdf / out.ttf / b0_raster.pdf /
b0_notext.pdf) SHA-256 **byte-identical** (full 64-hex digests) between the canonical
checkout and the fresh from-source clone — committed record:
`qualification/repro_hashcheck.json` (all_equal: true; per-artifact rows).
Determinism claim E7 generalizes from single-checkout reruns to independent checkouts
of the same tree on the pinned toolchain. Additionally, one pixel-hash binding was
independently re-derived from the SWRASTER1 preimage during reproduction (match).

## Tool versions for the record

qpdf: `qpdf version 12.4.2`; Poppler: `pdftotext version 24.02.0`; OTS: `ots 9.3.0`;
cargo: `cargo 1.99.0 (5f9046... 2026-08-27)`.

## Remaining execution caveats

- Copyleft/dependency metadata audit remains a registry-query result (recorded in
  UPSTREAMS.lock.toml), reproducible via the crates.io API queries described there.
- Corpus-dependent and external-MRC items remain BLOCKED (Q3/Q4).
