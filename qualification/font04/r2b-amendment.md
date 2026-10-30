# FONT-04 R2b P2 preregistration amendment v1.1

The owner approved the layout-only amendment dated 2026-10-31. Code inspection before opening found that the 96-line DPI schedules extended beyond the 9-inch sheet and were clipped; no P2 data exists. The original preregistration remains unchanged. Version 1.1 divides each original schedule, in order, into three sheets of 32 lines, preserving all draws, global identities, sizes, damage, transforms, and evaluation rules. Final scan rectangles must fit the physical sheet.

The generator uses the same observation code for generation and geometry-only mode. FONT-01 reproduced the frozen manifest and every reference file byte-for-byte; its geometry-only boxes matched all frozen public observation boxes by ID (the oracle labels do not themselves contain boxes). See `r2b-generator-identity.json`. The single P2 geometry-only run is recorded in `r2b-p2-geometry.json`: 6,768 expected and actual observations, 32 lines per sheet, and zero out-of-bounds boxes. It wrote geometry metadata only. P2 remains CLOSED for independent review.

Geometry commands require the same binary and other P2 preconditions as generation, but do not create the lock:

```
qualification/.venv/bin/python -m qualification.font04.r2b_generator --split p2 --binary target/release/scanweave --geometry-only qualification/font04/r2b-p2-geometry.json
```
