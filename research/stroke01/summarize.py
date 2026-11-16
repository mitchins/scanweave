"""Write aggregated scores and page-level, non-text diagnostics."""
import json,pathlib,statistics,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import calibration
B=pathlib.Path('/data/coding/scanweave/work/books01/stroke01/corrected')
s=json.loads((B/'synthetic.json').read_text()); real=json.loads((B/'real.json').read_text()); versions=json.loads((B/'versions.json').read_text()); gate=json.loads((B/'gate.json').read_text());shell=json.loads((B/'shell-reference.json').read_text())
out={'synthetic':{},'real':real,'versions':versions,'gate':gate,'shell_reference':shell,'validation':{}}
for split,rows in [('training',[r for r in s if r['font'] in calibration.TRAIN]),('heldout_font',[r for r in s if r['font']==calibration.HELDOUT])]:
 accepted=[r for r in rows if r['calibrated_accept']];good=[r for r in rows if calibration.good(r)];out['validation'][split]={'total':len(rows),'accepted':len(accepted),'accepted_correct':sum(calibration.good(r) for r in accepted),'good_total':len(good),'good_accepted':sum(r['calibrated_accept'] for r in good),'no_evidence_accepted':sum(r['calibrated_accept'] for r in rows if r['mode']=='no_evidence')}
for mode in ['clear','faded','broken','no_evidence','two_inks']:
 rows=[r for r in s if r['mode']==mode]; accepted=[r for r in rows if r['calibrated_accept']];group={'n':len(rows),'accepted':len(accepted),'mean_blob_core_fraction':statistics.mean(r['blob_core_fraction'] for r in rows),'mean_blob_supported_fraction':statistics.mean(r['blob_supported_fraction'] for r in rows),'methods':{}}
 for name in ['baseline','local','energy','geometry']:
  group['methods'][name]={}
  for tag,rs in [('raw',rows),('accepted_only',accepted)]:
   if not rs: group['methods'][name][tag]=None; continue
   m={'mean_'+k:statistics.mean(r['methods'][name][k] for r in rs) for k in ['boundary_f1','missing_fraction','false_ink_fraction']}
   m['exact_topology_count']=sum(r['methods'][name]['gt_topology']==r['methods'][name]['topology'] for r in rs);m['false_joins_total']=sum(r['methods'][name]['false_joins'] for r in rs);group['methods'][name][tag]=m
 out['synthetic'][mode]=group
pathlib.Path(__file__).with_name('results-corrected.json').write_text(json.dumps(out,indent=2,sort_keys=True)+'\n')
