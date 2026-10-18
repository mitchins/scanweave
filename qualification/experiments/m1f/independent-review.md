# Independent M1-F implementation and measurement review

Review was completed by a separate reviewer against the patch and qualification evidence. Findings:

- The image key is collision checked: SHA-256 narrows candidate matches and the complete canonical sample buffer is compared before reusing an object.
- The current key accounts for dimensions, bit depth, color model and encoding settings. The current patch type carries no alpha or soft-mask property; add those properties to the key if the representation later supports them.
- Resource IDs are assigned in first-use order, so identical inputs serialize deterministically.
- The one-page and multi-page paths both need to use the same image encoding options; the implementation forwards the policy to both paths.
- Rendered output comparisons under Poppler and PDFium are required to qualify DeviceGray, beyond inspecting PDF dictionaries.
- 12-page CPU time and memory are material; do not infer runtime improvement from reduced PDF size.
- The unresolved `8` placement/compositing discrepancy remains a hard gate for any irreversible background or source-ink restoration.

The review found no reason to change the reconstruction algorithm for this bounded F1 resource work. The recorded renderer and resource measurements below address the main implementation risks; the reviewer did not treat Adobe output as the quality oracle.
