# ScanWeave ledger

Format per AGENT_BRIEF/QUALIFICATION: milestone state, exact revision, tests/commands, failed
attempts, reviewer findings, unresolved coverage, accepted decisions. Append-only; newest gates
at the bottom.

## Gate: M0 plan review — APPROVED (2026-10-13)

- Artifact: `M0_PLAN.md` revision 2 (uncommitted; repo init is WP-A, this file and the plan are
  committed first with the packet reference).
- Reviewer: deepseek-reviewer (independent subagent, session `ses_ecb3c7da7ffeK3SKK1CcaRlg15`).
- Round 1: VERDICT REVISE — 4 blocking findings:
  1. shared geometric error budget asserted, not operationalized;
  2. §6.1 four-part encoding key absent from plan/proofs;
  3. E1/E2 evidence could pass without glyph reuse / distinct GIDs (no font-graph proof);
  4. second independent PDF engine optional, absence not wired to NOT_RUN/PROVISIONAL.
- Response: plan revised (error-budget policy `m0-probe-1`, four-part key in probe data model,
  CIDToGIDMap/content-stream-based E1/E2 evidence, PDFium required route + NOT_RUN wiring);
  all 9 non-blocking recommendations adopted; reviewer's 5 round-2 refinements folded in
  (executable four-part-key property test E0, E2 two-CIDs→two-GIDs→one-string wording,
  stage-wise decomposition for rejected glyphs too, VTracer-tolerance coupling recorded as
  §11.1-class probe risk, E6 reuses B0 glyphless-font path).
- Round 2: VERDICT **APPROVE** — all four findings RESOLVED, no new blocking findings.
- Decision: implementation authorized per plan. Expected M0 ceiling: PROVISIONAL (corpus not
  mounted); PASS reserved per operator exit table.

## WP-A/B note — additional locked crates (2026-10-13)

- `sha2 0.10.9` and `unicode-segmentation 1.13.3` added to scanweave-core during WP-C prep;
  both MIT OR Apache-2.0, sha256 recorded in UPSTREAMS.lock.toml. Reason: SPEC §4.2 binding
  hashes and §4.3 grapheme-integrity validation require them; no permissive equivalent was
  already in the graph. Per lock policy: explicit entry + this note (not silent).
- Environment constraint recorded: session has no root; apt installs impossible. qpdf built
  from pinned source, OTS from prebuilt release, PDFium from pinned release; tesseract
  recorded UNAVAILABLE (optional OCR subprocess; M0 synthetic probes do not invoke OCR).

## WP-D environment note (2026-10-13)

- Qualification Python deps (pypdfium2, jsonschema) live in `qualification/.venv`
  (gitignored). System pip is PEP-668-managed and `~/.local` site-packages is
  read-only in this session; a venv was the clean solution per operator direction.
- Engine #2 = PDFium via pypdfium2 (bundled PDFium build, Apache-2.0/BSD-3-Clause;
  qualification-only). The bblanchon pdfium tgz recorded in UPSTREAMS remains
  unused by the harness; noted honestly here.

## M0 implementation gate — PROVISIONAL (proposed; pending final independent review)

- WP-A..G executed 2026-10-13/14; commits per work package.
- Tests: 35 Rust (tests-first) + 7-page dual-engine verification + 8/8 E-proofs +
  dual-layer schema fixtures (6 negative reproduced) + B0 neutrality/transport.
- Notable failures encountered and fixed (all preserved in git history):
  blank-render bugs (CID 0 notdef reservation; ToUnicode codespace <0000>-<0000>;
  glyph units not transformed; missing ×upem scale; translation term missing /upem),
  hOCR reader class-stack bug, name-table sort order, maxp v1.0 fields, cmap
  one-char-one-glyph dedup, vtracer smoothing exceeding trace budget (resolved via
  corner=0/length=1.0 + 2× supersampling; 0.496px ≤ 0.50 allocation).
- Open items recorded in M0_REPORT.md §7 (sub-pixel edge metric, ﬁ 1px placement,
  p06 topology AA sensitivity, MRC/tesseract blocked, corpus blocked).
- Expected outcome: PROVISIONAL (no corpus, external baselines blocked). No M1 work.

## Final M0 review — REVIEW_PENDING (2026-10-14)

- deepseek-reviewer dispatch for the final implementation/artifact gate FAILED with an
  infrastructure error: "Upstream request failed: Insufficient account funds"
  (task_id ses_ec8d80710ffeY9txBR8aHFjS59). No review occurred.
- Per SPEC/AGENT_BRIEF: a missing reviewer is REVIEW_PENDING, not approval. The M0 exit
  decision in M0_REPORT.md §10 remains a PROPOSAL (PROVISIONAL), not a decision.
- NOT DONE without review: M1 authorization, any unblocking of the operator exit table.
- Retry: re-dispatch the final-gate reviewer when reviewer capacity is available.

## Final M0 review — VERDICT: PROVISIONAL (deepseek-reviewer, 2026-10-14, session ses_ec8c14e48ffedje5AJdKw6Ko0m)

- Reviewer could not execute commands (restricted shell); verdict based on independent
  re-parsing of committed artifacts (QDF dumps of CIDToGIDMap/ToUnicode) + harness/code
  reads. Execution NOT_VERIFIED items acknowledged in the review itself.
- FONT ARCHITECTURE VERDICT: E-proofs DO demonstrate different character codes reusing
  one visual glyph with independent Unicode mappings; OCR mistakes cannot become visual
  mistakes. Caveat: allocation key was 2/4 components.
