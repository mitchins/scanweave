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
