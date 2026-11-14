# BOOKS-01 human panel: unblinded comparison

**Inputs, in order:**
1. The reviewer's notes, unchanged: `responses.original.json`, sha256 `e24cb315…f7ef`.
2. Claude's interpretation, locked and pushed before the key was opened: `interpretation.json`, sha256 `b4d73f35…5f06`, commit `735ba26`.
3. The key, opened afterwards.

The free-text notes are the authoritative human review. The original AI assessments remain provisional. This panel is a calibration aid, not an independent evaluation of detector accuracy.

**Measured fact.** OCRmyPDF is pixel-identical to the source in all 20 panels (mean |Δ| = 0.00). ScanWeave differs from the source by 2.5–11.4 mean |Δ|, Archive MRC by 3.2–13.9, and Adobe by 4.6–35.4 (8-bit RGB, panel crops). Where a note puts OCRmyPDF among the weaker outputs (panels 004 and 006), it describes the source page's own condition, not anything the converter did.

## Comparative table
Labels were randomised independently per panel. "Worst aesthetically" is recorded as aesthetic only.

| Panel | Page / crop | ScanWeave | OCRmyPDF (= source) | Archive MRC | Adobe XI |
|---|---|---|---|---|---|
| 001 | luther "was" (0018) | better | better | implied: preserves faint-ink trajectory less well | implied: preserves faint-ink trajectory less well |
| 002 | 8967333 "OF" (0055) | **worst: "becomes a bit weaker"** | — | — | not mentioned |
| 003 | 8967333 "THE" (0056) | "adds a bit of gradient noise" (aesthetic) | "probably the cleanest" | — | "a bit too bold" |
| 004 | luther "ganz" (0014) | — | missing ink "made worse by thresholding" (output = source) | **missing ink made worse by thresholding** | — |
| 005 | luther "grosses" (0024) | — | — | worst | second worst |
| 006 | luther woodcut (0019) | — | second worst (output = source) | worst | — |
| 007 | luther coloured woodcut (0020) | — | — | worst | — |
| 008 | luther, background | alike | alike | smooths into a gradient (aesthetic; fine if intended) | alike |
| 009 | benner, background | — | — | foreground fragments harsh | — |
| 010 | arnold | — | — | worst aesthetically | — |
| 011 | luther, border | — | — | worst aesthetically ("if that's what matters") | — |
| 012 | arnold | — | — | worst aesthetically | — |
| 013 | arnold | — | — | worst aesthetically | — |
| 014 | 12342014 | — | — | worst aesthetically | — |
| 015 | arnold | — | — | worst aesthetically | — |
| 016 | arnold | — | — | worst aesthetically | — |
| 017 | aventinus (control) | — | — | — | worst aesthetically |
| 018 | 8967333 (control) | — | — | — | "probably clearer … without losing stroke" |
| 019 | luther (control) | "like the source" | — | "a bit on the weak side" | "probably ok"; thresholding acceptable here |
| 020 | aventinus (control) | less clear than Adobe | less clear than Adobe | worst | second worst, "decent", "more clarity" than ScanWeave and OCRmyPDF |

**Summary, without adding severity.**
- Archive MRC is named worst in 11 panels: 8 as "worst aesthetically" and 3 others. Weakening or missing ink is noted in panels 004 and 019, and loss is implied in 001.
- Adobe is named worst once (aesthetically), second worst twice, and "too bold" once. It is described as clearer or more readable in three controls (018, 019, 020).
- ScanWeave is named worst once ("a bit weaker", panel 002), gets "gradient noise" once (003), and is "better" or "like the source" twice (001, 019).
- The reviewer separates **restoration and readability** (Adobe's thresholding sometimes reads clearer) from **fidelity to the source**. The acceptance rule should keep these as separate axes rather than treating one as a defect of the other.

**Detector candidates.** Of the 9 new candidates (008–016), the human named the flagged row as worst in 4 (MRC in 012 and 015; MRC in 009 as "harsh"; and none of the Adobe-flagged 010, 013, 016). The ScanWeave-flagged candidate (014) drew no comment on ScanWeave. This is calibration context only, not a detector accuracy estimate.

## Potential material defects that need clarification
Only these four. The rest of the panel needs no repeat.
1. **Panel 002, ScanWeave (C) "becomes a bit weaker".** Is the O or F still the same character, or is a stroke actually lost? This is the only ScanWeave content concern raised. On the same crop, the AI's provisional finding was that Adobe (D) breaks the O into two arcs; the notes don't mention D. Does D's O look broken to you?
2. **Panel 003, Adobe (C) "a bit too bold".** The AI's provisional finding was that the H crossbar and part of the E are replaced by paper. Is that visible, or is it only heavier weight?
3. **Panel 004, Archive MRC (C).** Is the missing ink worse than in the source? Output D in this panel is pixel-identical to the source, so it shows the source's own condition.
4. **Panel 001, "was".** Do outputs B (Adobe) and D (MRC) still read as "was", or as a different word? The AI's provisional finding was that D reads like "n'a".
