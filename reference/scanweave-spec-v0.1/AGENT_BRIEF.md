# Coding-agent handoff — ScanWeave v0.1

## Objective

Build a cohesive, offline Rust library and CLI that consumes scanned page pixels plus existing OCR and produces small, searchable PDFs with source-derived vector fonts where qualified, retaining original raster regions elsewhere. The detailed contract is in `SPEC.md`; test gates are in `QUALIFICATION.md`. Read `SOURCES.md` before selecting dependencies.

Do not build a PDF editor, OCR engine, general workflow platform, neural font-restoration model or GUI. Do not replace source text with a similar installed font. Do not use an OCR label to choose the visual shape. The product should work after Tesseract and also from another host application's pixels/OCR.

## Authorization for the first implementation turn

Execute **M0 only**, then stop for review. This is authorization to create the initial repository/workspace and bounded probes in the designated working directory, not to publish a package, merge into an upstream project or access unrelated private documents. The supplied benign corpus is the only real-document input. If it is not mounted, run the synthetic probes and record the corpus-dependent portion as blocked; do not invent measured corpus results.

### M0 tasks

1. Resolve exact toolchain and dependency versions/licences from upstream. Create `UPSTREAMS.lock.toml` with repository/package identity, immutable version or revision, source checksum, licence/notice hashes, selected features, usage scope and platform status. Distinguish runtime, optional OCR subprocess and qualification-only dependencies. Existing version numbers in earlier conversation or marketing text are not lockfile evidence.
2. Implement the normalized page schema/types and a tiny hOCR reader with honest word/symbol granularity. Establish pixel-edge coordinates, explicit physical dimensions and file/pixel-hash binding. Write failing tests for stale OCR, bad UTF-8 ranges, missing DPI, wrong page pairing and unsupported transforms before implementation.
3. Run a bounded vertical probe: source raster mask → VTracer/compound contour → TrueType via Fontations → Type0/CIDFontType2 PDF via pdf-writer → independent render and extraction. Include Latin `8` and `6`, a detached mark in kana, a ligature/multi-codepoint string and a glyph on coloured paper. At least one glyph must be traced from source pixels rather than copied from a source font outline.
4. Prove separate GID/CID/Unicode mappings: same outline with different semantic strings; different outlines with the same string; an observed `8` with OCR `6` that remains visibly `8`. Check that counter holes are true contours, not white fill. Validate fonts with an independent parser/OTS and final PDFs with qpdf plus independent rendering/extraction tools.
5. Build the searchable raster control using the same OCR. Run the bounded benign pilot through existing qualified MRC/raster baselines when inputs and tools are available. Record exact settings, failures, external OCR differences and measured bytes. No claimed size advantage until measured.
6. Record one product-value hypothesis and the M1/M2 plan. Freeze the architecture/contract decisions that the probe has actually resolved; explicitly list unresolved capabilities and test evidence. Stop at M0 for independent review.

## Implementation discipline

Use stable behaviour IDs and Given/When/Then expectations, not a large test DSL. A test must fail for the defect before the fix, where practical. Keep commits small and coherent. Update the ledger after each gate. Do not rename a failing test, lower an invariant, exclude a bad document, or substitute synthetic success for a blocked real-data gate without an explicit recorded decision.

Prefer three production crates: `scanweave-core`, `scanweave-io`, `scanweave-cli`. The core owns reconstruction logic but no filesystem/network/process access. The host-neutral plan must be usable by a Rust application without running a CLI. A development-only qualification harness can use Python and independent tools; Python is not a mandatory production dependency.

Use existing OCR, codecs, tracing, font and PDF libraries. No direct reuse of copyleft implementation code in the permissive core without an explicit licensing decision. No model or font download during document processing. Do not package proprietary font files or private reconstruction dictionaries.

No automatic text correction, dehyphenation, Unicode compatibility normalization, image cleanup, whitening, smoothing of uncertain marks, or generic font substitution. Preserve barcodes, handwriting, stamps, figures, rules and unknown ink. Financial presets add protection but do not certify that all sensitive fields were detected.

A successful openable PDF is not success. A hidden OCR layer under an unchanged page is a control/fallback, not reconstruction. A vector overlay that leaves the old full-resolution scan bytes in the file fails the reconstruction-size contract. A pure-raster result can pass safety but cannot pass the real-vector gate.

Never infer semantic accuracy from visual fidelity or vice versa. Report upstream OCR mistakes without changing source shapes. Every searchable span must have one semantic owner. No duplicate invisible layer under already mapped visible text.

## Review and reporting

Obtain independent review of the plan and the actual implementation/artifacts. Use the configured separate reviewer, not an invented tool or a second paragraph written by the implementer. Where available, the usual `deepseek-reviewer` can handle minor milestones, with independent PR review for major milestones. A missing reviewer is `REVIEW_PENDING`, not approval.

The M0 report must contain:

- Exact code revision, dirty-state disclosure, toolchain/dependency lock and source hashes.
- Files changed and the purpose of each architectural boundary.
- Commands/tests actually executed, exit codes and raw artifact paths/hashes.
- Raster and reconstructed PDF samples, extraction output, font/reader checks and counter-hole evidence.
- Side-by-side evidence for wrong-OCR-label preservation; no screenshots fabricated from an imagined output.
- Pilot baseline measurements where run; precise blockers where not run.
- Resource/timing observations separated from OCR cost and setup time.
- Reviewer findings and response, unresolved issues, and explicit M0 PASS/HOLD/FAIL decision.

Do not mark any corpus HUMAN_VERIFIED without a real scoped review. Do not claim broad script/platform support from compilation alone. Preserve failed experiments. Stop after M0; provide the concrete evidence and bounded next milestone instead of implementing the entire backlog in one run.
