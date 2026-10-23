# Independent required-glyph review

Reviewed source: `document.rs` required-entry collection/remapping and
`fontbuild.rs` required-font construction. Reviewed evidence:
`local/financial-verification.json` and `local/verify-product.py`.

The reviewer confirmed visible zero-based and invisible one-based CID remapping,
retention of semantic-owner programs, faithful-path isolation, and validity of
the conservative head design envelope. A mandatory `.notdef` maxp undercount was
identified and fixed; empty/owner-only tests now assert 4 points, 1 contour and
correct glyph counts. Actual OTS also exposed an empty cmap; the required-only
builder now emits U+0000→GID0 without adding PDF Unicode ownership.

Evidence review confirmed 52/52 exact financial renders, unchanged glyph/Unicode
and text-matrix records, graphics operations, image streams and extraction.
Font program counts/bytes match the report. No remaining code or evidence
blocker was found in the measured output.

Final-binary repeat is a separate outstanding qualification step: its PDF hash
must be bound to the recorded executable SHA before claiming deterministic
final-binary reproduction. GitHub CI, Sonar and CodeRabbit results are recorded
in the product PR, not inferred from this independent review.
