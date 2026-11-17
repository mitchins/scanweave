"""Publish per-region disposition transitions without OCR text or pixels."""
import json,pathlib,collections
B=pathlib.Path('/data/coding/scanweave/work/books01/stroke02/pages-extensions');Q=pathlib.Path('/tmp/scanweave-books01/qualification/books01/corpus.frozen.json')
out=[]
for p in json.loads(Q.read_text())['pages']:
 if p['split']!='dev':continue
 d=B/p['id'].split('/')[-1];x=json.loads((d/'metrics.json').read_text())
 if x['status']!=0:out.append({'id':p['id'],'status':x['status']});continue
 old={r['id']:r for r in x['baseline']['regions']};new={r['id']:r for r in x['candidate']['regions']};changes=[]
 for i in sorted(old.keys()|new.keys()):
  a,b=old.get(i),new.get(i)
  if a!=b:changes.append({'region_id':i,'baseline':a,'candidate':b})
 out.append({'id':p['id'],'extensions':x.get('extensions'),'region_changes':changes})
pathlib.Path(__file__).with_name('gate-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print('pages with region changes',sum(bool(x.get('region_changes')) for x in out),'total changes',sum(len(x.get('region_changes',[])) for x in out))
