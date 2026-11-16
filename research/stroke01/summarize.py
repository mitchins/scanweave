"""Write only aggregated scores and page-level, non-text diagnostics."""
import json, pathlib, statistics
B=pathlib.Path('/data/coding/scanweave/work/books01/stroke01')
s=json.loads((B/'synthetic.json').read_text()); real=json.loads((B/'real.json').read_text()); versions=json.loads((B/'versions.json').read_text()); out={'synthetic':{},'real':real,'versions':versions}
for mode in ['clear','faded','broken','no_evidence']:
 rows=[r for r in s if r['mode']==mode]; group={'n':len(rows),'declined':sum(r['declined'] for r in rows),'methods':{}}
 for i,name in enumerate(['baseline','local','energy','geometry']):
  m={'mean_'+k:statistics.mean(r['methods'][name][k] for r in rows) for k in ['boundary_f1','missing_fraction','false_ink_fraction']}
  m['exact_topology_count']=sum(r['methods'][name]['gt_topology']==r['methods'][name]['topology'] for r in rows);m['false_joins_total']=sum(r['methods'][name]['false_joins'] for r in rows);m['mean_rescan_rmse']=statistics.mean(r['fit'][i] for r in rows);group['methods'][name]=m
 out['synthetic'][mode]=group
pathlib.Path(__file__).with_name('results-summary.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
