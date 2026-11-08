import os,sys,subprocess,time,hashlib
from pathlib import Path
q=Path('/data/coding/scanweave/qualification'); root=q/'acr06/local/trace32'; scripts=q/'acr06/trace32'; out=root/'runs';out.mkdir(exist_ok=True)
jobs=[('single',q/'pdf_packaging/real/input/scan-c03-29.pdf',300,'off',3),('competitive600',q/'clearscan_competitive/600/source.pdf',600,'off',3),('mixed',q/'pdf_packaging/groups/mixed-input.pdf',300,'off',3),('historical',q/'pdf_packaging/groups/historical-input.pdf',300,'off',3),('competitive300',q/'clearscan_competitive/300/source.pdf',300,'off',1)]
jobs += [(g,q/f'pdf_packaging/groups/{g}-input.pdf',300,'off',1) for g in ('financial','forms','receipts')]
jobs += [('competitive600-q3',q/'clearscan_competitive/600/source.pdf',600,'cover-2.0-ceiling-q3',1),('single-q3',q/'pdf_packaging/real/input/scan-c03-29.pdf',300,'cover-2.0-ceiling-q3',1)]
if len(sys.argv)>1 and sys.argv[1]=='q3only': jobs=[job for job in jobs if job[0].endswith('-q3')]
env=dict(os.environ,SCANWEAVE_PDFIUM_LIBRARY='/data/coding/scanweave/tools/src/pdfium/lib/libpdfium.so',LD_LIBRARY_PATH='/data/coding/scanweave/tools/dist/lib',OMP_THREAD_LIMIT='1',RAYON_NUM_THREADS='4',SCANWEAVE_RESEARCH_PYTHON='/nonexistent-font04-python')
for name,src,dpi,mode,reps in jobs:
 for rep in range(1,reps+1):
  for arm in (('main','candidate') if rep%2 else ('candidate','main')):
   dst=out/f'{name}-{arm}-{rep}.pdf'; log=dst.with_suffix('.log');cmd=['/usr/bin/time','-v',str(root/(arm+'.bin')),str(src),str(dst),'--dpi',str(dpi),'--profile','clearscan','--glyph-sharing',mode]
   print('START',name,arm,rep,flush=True); start=time.monotonic()
   with log.open('w') as f:p=subprocess.run(cmd,stdout=f,stderr=subprocess.STDOUT,env=env)
   print('DONE',name,arm,rep,p.returncode,round(time.monotonic()-start,2),flush=True)
   if p.returncode:sys.exit(p.returncode)
  if rep==1:
   a=out/f'{name}-main-1.pdf';b=out/f'{name}-candidate-1.pdf'
   same=hashlib.sha256(a.read_bytes()).digest()==hashlib.sha256(b.read_bytes()).digest();print('IDENTITY',name,same,flush=True)
   if not same:
    for engine,py in [('poppler',q/'.venv/bin/python'),('pdfium',q/'.venv/bin/python'),('mupdf',q/'acr06/local/mupdf-venv/bin/python')]:
     print('AUDIT',name,engine,flush=True)
     with (out/f'{name}-{engine}.log').open('w') as f:p=subprocess.run([str(py),'-I',str(scripts/'audit_render.py'),engine,str(a),str(b)],stdout=f,stderr=subprocess.STDOUT,env=env)
     if p.returncode: print('RENDER FAIL',name,engine,p.returncode,flush=True);sys.exit(10)
print('ALL COMPLETE',flush=True)
