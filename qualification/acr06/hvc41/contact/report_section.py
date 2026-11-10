import json,pathlib,statistics
E=pathlib.Path('/data/coding/scanweave/qualification/acr06/hvc41');C=E/'contact';rows=json.loads((C/'decomposition.json').read_text());props=json.loads((C/'new-proposals.json').read_text());baseline={(x['document'],x['page']):x for x in json.loads((E/'trial-funnel.json').read_text())};out=[]
def w(x=''):out.append(x)
def target(x):return x['document']=='historical' or (x['document']=='receipts' and x['page'] in (4,6,7,8,9))
w('## ContactNonText decomposition')
w()
w('**Actual bottleneck: bounding-box contact with page-spanning artwork components.** With the interior estimator on historical pages 3–5, all 2,271 owned units are in regions whose bboxes overlap artwork bboxes. For 2,024 units there is no artwork pixel within four Euclidean pixels of any unit pixel in that region; 247 units are in regions with actual nearby artwork pixels. Suspect flags overlap those categories. On each of the three pages, the largest artwork component has a page-spanning bbox intersecting every text region, while **that component itself has zero unit-pixel contacts** within four pixels. Other components account for the real pixel contacts.')
w()
w('This diagnostic uses the same connected components, ownership, OCR, margins and estimators as the earlier run. The counterfactual replaces bbox intersection with a mask-pixel Euclidean distance of at most `CONTACT_MARGIN_PX = 4`, and retains the existing independent suspect and protected-region tests. It is behind `SCANWEAVE_HVC41_PIXEL_CONTACT` on research commit `4c9a6ca` only. Pages with pre-containment vectors are forced to source-raster containment, including in the corner run. No unverified glyphs are exposed. The focused proximity test passes, including boundary and diagonal distances.')
w()
w('For each text region, [per-page region JSON](contact/) records unit indexes, original planner disposition, bbox contacts with component IDs, pixel counts, bbox fill ratios and pixel-contact booleans, plus suspect unit symbols and boxes. The `suspect` test in `ownership.rs::unit_ink_exceeds_slots` compares the owned component ink bbox to its **original owning OCR slot** bbox expanded by six pixels: any side beyond that is suspect. The recorded slots may subsequently include absorbed slots. Protected regions retain priority. Standalone artwork entries are also included. [decomposition.json](contact/decomposition.json) lists the five largest artwork components per page; [panel index](contact/panel-index.json) hashes 20 source-overlay sheets showing the three largest masks and bboxes for each affected page and estimator.')
w()
w('The cells below are **units / union of source-reference ink pixels**. “BBox only” means at least one artwork bbox intersects, but no artwork pixel is within four pixels; “pixel” means at least one actual nearby artwork pixel; “suspect” is independent and can overlap either. Counts are region-level: an entire multi-unit region is counted if any of its units meets the condition. OCR-local ink is the proxy described above, not ground-truth characters; receipt 7 has no reference. The corner rows compare against the actual current estimator, not a polarity-adjusted estimate.')
w()
w('| Estimator / page | Bbox only: units / ref px | Pixel contact: units / ref px | Suspect: units / ref px |')
w('|---|---:|---:|---:|')
for x in rows:
 if not target(x):continue
 v=x['categories'];cells=[f"{v[k]['units']:,} / {v[k]['reference_ink_pixels_unioned']:,}" for k in ('bbox_only','pixel_contact','suspect')];w(f"| {x['mode']} {x['document']} {x['page']} | {' | '.join(cells)} |")
w()
w('Largest interior artwork components on the three principal pages:')
w()
w('| Page | Component IDs | Bbox (source px) | Artwork pixels | Bbox fill | Units bbox-hit / actually nearby |')
w('|---|---|---|---:|---:|---:|')
for x in rows:
 if x['mode']!='interior' or x['document']!='historical' or x['page'] not in (3,4,5):continue
 a=x['largest_artwork'][0];w(f"| historical {x['page']} | {a['component_ids']} | {a['bbox']} | {a['pixels']:,} | {100*a['bbox_fill_ratio']:.1f}% | {x['top_art_bbox_units']} / {x['top_art_pixel_contact_units']} |")
