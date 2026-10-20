# Independent review: full-em semantic owner frame

## Artifacts reviewed

- Synthetic 300-DPI output: `300/owner-em.pdf`, 733,974 bytes, SHA-256 `8e57afa9599f3be936f44a13b326e09b40b7e82cfdd57c32bd80666944d8cc4c`.
- Real cord00 output: `real/owner-em-cord00.pdf`, SHA-256 `68679ca9544d01d8a7109d7f228969e419436de04e42221bd2944c186eb684f9`.
- Semantic owner implementation at HEAD `ec7bcdc`, with the direct encoding/union regression test present as an uncommitted working-tree change during this review.

## Independent checks

For all eight synthetic pages, I compared Poppler `pdftotext -layout` and `pdftotext -raw` after removing whitespace. Every page matched. Raw extraction also matched the supplied OCR reading order and separators exactly on all eight pages. Non-space page counts were 76 on page 0 and 68 on each of pages 1–7. The trailing form-feed produced an extra empty split entry, which is not a PDF page. `pdfinfo` reports 8 pages at 432 × 216 pt.

I independently compared the full-em PDF to the preserved pre-owner geometry PDF (`300/source-gate-trial/final.pdf`, SHA-256 `f2ec4e0425869eaba5a3bc4ec41ec583b0e9342ce3990abf6236e3e45e515aa5`) by re-running the outline audit on both. Both contain the same 515 visible `(page, symbol)` occurrences. Across all of them, outline hashes, text matrices, and placed outline bounds are identical. CID indices changed for 118 occurrences and GID indices for 119 because the shared document font now contains the private owner glyph; the outline reuse distribution is unchanged.

On `real/owner-em-cord00.pdf`, I independently extracted text with PDFium and Poppler `pdftotext -raw`: both yielded 423 non-space characters, and the normalized strings matched exactly. The preserved regression report records the preceding arm at 467 PDFium versus 423 Poppler characters (edit distance 56), and the fixed arm at 423 versus 423 (edit distance 0).

## Targeted code review

The full-em frame has bbox `[0, 0, 1022, 2048]` and span `[1022, 2048]`. It is appended after visible glyph shapes, and ClearScan owner CIDs use `(owner-frame index, character)` keys. The regular document font and its existing union/remap path are reused; the repeated frame shape key collapses to one glyph across pages. The new direct regression test constructs repeated `é` labels that are both visible and hidden, asserts distinct shape/CID ownership, and checks that the shared document union retains one semantic-owner frame.

The updated frame fixes the previously observed `pdftotext -layout` versus `-raw` ordering disagreement on this synthetic fixture while preserving visible glyph outlines and placement. No concrete correctness defect remains in the reviewed owner-frame/CID change. The working-tree unit test had not yet been run at the time of review; the parent reported that the full qualification reruns were in progress.
