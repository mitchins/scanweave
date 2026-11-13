# Registration acceptance rule

Declared before inspecting registration results. A JP2 is accepted only if the
access-image-to-original mapping can be established independently using at
least eight spatially separated image patches, with at least 80% inliers and
an inlier residual at most 2 original-frame pixels (95th percentile). The only
allowed mapping is independent positive x/y scales and translations, with an
optional exact quarter-turn of the original pixels. In addition, the fraction
of thresholded ink inside projected GT TextLine polygons must be no more than
0.02 below the corresponding access-image fraction. Ambiguous or insufficient
matches, absent text, inconsistent geometry, or failure of either check cause
fallback to WebP. All transforms act on GT coordinates; original samples are
never resampled, cropped, or deskewed for source PDF construction.