w()
w('The following funnel is the contained interior-mode counterfactual. `Vector` is the number of regions changed from bbox-contact raster to pixel-contact vector at the initial planning stage. Proposals are actual pre-containment visible occurrences after the other pipeline gates; “new” counts those within newly released regions. Reference overlap is the union of their owned source masks, not rendered outline coverage. The screen is post-hoc: source-mask reference precision ≥0.9, page-fill luminance within 25 of the unit’s reference-ink median, donor source-mask IoU ≥0.98, and prototype trace IoU ≥0.98 when reported. The donor IoU and trace-budget flags are proxies, not a complete independent geometry test; neither this screen nor OCR label verifies the emitted character. Full per-occurrence measurements are in [new-proposals.json](contact/new-proposals.json).')
w()
w('| Interior page | Newly vector regions / units | Pre-containment proposals: bbox → pixel | Newly proposed / proxy ink overlap | Screened / proxy ink overlap |')
w('|---|---:|---:|---:|---:|')
for x in rows:
 if x['mode']!='interior' or not target(x):continue
 v=x['categories'];b=baseline[(x['document'],x['page'])];fmt=lambda z: 'n/a' if z is None else f'{100*z:.1f}%';w(f"| {x['document']} {x['page']} | {x['new_vector_regions']} / {v['new_vector']['units']} | {b['precontainment_occurrences']} → {x['precontainment_occurrences']} | {v['new_proposed']['units']} / {fmt(v['new_proposed']['reference_ink_fraction'])} | {v['screened']['units']} / {fmt(v['screened']['reference_ink_fraction'])} |")
w()
p3=[x for x in props if (x['mode'],x['document'],x['page'])==('interior','historical',3)];deltas=[x['fill_luminance_delta'] for x in p3 if x['fill_luminance_delta'] is not None]
w(f"For historical p3 all {len(p3)} newly proposed units fail the exploratory fill threshold; median absolute fill difference is {statistics.median(deltas):.1f} luminance units. The threshold is not calibrated, and reference boxes can miss or include neighboring content, so this is a warning rather than a character verdict. Pages 4 and 5 have more screen passes, but no traced outline has been independently matched to the source. Consequently neither the 17.5% p4 screened-mask proxy nor any other number proves the ≥10% safe-visible-vector target.")
w()
w('The [40 unit panels](contact/panel-index.json) show source / corner segmentation / interior segmentation / newly proposed unit mask at enlarged scale: 20 worst proxy-agreement cases and 20 seeded-random cases (seed 41037), without using OCR labels as ground truth. A low proxy overlap can reflect a missed or inaccurate OCR box; the panels do not display or validate the traced glyph. The masks retain the source ownership geometry; they are not generated vectors.')
w()
normal=[x for x in rows if x['mode']=='corner' and (x['document'] in ('financial','mixed','forms') or (x['document']=='receipts' and x['page'] in (1,2,3,5,10)))];changed=[x for x in normal if x['new_vector_regions']];w(f"**Normal-page regression exposure:** with the corner estimator unchanged, the proximity rule changes initial region dispositions on {len(changed)} of {len(normal)} normal-polarity pages: {sum(x['new_vector_regions'] for x in changed)} regions containing {sum(x['categories']['new_vector']['units'] for x in changed):,} units. This is planner exposure, not a claim that all units became visible vectors. The full 32-page corner run is recorded in `decomposition.json`; forced containment means its outputs are not an unchanged-visible-output candidate.")
w()
w('| Normal page with changed regions | Regions | Units |')
w('|---|---:|---:|')
for x in changed:w(f"| {x['document']} {x['page']} | {x['new_vector_regions']} | {x['categories']['new_vector']['units']} |")
w()
w('The bbox test is therefore the dominant planning bottleneck on these historical pages, and pixel proximity is a useful **bounded research direction**, not an implementation ready to ship. A single further experiment would first need a source-supported estimator/admission rule that handles the failed reverse-panel and small-receipt controls, confines any planner change so normal pages and shared donors remain unchanged, and independently validates each released outline, fill, counters, placement, extraction and rendering against the source. Until then retain #39 containment; no product experiment or default change is recommended.')
w()
p=E/'REPORT.md';s=p.read_text();start=s.find('## ContactNonText decomposition\n');end=s.find('## Cost, reproducibility, and recommendation\n');assert end>=0
if start>=0:s=s[:start]+s[end:];end=s.find('## Cost, reproducibility, and recommendation\n')
s=s[:end]+'\n'.join(out)+'\n'+s[end:];s=s.replace('**Recommendation: no implementation experiment selected.** Keep #37 containment and preserve these measurements for an independently specified future study. Do not infer that all possible estimators are unsafe.','**Recommendation: no implementation experiment selected yet.** The bounded follow-up and its prerequisites are set out in the ContactNonText decomposition. Keep #37 containment. Do not infer that all possible estimators are unsafe.')
p.write_text(s)
