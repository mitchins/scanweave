# FONT-04 — Product mission: ship document-wide glyph sharing

**Owner decision (2026-10-24).** B2′ is accepted as a successful research result
(`FONT_04_REVIEW_B2PRIME.md`). **cover-2.0 is the release candidate.** cover-1.5 is kept
as a comparison arm only.

This is product engineering, not another discovery cycle. **The deliverable is a working,
independently qualified ScanWeave with reusable document-specific fonts, merged to
`main`. Another successful experiment on a research branch does not count.**

## Fixed inputs

| Item | Value |
|---|---|
| Research reference | `research/font04-document-fonts` at `165a7ef` (B2′ code `5e8bb6f`) |
| Product base | remote `main` at `c10e3df` (record the SHA you actually start from) |
| Reference output, cover-2.0 | `financial-B2prime-cover-2.0.pdf`, SHA-256 `d4d0b262…2563` |
| Comparison output, cover-1.5 | SHA-256 `700ad687…cb8d` |
| Default output | SHA-256 `74c31136…ab0f`. Must stay byte-identical |
| P2 preregistration | `qualification/font04/p2-preregistration.json`, SHA-256 `a4f9ccd3…b466` |

## Scope

**In scope:**
- freezing cover-2.0;
- a native Rust implementation behind an opt-in flag;
- renderer and text compatibility;
- single-use P2, the 32-page corpus and blind review;
- one product PR, merged.

**Out of scope:**
- threshold tuning on the financial document;
- the next-best-canonical or split-group experiment, unless qualification shows a concrete
  problem it would solve (stop and report first);
- damage repair;
- raster compression;
- OCR or Unicode changes;
- B3 rare-class sharing beyond what the frozen rule already abstains on;
- PR #24/#25 hygiene, which is a separate track.

**Safeguards that must not weaken:**
- hard structural checks;
- the canonical hygiene screen;
- the stroke-weight band;
- the ownership-aware unexplained-ink veto;
- outline-level net retirement;
- text identity, verified by construction and by extraction.

## R0 — Freeze the method (research branch)

