# FONT-04 — Independent review of Checkpoint R1

Reviewed:
- product branch `feat/glyph-sharing` at `3fcd4ea` (runtime build `a0584c8`);
- research receipt `85f7ae7`;
- freeze commit `5356255`, under contract `3610e00`.

Reviewer artifacts are in `qualification/font04/review_r1/`.

## Verdict

**R1 is accepted. The native Rust pathway is a faithful, deterministic implementation of the
frozen cover-2.0 method.** It may proceed to R2, under the conditions in §5.

## 1. Reproduction (mine)

| Check | Result |
|---|---|
| Clean build of `3fcd4ea` in a separate worktree, `--release --locked` | OK |
| `--glyph-sharing cover-2.0` on `financial-input.pdf` (`206f0f66…`), pinned PDFium chromium/8100, `SCANWEAVE_RESEARCH_PYTHON=/nonexistent` | `b007a27d…`, byte-identical to Codex's cover-2.0 and its repeat |
| Text extraction (mine) | Poppler default, `-layout` and `-raw`, and PDFium page text are identical to default |
| Python at runtime | None. The only subprocesses in shipped code are the existing `pdftoppm`/OCR invocations |
| Runtime, same machine | Default 7 min 56 s, 1.47 GB peak RSS (`74c31136…`, re-verified). cover-2.0: 20 min 47 s, 1.93 GB peak RSS. 24 cores, load average about 7 on both runs |

## 2. Parity with the frozen research oracle

Recomputed from `reference-oracle.json` and `r1-native-ledger.json`.

| Measure | Result |
|---|---|
| Accept/reject agreement | 3,522 / 3,524 (99.94%) |
| Canonical agreement on jointly accepted members | 1,745 / 1,749 (99.77%) |
| Safety superset | **0 violations.** No member the oracle rejects on a hard check, hygiene, weight band or owned-ink check is accepted by Rust |
| Owned-ink veto | Same 52 members in both, including member 3422 (glyph-277) |
| Accepted | 1,750 in both |
| Net outlines retired | 326, against 327 |

The two decision divergences:
- **Member 174** is accepted by Rust. The oracle rejected it only on `ranking_or_economy_exception`, a soft rule, not a safety check.
- **Member 1307** is rejected by Rust on the stroke-weight band, where the oracle accepted it. Rust is stricter here.

**Blind review.** I graded all 12 sealed panels covering the six divergent members, in PDFium
and Poppler. My judgments were saved and hashed before the key was opened (`1f2eaea8…`). All 12
are indistinguishable from current output. No divergence is harmful.

## 3. Product code

- **Scope:** 25 files.
  - Rust: `glyph_sharing/` (fit, font, group, ownership, plan, source, transport);
  - CLI flag wiring and `docs/glyph-sharing.md`;
  - tests and small fixtures;
  - `THIRD_PARTY_LICENSES/scipy.txt`, for the BSD-licensed port of the trust-region fit.
- **Default:** `--glyph-sharing off` is the default. Financial default byte identity was
  re-verified by Codex (`74c31136…`).
- **CI:** the `sonar.yml` change only moves Rust coverage after the hash-pinned venv, so tests
  can load the pinned PDFium. It adds no exclusions and lowers no gate.
- **Economy:**
  - Font 727,259 → 664,549 B (−8.6%); PDF −52.9 KB.
  - Serialization is smaller than the research emitter's, because of one shared `W` array,
    sparse CID maps and integer-quantized canonicals. Membership policy is unchanged.
  - The 54 zero-credit groups cost 24.1 KB of outlines plus 3.3 KB of stubs, reported
    separately as required.
- **Determinism:** identical across repeat runs and across 1 and 4 rayon threads.

## 4. Findings

1. **PDFium is a runtime dependency of the opt-in path.** The owned-ink preflight renders with
   PDFium (`glyph_sharing/ownership.rs`), loaded from `SCANWEAVE_PDFIUM_LIBRARY` or the system
   loader.
   - That is acceptable for an opt-in feature: PDFium is a pinned upstream
     (`UPSTREAMS.lock.toml`, chromium/8100), and a missing library is an explicit error, never
     a skipped check.
   - But **decisions can depend on the PDFium build**, so results are reproducible only
     against the pinned build.
2. **Runtime.** **Sharing makes conversion 2.6× slower: +12 min 51 s on 13 pages. Peak
   memory is 32% higher (+0.47 GB).**
   - This is the most important product finding at R1. It does not affect correctness, but a
     13-page document taking 21 minutes is not hassle-free.
   - No stage breakdown is reported yet. The likely costs are the per-member trust-region fits
     (35 evaluations each, over about 3,500 members and their candidate canonicals) and the
     PDFium owned-ink preflight, which renders source, default and candidate at 4×.
3. **CLI surface.** `cover-1.5` is user-visible. It is the comparison arm, not a product
   option. Decide at R3: either a single `--glyph-sharing on|off`, or keep the names and mark
   1.5 as diagnostic.
4. **Adobe Reader is still blocked on the owner**, waiting for the Windows x64 installer for
   26.00221.901. The PDFKit kit is prepared for R3.

## 5. Conditions for R2

1. **Pin and record PDFium.**
   - The conversion report records the PDFium library identity: version string or library
     SHA-256.
   - All R2 runs use the pinned chromium/8100 build.
   - This is a reporting change only, and must not alter any PDF. Prove that with the
     financial hash `b007a27d…`.
2. **Order of R2.**
   - Run the **32-page development corpus** and its blind review first. It is reusable
     evidence, not a single-use holdout.
   - **Open P2 only after the Adobe Reader check passes.** A Reader-driven transport fix after
     P2 would burn the holdout.
3. **Runtime and memory.**
   - Report paired default/sharing wall time and peak RSS per document, with a stage
     breakdown.
   - Do performance work before P2 **only if every output stays byte-identical**: the
     financial hash plus every corpus output. Examples: caching renders, parallelizing across
     groups with ordered reduction, pruning candidate pairs that cannot pass a hard check
     before fitting.
   - Suggested target, not a gate: sharing overhead of at most 1× default wall time. Any
     change that alters output is a method change and needs a stop.
4. Everything else in `FONT_04_PRODUCT_MISSION.md` R2 stands.
