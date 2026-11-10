#!/usr/bin/env python3
"""Exploratory overlap inventory, not a validated character classification."""
import collections,json,pathlib,re,xml.etree.ElementTree as ET
import pypdfium2 as pdfium, pypdfium2.raw as raw
R=pathlib.Path('/data/coding/scanweave'); groups=['historical','financial','mixed','receipts','forms']
def box(s):
 m=re.search(r'(?:x_bboxes|bbox) (\d+) (\d+) (\d+) (\d+)',s or '')
 return list(map(int,m.groups())) if m else None
def area_inter(a,b): return max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
summary={}
for g in groups:
 report=json.loads((R/f'qualification/acr06/local/ink33r/{g}.pdf.json').read_text()); pdf=pdfium.PdfDocument(str(R/f'qualification/acr06/local/ink33r/{g}.pdf')); pages=[]
 for pnum,p in enumerate(report['pages']):
  pg=pdf[pnum]; w,h=pg.get_size(); W,H=p['raster_width'],p['raster_height']; vb=[]
  for obj in pg.get_objects():
   if obj.type==raw.FPDF_PAGEOBJ_TEXT and raw.FPDFTextObj_GetTextRenderMode(obj.raw) in (0,2,4,6):
    x0,y0,x1,y1=obj.get_bounds(); vb.append([x0*W/w,(h-y1)*H/h,x1*W/w,(h-y0)*H/h])
  root=ET.fromstring(p['hocr']); lines=[]
  for node in root.iter():
   if 'ocr_line' not in node.attrib.get('class','').split(): continue
   chars=[]
   for c in node.iter():
    if 'ocrx_cinfo' in c.attrib.get('class','').split():
     b=box(c.attrib.get('title'));
     if b and b[2]>b[0] and b[3]>b[1]:
      ca=(b[2]-b[0])*(b[3]-b[1]); hit=max((area_inter(b,v)/ca for v in vb),default=0); chars.append(hit>=.25)
   if chars: lines.append((sum(chars),len(chars)-sum(chars)))
  pages.append({'visible_objects':len(vb),'ocr_lines':len(lines),'mixed_overlap_estimate':sum(a>0 and b>0 for a,b in lines),'vector_only_estimate':sum(a>0 and b==0 for a,b in lines),'no_vector_overlap':sum(a==0 for a,b in lines)})
 summary[g]=pages
(R/'qualification/acr06/ink33r/line-inventory.json').write_text(json.dumps(summary,indent=2)+'\n')
