import json,sys,subprocess,time,os
from pathlib import Path
from lxml import etree
B=Path(__file__).resolve().parent;R=B.parents[1];V=Path(sys.executable).parent;D=B/'groups';groups=json.loads((B/'groups.json').read_text())
for name,group in groups.items():
 rec=D/f'{name}-archive.run.json'
 if rec.exists() and json.loads(rec.read_text()).get('status')==0:continue
 root=etree.Element('html');body=etree.SubElement(root,'body')
 for id in group['members']:
  doc=etree.parse(str(B/'real/archive'/(id+'.hocr')))
  for page in doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocr_page ")]'):body.append(page)
 hocr=D/(name+'.hocr');hocr.write_bytes(etree.tostring(root));out=D/f'{name}-archive.pdf';cmd=list(map(str,[V/'recode_pdf','-P',R/group['input'],'-T',hocr,'-o',out,'--mask-compression','ccitt','--threads','1']));start=time.monotonic()
 with (D/f'{name}-archive.log').open('w') as f:status=subprocess.run(['/usr/bin/time','-v','-o',str(D/f'{name}-archive.time.txt')]+cmd,stdout=f,stderr=subprocess.STDOUT,env=dict(os.environ,OMP_THREAD_LIMIT='1',PATH=str(V)+':'+os.environ['PATH']),timeout=240).returncode
 rec.write_text(json.dumps({'group':name,'arm':'archive','command':cmd,'status':status,'seconds':time.monotonic()-start,'timing_scope':'recode only; uses separately recorded Tesseract preparation','pdf_bytes':out.stat().st_size if out.exists() else None},indent=2));print(name,status,flush=True)