- Blocking findings (all repaired in the post-review commit):
  - B1 four-part key absent → `encoding.rs` implements the full key; report corrected.
  - B2 E0 not executable → `e0_four_part_key_property` Rust mutation test, run by harness.
  - B3 visual gate unevaluable (integer metric floor) → sub-pixel AA edge metric
    implemented; honest measured outcomes recorded (poppler passes edge on 4 pages;
    pdfium ~1.1px; p01 MAE 0.0206>0.02; p04/p06 fail) — no waiving.
  - B4 byte breakdown claimed-not-delivered → breakdown.json emitted per page and
    surfaced in measurements.json; flate2 + visioncortex added to UPSTREAMS.lock.toml.
- Non-blocking items accepted for M1: 2× DPI render comparison, threshold-offset
  representation, report revision-line staleness (fixed), PDFium double-provisioning
  (already disclosed), copyleft/determinism execution verification.
- DECISION: PROVISIONAL stands (reviewer's own verdict; repairs address blocking items;
  corpus + external baselines remain blocked). M1 NOT authorized.

## Operator disposition — M0-Q authorized (2026-10-14)

- Commit 3172a32 ACCEPTED as the provisional M0 baseline; tagged `m0-provisional-baseline`.
- PROVISIONAL accepted as correct. M1 remains BLOCKED.
- Architecture, reconstruction algorithm and public interfaces FROZEN unless a concrete
  qualification failure demonstrates a defect (repair allowed; redesign is not).
- Next phase: **M0-Q (qualification closure)** — evidence gaps only:
  1. independent reproduction (full suite executed, versions/commands/hashes recorded)
  2. visual-failure characterization (PDFium ~1.1px displacement; p01 MAE 0.0206 vs 0.02)
     — geometric fidelity vs renderer AA distinction; defects repaired or a versioned,
     independently-reviewed policy amendment proposed; thresholds never auto-relaxed
  3. benign pilot corpus mounted (document-level split isolation; holdouts preserved)
  4. external MRC baselines on identical sources (bytes, extraction, fidelity, non-text;
     repeated-glyph coverage)
  5. consolidated gate report: every criterion PASS/FAIL/BLOCKED, no implicit waivers
- Evidence-ledger distinction preserved per operator: the previous review verified QDF
  properties by re-parsing but did NOT independently execute the full suite; that
  distinction stands until an unrestricted execution reproduction is recorded.
- Expectation recorded: reconstruction need not beat MRC per-document; M0-Q establishes
  correctness and measurable costs, not compression superiority.

## M0-Q phase entries (2026-10-14) — reviewer REVISE findings repaired

- **Corpus mount check**: no benign corpus anywhere on this machine (filesystem scan of
  /data, /mnt, /media, /opt, /srv recorded in session). Q3 remains BLOCKED; adapter
  delivered (`qualification/corpus_adapter.py`).
- **External-baseline tool builds** (all pinned, no root): libtiff 4.6.0 (sha256
  88b3979e…), leptonica 1.85.0 (3745ae3b…, rebuilt with TIFF, webp/openjpeg off),
  tesseract 5.5.0 (f2fb34ca…), OpenJPEG 2.5.2 (90e3896f…), OCRmyPDF 17.13.0 (venv),
  archive-pdf-tools 1.5.7 @ 8fe8b5b7. eng.traineddata sha256 7d4322bd….
- **IA-tools compatibility shim (recorded per prior review)**: recode.py getPageImageList
  → get_page_images (PyMuPDF ≥ 1.22 removed the alias; Python 3.12 has no legacy build)
  + modulo index guard. 6 lines, applied to BOTH the source tree and the venv-installed
  copy. Black-box AGPL comparator; no code enters the permissive engine.
- **Defect repairs in the frozen-phase code** (charter-sanctioned; disclosed per review
  B5): (1) ink colour — reconstruction painted pure black over gray-30 source ink;
  now samples and repaints source ink colour (caught by the whole-page MAE gate; p01
  poppler now passes all criteria, MAE 0.0206→0.0052). (2) units.rs ownership: greedy
  first-claim → tightest-containing-box (real OCR boxes overlap); did NOT fix the
  touching-char loss; reproduction re-run on the final tree. (3) hOCR reader: tesseract
  5.5 cinfo format (direct char text, x_conf, word text = char concat).
- **Reproduction re-run on the FINAL tree** (after all repairs): 37 tests pass; 28/28
  artifacts byte-identical across independent checkouts; full SHA-256 digests committed
  at qualification/repro_hashcheck.json (supersedes the truncated-digest check at
  6fb9d24 flagged by the reviewer).
- **measure.py**: external-baselines section now EXECUTES the pinned tools (no longer
  hard-coded BLOCKED); p09 real-page comparison recorded in measurements.json.
- **p08/p09/p10 fixtures** added (symbols; real-tesseract text page; 4-page repeated
  text). probe_results.json covers 8 gate pages after re-run.
- Report corrections per review B1/B2/B6/B7: MAE narrative corrected (ink-colour defect,
  not AA softness), displacement stats per-page (no aggregate cherry-pick; p04 worse,
  p08 completed), page count fixed, B0 113-char wording corrected (loss is in OCR-import
  segmentation, affects B0 and B2 equally; NOT tesseract misrecognition — earlier
  examples misattributed and corrected).
- m0-qual-1 amendment NARROWED (MAE replacement withdrawn — the gate was right); the
  remaining draft item is engine-AA-aware edge comparison, pending M1 calibration data.
