# Proposed acceptance rule — owner review required

Do not rank outputs in this pilot. A page would be eligible only if all applicable checks pass:

1. Independent adjudication confirms no wrong-character shape, missing-ink or border-inversion defect on the sampled material; all material suspected candidates must be resolved. Absence of a sampled finding is not proof of absence.
2. At each declared renderer and resolution, text-region SSIM ≥ 0.98 and ink recall ≥ 0.99; paper SSIM ≥ 0.98; illustration SSIM ≥ 0.98 when a region exists. Undefined metrics are not automatic passes. Also review ΔL, ΔE2000, ink precision and sampled colour/halo candidates.
3. Reading-normalized PDFium extraction CER is no more than 0.05 absolute above the selected frozen-hOCR CER, using the known-character denominator and wildcard rules in `methodology.md`. Literal PDFium search hits at least 10 of the 20 sampled eligible GT terms; fewer than 20 terms use the same 50% floor. Adobe is evaluated separately because its OCR language is unmatched.

Justification and limits: the OCRmyPDF visual control’s PDFium source-DPI text SSIM range is 1.000000–1.000000, and ink recall range is 1.000000–1.000000 over these six pages. The proposed floors allow small deviations from that control; they are not established perceptual pass limits. Search and CER tolerances are initial engineering proposals, not statistical guarantees. The six-page pilot and non-adjudicated detector output are insufficient to validate these limits. Owner review and blinded human findings are required before freezing them.
