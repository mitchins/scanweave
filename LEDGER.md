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
  poppler now passes all criteria, MAE 0.0206→0.0038 poppler / 0.0052 pdfium). (2) units.rs ownership: greedy
  first-claim → tightest-containing-box (real OCR boxes overlap); did NOT fix the
  touching-char loss; reproduction re-run on the final tree. (3) hOCR reader: tesseract
  5.5 cinfo format (direct char text, x_conf, word text = char concat).
- **Reproduction re-run on the FINAL tree** (after all repairs): 36 tests pass; 32/32
  artifacts byte-identical across independent checkouts over 8 gate pages; full SHA-256
  digests committed at qualification/repro_hashcheck.json. An earlier truncated-digest
  spot-check existed only outside the tree (never committed) — the committed record is
  the final-tree full-digest file.
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

## M0-Q round-2 reconciliation (HEAD 440a29a, child of 9c28819) — appended verbatim from the reviewer

> M0-Q round-2 reconciliation (HEAD 440a29a, child of 9c28819): the evidence base is now consistent with the committed artifacts — independent reproduction on the final tree is 36 tests / 32 byte-identical artifacts across 8 gate pages (repro_hashcheck.json `all_equal: true`), the visual characterization is re-derived (p08 present; p01 0.257 px / 74.3%; p01 MAE 0.0038 poppler), external baselines are harness-executed and committed (p09 24,058/45,020/40,120/…; p10 totals src 164,141 / B0 216,444 / B2 100,282 / OCRmyPDF 169,244 / IA MRC 189,213), the p08 pdfium transport-order exception is surfaced in the §5 gate table, and all thirteen gate rows are PASS/FAIL/BLOCKED with no implicit waiver. Established: charter points 1, 4, 6, 7, 8 PASS; the touching-character 5/118 loss is honestly attributed to OCR-import segmentation (B0 and B2 equally). Remaining open: three narrative-doc citation lags (report/ledger still state 28/28-7-pages instead of 32/8, cite poppler p01 MAE 0.0052 instead of 0.0038, cite p05 0.199/80.1% instead of 0.133/86.7%, and cite OCRmyPDF 40,120 vs committed 40,121), plus the previously scoped BLOCKED items (benign corpus not mounted; m0-qual-1 amendment review pending; MRC lossy matrix deferred). M1 remains NOT AUTHORIZED: the multi-symbol ownership solver is its first deliverable, unblocking with corpus mount.

(The four enumerated citation lags were corrected in the same commit that appends this
statement: 32/8 everywhere, poppler p01 MAE 0.0038, p05 0.133 px / 86.7%, OCRmyPDF
40,121. No data values changed — citations only.)

## M0-Q hardening pass (2026-10-14)

- Item 1: sub-pixel edge interpolation CORRECTED (mirrored direction →
  inside→outside t*); rigorous i50 = (paper+ink)/2 per image; 11 analytical
  tests green incl. mirrored-implementation regression guard; visual metric
  regenerated (Poppler p95 0.50–0.52, pdfium 0.51–1.00; MAE passes all pages
  Poppler Poppler p01 0.0038). No threshold relaxations.
- Item 2: touching-character transport defect REPAIRED — one visual unit may
  carry multiple semantic chars (ordered by OCR slot index, not polygon x0).
  Regression tests RED 113/118 → GREEN; end-to-end 118/118 exact-order in both
  engines. Also fixed: normalized-JSON export emitted null for schema-optional
  fields (real interchange bug caught by the adapter's validation).
- Item 3: extraction verified against the ORIGINAL OCR input (cardinality +
  duplicates + per-span coverage, both engines); p08 ordering stays FAIL.
- Item 4: corpus_adapter hardened (pixel-hash binding, OCR validation,
  document-level splits, sealed holdouts); runner --pages argparse +
  --fixtures-dir; miniature synthetic-corpus end-to-end test all green.
- Item 5: dates reconciled (2024→2026); measure.py external runs fail closed;
  measurements regenerated (p09 B2 24,110B; p10 B2 100,490B = 0.59× OCRmyPDF,
  0.53× IA MRC); non-quality-equivalent mark superseded by the item-2 repair.
- Full suite: 38 cargo tests (incl. E0 + p09/p10 transport regressions),
  sub-pixel analytical, corpus pipeline, schema layer — all green. REVIEW OF
  THIS PASS PENDING (deepseek-reviewer).

## M0-Q hardening-pass ACCEPTED (deepseek-reviewer, 2026-10-14)

> **Ledger statement (M0-Q hardening-pass acceptance).** The M0-Q hardening pass is
> accepted at final revision 086bf57: the reviewer's two residual findings are closed —
> the gate-artifact write privilege is now restricted to the unqualified default run
> with all subsets/overrides failing closed absent an explicit `--out`
> (checks.py:742-752), and the reproduction record pins the hardening-pass final
> revision with 38 cargo tests (matching the tree's 38 `#[test]` functions), 8 gate
> pages, and 8/8 E-proofs while retaining the historical `597386f`=36-test and
> `9c28819`=digest-only records — and the canonical `qualification/probe_results.json`
> (8 pages, top-level gates E0–E7 all true, 8 eproofs) was demonstrably not modified by
> either of the last two commits. The previously scoped BLOCKED items (benign corpus
> not mounted, m0-qual-1 amendment review pending, MRC lossy matrix deferred) remain
> open and are not waived; M1 remains NOT AUTHORIZED.

## M0-Q final correctness correction — defects REVISE-repaired (2026-10-14)

- A (semantic search): RED recorded (raw extraction 'Tota l a m o u nt...', all three
  queries MISSING in PDFium). Repaired via per-span /ActualText marked-content runs
  (SPEC §6.2, ToUnicode retained as per-glyph fallback; astral spans keep ToUnicode
  since PDFium drops astral inside ActualText). GREEN: all three queries in PDFium +
  Poppler for B2 and B0; 118/118 exact transport; test_text_search.py covers
  decimals/negatives/refs/ligatures/kana/supplementary-plane + defect-signature
  guard; checks.py word_boundary_ok + no_intra_word_spaces are now PRIMARY gates
  (cardinality supplementary). p08 pdfium ordering FAIL preserved (cause: PDFium
  \x02 span artifact + layout order).
- B (holdout sealing): RED recorded (holdout normalized content written to the
  bundle; seal varied with --out). Repaired: holdout identified pre-processing;
  sealed from canonical identity + source-byte hashes (scanweave-holdout-seal/1);
  never materialized without --include-holdout; seal byte-content-bound and
  location-independent; --include-holdout preserves the development seal; explicit
  --out to the canonical gate artifact refused (B7).
- Tests: text_search (all), corpus_adapter (all incl. B1/B2/B7), subpixel analytical,
  schema layer, 38 cargo tests. Reproduction: fresh checkout at final revision,
  38 tests + 8/8 E-proofs + 32/32 artifacts byte-identical.
- awaiting deepseek-reviewer sign-off of this correction.
