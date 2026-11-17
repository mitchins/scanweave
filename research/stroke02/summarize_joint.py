"""Publish numeric diagnostics only; crop images and PDFs remain local."""
import json
from pathlib import Path
P = Path('/data/coding/scanweave/work/books01/stroke02')
profiles = json.loads((P/'joint-profiles.json').read_text())
render = json.loads((P/'joint-render.json').read_text())
counter = json.loads((P/'counter-test.json').read_text())
out = {'profiles': {}, 'counter': {k: counter[k] for k in ('region_bbox', 'hole_pixels', 'local_noise_linear_mad', 't_max_physical', 'rule', 'decision', 'delta_range')}, 'render': {}}
for page, regions in profiles.items():
    out['profiles'][page] = [{**{k: r[k] for k in ('bbox','noise_linear_mad','core_direction_linear','core_pixels','paper_linear','t_max_physical','profiles','free_amplitude','best')}, 'grid_count': len(r['grid']), 'within_noise_count': len(r['within_noise'])} for r in regions]
for page, runs in render['runs'].items():
    fields = ('idx','bbox','style','sigma','t','noise','pdf_rescan_luma_rmse','within_noise','pdf_components','pdf_holes','join','cross','pdf_mass_px','width_mad','ink_srgb')
    out['render'][page] = {'decisions': render['decisions'][page], 'candidates': [{k:g[k] for k in fields} for run in runs for g in run['groups']]}
out['noise_note'] = render['noise_note']
out['policy'] = render['policy']
Path(__file__).with_name('results-joint.json').write_text(json.dumps(out, indent=2)+'\n')
