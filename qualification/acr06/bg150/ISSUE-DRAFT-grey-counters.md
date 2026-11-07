# Draft issue (not filed): the default ClearScan background replaces glyph ink with paper-grey blobs (historical p5)

Found during the ACR-06 independent review of the 150-DPI background experiment (`REPORT.md`). This is not caused by that experiment: the default output on current main (36ad4ea) has it.

## Observation

`qualification/pdf_packaging/groups/historical-input.pdf`, page 5 (CP3 "historical-p4"). Default ClearScan output: `--dpi 300 --profile clearscan --glyph-sharing off`, output SHA-256 `8486f69c…f9a`.

The output page has a single layer: one 1171×1626 DCT background (`/Im0`) and no vector glyphs. In that background, the ink of several glyphs is replaced by a flat mid-grey (paper-tone) blob. At 300 DPI, crop origin (149, 1180), size 720×240:

- the lower bowl of `g` in "ingenui" (first line): source median 74 (ink), output median 105 (grey fill);
- the `d` of "rudiméta" and the `a` of "ad" (third line).

It shows in both PDFium and Poppler, so it is in the image data, not the renderer.

## Since when

It is already present in the FONT-04 R2a baseline (`font04/local/R2a/baseline/historical-off.pdf`), in pre-#34 main (`acr06/local/donorfix/candidate/historical.pdf`), and on current main. The cause has not been diagnosed. Candidates are residual cleanup or speck removal that paints local paper over ink, or ink erased for a glyph whose vector replacement was later rejected and whose source pixels were not restored.

## Why it matters

The mission states that "restoring correct characters is mandatory". This visibly damages characters on historical text, where text drawn as vectors is about 0.1%, so the background is the only representation of the text.

## Suggested next step

Diagnose in a bounded way. For each changed region, trace which pipeline stage modifies those background pixels, and survey the corpus for the same signature: output pixels inside source ink lifted to near-paper tone. Do not change any defaults until that is understood.
