#!/usr/bin/env python3
import hashlib,subprocess,sys
from pathlib import Path
from PIL import Image,ImageChops
root=Path('/data/coding/scanweave/qualification/acr06/local/trace32'); out=root/'poppler-probe'; out.mkdir(exist_ok=True)
for dpi in ('217.3','200','300','600'):
 for arm in ('profile','experimental'):
  print('render',dpi,arm,flush=True)
  subprocess.run(['pdftoppm','-r',dpi,'-png',str(root/(arm+'.pdf')),str(out/(arm+'-'+dpi))],check=True)
 a=sorted(out.glob('profile-'+dpi+'-*.png')); b=sorted(out.glob('experimental-'+dpi+'-*.png'))
 if len(a)!=len(b): print('PAGE COUNT MISMATCH',len(a),len(b),flush=True);sys.exit(1)
 for x,y in zip(a,b):
  with Image.open(x) as i,Image.open(y) as j:
   if i.size!=j.size or i.mode!=j.mode: print('FAIL',dpi,x.name,'geometry',i.size,j.size,i.mode,j.mode,flush=True);sys.exit(1)
   d=ImageChops.difference(i,j); box=d.getbbox()
   if box:
    hist=d.convert('RGB').getdata(); count=sum(1 for p in hist if p!=(0,0,0)); print('FAIL',dpi,x.name,'changed_pixels',count,'bbox',box,flush=True);sys.exit(1)
  print('PASS',dpi,x.name,flush=True)
 print('completed',dpi,flush=True)
