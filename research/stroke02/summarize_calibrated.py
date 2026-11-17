"""Commit numeric results without publishing input text, images or PDFs."""
import json,pathlib
p=pathlib.Path('/data/coding/scanweave/work/books01/stroke02')
profiles=json.loads((p/'joint-profiles.json').read_text());rend=json.loads((p/'joint-render.json').read_text());fair=json.loads((p/'fair-compare.json').read_text());oracle=json.loads((p/'oracle-calibration.json').read_text());out={'oracle':oracle,'regions':{}}
for key,regions in profiles.items():
 out['regions'][key]=[]
 for i,r in enumerate(regions):
  minima=[{'sigma':s,'rmse':min(x['rmse'] for x in r['grid'] if x['sigma']==s)} for s in [.3,.5,.7,.93,1.22]]
  candidates=[]
  for run in rend['runs'][key]:
   g=next((g for g in run['groups'] if g['idx']==i),None)
   if g is None:continue
   name=g['style']+'-'+format(g['sigma'],'.2f');candidates.append({'style':g['style'],'sigma':g['sigma'],'t':g['t'],'components':g['pdf_components'],'holes':g['pdf_holes'],'join':g['join'],'retained_cross_group_components':g['cross'],'forward':fair[key][i]['results'][name]})
  out['regions'][key].append({'bbox':r['bbox'],'profile_best':r['best'],'profile_rmse_by_sigma':minima,'comparators':{k:v for k,v in fair[key][i]['results'].items() if k in ('sw-E','mrc-M','adobe-E')},'candidates':candidates})
pathlib.Path(__file__).with_name('results-calibrated.json').write_text(json.dumps(out,indent=2)+'\n')
