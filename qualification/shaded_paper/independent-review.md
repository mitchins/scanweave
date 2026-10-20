# Independent evidence review

Reviewer: existing `/root/independent_review`, read-only code/count/render inspection.

Confirmed:

- A: 792 visual units; all 192 text regions ContactNonText; 860 text draws all invisible; zero visible glyphs.
- B: 73 actual visible CID/GID paints, 63 unique painted GIDs, 16,345 suppressed ink pixels, zero suppressed antialias fringe.
- A→B raster −8,300 B; font +66,717 B; content +139 B; complete PDF +59,178 B.
- The narrower contact check unlocks some vector text; it does not solve all enclosing-frame/unsupported cases.
- PDFium and Poppler crops both show residual source rings at accepted 1/G. Rough vector contours remain visible. The defensible negative is a retained double edge and growth for this candidate, not that every B glyph is wrong or that every finer contact rule will fail.
- Both renderers retain the same 860 nonspace characters; B changes whitespace only.
- Rebuilt normal CLI output matches the published PDF hash exactly; no trial behavior remains enabled.
- No pristine historical font truth exists. Observation/proposal counts are not final rendered-glyph correctness.

Catch-up test review independently confirmed that the corrected auto-accounting regression checks the emitted candidate's bytes/stats/selection. The retained M1-D donor test still exposes a substantive missing repair and remains a merge blocker. CodeRabbit skipping due to file count is not an approval.

Conclusion: reject this bounded candidate, preserve failure evidence, and do not make a broader impossibility or quality claim.
