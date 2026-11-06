# ACR-06 CP2: CamScanner datapoint and default donor-geometry defect

Inputs: the decoded source pixels in `local/winvm/share/in/src/` (lossless; hashes in its `manifest.json`). CamScanner outputs were produced by the owner on the CamScanner web app (default "Magic Pro", 2026-11-06) from those PNGs. ScanWeave outputs come from `font04/local/PR4/scanweave` (tree identical to `main` 79b30e5), run with `--profile clearscan`. Adobe XI outputs are the frozen `pdf_packaging/groups/*-adobe.pdf` and `clearscan_competitive/300/adobe.pdf`. Output hashes are in `SHA256SUMS`.

Run from `qualification/`:

    .venv/bin/python -I acr06/cp2/align_render.py . acr06/local/cp2/aligned      # renders + ORB/RANSAC registration -> pages.json
    .venv/bin/python -I acr06/cp2/align_synthetic.py . acr06/local/cp2/aligned   # synthetic pages: scale-searched template match + assignment
    .venv/bin/python -I acr06/cp2/page_attribution.py <pdf> [page]               # per-page byte attribution
    .venv/bin/python -I acr06/cp2/donor_mismatch.py . acr06/local/cp2/donor 6    # donor size-mismatch census + sample sheet
    .venv/bin/python -I acr06/cp2/detail.py <aligned> <page> x0 y0 x1 y1 out.png [zoom]

**CamScanner web output:** FPDF 1.7. Every page is forced to A4 and holds one 8-bit DCT JPEG (RGB, or gray for the synthetic pages) at about 215 DPI-equivalent, after automatic crop and resampling (0.91–1.65×). There are no fonts and no text layer. The synthetic pages came back in reverse order.

**Default ClearScan defect:** `repaired_from_document_donors` and `canonical_reuse_of_document_outline` accept donors whose replacement box differs greatly from the observed glyph. This produces visible wrong characters (see `donor-mismatch.json`). Measurement only; there is no product change here.
