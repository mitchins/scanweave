# Document glyph sharing (opt-in)

```sh
scanweave input.pdf output.pdf --profile clearscan --dpi 300 --glyph-sharing cover-2.0
```

The default is `--glyph-sharing off`. It retains the existing ClearScan PDF bytes.
`cover-1.5` is the frozen comparison point. Both options use native Rust; neither
starts Python or reads a research decision ledger. Labels need at least ten
visible draws in the document. Ineligible and rejected draws retain default.

The frozen owned-ink check uses PDFium, already a workspace dependency. Install
its shared library through your normal trusted package source and make it
available to the system loader, or set `SCANWEAVE_PDFIUM_LIBRARY` to its full path.
The default conversion does not load PDFium. A missing library during an opt-in
ownership check is an explicit error, not a skipped check.

Sharing preserves each occurrence's CID, text matrix, PDF width and ActualText.
TrueType composite stubs retain original advances and reference source-traced
canonicals. Separate CID-map resources resolve repeated-CID placements. Invisible
owners retain original programs. Net retirement is aggregate document accounting;
there is no per-group net-retirement gate. If aggregate retirement would be
negative or encoded font bytes would grow, the document emits default and records
that fallback in its JSON report. Candidate economy figures remain in the report
when fallback occurs; `substituted` is zero and member decisions retain default.
Zero-credit groups and their canonical/stub bytes are reported separately.

The existing per-page tracing reports describe reconstruction before document
sharing. The `glyph_sharing` report describes substitutions and actual font
economy; the R1 scorecards measure the emitted shared output independently.

Numerical reductions run serially in member/pixel order. Group priorities use
explicit index tie breaks. The bounded Huber trust-region fit retains the frozen
35 evaluations, `.001` relative differences and `1e-5` stopping tolerances; its
three-dimensional dense subproblem uses a deterministic symmetric eigensystem.
Hard checks use the original strict comparisons with no epsilon enlargement.
Offsets and F2Dot14 coefficients use round-to-even quantization. Changing thread
counts does not change reduction order. Qualification records numerical
variations and all membership/canonical divergences against the frozen oracle.

The numerical solver derives from SciPy's BSD-licensed TRF implementation; its
notice is in `THIRD_PARTY_LICENSES/scipy.txt`. No new crate was introduced:
`pdfium-render` was already in the workspace, and the existing `write-fonts`
reader feature is enabled to retain original glyph metrics safely.

FONT-04 qualification is reviewer-pending. This branch is not promoted to main.
