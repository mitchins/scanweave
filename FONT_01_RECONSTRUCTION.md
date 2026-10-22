# FONT-01 — canonical recovery and real typography

## Decision

No canonical group or learned font model is promoted. A source-only medoid can
repair a damaged observation, but these experiments also replace healthy marks
with unsupported geometry. Fewer groups and lower average raster error are not
sufficient product evidence.

## Recovery experiment

For each target, exclude it from donor selection. Within a proposed same-character
group, compare: highest-contrast/lowest-component source witness, registered medoid,
and pointwise median of source witnesses aligned to that medoid. Pristine shapes
enter only **after** candidates are fixed. The oracle-cohort control supplies true
face-character membership, not pristine donor selection; it is not a mathematically
optimal reconstruction ceiling. The inferred arm uses frozen complete-link groups.
At least two other observations are required.

All scores below are binary shape-only IoU after bounded diagnostic registration
in normalized48×48 frames. They are **not final-PDF or placement fidelity**.
Actual page crops can contain neighboring ink; clean isolated authoring oracles do
not. Independent normalization can change the apparent target frame after damage.
Consequently these figures diagnose selection/contamination, not guaranteed glyph
accuracy. Direct PDF claims would require source-owned targets and unchanged
physical placement, which this failed candidate does not establish.

Unseen true-cohort control, paired target populations:

| Damage | Targets | Source | Quality witness | Medoid | Median |
|---|---:|---:|---:|---:|---:|
| D0 | 504 | .7656 | .7505 | .6988 | .7442 |
| D1 | 352 | .7534 | .7757 | .7454 | .7762 |
| D2 | 325 | .6918 | .7738 | .7344 | .7712 |
| D3 | 325 | .6313 | .7753 | .7351 | .7719 |
| D4 | 294 | .5583 | .7797 | .7431 | .7817 |

Known cohorts contain useful repair evidence, especially under D3/D4. But D0
medoids regress285/504 targets and improve219; D1 regresses183/352. A canonical
median is not uniformly better than choosing a strong donor. Do not compare the
control's averages against the inferred arm's different target population.

For inferred groups, only450/1,800 targets have two other donors (183D0,138D1,
84D2,39D3,6D4). On its paired D0 population, source.8666 falls to medoid.7929
and median.8088; D1 source.8668 falls to.8122/.8263. The six D4 cases improve
on average but cannot qualify broad damaged-glyph recovery. All remaining targets
explicitly lack enough group evidence for this control; no donor is fabricated.

Blinded source/reference/X/Y sheets were inspected independently before revealing
candidate identities. One numeral1's base was credibly recovered by the medoid
(.7825→.9565); consensus was slightly worse(.9424). Correctly grouped healthy comma
and exclamation examples regressed severely, exposing crop/registration/neighbor
contamination independently of face classification. A contaminated T group
regressed. Full-stop donors plausibly restore missing dots, but a median introduces
gray structured ghosts despite favorable thresholded IoU. Initial blinded
interpretation of those fragments was corrected after the punctuation labels were
revealed. None demonstrates a superior general fusion method.

## Real document evidence

Accepted financial PDF SHA256:
`32b7c13e664b32fadeea41b99d9299479f129bfac3bd20debbbf481a6f885e51`.
Its embedded TrueType program has3,264 slots,1,904,648 decoded bytes and1,065,434
encoded bytes, with3,717 visible glyph draws. Town Officers (printed5, PDFpage1)
has42 visible e occurrences using19 GIDs, confirming the starting observation.
There are3,143 distinct nonempty raw glyf programs; exact byte duplication alone
cannot explain the slot count or establish compatible faces. Real fonts are not
known, so no face-accuracy ground truth is invented.

Fixed physical-coordinate source/Adobe/ACR-05 sheets in both Poppler and PDFium
show:

- Repeated expires is readable but remains inconsistent and partly fragmented.
  Adobe also preserves a damaged final shape; it is not an absolute oracle.
- Printed105 (PDFpage11) retains the broken opening of constant in all three
  images. Native OCR is `ronstant`/a prefixed quote variant. Expected wording is
  not permission to insert c or rewrite Unicode. No recovery is claimed.
- A mixed illustration/body page retains inherited weight irregularity and an
  overlap-like defect around took. Adobe is heavier than source in places, and
  its smoothness is not proof of typographical truth.

No unqualified candidate changes those real pages. Existing fonts, search and
ACR-05 output remain intact. There is no claimed product reduction in19e designs,
no new real-glyph coverage, and no learned semantic correction.

## Separate unused-program control — not promoted

The actual font references2,237 GIDs across visible/invisible text;1,027 programs
are unused (593,262 raw glyf bytes). Add.notdef for the subsetting control.
A retain-GIDs fontTools shadow keeps referenced coordinates, contour flags,
endpoints and hmtx unchanged, without inferring any face or Unicode merge:

| Arm | Complete PDF bytes |
|---|---:|
| Native ACR-05 | 3,187,571 |
| Save-only serialization control | 3,187,113 |
| Used-GID shadow | 2,859,982 |

The measured font-related saving is327,131 bytes against the save-only control,
not327,589 attributed entirely to subsetting. Decoded font falls to1,310,292 bytes.
Both derivative PDFs pass qpdf; native text matches in both engines.

**This control does not qualify.** PDFium pixels match all13 pages at150DPI, but
Poppler differs on pages7/8/9:274/91/101 pixels, maximum channel differences
120/38/38. The first internal summary incorrectly claimed all-engine equality;
independent review caught it and the user was corrected before any promotion.
Subsetting changes global head/hhea/maxp/OS2 values and unused hmtx as well as glyf.
A one-variable follow-up restores head.flags9→11; the same three Poppler pages
still differ, refuting that flag as the sufficient cause. Exact remaining cause
is unresolved; unchanged used outlines alone do not prove renderer equivalence.
No font-packing code is integrated. This is a bounded next resource investigation,
separate from cohort learning, not a claimed repair or font-design deduplication.

## Evidence and reproduction

Large PDFs, complete pair/cluster ledgers, normalized overlays, fonts, weights and
renderings remain under ignored `qualification/font01/local/`. Compact metrics
and hashes are in `qualification/font01/results.json`; small representative sheets
are under `qualification/font01/examples/`. Source-only scripts and evaluator
functions are versioned. The recovery API explicitly labels its oracle-cohort
control and diagnostic IoU. See the research README for exact invocations.

No Rust inference is added: no arm passed the frozen gates, so there is no honest
Python/Rust model-parity or improved-product-PDF claim. The useful result is a
reproducible test that reveals unsafe grouping and witness selection before those
decisions contaminate the existing converter.
