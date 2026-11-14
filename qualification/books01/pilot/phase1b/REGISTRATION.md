# Phase 1b registration rule (declared before fitting)

For each page, output, renderer and DPI, fit one output-to-source global
similarity transform from SIFT keypoint correspondences on aspect-preserving
reduced copies. A uniform scale, rotation and translation are permitted;
anisotropic scaling and shearing are not fitted. The source and output pixel
grids and page boxes are recorded independently. No local or elastic warp is
permitted. The reference rendering and native outputs remain unchanged.

A non-identity fit is accepted only with at least 8 spatially distinct
correspondence inliers, at least 60% of descriptor matches inliers, coverage
of at least three quadrants of the page, median inlier residual <= 3 and 95th
percentile <= 6 pixels in the 150-DPI-equivalent source coordinate system,
absolute rotation <= 2 degrees and scale in [0.97, 1.03]. For pixel-identical
images, exact equality is sufficient evidence for the identity transform.
Insufficient matches, ambiguous fits or failed criteria are marked unaccepted;
no aligned fidelity score may silently substitute an unverified fit. Crop and
page-box differences are reported independently, never repaired by estimating
a content-specific crop. Interpolation of existing rendered pixels is used
only for aligned metric copies; the native renders and source files stay intact.
