# Independent evidence and visual review

Reviewer: separate `/root/raster_evidence_review`, read-only review of source,
actual PDF inventories, comparison sheets and final report. No holdout access.

Initial findings corrected:

- XObject-only accounting missed 28 Adobe inline stencils. They are now inventoried
  with dictionary, payload/hash, CTM/state and placement. Their compressed page-stream
  cost is not incorrectly assigned to independent raster streams.
- Graphics/text operator state and mask-parent associations were incomplete;
  records now retain them. State histories are not represented as a full renderer.
- Type3 programs, direct font dictionaries, mask dependency closure, resource
  reuse identity and serialized remainder terminology were corrected/tested.
- Original capture DPI is distinct from nominal matched input 300 DPI. Roles do not
  infer semantic pixel contents from image area.
- Missing frozen source artifacts fail explicitly; mutable historical tool drift
  is recorded separately.

Visual review inspected actual source/Adobe/O3/ScanWeave fixed crops in both
renderer variants for historical pages, receipts, financial text, mixed artwork,
Linn and NARA, full-page snapshots and experiment regions.

Findings:

- O3 visibly posterizes cord-00 photographed background and history-02 shaded
  book edge, losing continuous dark tones/green spine colour. Its history-04 seal
  becomes mottled/darker.
- Adobe retains colour but smooths texture and softens stamp detail. Some small
  history-01 heavy glyph shapes/counters change.
- No obvious amount/decimal disappearance was visible in the inspected cord-05
  crop. This is bounded evidence, not all-number certification.
- Exact Indexed/expanded-RGB experiment images look identical and are pixel-identical
  in both engines. This validates the representation/encoding combination **after quantization** (Indexed/predictor 15 versus RGB/plainFlate), not safe source
  quantization.
- Whole-page 150 Q100 softens source detail and does not justify blanket adoption.

Final arithmetic independently checked: ScanWeave 45,453,391 B, Adobe 4,178,103 B,
O3 15,315,903 B; ScanWeave raster42,894,958 B including 35,763,822 B whole pages.
All five fresh main collection hashes match frozen Q100 outputs.

**No blocking unsupported conclusion found in the final bounded report.** Causal
shares, obsolete-fringe identity and safe attainable savings remain explicitly
unresolved where evidence is insufficient. Conditional future spatial protection
is not approved for product use. No production codec/ownership change is approved
by this review. CI/CodeRabbit results are separately recorded on the research PR.

## Final coordinate-contract review

Self-review identified 35 numerically different CropBox/MediaBox cases (19 Adobe,
16 archive). The former PDFium/Poppler default-box mismatch invalidated those
fixed-coordinate comparisons. The reviewer inspected the correction: a temporary
full-document copy retains the original crop as an explicit clip and renders on
its MediaBox canvas; annotations in unsupported cases fail explicitly. No source
PDF is changed. The cache contract is versioned.

All 384 page and 304 region measurements, layer replay and individual-component
views were rerun. The reviewer reinspected corrected history-02 corner and
history-04 stamp sheets in both engines. Posterization/colour loss in O3 and
softer Adobe texture/stamp detail remain supported. No new blocker was found for
the actual corpus geometry. Earlier invalid comparisons are explicitly superseded
and preserved locally, not silently treated as current evidence.
