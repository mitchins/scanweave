# ACR-06 C2 review: does corrected-only ownership restore useful 600-DPI sharing?

Evidence: `exp/acr06-highdpi-ownership` at `a196c32` (`qualification/acr06/c2/REPORT.md`). Spent inputs only; no holdout opened. The research switch `SCANWEAVE_RESEARCH_OWNERSHIP` is inert when unset. Unset build = `main` byte-for-byte (P2″ 200/300/600), and trace mode reproduced all 38 saved PR #26 q3 outputs.

## Findings (reviewer-verified)

- **Legacy at 600 DPI is mostly invalid geometry, not a judgement.** Of 158 preflight assignments at 600 DPI, the legacy crop fell outside its render on 62. 47 of those the corrected check passes.
- **Legacy also misses real exceptions at 600 DPI.** In 23 further assignments, legacy reports no exception and the corrected check does. Removing legacy is therefore not "just relaxing"; under the combined rule the corrected check is the one that protects.
- **Benefit is negligible.** Corrected-only admits 35 extra substitutions at 600 DPI and 6 on financial (non-integer, 435/1813 pt/px matched exactly). PDF saving vs q3: 7,423 B over 11.99 MB at 600 DPI (0.062%); financial 150 B. One document (P2′ sheet 6) got 151 B larger.
- **Fidelity cost is small on average but real per glyph.** Pooled 600-DPI mean pristine error +0.00007 (both renderers); individual glyphs up to +0.058 (P2 sheet 7, overlapping N members). The approximate independent owned-component screen fired on 2 members (p2-7 `w000044s0001` Poppler; p2prime-8 `w000050s0005` both renderers).
- **Panels** (all 35 members, both renderers, native 600 DPI, reviewer inspected the first 30 rows): no wrong characters; some visible weight and proportion changes (e.g. p2-7 `n` members), which is the expected style cost of sharing.
- **Runtime/RSS:** unchanged within one-run noise.
- **Scope gap:** 38 documents, not 41; forms, receipts and historical were not rerun. They had no substitutions removed by the repair, so this does not change the verdict.

## Recommendation

Do not propose a corrected-only amendment: the benefit (≈0.06%) does not justify a new qualification with a fresh evaluation set, and the per-glyph error increases are not free. Keep the combined veto. Instead, if wanted, a small diagnostics change: report in the conversion sidecar how many assignments were rejected because the legacy crop was out of bounds, so a 600-DPI user can see why sharing did little. No default change, no FONT-04 verdict change.

Housekeeping: `numeric-records.json` (25 MB, one line) was committed on the research branch; the first push failed with a GitHub `commit_refs` server error and Codex published the same tree through the Git data API. This is an unprotected research branch, so no protection was bypassed.
