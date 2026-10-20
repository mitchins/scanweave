# ClearScan targeted publication review

Review base: PR1 `0e82e6416a66e94839f52d0a922b02900180d44e`. Remote fetch confirmed PR2 `ecb149f`, PR3 `31efedb`; all three original heads have green GitHub Rust/Clippy/Python/publication checks. This review examines current runtime source, not the historical artifact diff. The catch-up CodeRabbit size skip is not approval.

## Disposition

- **PR1:** ready for operator merge approval after the two small import corrections below pass the updated CI. No other blocking correctness defect found in the targeted review. Do not merge automatically.
- **PR2 / PR3:** recommend closing unmerged, retaining their published branches, PR discussions, reports, hash manifests and rejected patches. They record useful negative results but add no accepted runtime improvement. Do not delete the evidence branches. Closure itself awaits operator direction.
- New whole-page raster work belongs on a separate branch/PR from this reviewed product; no shaded-paper or fringe candidate is promoted.

## Scope and findings

1. **Input validation / pixel binding / geometry:** the narrow image importer validates image properties, native dimensions and a physical transform, then binds source RGB hashes to conversion input. Unsupported transforms, crops, rotations and resource properties use Poppler. Two confirmed gaps were corrected:
   - A valid `/DefaultRGB` resource could override device-colour interpretation while direct import bypassed Poppler; the later hash checked the same direct-decoded RGB and could not detect that mismatch. Added explicit page-resource veto for `/DefaultRGB` and `/DefaultGray` (including resolved page resources), with valid calibrated-colour fixtures. The RGB regression fails before correction.
   - All source hints could be decoded before the ordinary import's aggregate budget check. Added separate 512 MiB aggregate attempted RGB decode and retained encoded-stream caps, checked before stream copying/decoding. Malformed attempted decodes also consume budget. Exhaustion disables hints; ordinary bounded Poppler import remains available. Focused tests verify cumulative exhaustion and pre-allocation refusal. These are separate caps, not a strict 512 MiB process RSS guarantee; the loaded PDF, retained inputs and decoder temporaries consume additional memory.
2. **Ownership / cleanup:** accepted emitted vector ownership drives removal; protected/unclassified content remains raster. Source-exact coalescing uses the cleaned source. The two rejected local-paper/fringe trials are not in runtime code. Native raster fallback and the independent faithful contract remain in place. No newly demonstrated cleanup-boundary blocker found.
3. **Canonical font / donor repair:** reviewed cohort qualification, medoid/member fallback, immutable selected-witness provenance, original .78 donor / .98 source-preservation policies and alternate-style separation. Original damaged-e and auto-selected-candidate regressions run unfiltered. No threshold reduction or fabricated repair.
4. **Unicode / placement / ActualText:** retained independent occurrence ownership, visible/glyphless owners, per-span ActualText and collection of noncontiguous span runs. Existing extraction/native-search regressions cover partial reconstruction and narrow owners. No removal of ActualText or semantic rewrite.
5. **Serialization / CLI:** reviewed deterministic stream/object serialization of writer-owned output, resource identity/collision checks, ordinary PDF import failures and staged output/report publication. Unsupported source resources are not transplanted. Two publication renames are not transactional; a second-rename failure is explicitly reported. No general rewrite performed.

## Checks and independent review

Focused source-image tests, unfiltered workspace Rust tests, Clippy with warnings denied and all nine Python CI contracts are executed for the correction; results are retained in `qualification/tonal_raster/product-*` and the updated GitHub run. No tests or thresholds are skipped/relaxed. Latest CI status must be read at PR1 before operator merge.

The existing independent reviewer examined all five areas, identified the aggregate import bound, reviewed the fixes and found no remaining blocking correctness issue. Its memory-cap caveat is incorporated above. This is a targeted correctness review, not an assertion that the entire historical research corpus or every real-world visual outcome is qualified.

## Remaining visible limitations

Real pages with failed OCR or shaded-paper segmentation may emit no vector text. Ordinary tonal raster preservation remains expensive. Local shaded glyph contours/cleanup failed quality gates and stay rejected. Existing P01–P08 visual failures and renderer-specific fallback sampling remain documented; green CI is not a claim those visual cases pass. Receipt numeric search remains limited (17/49 in the frozen development sample). These measured limitations do not justify shipping rejected reconstruction paths.

**Operator decision requested:** approve merging PR1 after current CI is green, and approve closing PR2/PR3 unmerged while preserving their published evidence branches. No merge or closure is performed by this report.
