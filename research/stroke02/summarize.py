"""Keep small, non-text result summaries; generated data remains local."""
import json,pathlib
B=pathlib.Path('/data/coding/scanweave/work/books01');O=B/'stroke02'
def load(name):return json.loads((O/name).read_text())
crops=load('crop-results.json');subset=['inverse12','local12','local_observed_low','inverse_layers']
summary={'diagnostics':load('diagnostics.json'),'psf':load('psf-fits.json'),'ambiguity':load('ambiguity.json'),'ink_mass':load('ink-mass.json'),'actual_pdf_digit_metrics':load('actual-pdf-digit-metrics.json'),'synthetic_physics':load('synthetic-physics.json'),'candidate_crops':{k:{n:crops[k][n] for n in subset} for k in crops}}
pathlib.Path(__file__).with_name('results.json').write_text(json.dumps(summary,indent=2)+'\n')
