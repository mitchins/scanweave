"""Classify PDFium extraction differences without publishing extracted text."""
import collections, difflib, json, pathlib
import pypdfium2 as pdfium
B=pathlib.Path('/data/coding/scanweave/work/books01'); D=B/'stroke02/pages-refit';Q=pathlib.Path('/tmp/scanweave-books01/qualification/books01')
pages=[x for x in json.loads((Q/'corpus.frozen.json').read_text())['pages'] if x['split']=='dev']
def extract(path):
 d=pdfium.PdfDocument(str(path));return d[0].get_textpage().get_text_range()
out=[]
for p in pages:
 k=p['id'].split('/')[-1]; metrics=json.loads((D/k/'metrics.json').read_text())
 if metrics['status'] != 0: out.append({'id':p['id'],'status':metrics['status']});continue
 run=json.loads((B/'phase2/runs'/k/'runs.json').read_text());a=extract(run['rows']['sw-E']['path']);b=extract(D/k/'candidate.pdf');diff=metrics['text_diff']; ops=[]
 for tag,i,j,u,v in difflib.SequenceMatcher(None,a,b,autojunk=False).get_opcodes():
  if tag=='equal':continue
  left,right=a[i:j],b[u:v]
  ops.append({'kind':tag,'baseline_length':len(left),'candidate_length':len(right),'whitespace_only':not (left.strip() or right.strip()),'baseline_ufffe':left.count('\ufffe'),'candidate_ufffe':right.count('\ufffe')})
 out.append({'id':p['id'],'new_ufffe_in_edits':sum(max(0,x['candidate_ufffe']-x['baseline_ufffe']) for x in ops),'text_diff':diff,'ownership_moves':metrics['ownership_moves'],'changed_region_dispositions':metrics['changed_region_dispositions'],'operations':ops})
pathlib.Path(__file__).with_name('extraction-refit-audit.json').write_text(json.dumps(out,indent=2)+'\n')
print(json.dumps([{'id':x['id'],'diff':x.get('text_diff'),'ownership_moves':x.get('ownership_moves')} for x in out if x.get('text_diff',{}).get('same') is False],indent=2))
