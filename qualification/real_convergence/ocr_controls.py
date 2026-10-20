import json,time,subprocess,hashlib,os,re
from pathlib import Path
from lxml import etree
B=Path(__file__).resolve().parent;R=B.parents[1];P=R/'qualification/pdf_packaging';out=[]
for id in ['cord-00','cord-01','cord-05','cord-06']:
 root=B/id;subprocess.run(['pdftoppm','-singlefile','-r','300','-png',str(P/'real/input'/f'{id}.pdf'),str(root)],check=True)
 truth=json.loads((R/'qualification/clearscan_competitive/real'/f'{id}.truth.json').read_text());queries=list(dict.fromkeys(w['text'] for line in truth['valid_line'] for w in line['words'] if len(w['text'])>=4 and sum(c.isdigit() for c in w['text'])>=3))[:5]
 for psm in [3,6,11]:
  path=B/f'{id}-psm{psm}';cmd=['tesseract',str(root.with_suffix('.png')),str(path),'--dpi','300','--psm',str(psm),'-c','hocr_char_boxes=1','hocr'];start=time.monotonic();subprocess.run(cmd,env=dict(os.environ,OMP_THREAD_LIMIT='1'),check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
  tree=etree.parse(str(path.with_suffix('.hocr')));words=tree.xpath('//*[contains(concat(" ",@class," ")," ocrx_word ")]');texts=[''.join(''.join(c.itertext()) for c in w.xpath('.//*[contains(@class,"ocrx_cinfo")]')) for w in words];text=' '.join(texts)
  chars=tree.xpath('//*[contains(@class,"ocrx_cinfo")]');valid=0
  for c in chars:
   m=re.search(r'x_bboxes (\d+) (\d+) (\d+) (\d+)',c.get('title',''))
   if m:
    x0,y0,x1,y1=map(int,m.groups());valid+=x1>x0 and y1>y0
  rec={'id':id,'psm':psm,'seconds':time.monotonic()-start,'words':len(words),'characters':len(chars),'valid_boxes':valid,'text':text,'queries':[{'text':q,'found':q in text} for q in queries],'command':cmd};out.append(rec);print(id,psm,len(words),sum(q in text for q in queries),flush=True)
(B/'ocr-controls.json').write_text(json.dumps(out,indent=2))
