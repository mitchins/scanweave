#!/usr/bin/env python3
"""Render all source pages with PDFium and Poppler at 300 DPI."""
import json,subprocess,tempfile
from pathlib import Path
import numpy as np
import pypdfium2 as pdfium
from PIL import Image
q=Path('/data/coding/scanweave/qualification'); root=q/'acr06/local/bg150'; out=q/'acr06/bg150/source-renders.json'
inputs={g:q/f'pdf_packaging/groups/{g}-input.pdf' for g in ['financial','forms','historical','mixed','receipts']}
inputs.update({'single':q/'pdf_packaging/real/input/scan-c03-29.pdf','competitive300':q/'clearscan_competitive/300/source.pdf','competitive600':q/'clearscan_competitive/600/source.pdf','fresh1':root/'fresh/page-1.pdf','fresh2':root/'fresh/page-2.pdf','freshtruth1':root/'fresh-truth/page-1.pdf','freshtruth2':root/'fresh-truth/page-2.pdf'})
results={}
with tempfile.TemporaryDirectory() as td:
 for name,path in inputs.items():
  doc=pdfium.PdfDocument(str(path)); rows=[]
  for i in range(len(doc)):
   a=doc[i].render(scale=300/72).to_pil().convert('RGB')
   prefix=f'{td}/page'; subprocess.run(['pdftoppm','-f',str(i+1),'-l',str(i+1),'-r','300','-singlefile','-png',str(path),prefix],check=True,capture_output=True)
   b=Image.open(prefix+'.png').convert('RGB')
   row={'page':i+1,'pdfium_size':a.size,'poppler_size':b.size}
   if a.size==b.size:
    diff=np.max(np.abs(np.asarray(a,dtype=np.int16)-np.asarray(b,dtype=np.int16)),axis=2)
    row.update(changed_pixels=int((diff>0).sum()),mean_abs=float(diff.mean()),max_abs=int(diff.max()))
   rows.append(row)
  results[name]=rows; out.write_text(json.dumps(results,indent=2)+'\n'); print(name,flush=True)
