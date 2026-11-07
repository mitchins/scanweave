#!/usr/bin/env python3
"""Compare page streams, text extraction and renderer differences for two PDFs."""
import argparse, hashlib, json, subprocess, tempfile
from pathlib import Path
import numpy as np
import pikepdf
import pypdfium2 as pdfium
from PIL import Image

P=argparse.ArgumentParser(); P.add_argument('default'); P.add_argument('candidate'); P.add_argument('output'); A=P.parse_args()
hashbytes=lambda b: hashlib.sha256(b).hexdigest()
files=[A.default,A.candidate]; pdfs=[pikepdf.open(x) for x in files]; docs=[pdfium.PdfDocument(x) for x in files]

def streams(pg):
    seen=set(); result={'font':[], 'content':[], 'image':{}}
    def walk(obj,kind=None,path=''):
        if not isinstance(obj,(pikepdf.Stream,pikepdf.Array,pikepdf.Dictionary)): return
        if obj.is_indirect:
            if obj.objgen in seen: return
            seen.add(obj.objgen)
        if isinstance(obj,pikepdf.Stream):
            h=hashbytes(obj.read_raw_bytes())
            if obj.get('/Subtype') == '/Image':
                result['image'][path]={'sha256':h,'width':int(obj.Width),'height':int(obj.Height),'bytes':len(obj.read_raw_bytes()),'filter':str(obj.get('/Filter'))}
            elif kind in ('font','content'): result[kind].append(h)
        for k,v in (enumerate(obj) if isinstance(obj,pikepdf.Array) else obj.items()):
            if str(k) in ('/Parent','/P'): continue
            newkind=kind
            if str(k) in ('/Font','/FontFile','/FontFile2','/FontFile3','/FontDescriptor','/DescendantFonts','/ToUnicode','/CIDToGIDMap','/CIDSet'): newkind='font'
            if str(k)=='/Contents': newkind='content'
            walk(v,newkind,path+'/'+str(k))
    walk(pg.obj)
    for k in ('font','content'): result[k].sort()
    return result

def text_pdfium(doc,i): return doc[i].get_textpage().get_text_range()
def poppler(path,i,output):
    subprocess.run(['pdftoppm','-f',str(i+1),'-l',str(i+1),'-r','300','-singlefile','-png',path,output],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.PIPE)
    return Image.open(output+'.png').convert('RGB')
def compare(a,b):
    if a.size!=b.size: return {'size_mismatch':[a.size,b.size]}
    x=np.asarray(a,dtype=np.int16); y=np.asarray(b,dtype=np.int16); diff=np.max(np.abs(x-y),axis=2)
    return {'changed_pixels':int((diff>0).sum()),'mean_max_channel_abs':float(diff.mean()),'max_abs':int(diff.max())}

out={'default':A.default,'candidate':A.candidate,'default_bytes':Path(A.default).stat().st_size,'candidate_bytes':Path(A.candidate).stat().st_size,'pages':[]}
with tempfile.TemporaryDirectory() as td:
    for i in range(len(pdfs[0].pages)):
        a,b=[streams(p.pages[i]) for p in pdfs]
        changed=[k for k in sorted(set(a['image'])|set(b['image'])) if a['image'].get(k)!=b['image'].get(k)]
        pdfium_images=[doc[i].render(scale=300/72).to_pil().convert('RGB') for doc in docs]
        poppler_images=[poppler(f,i,f'{td}/{j}') for j,f in enumerate(files)]
        poptext=[subprocess.run(['pdftotext','-f',str(i+1),'-l',str(i+1),f,'-'],check=True,capture_output=True).stdout for f in files]
        row={'page':i+1,'font_streams_equal':a['font']==b['font'],'content_streams_equal':a['content']==b['content'],
             'images_default':a['image'],'images_candidate':b['image'],'changed_image_paths':changed,
             'pdfium_text_equal':text_pdfium(docs[0],i)==text_pdfium(docs[1],i),'poppler_text_equal':poptext[0]==poptext[1],
             'pdfium_render_diff':compare(*pdfium_images),'poppler_render_diff':compare(*poppler_images),
             'note':'Render differences are whole-page; if only a background stream changed and content is equal they arise through that background, including its compositing edges.'}
        out['pages'].append(row)
        Path(A.output).write_text(json.dumps(out,indent=2)+'\n')
        print(f'{A.output}: page {i+1}',flush=True)
