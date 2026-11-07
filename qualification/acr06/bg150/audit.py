#!/usr/bin/env python3
"""Cross-check final report inputs and record completion independently."""
import hashlib,json
from pathlib import Path
import pikepdf
q=Path('/data/coding/scanweave/qualification'); e=q/'acr06/bg150'; root=q/'acr06/local/bg150'
groups=['financial','forms','historical','mixed','receipts']; names=groups+['single','competitive300','competitive600','fresh1','fresh2','freshtruth1','freshtruth2']
load=lambda p:json.loads(p.read_text())
def statuses(path):
 return dict(line.split() for line in path.read_text().splitlines() if len(line.split())==2)
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
qpdf=statuses(root/'qualification/qpdf-status.txt'); det=statuses(root/'determinism.txt'); release={}
for line in (root/'release-verify/status.txt').read_text().splitlines():
 op,name,code=line.split();release.setdefault(name,{})[op]=code
source=load(e/'source-renders.json'); thin=load(e/'thin-rules.json'); byte=load(e/'bytes.json'); result={'documents':{},'failures':[]}
for name in names:
 pdf=root/'candidate'/f'{name}.pdf'; base=root/'baseline'/f'{name}.pdf'; repeated=root/'repeat'/f'{name}.pdf'; final=root/'release-verify'/f'{name}.pdf'
 with pikepdf.open(pdf) as doc: count=len(doc.pages)
 quality=load(e/f'quality-{name}.json')['pages']; preservation=load(e/f'preservation-{name}.json')['pages']; panels=load(root/'panels'/f'{name}-index.json')
 row={'pages':count,'quality_pages':len(quality),'preservation_pages':len(preservation),'source_render_pages':len(source.get(name,[])),'thin_rule_pages':len(thin.get(name,[])),
      'default_sha256':sha(base),'candidate_sha256':sha(pdf),'repeat_sha256':sha(repeated),'release_sha256':sha(final),
      'identical_all':sha(base)==sha(pdf)==sha(repeated)==sha(final),'qpdf':qpdf.get(name),'determinism':det.get(name),'release':release.get(name),
      'font_content_text_equal':all(all(r[k] for k in ('font_streams_equal','content_streams_equal','pdfium_text_equal','poppler_text_equal')) for r in preservation),
      'changed_image_paths':sum(len(r['changed_image_paths']) for r in preservation),'panels':len(panels),'bytes_accounted':name in byte,
      'pdfium_pixels_changed':sum(r['pdfium_render_diff'].get('changed_pixels',-1) for r in preservation),'poppler_pixels_changed':sum(r['poppler_render_diff'].get('changed_pixels',-1) for r in preservation)}
 result['documents'][name]=row
 if not (count==len(quality)==len(preservation)==len(source.get(name,[]))==len(thin.get(name,[])) and row['identical_all'] and row['font_content_text_equal'] and row['changed_image_paths']==0 and row['panels']==0 and row['bytes_accounted'] and row['pdfium_pixels_changed']==0 and row['poppler_pixels_changed']==0 and qpdf.get(name)=='0' and det.get(name)=='0' and release.get(name)=={'run':'0','same':'0'}): result['failures'].append(name)
result['python_gates']=load(root/'checks/python-results.json');result['python_gate_failures']=[r['gate'] for r in result['python_gates'] if r['returncode']]
if len(result['python_gates'])!=20 or result['python_gate_failures']:result['failures'].append('python gates')
for filename in ('cargo-test-release.status','clippy-release.status','debug-build-release.status','python-release-driver.status'):
 if (root/'checks'/filename).read_text().strip()!='0':result['failures'].append(filename)
policies=load(e/'default-policies.json')
if not (len(policies)==5 and all(x['equal'] for x in policies.values())):result['failures'].append('default policies')
if any(code!='0' for code in statuses(root/'release-default/identity.txt').values()) or len(statuses(root/'release-default/identity.txt'))!=5:result['failures'].append('default PDF identity')
(e/'audit.json').write_text(json.dumps(result,indent=2)+'\n')
print('failures:',result['failures'])
raise SystemExit(bool(result['failures']))
