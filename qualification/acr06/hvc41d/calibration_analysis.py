#!/usr/bin/env python3
"""Development analysis on existing PDF font glyphs; no OCR or conversions."""
import json,pathlib,math,hashlib
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06'); E=R/'hvc41d'; P=R/'local/hvc41d'; rows=json.loads((E/'font-control-ledger.json').read_text()); imgs=[]
def measure(a,b):
 if not a.any() or not b.any():return 0.,0.
 # one source pixel in Euclidean metric, no registration search
 disk=nd.generate_binary_structure(2,1); near_a=nd.binary_dilation(a,structure=disk);near_b=nd.binary_dilation(b,structure=disk)
 return min((b&near_a).sum()/b.sum(),(a&near_b).sum()/a.sum()), b.sum()/a.sum()
def shift(a,dy,dx):
 b=np.zeros_like(a);h,w=a.shape; y0=max(dy,0);y1=min(h,h+dy);x0=max(dx,0);x1=min(w,w+dx);b[y0:y1,x0:x1]=a[y0-dy:y1-dy,x0-dx:x1-dx];return b
def scale(a,f):
 h,w=a.shape; m=np.asarray(Image.fromarray(a).resize((max(1,round(w*f)),max(1,round(h*f))),Image.Resampling.NEAREST)); out=np.zeros_like(a); sy=max(0,(m.shape[0]-h)//2);sx=max(0,(m.shape[1]-w)//2);dy=max(0,(h-m.shape[0])//2);dx=max(0,(w-m.shape[1])//2);hh=min(h,m.shape[0]);ww=min(w,m.shape[1]);out[dy:dy+hh,dx:dx+ww]=m[sy:sy+hh,sx:sx+ww];return out
for r in rows:
 a=np.asarray(Image.open(r['panel']).convert('L'))[::4,::4];cw=a.shape[1]//4;x0,y0,x1,y1=map(int,r['ocr_box']);w=x1-x0+6;h=y1-y0+6;ref=a[20:20+h,2*cw:2*cw+w]>128;font=a[20:20+h,3*cw:3*cw+w]>128
 imgs.append((ref,font));r['tolerant_score'],r['area_ratio']=measure(ref,font)
# Challenge the exact same font glyph against an independently derived different source character,
# resized only for comparable canvas. Identity labels are unverified and therefore exploratory.
neg={k:[] for k in ('shift_2','scale_085','scale_115','filled_counter','substitution','colour_16')}
for i,(r,(a,b)) in enumerate(zip(rows,imgs)):
 if not a.any() or not b.any():continue
 for dy,dx in [(0,2),(0,-2),(2,0),(-2,0)]:
  z=measure(a,shift(b,dy,dx));neg['shift_2'].append({'index':i,'shift':[dy,dx],'score':z[0],'area':z[1],'fill_error':r['fill_luminance_error']})
 for factor in (.85,1.15):
  z=measure(a,scale(b,factor));neg[f'scale_{int(round(factor*100)):03}'].append({'index':i,'score':z[0],'area':z[1],'fill_error':r['fill_luminance_error']})
 hole=nd.binary_fill_holes(b)&~b
 if hole.sum()>=2:
  z=measure(a,b|hole);neg['filled_counter'].append({'index':i,'hole_pixels':int(hole.sum()),'score':z[0],'area':z[1],'fill_error':r['fill_luminance_error']})
 neg['colour_16'].append({'index':i,'score':r['tolerant_score'],'area':r['area_ratio'],'fill_error':16.0})
 for j,(s,(other,_)) in enumerate(zip(rows,imgs)):
  if i==j or r['control']!=s['control'] or r['char_ocr_unverified'].lower()==s['char_ocr_unverified'].lower() or not other.any():continue
  if abs(other.shape[0]-a.shape[0])>2 or abs(other.shape[1]-a.shape[1])>2:continue
  m=np.asarray(Image.fromarray(other).resize((a.shape[1],a.shape[0]),Image.Resampling.NEAREST)); z=measure(m,b);neg['substitution'].append({'index':i,'other_index':j,'chars':[r['char_ocr_unverified'],s['char_ocr_unverified']],'score':z[0],'area':z[1],'fill_error':r['fill_luminance_error']});break
scores=[]
for t in [.90,.93,.95,.97,.98,.99,1.0]:
 for lo,hi in [(.8,1.2),(.85,1.15),(.9,1.1),(.95,1.05)]:
  passes=lambda x:x['score']>=t and lo<=x['area']<=hi and x['fill_error'] is not None and x['fill_error']<=15
  pos=sum(passes({'score':r['tolerant_score'],'area':r['area_ratio'],'fill_error':r['fill_luminance_error']}) for r in rows)
  scores.append({'score_min':t,'area_min':lo,'area_max':hi,'positive_pass':pos,'total':len(rows),'negative_reject':{k:{'rejected':sum(not passes(x) for x in v),'total':len(v)} for k,v in neg.items()}})
(E/'calibration-exploratory.json').write_text(json.dumps({'rows':rows,'negative_examples':neg,'grid':scores},indent=2,ensure_ascii=False,default=lambda x:x.item())+'\n')
# Contact sheets: clearly separated boxes and labels, four columns, 16 examples per page.
for j in range(0,len(rows),16):
 sheet=Image.new('RGB',(1200,4*230),'white');d=ImageDraw.Draw(sheet)
 for k,r in enumerate(rows[j:j+16]):
  original=Image.open(r['panel']); cw=original.width//4; crop=original.crop((0,80,cw*2,original.height)); crop.thumbnail((286,190),Image.Resampling.NEAREST);x=(k%4)*300;y=(k//4)*230;sheet.paste(crop,(x,y+35));d.text((x+3,y+3),f"{j+k} {r['control']} word {r['word_index']} char {r['char_ocr_unverified']!r}",fill='black');d.text((x+3,y+17),f"score {r['tolerant_score']:.3f} area {r['area_ratio']:.2f}",fill='black')
 sheet.save(P/f'control-sheet-{j//16+1:02}.png')
print('rows',len(rows),'negatives', {k:len(v) for k,v in neg.items()})
for x in scores:
 if x['score_min'] in (.95,.98) and x['area_min'] in (.8,.9):print(x)
