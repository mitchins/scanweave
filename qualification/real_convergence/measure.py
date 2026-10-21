"""Measure completed PDFs against frozen same-input arms; no real-font oracle."""
import json,hashlib,subprocess,tempfile,sys,importlib.util,re,collections
from pathlib import Path
import pikepdf,numpy as np,pypdfium2 as pdfium
B=Path(__file__).resolve().parent;R=B.parents[1];P=R/'qualification/pdf_packaging';sys.path.insert(0,str(R/'qualification'))
from tools_env import qpdf_bin,qpdf_env,ots_bin
spec=importlib.util.spec_from_file_location('previous_measure',P/'measure_real.py');m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
sha=lambda b:hashlib.sha256(b).hexdigest()
def inspect(path,ids,source,previous):
 report=json.loads(Path(str(path)+'.json').read_text());conversion=report['conversion'];q=pikepdf.open(path);res=m.resources(path);res['overhead_bytes']=res['pdf_bytes']-res['raster_bytes']-res['font_bytes']-res['content_bytes'];record={'pdf':str(path.relative_to(R)),'ids':ids,'resources':res,'stage_timings':conversion['stage_timings'],'import_ms':report.get('import_ms'),'pages':[],'fonts':[],'native':[]}
 run=path.with_suffix('.run.json');record['run']=json.loads(run.read_text()) if run.exists() else None;record['peak_command_kib']=m.memory(path.with_suffix('.time.txt'))
 v=subprocess.run([qpdf_bin(),'--check',str(path)],env=qpdf_env(),capture_output=True,text=True);record['qpdf']={'status':v.returncode,'log':v.stdout+v.stderr}
 with tempfile.TemporaryDirectory() as temp:
  for o in q.objects:
   if isinstance(o,pikepdf.Dictionary) and '/FontFile2' in o:
    data=o.FontFile2.read_bytes();f=Path(temp)/f'{len(record["fonts"])}.ttf';f.write_bytes(data);r=subprocess.run([ots_bin(),str(f)],capture_output=True,text=True);record['fonts'].append({'sha256':sha(data),'decoded_bytes':len(data),'status':r.returncode,'log':r.stdout+r.stderr})
 seen=set()
 for i,(id,pr,prov) in enumerate(zip(ids,conversion['page_reports'],report['pages'])):
  old=json.loads((P/'real-measurements.json').read_text());old=next(r for r in old if r['id']==id)['arms']['scanweave'];queries=[r['text'] for r in old['queries']]
  a=m.text_stats(path,i,queries);a['id']=id;a['poppler_text']=subprocess.check_output(['pdftotext','-raw','-f',str(i+1),'-l',str(i+1),str(path),'-']).decode(errors='replace');a['renderer_text_equal_ignoring_whitespace']=''.join(a['pdfium_text'].split())==''.join(a['poppler_text'].split());a['funnel']={k:pr[k] for k in ['supplied_chars','components_total','components_owned','components_artwork','visual_units','fallback_reasons','coverage','font_glyphs','raster_ink_pixels_suppressed','antialias_fringe_pixels_suppressed']};a['funnel'].update(ocr_words=prov.get('ocr_words'),observations=len(pr['reconstruction']['observations']),prototypes=len(pr['reconstruction']['prototypes']),accepted_vectors=sum(o['owner'].startswith('visible') for o in pr['occurrences']),decisions=dict(collections.Counter(o['decision'] for o in pr['reconstruction']['occurrences'])),stage_timings_ms=pr.get('stage_timings_ms'),raster_import=prov.get('raster_import','Poppler'),selected_psm=prov.get('selected_psm',3));a['renderers']={}
  for renderer in ['poppler','pdfium']:
   current=np.asarray(m.frame(path,i,renderer)).astype(np.int16);src=np.asarray(m.frame(source,i,renderer)).astype(np.int16);before=np.asarray(m.frame(previous,i,renderer)).astype(np.int16);h=min(current.shape[0],src.shape[0],before.shape[0]);w=min(current.shape[1],src.shape[1],before.shape[1]);d=np.abs(current[:h,:w]-src[:h,:w]);b=np.abs(current[:h,:w]-before[:h,:w]);a['renderers'][renderer]={'size':list(current.shape),'source_mae':float(d.mean()),'source_changed_fraction':float(np.any(d,axis=2).mean()),'previous_mae':float(b.mean()),'previous_changed_fraction':float(np.any(b,axis=2).mean()),'note':'source deviation, not pristine-font truth'}
  record['pages'].append(a)
  for index,patch in enumerate(pr['patches']):
   image=q.pages[i].Resources.XObject.get('/Im'+str(index))
   if image is None or image.objgen in seen:continue
   seen.add(image.objgen);raw=image.read_raw_bytes();background=patch['compact_background'];whole=not background and len(pr['patches'])==1
   item={'page':i,'object':image.objgen,'bytes':len(raw),'sha256':sha(raw),'width':int(image.Width),'height':int(image.Height),'filter':str(image.Filter),'predictor':int(image.get('/DecodeParms',{}).get('/Predictor',1)),'class':'paper' if background else ('native_whole_page' if whole else 'native_exception')}
   samples=np.asarray(pikepdf.PdfImage(image).as_pil_image().convert('RGB'));gray=bool(np.all(samples[:,:,0]==samples[:,:,1]) and np.all(samples[:,:,1]==samples[:,:,2]));item['gray']=gray
   if gray:
    hist=np.bincount(samples[:,:,0].reshape(-1),minlength=256);item['histogram']=hist.tolist();item['strict_bitonal']=bool(set(np.nonzero(hist)[0])=={0,255});item['gray_levels']=int((hist>0).sum())
   record['native'].append(item)
 return record

def main():
 groups=json.loads((P/'groups.json').read_text());all=[]
 for name,g in groups.items():
  path=B/'collections'/f'{name}.pdf';checkpoint=B/'collections'/f'{name}.measure.json'
  if not path.exists():continue
  if checkpoint.exists():rec=json.loads(checkpoint.read_text())
  else:
   rec=inspect(path,g['members'],P/'groups'/f'{name}-input.pdf',P/'groups'/f'{name}-scanweave.pdf');checkpoint.write_text(json.dumps(rec,indent=2));print(name,rec['resources']['pdf_bytes'],flush=True)
  all.append(rec)
 (B/'measurements.json').write_text(json.dumps(all,indent=2))
 known=json.loads((P/'cord-known-numeric-search.json').read_text());new=B/'collections/receipts.pdf'
 if new.exists():
  out=[]
  for i in range(10):
   id=f'cord-{i:02}';base=next(r for r in known if r['id']==id and r['arm']=='scanweave');queries=[q['text'] for q in base['queries']];tp=pdfium.PdfDocument(str(new))[i].get_textpage();text=subprocess.check_output(['pdftotext','-raw','-f',str(i+1),'-l',str(i+1),str(new),'-']).decode();out.append({'id':id,'queries':[{'text':q,'pdfium':tp.search(q).get_next() is not None,'poppler':q in text} for q in queries]})
  (B/'cord-numeric-search.json').write_text(json.dumps(out,indent=2))
if __name__=='__main__':main()
