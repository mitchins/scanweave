# M1-C Experimental Protocol (frozen before running)

Frozen Git HEAD: c77ab290c58d2ff5f7ccb94ff8b6caa5d938d9f3
Frozen at: see FROZEN_HEAD.txt
Sealed corpus: untouched.
Random seed (all draws): 20261015.
Evaluation split: character-plus-degradation space, no held-out external font; holdout reserved.

Families (development): DejaVuSans-Bold, DejaVuSerif-Bold, URWGothic-Demi, P052-Roman, NimbusMonoPS-Regular, IPAGothic.
Glyphs: {'6','8','0','O','o','l','1','a','g','e','i'} plus kana {'ガ','パ','が'} (negative controls include cross-family 6/8/0/O and rn vs m).
Target sizes (rendering reference): 7, 8, 9, 10pt at single reference? Observations rendered at 200/300/600 DPI with degradation; all comparisons measured at REF_DPI=600 px grid.
Observation counts: N = 1,2,4,8,16,32.
Arms: A single-observation, B visual-clustering observed medoid, C robust multi-observation, D oracle (evaluator only).
Success thresholds: C vs B >=15% median reduction in boundary error on target degraded small-text subset; bootstrap 95% CI excludes zero; zero false merges on safety set; OCR-label mutations zero visual change.
Negative controls: known glyphs intentionally excluded from fusion clusters; false-merge counts expected zero.
