# Independent implementation and measurement review

A separate reviewer inspected the implementation diff, actual PDFs/resources, tests and scalar measurements. It did not modify the converter.

## Findings and corrections

1. Self-halo/max-neighbour erasure could let an unknown mark validate its own removal. Removed: the final fringe model requires an independent donor, registered using owned ink only, with explicit caller/artwork protection.
2. Protected caller regions were initially absent from the paper-sampling guard. Their conservative boxes now participate before erasure and over the entire sampling radius; coloured adjacent and overlapping-box tests pass.
3. Verified donor pixel-centre/halo mapping and registration frame. Thin donors now estimate dark from masked samples and paper from the halo. No actual outline/placement mutation occurs.
4. Native-sample equality did not prove visible faint-rule preservation. Tests exposed erased crossing samples. The final weak-rule ownership preserves all330/1306 added samples in native image resources, including binary-mask intersections.
5. The initial detector could join scattered paper noise into broad strips. Support now needs eight physical pixels with at most four pixels of weak non-ridge gap, with dark source ink allowed to bridge. Horizontal300/600 and vertical/minimum-support tests cover it.
6. Whole-page source-raster versus native-background versus final controls isolate remaining patch sampling. PDFium source-raster error is0, while native-background is4.67/2.18 mean gray-level error; Poppler's corresponding baseline is1.29/.48 and patch result4.12/2.16. Native-background and final mean errors differ by no more than.004. This is contrast attenuation, not rendered pixel identity. Both native source hashes and independent rendered results remain available.
7. Checked the sparse paper-resource exception mapping, dimensions, sampling margins and safe fallback to150 DPI. Bounds apply to150↔75 sample representations, not directly to original-source/final-render error.

## Explicit remaining trade-offs

The reviewer noted that a weak binary-owned glyph sample can also qualify as a coherent rule. The implementation deliberately gives the rule preservation priority: the600 control contains two genuine rule samples incorrectly included in a glyph mask. Excluding every owned sample erased those marks. Thus faint typographic strokes resembling rules may remain native; the synthetic audit proves zero retained dark glyph cores, not zero remaining gray samples in every circumstance.

The controls cover a small synthetic suite and two real pages. They do not guarantee preservation of every isolated unknown mark or correct local paper under arbitrary illumination. The review is implementation/measurement scrutiny, not a blanket visual certification.

## Final evidence check

Independent review confirmed the serialized sizes, byte accounting, renderer-specific measurements, fair same-footprint oracle comparison, rejected contour trial and real-document results. The final report now explicitly distinguishes the native-background/final Poppler lightening samples from the source-raster control. Weak-rule priority over weak glyph-mask samples remains an explicitly documented conservative trade-off.