1. Write `qualification/font04/method-freeze.json`. Record:
   - the algorithm, as an ordered list of stages: snapshot, eligibility, weight band,
     hygiene, cover grouping, canonical trace, placement fit, hard checks, owned-ink veto,
     net-retirement, composite stub and font-variant emission;
   - every constant and threshold, including multiplier 2.0, with its source line;
   - the class-eligibility rule in general form for any document (for example "≥10
     visible draws of the label in this document"). It must not refer to this document's
     classes;
   - reference hashes: plan membership, canonical set, emitted bindings, output PDF;
   - the P2 preregistration SHA-256.
2. Make the method-freeze commit. It references the preregistration hash, as the P2 guard
   requires. After this commit, constants change only through a recorded stop and
   owner approval.
3. Build a **reference oracle**: a frozen per-member decision ledger from the research
   implementation. Record member, canonical, accept or reject, first failing check, value
   and limit, and fitted transform. This is the parity target for R1.
4. Turn every material regression into a test fixture:
   - the 16 registered cases;
   - the 4 new cases from my review: members 3013, 2466, 63 and 1450;
   - glyph-277, `glyph-3422` and `glyph-1233`.

## R1 — Native Rust pathway (product branch)

Create one short-lived branch from `main`, for example `feat/glyph-sharing`. Do not stack
it on the research branch. Bring over only shipped code, tests and small fixtures. The
research harness, ledgers and local artifacts stay on the research branch.

1. **Flag.** Default ClearScan stays byte-identical. Prove it with a test against the
   default hash and with the existing default suites. Sharing is opt-in, for example
   `--glyph-sharing`. You choose the name; document it in the CLI help.
2. **No Python at runtime.**
   - Port the planner stages to Rust, in the existing crates (`scanweave-io` and
     `scanweave-cli`).
   - Remove the `SCANWEAVE_RESEARCH_PYTHON` subprocess from the product path.
   - Any SciPy or fontTools behaviour you depend on, such as `ndimage` sampling,
     morphology, labelling or composite glyph emission, must be reimplemented and
     unit-tested.
   - Dependencies: prefer what the workspace already uses. Any new crate needs a
     licence check and justification.
3. **Determinism.**
   - Output is identical across repeat runs and thread counts.
   - Floating-point decisions near a threshold are resolved deterministically. Document
     how.
4. **Parity with the oracle**, on the financial document. All of these are required:
   - **Safety superset:** every member the oracle rejects on a hard check, hygiene, weight
     band or owned-ink veto is also rejected by Rust, or kept as default for a stricter
     reason. All regression fixtures pass.
   - **Membership agreement:** at least 98% identical accept/reject decisions, and the
     same canonical for at least 98% of accepted members. Enumerate every divergence and
     explain its cause, for example float order or resampling. Every member that Rust
     accepts but the oracle rejected goes into the blind review set.
   - **Economy and fidelity:** net outlines retired is at least 95% of 327. Analytic
     source-error mean and p95 are no worse than the oracle by more than the measured
     renderer floor. Text extraction is identical to default.
   - If 98% is not reachable because of an unavoidable numerical difference, stop and
     report with the divergence ledger. Do not tune thresholds to recover membership.
5. **Tests.**
   - Unit tests for each stage.
   - Composite-glyph and font-variant serialization tests: OTS clean, and qpdf or an
     equivalent structural check.
   - An end-to-end opt-in test on a small committed fixture.
   - The default byte-identity test.
   - The regression fixtures.
   - Coverage on new shipped code meets the repository's Sonar gate.

## C — Renderer and text compatibility

Run this against the **Rust** cover-2.0 output, the default output and the cover-1.5
comparison.

| Consumer | Requirement |
|---|---|
| PDFium | Renders every page; text extraction identical to default |
| Poppler | Renders every page; `pdftotext` default, `-layout` and `-raw` identical to default |
| MuPDF | Renders every page; text identical to default |
| **Current Adobe Acrobat Reader (Windows) in a fresh Wine prefix** | See below |
| Apple PDFKit / Preview | **Deferred to R3**, before merge. Prepare a small Swift PDFKit check kit now (render plus `PDFDocument.string` comparison). The owner runs it on a Mac |

**Adobe Reader procedure.**
- Use a **new** Wine prefix, for example `~/.wine-reader-current`.
- **Never touch `~/.wine-acrobat-xi`.** That prefix is the ClearScan generator, not a
  verification consumer, and Acrobat XI is not the compatibility target.
- The owner supplies the current Reader build `26.00221.901`. A Windows installer is
  required: the downloaded `.dmg` is the macOS package. If only the `.dmg` is present,
  pause this step and report. Do not fetch installers from unofficial sources.
- Disable the updater and telemetry where possible. Run on a separate Xvfb display, not
  `:99`.
- For each page of the three PDFs:
  - capture a render at a fixed zoom, plus a zoomed crop of a dense text region;
  - confirm there are no error dialogs or missing or garbled glyphs;
  - copy all text (select all, copy) and compare it to the default output's text;
  - search for at least 10 known words, including repeated words across pages;
  - compare against PDFium at matched resolution.
- Investigate any genuine difference, such as a missing glyph, a wrong component offset,
  a text-order change or a font error, **before** P2. Rasterization differences that also
  appear between default and PDFium are not defects. Show this with the default control.

The binary-thresholded comparison is an optional visual diagnostic only. It must not
change any PDF and must not block release.

### Checkpoint R1 — stop for independent review

Deliver:
- the freeze commit SHA;
- the oracle ledger;
- the Rust branch SHA;
- complete Rust PDFs for default, cover-2.0 and cover-1.5;
- the parity report, with every divergence enumerated;
- sealed blind sheets for every Rust-only acceptance;
- the Reader results;
- the PDFKit kit;
- test and coverage status.

**P2 is opened only after this review accepts the frozen Rust implementation.** It is
single-use.

## R2 — Single-use qualification

1. **P2.** Generate it through the guarded generator, once, with the frozen Rust
   implementation. Report:
   - pristine error, IoU, contour distance and area bias, by DPI and damage band;
   - material defects from blind review;
   - designs retired and draws per design;
   - false rejection on same-design members.

   No iteration on P2 results. Any change after P2 is a new method and needs a new
   holdout.
2. **The complete 32-page real corpus**, the established development corpus. Per document
   and in total, measure:
   - font bytes;
   - actual retired designs, following CID → GID;
   - added canonicals and net designs;
   - total PDF bytes against default and against a save-only control;
   - analytic, PDFium and Poppler fidelity, with floors;
   - text extraction equality in all engines;
   - end-to-end runtime and peak RSS, paired with default on the same machine.
3. **Blind review package**, sealed, with the key held separately:
   - every newly admitted member, or a random sample of at least 300 if larger, stratified
     by document;
   - at least 150 rejected;
   - repeated words;
   - cross-style probes;
   - all regression fixtures.

### Checkpoint R2 — stop for independent review

## R3 — Product PR and merge

After R2 is accepted:
1. Open **one** focused PR from the product branch to `main`. It carries the shipped Rust
   code, tests, fixtures, CLI docs and a short qualification summary. Research artifacts
   stay out of it.
2. CI and Sonar must pass on the shipped code.
   - Fix real issues. Disposition false positives one by one, with reasons.
   - Do not exclude shipped code from analysis, and do not weaken any gate.
3. The owner runs the macOS PDFKit kit. If a genuine incompatibility appears, fix it in
   the PR and re-verify the other consumers.
4. Merge through the normal protected flow, with required reviews and checks. Record the
   final `main` SHA. No force-push, no bypass, no admin override.

## Standing rules

- Default ClearScan stays byte-identical until a separate decision changes the default.
- Stage explicit paths only. Never use `git add -A`, `git add .` or `commit -a`.
- Never commit untracked ACR-02/03/04 artifacts, `adobe-acrobat-sandbox/`, archives,
  installers (`AdobeReader*`), or `qualification/font04/local/`.
- No new stacks of unmerged product PRs.
- PR #24 stays draft. PR #24/#25 hygiene is independent of this release.
- Stop and report rather than improvise if any of these happens:
  - a safeguard would have to weaken;
  - parity fails;
  - a renderer shows a genuine defect;
  - P2 or corpus results fail.
