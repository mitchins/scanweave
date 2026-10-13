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
