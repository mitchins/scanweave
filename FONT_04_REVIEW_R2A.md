# FONT-04 — Independent review of Checkpoint R2a

Reviewed:
- research `2d6293c` (R2a evidence) and `068ad33` (Reader attempt);
- product `76681da`.

My blind judgments were committed before the key was opened: `51877d2`,
`qualification/font04/review_r2a/blind-judgments.json`, SHA-256 `8d961953…39d2`.

## Verdict

**R2a is accepted.** The mixed-document tail that triggered the stop is **immaterial** under
the decision rule fixed in `FONT_04_REVIEW_R2A_STOP.md` before grading.

The remaining gate before P2 is the **Adobe Reader check, which is still blocked**. See §4.

## 1. Blind review result

| | Mixed substitutions | Materially worse | Minor | Indistinguishable |
|---|---:|---:|---:|---:|
| All admitted mixed substitutions (326 members, 652 panels) | 326 | **0** | 2 | 324 |
| Mixed >0.02 tail stratum | 88 | **0** | 1 (member 518) | 87 |
| Financial >0.02 tail stratum | 88 | **0** | 0 | 88 |

The two minor members are:
- 518, the "w" in "with";
- 390, an "I" slightly lighter in PDFium only.

**Decision rule:**
- Rule 1: 0% of mixed substitutions are materially worse, against a 5% limit. **Pass.**
- Rule 2: 0% against financial's 0%, so the difference is 0 points, against a 10-point
  limit. **Pass.**

Every material defect I found blind turned out, after decoding, to be outside admitted output:
- **Pre-existing default defects.** Current and candidate are identical in each case.
  - In the mixed document's repeated word "body", the "o" renders as a tall elongated O. The
    same output shows "t꜊k", "t☐ me" and "t☐y" on mixed page 1 of `mixed-off.pdf`.
  - The oversized "TO" in forms member 204 is in the **current** arm.
  - The oversized "I" in "REWIND" appears in both arms.

  These belong to the default ClearScan reconstruction, not to sharing. They are logged here
  for a separate track and are out of scope.
- **Rejected counterfactuals.** Mixed member 36 ("but" shown as "bor") was *rejected* by the
  method. I checked the shipped PDF: every "but" renders correctly in Poppler and in the
  pinned PDFium.

**Sensitivity limit, stated plainly.** My visual pass caught gross defects: wrong, garbled and
oversized glyphs. It did **not** catch member 518's roughly 10% shrink, which is about 2 px at
panel resolution. I found that only through a blind pixel measurement after the pass, and graded
it minor. A reviewer at reading size would plausibly do the same. The rule was set at
"materially worse", and nothing came close.

## 2. Package defects (harness only; no product impact)

These are for Codex to fix before the P2 package is built:
1. **Rejected and fixture candidates render as a knocked-out page with only the target glyph
   drawn.**
   - This affects 305 rejected panels and 45 of the 46 fixture panels.
   - Those arms cannot be graded against the source. Fixture panels in particular were
     effectively ungraded for the candidate.
2. **30 reference arms are solid black boxes or garbled letter collages.** Examples: "leebm"
   for "Term", "faPan" for "from".
3. These defects did not affect the admitted-substitution strata the rule depends on. My inferred
   reference arm matched the true source in 1,147 of 1,162 accepted panels.

## 3. Corpus and runtime (from `r2a-corpus.json` and `r2a-profile.json`)

- **Fonts and PDFs:**
  - Font bytes: 1,037,603 → 968,734 (−6.6%).
  - Net outlines retired: 414.
  - Total PDF bytes: −55.8 KB against default, −46.0 KB against the save-only control.
- **Where sharing applies:**
  - Financial carries almost all the benefit.
  - Mixed: font −2.5%, but its PDF is 5.5 KB *larger* than the save-only control.
  - Forms falls back to default via the economy guard.
  - Receipts and historical have no groups.
- **Checks:** text equality in all five engines, qpdf, OTS and determinism all pass.
- **Runtime:**
  - Financial sharing/default wall time is 1.73× (was 2.6×). Corpus total is 1.64×.
  - The ordered row-worker optimization is byte-identical on every output.
  - Peak RSS is still +31% on financial: 1.87 GB against 1.43 GB.

## 4. Adobe Reader — still blocked

The check uses current Reader 26.002.22031 (x64, Adobe-signed) in a fresh Wine 9.0 prefix.
- The base MSI installs.
- The bundled MSP fails with MSI 1603 on `AcroPDF.dll` and rolls back.
- The rolled-back 21.1 executable then null-derefs on launch.
- No PDF was opened.

Reader DC x64 is not a supported Wine target, so this is an environment limit, not a PDF
finding. P2 stays closed until a Reader result exists. The owner chooses the route:
- **(a) Recommended:** the owner runs the check on real Windows, or a Windows VM, with the
  same procedure.
- **(b)** The owner supplies the official 32-bit Reader DC installer. Codex retries in Wine with
  protected mode off.

## 5. Next

1. Owner: pick a Reader route (§4).
2. Codex: fix the package defects in §2. Harness only; no product or method change.
3. After a Reader pass: P2 once, through the guarded generator, with the frozen product
   `76681da`.

## Addendum: package fix accepted (`6dde420`)

The package defects had one cause, in the review harness only. pikepdf `copy_foreign` reused the
imported font, so installing the probe font also replaced the page's default `/F1`. That produced
the knocked-out candidate arms, the garbled reference arms and the "bor" counterfactual. No product
code, PDF, method or threshold changed.

The v2 package (`local/R2a/blind-review-v2/`) passes Codex's checks on all 4,884 arms:
- no changes outside the target window;
- no black arms;
- ink in every source glyph box.

My spot check agrees: full word context appears in all three arms.

**Re-checked after the fix.** Both default defects I cited in §1 are real in the shipped PDFs, not
harness artifacts:
- the oversized "TO" appears in `forms-off.pdf` page 2 at 300 dpi;
- "b()dy" appears in `mixed-off.pdf` page 1.

**The verdict stands.** The R2a decision depended only on admitted substitutions, and those arms
were already correct:
- member 518's measured shrink matches Codex's unblinded evidence;
- the shipped mixed PDF renders correctly.

The v2 format becomes the template for the P2 package. I am not re-grading R2a on v2.
