# Handoff integrity checks

These checks apply only to the specification packet, not to an implemented reconstruction engine.

Two JSON Schema documents pass Draft 2020-12 schema validation. The illustrative OCR page passes its schema. Six deliberately invalid structural variants were rejected (unknown property, malformed hash, zero physical width, undersized polygon, duplicate reading-order reference and unsupported direction). The example's UTF-8 ranges and affine page dimensions were also checked.

The TOML configuration parses, its offline/no-JBIG2/no-incremental/default-policy values were checked, Markdown code fences balance, and all 18 source-reference IDs resolve in SOURCES.md. No document images, PDFs, model weights or font files are included.

No OCR run, glyph reconstruction, PDF rendering, corpus benchmark or production qualification was executed. Those are M0-M5 deliverables, not results of this handoff.
