# Independent evidence and visual review

Reviewer: separate `/root/raster_evidence_review`, read-only review of source,
actual PDF inventories, comparison sheets and final report. No holdout access.

Initial findings corrected:

- XObject-only accounting missed28Adobe inline stencils. They are now inventoried
  with dictionary, payload/hash, CTM/state and placement. Their compressed page-stream
  cost is not incorrectly assigned to independent raster streams.
- Graphics/text operator state and mask-parent associations were incomplete;
  records now retain them. State histories are not represented as a full renderer.
- Type3 programs, direct font dictionaries, mask dependency closure, resource
  reuse identity and serialized remainder terminology were corrected/tested.
- Original capture DPI is distinct from nominal matched input300DPI. Roles do not
  infer semantic pixel contents from image area.
- Missing frozen source artifacts fail explicitly; mutable historical tool drift
  is recorded separately.

Visual review inspected actual source/Adobe/O3/ScanWeave fixed crops in both
renderer variants for historical pages, receipts, financial text, mixed artwork,
Linn and NARA, full-page snapshots and experiment regions.

Findings:

- O3 visibly posterizes cord00 photographed background and history02 shaded
  book edge, losing continuous dark tones/green spine colour. Its history04 seal
  becomes mottled/darker.
- Adobe retains colour but smooths texture and softens stamp detail. Some small
  history01 heavy glyph shapes/counters change.
- No obvious amount/decimal disappearance was visible in the inspected cord05
  crop. This is bounded evidence, not all-number certification.
- Exact Indexed/expanded-RGB experiment images look identical and are pixel-identical
  in both engines. This validates packing **after quantization**, not safe source
  quantization.
- Whole-page150Q100 softens source detail and does not justify blanket adoption.

Final arithmetic independently checked: ScanWeave45,453,391B, Adobe4,178,103B,
O3 15,315,903B; ScanWeave raster42,894,958B including35,763,822Bwhole pages.
All five fresh main collection hashes match frozen Q100 outputs.

**No blocking unsupported conclusion found in the final bounded report.** Causal
shares, obsolete-fringe identity and safe attainable savings remain explicitly
unresolved where evidence is insufficient. Conditional future spatial protection
is not approved for product use. No production codec/ownership change is approved
by this review. CI/CodeRabbit results are separately recorded on the research PR.
