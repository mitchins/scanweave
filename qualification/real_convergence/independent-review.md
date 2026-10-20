# Independent implementation and measurement review

Reviewer: existing `/root/independent_review`, independent of implementation.

Findings addressed:

1. Pixel mean/max limits did not establish safe lossy encoding of faint native marks. Removed native JPEG candidate; retained source JPEG only when binding/geometry checks succeed and existing qualified reduced-paper behavior.
2. Encoded-source hints require decoded-pixel and physical-geometry binding, private properties, strict dictionary/operator validation and bounded decoding. Implemented checks and focused rejection tests.
3. Count actual emitted glyph paints, not proposed regions or PDFium text characters. Added independent CID-to-GID stream inventory.
4. The inventory exposed five missing NARA digits from noncontiguous span grouping. Fixed grouping without changing image/font streams. Controlled source/before/fixed renders show restored paint. Poppler raw/layout and PDFium extraction hashes match exactly.
5. Reject the historical local-background recovery because final words became heavy and cleanup produced halos. Removed the candidate rather than crediting its increased observation count.

Final review: no remaining correctness blocker found in the span correction. Confirmed five restored paints (5,1,9,1,3), forms 859,981 B / 500 actual draws, five-collection total 59,599,260 B and 27.291% saving versus input. Real pages do not have pristine typography truth; source-relative measurements must not be called real glyph IoU.

Review is bounded code/evidence review, not general safety certification for unknown scans. Existing PDFium narrow-owner, historical segmentation and inherited regression limitations remain reported.

Final report review confirmed every scorecard total, 21,710,571 B saving versus prior ScanWeave, 5,404 actual draws and 3,489 unique painted GIDs summed per document. No factual blocker remained. Frozen previous forms painted 496 glyphs; the immediate before-grouping candidate painted 495; corrected current forms paint 500.
