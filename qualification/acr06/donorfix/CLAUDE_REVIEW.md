# Issue 29: independent review of the local-tracing candidate

Reviewer: Claude (scientific lead). Candidate: uncommitted worktree `fix/donor-geometry-29` at the time of review, from main 79b30e5. Codex's `REPORT.md` stands as the engineering record. This file records where my judgement differs from it and why.

## Verdict

**Qualified as a correctness fix, with the caveats below disclosed for owner decision.** Codex classed the candidate "not qualified" because of the strict surrounding-pixel and zero-overlap criteria and one PDFium extraction change. On inspection none of these is a material defect introduced by the rule:

- every changed visible substitution is either a corruption removed or an equivalent rendering;
- the pixel differences outside glyph neighbourhoods are raster re-encoding with no visible change;
- the overlaps are pre-existing (main has 48, the candidate 4, and none is new);
- the PDFium item is an instance of an extraction-ordering behaviour main already shows on 53 pages.

## Changed-substitution review (every row, not sampled)

Inputs: `panel-index.json` (1,443 rows over 54 runs), plus my own 300-DPI PDFium sheets (`review_sheets.py`, output under `local/donorfix/review339/`, 11 sheets). For each row, the script measures mean absolute grey error against the source inside the target glyph box, for main and for the candidate.

| Class | Rows | Review |
|---|---:|---|
| invisible → invisible (glyph not drawn in either build) | 1,104 | Pixel-identical at 300 DPI in the glyph box (`main_vs_cand = 0`); decision-label change only |
| visible → visible | 325 | Inspected one by one: source / main / candidate in word context, target outlined |
| visible → invisible (raster fallback) | 14 | Inspected one by one |

Result for the 339 rows that change visible output:

- Candidate error against source is ≤ main on **every** row; the largest increase is 0.00.
- No newly introduced wrong character, case change, neighbour consumption or blob.
- Main corruptions removed include all 12 confirmed glyphs. Beyond those, the review saw many more:
  - giant `I` in "REWIND"; raised `e` in "the"; raised `l` in "c'leaned";
  - blobbed "to" and "full."; broken `1` in "8813" and "9O1Il";
  - shrunken `u`/`g`; narrow or bloated `e` across the P2 stress sheets;
  - historical Fraktur blobs.
- Faint and damaged fresh-set glyphs render in the same style as main (ClearScan darkening). No genuine stroke restoration visible in main was lost on the reviewed rows.

## Items Codex flagged as blocking

1. **Historical PDFium "‘Quoquo" repeat.**
   - The content stream holds the same 667 glyph ops, with the same Unicode sequence, in main and the candidate.
   - Five glyphs change mode or position. The relevant one is `w000105s0001` `t`, whose owned ink is 1×1 px. Main painted a 14×10 donor `t` over ink owned by its neighbour; the candidate rejects it, and the glyph becomes invisible OCR text.
   - PDFium's text page then reports 805 chars against 797 and repeats one word. Poppler is unchanged, and search on the affected words is unchanged.
   - PDFium-only word surpluses over Poppler already exist in main on 53 pages (338 words). The candidate's net change is +1 on historical p1; mixed and forms change line breaks only.
   - Judgement: minor, pre-existing class; disclose it; follow up in the invisible-text placement code, not in this PR.
2. **Surrounding pixels on P2 sheet 5** (14,832 PDFium px beyond 16 render px). At 150 DPI the far-away differences are edge-only antialias and re-encoding changes in raster patches. Main and the candidate are visually indistinguishable there (`p25cmp.png` in the scratchpad review). These are documented output changes, not damage.
3. **Fresh seed 1 at 600 DPI**, page IoU 0.914106 → 0.913918. The visible fresh-600 rows (office, ffi) are equivalent; the second seed improves.

## Runtime (sequential, same machine, my measurement)

| Input | Main | Candidate |
|---|---:|---:|
| single | 30.2 s | 32.4 s |
| mixed (group) | 105.3 s | 117.0 s |
| historical (group) | 69.0 s | 68.8 s |
| competitive 600 DPI (`--dpi 600`) | 37.1 s | 69.0 s |

The 600-DPI cost is local tracing: 190 rejected glyphs at about 195 ms each, and tracing time goes from 14.4 s to 51.5 s. Those glyphs are raster-owned in both builds there. This is a disclosed cost. A follow-up could defer local tracing until vector ownership is known.

## Reproduction

The candidate rebuilt from the worktree reproduces Codex's candidate PDFs byte for byte (single, mixed, historical, competitive600). Main reproduces too.

## Rule notes

- The thresholds are engineering choices, not calibrated:
  - edges within max(2 px, 15%) for healthy glyphs, max(2 px, 25%) for damaged ones;
  - page-scale IoU ≥ 0.70 / 0.65;
  - no donor ink on separately owned ink.
- The 0.70 healthy floor was lowered from 0.75 against an existing repository fixture, before the fresh sets were run.
- No pre-existing gate or threshold changed. FONT-04 q3 is untouched.
- The m1d damaged-crossbar control still repairs.
