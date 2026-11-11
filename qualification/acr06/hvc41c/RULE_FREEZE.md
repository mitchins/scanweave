# HVC-41C development-rule freeze

This freeze records the development rule after control calibration and before any historical-p1 recovery pilot. No historical admission or vector experiment has been run. These are development data; held-out qualification would be required. The rule is an offline prototype, not connected to live PDF emission.

For each OCR word (one word is one provisional region), take an exterior ring around its word box: pad by 35% of word height, clamped to 4–18 source pixels. Exclude the word and all other OCR word boxes expanded by one pixel, all artwork component bounding boxes expanded by one pixel, any supplied protected-region bounding boxes expanded by one pixel, and the outer two-pixel page perimeter. Reject if a word intersects an artwork or protected bbox, or if fewer than 32 ring pixels remain. If a protected region is malformed, exclude the entire page. The supplied development PDFs have no explicit protected polygons.

Use median ring luminance as paper. Require paper luminance at least 70 and ring p90−p10 at most 25. In the word box, source pixels at least 30 luminance units below paper form the dark class; require at least six such pixels, 2–75% of the word box, and a contrast between paper median and dark-pixel median of at least 100. The latter was selected **on the development controls** after the photograph control admitted 26 background-artwork words with the initial 45-unit threshold; those admitted photographic objects had contrast up to about 96, while the financial positive sample had a much higher median. This is a conservative calibrated separator, not a general paper or text model; it rejects faded/low-contrast content and needs held-out controls. No p1 data was used in this calibration.

Each word is evaluated independently, including punctuation. Unsupported words remain raster; a failing word does not reject its neighbours. Existing ownership artwork bboxes are used as a conservative exclude mask. OCR labels are hypotheses, not proof of text identity.

For the independent font check, render the actual existing PDFium text object in isolation from the completed PDF at source page geometry; derive paper from the exterior word ring and source dark ink from the character box padded by three pixels. Exclude samples whose padded box overlaps other characters of the word. Compare source pixels below the halfway paper/ink level with rendered-font pixels below the halfway white/fill level. Keep IoU >= 0.90 and fill luminance error <= 15 unchanged. In the final validation no spatial shift is allowed. Post-hoc shifts are diagnostic only, never acceptance. This method has already failed visually recognizable clean-control glyphs; stop before p1 as required.

SHA-256:
- `calibrate.py`: `8fb8d8fc9845d90eafdb8631be0b2b2d8b7317c58f097f8aa596cb03dc91b4b5`
- `validate_controls.py`: `bfa619d82a48ce1bcb9dde44c9439e56168a5f5ec54cc87792e9302a5a924b9d`
- `calibration-words.json`: `1a2d763dd65cfacbfa24853f1d18abac625b42d40155fbdc09b5b019d0fc4410`
