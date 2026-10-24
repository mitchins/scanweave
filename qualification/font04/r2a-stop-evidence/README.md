# R2a stop: accepted mixed-document member 518

This is an **unblinded defect report**, not the sealed R2a review package.

On page 2 of `qualification/pdf_packaging/groups/mixed-input.pdf`, the `w` in
“with” (`w000044s0000`, native member 518, source draw 595) is accepted against
canonical 838 (`w000578s0000`, the `w` in “while”, source draw 1030).
The frozen R1 executable produces this substitution. It predates the attempted
R2a optimization.

The replacement is visibly smaller and lighter than the source/current glyph.
Its emitted outline bounding box is 257 × 191 font units, versus 286 × 209,
with **the same CID and text matrix**: 10.14% narrower and 8.61% shorter.
Both PDFium and Poppler show the change in complete page context.

| Isolated owned-source measurement | Default | Sharing |
|---|---:|---:|
| Analytic source error | 0.01893446 | 0.13930203 |
| Analytic IoU | 0.88978914 | 0.72066247 |
| Analytic area bias | +0.01948251 | −0.11797008 |
| PDFium source error | 0.13591622 | 0.20506410 |
| Poppler source error | 0.13376555 | 0.19432418 |

The direct-outline/analytic default error floor is **0.00242792**. Complete-page
analytic error also rises, 0.02863570 → 0.15188501. Complete-page PDFium error
rises 0.02146588 → 0.15046007. Poppler has a much larger phase floor, retained
explicitly in `case.json`; the stop does not rely on a Poppler error threshold.

`mixed-member518-context.png` shows source/current/sharing in both renderers;
`mixed-canonical838-context.png` shows the donor in the original scan.
`mixed-worst-delta.png` shows the ten largest isolated analytic increases among
accepted mixed-document draws. The views are diagnostics, not blinded judgments.

`case.json` contains complete hashes, native decision/transform, per-engine
measurements and floors, and the actual CID → GID → component evidence:
CID 556 resolves to default GID 529; the shared resource resolves it to composite
GID 1184, referencing canonical GID 872. The text matrix is unchanged.

The exact native baseline is reproduced with the retained accepted R1 executable:

```sh
SCANWEAVE_PDFIUM_LIBRARY="$PWD/tools/src/pdfium/lib/libpdfium.so" \
OMP_THREAD_LIMIT=1 RAYON_NUM_THREADS=4 \
qualification/font04/local/R1-native/scanweave \
  qualification/pdf_packaging/groups/mixed-input.pdf /tmp/font04-mixed-sharing.pdf \
  --dpi 300 --profile clearscan --glyph-sharing cover-2.0
```

Expected sharing SHA-256:
`6389a7c7662bda1d4012ecbcfe876587cc8fc96e48149ead33f8e9f791306b89`.
Default: `c3f224bf18e5d2aeeba6e03de20000b84ff31893fc945e14882719b114d616d9`.
Pinned PDFium: `b8784cbd652ad2993332b7695e2c80f3a797f877fc47d9be97b66bca9639539e`.

Qualification stopped under the owner's material-defect rule. No threshold,
safeguard, membership policy, or transport repair was changed in response.
