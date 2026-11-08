#!/usr/bin/env python3
"""Attach each PDFium Adobe text object and render mode to OCR geometry;
raw fill-space/operators are recorded separately in operator-audit.json."""
import ctypes,json,pathlib,sys,collections
import pypdfium2 as pdfium,pypdfium2.raw as raw
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
from prepare import E,O,P,G,area,inter

def transform(b,m):
 x0,y0,x1,y1=b; p=np.array([[x0,y0,1],[x1,y0,1],[x0,y1,1],[x1,y1,1]])@m.T
 return [float(p[:,0].min()),float(p[:,1].min()),float(p[:,0].max()),float(p[:,1].max())]
def process(g):
 pdf=pdfium.PdfDocument(str(P/f'{g}-adobe.pdf')); prep=json.loads((E/f'prepare-{g}.json').read_text()); summaries=[]
 for pi in range(len(pdf)):
  d=json.loads((O/'maps'/g/f'{pi+1:02d}.json').read_text()); mat=np.array(prep[pi]['registration']['matrix']); lines=d['lines']; W,H=d['width'],d['height']; pg=pdf[pi]; tp=pg.get_textpage(); pw,ph=pg.get_size(); out=[]
  for ob in pg.get_objects():
   if ob.type!=raw.FPDF_PAGEOBJ_TEXT: continue
   x0,y0,x1,y1=ob.get_bounds(); b=transform([x0*W/pw,(ph-y1)*H/ph,x1*W/pw,(ph-y0)*H/ph],mat); mode=raw.FPDFTextObj_GetTextRenderMode(ob.raw); c=[ctypes.c_uint() for _ in range(4)]; ok=raw.FPDFPageObj_GetFillColor(ob.raw,*[ctypes.byref(x) for x in c]); n=raw.FPDFTextObj_GetText(ob.raw,tp.raw,None,0); buf=(ctypes.c_ushort*(n//2+2))(); raw.FPDFTextObj_GetText(ob.raw,tp.raw,buf,n); text=bytes(buf)[:n].decode('utf-16-le','replace').rstrip('\x00')
   overlaps=[(inter(b,l['box']),li) for li,l in enumerate(lines) if inter(b,l['box'])>0]; li=max(overlaps)[1] if overlaps else None; wi=None
   if li is not None:
    overlaps=[(inter(b,w['box']),k) for k,w in enumerate(lines[li]['words']) if w['box'] and inter(b,w['box'])>0]; wi=max(overlaps)[1] if overlaps else None
   out.append({'box':b,'mode':mode,'rgba':[x.value for x in c] if ok else None,'text':text,'line_id':lines[li]['id'] if li is not None else None,'word_id':lines[li]['words'][wi]['id'] if wi is not None else None})
  tp.close();pg.close(); colors=collections.defaultdict(set)
  for o in out:
   if o['mode'] in (0,2,4,6) and o['word_id'] and o['rgba']:colors[o['word_id']].add(tuple(o['rgba']))
  sums={'page':pi+1,'objects':len(out),'visible_objects':sum(o['mode'] in (0,2,4,6) for o in out),'mapped_line':sum(o['line_id'] is not None for o in out),'visible_multicolor_words':sum(len(x)>1 for x in colors.values()),'visible_words':len(colors),'single_unicode_visible_objects':sum(len(o['text'])==1 and o['mode'] in (0,2,4,6) for o in out)}
  (E/f'adobe-objects-{g}-{pi+1:02d}.json').write_text(json.dumps({'summary':sums,'objects':out},separators=(',',':'))+'\n');summaries.append(sums)
 (E/f'adobe-policy-{g}.json').write_text(json.dumps(summaries,indent=2)+'\n'); print('done',g,flush=True)
if __name__=='__main__':
 for g in G:process(g)
