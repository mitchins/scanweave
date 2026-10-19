"""Fair same-membership document accounting and page-level verification."""
import importlib.util,json,sys,tempfile,subprocess,time,hashlib
from pathlib import Path
import pikepdf,numpy as np
B=Path(__file__).resolve().parent;R=B.parents[1];sys.path.insert(0,str(R/'qualification'));from tools_env import qpdf_bin,qpdf_env,ots_bin
spec=importlib.util.spec_from_file_location('measure',B/'measure_real.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
groups=json.loads((B/'groups.json').read_text());real={r['id']:r for r in json.loads((B/'real-measurements.json').read_text())};results=[]
for name,group in groups.items():
 for arm in ['input','adobe','scanweave','ocrmypdf1','ocrmypdf3','archive']:
  path=B/'groups'/f'{name}-{arm}.pdf';run=B/'groups'/f'{name}-{arm}.run.json'
  if not path.exists():
   results.append({'group':name,'arm':arm,'missing':True,'run':json.loads(run.read_text()) if run.exists() else None});continue
  checkpoint=B/'groups'/f'{name}-{arm}.measure.json'
  if checkpoint.exists():results.append(json.loads(checkpoint.read_text()));continue
  result={'group':name,'arm':arm,'members':group['members'],'resources':m.resources(path),'peak_kib':m.memory(B/'groups'/f'{name}-{arm}.time.txt'),'run':json.loads(run.read_text()) if run.exists() else None,'pages':[]}
  q=pikepdf.open(path);assert len(q.pages)==len(group['members']);fonts=[]
  with tempfile.TemporaryDirectory() as tmp:
   for obj in q.objects:
    if isinstance(obj,pikepdf.Dictionary) and '/FontFile2' in obj:
     f=Path(tmp)/f'{len(fonts)}.ttf';f.write_bytes(obj.FontFile2.read_bytes());v=subprocess.run([ots_bin(),str(f)],capture_output=True,text=True);fonts.append({'status':v.returncode,'decoded_bytes':f.stat().st_size,'log':v.stdout+v.stderr})
  result['font_validation']=fonts
  c=subprocess.run([qpdf_bin(),'--check',str(path)],env=qpdf_env(),capture_output=True,text=True);result['qpdf']={'status':c.returncode,'log':c.stdout+c.stderr}
  report=Path(str(path)+'.json')
  if arm=='scanweave' and report.exists():
   j=json.loads(report.read_text())['conversion'];result['conversion']={k:j[k] for k in ['coverage','stage_timings','image_xobjects','image_references','content_bytes','font_bytes']};result['vector_occurrences']=sum(o['owner'].startswith('visible') for p in j['page_reports'] for o in p['occurrences']);result['observations']=sum(len(p['reconstruction']['observations']) for p in j['page_reports'])
  for index,id in enumerate(group['members']):
   queries=[i['text'] for i in real[id]['arms']['scanweave']['queries']];page=m.text_stats(path,index,queries);page['id']=id;page['poppler_text']=subprocess.check_output(['pdftotext','-f',str(index+1),'-l',str(index+1),'-raw',str(path),'-']).decode(errors='replace');page['renderer_text_equal_ignoring_whitespace']=''.join(page['poppler_text'].split())==''.join(page['pdfium_text'].split());page['renderers']={}
   for ren in ['poppler','pdfium']:
    im=m.frame(path,index,ren);source=m.frame(B/'groups'/f'{name}-input.pdf',index,ren);a=np.asarray(im).astype(np.int16);b=np.asarray(source).astype(np.int16);h=min(a.shape[0],b.shape[0]);w=min(a.shape[1],b.shape[1]);d=np.abs(a[:h,:w]-b[:h,:w]);page['renderers'][ren]={'size':list(im.size),'source_size':list(source.size),'source_relative_mae':float(d.mean()),'changed_fraction':float(np.any(d!=0,axis=2).mean())}
   result['pages'].append(page)
  checkpoint.write_text(json.dumps(result,indent=2));results.append(result);print(name,arm,result['resources']['pdf_bytes'],flush=True)
(B/'group-measurements.json').write_text(json.dumps(results,indent=2))
