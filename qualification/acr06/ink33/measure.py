#!/usr/bin/env python3
"""Measure matched OCR character boxes at 300 DPI. Output is exploratory,
not ground truth: overlap ambiguity, OCR errors and raster alignment matter."""
import json, math, pathlib, subprocess, sys
import numpy as np
from PIL import Image
from scipy.stats import spearmanr
from scipy.ndimage import gaussian_filter
from skimage.metrics import structural_similarity
import pypdfium2 as pdfium
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
from prepare import E,O,B,P,G,area,inter,lum,render,baseline

NAMES=['source','scanweave','adobe','a','b','c']
def stats(vals):
 a=np.array([x for x in vals if x is not None and np.isfinite(x)],dtype=float)
 if not a.size: return None
 return {'n':int(a.size),'p10':float(np.percentile(a,10)),'p25':float(np.percentile(a,25)),'p50':float(np.median(a)),'p75':float(np.percentile(a,75)),'p90':float(np.percentile(a,90))}
def metric(im,b):
 x0,y0,x1,y1=map(int,b); H,W=im.shape[:2]; x0=max(0,x0); y0=max(0,y0); x1=min(W,x1); y1=min(H,y1)
 if x1-x0<2 or y1-y0<2: return None
 y=lum(im[y0:y1,x0:x1]); bg=float(np.percentile(y,85)); ink=y[y<bg-10]
 if ink.size<3: return None
 core=float(np.median(ink[ink<=np.quantile(ink,.3)])); contrast=bg-core
 if contrast<10: return None
 mask=y<(core+bg)/2; density=float(np.mean(mask)); gy,gx=np.gradient(y); grad=np.sqrt(gx*gx+gy*gy)
 def perimeter(z):
  z=np.pad(z.astype(np.int8),1); return int(np.abs(np.diff(z,axis=0)).sum()+np.abs(np.diff(z,axis=1)).sum())
 smoothed=gaussian_filter(mask.astype(float),.65)>=.5; ps=perimeter(smoothed); rough=(perimeter(mask)-ps)/ps if ps else None
 edge=(y>=core+.1*contrast)&(y<=core+.9*contrast)&(grad>=2)
 width=float(.8*contrast/np.median(grad[edge])) if np.count_nonzero(edge)>=3 else None
 return {'tone':core,'density':density,'edge':width,'roughness':rough}
def mval(m,k): return m.get(k) if m else None
def summarize(chars):
 out={}
 for name in NAMES:
  ok=[c for c in chars if c['measure'][name] is not None and c['measure']['source'] is not None]
  tones=[c['measure'][name]['tone'] for c in ok]; v=[c['measure'][name]['tone'] for c in ok if c['class']=='vector']; r=[c['measure'][name]['tone'] for c in ok if c['class']=='raster']
  out[name]={'n':len(ok),'tone_iqr':float(np.percentile(tones,75)-np.percentile(tones,25)) if len(tones)>=2 else None,
   'gap':float(np.median(v)-np.median(r)) if v and r else None,
   'tone_error':float(np.median([abs(c['measure'][name]['tone']-c['measure']['source']['tone']) for c in ok])) if ok else None,
   'signed_error':float(np.median([c['measure'][name]['tone']-c['measure']['source']['tone'] for c in ok])) if ok else None,
   'density_vector':float(np.median([c['measure'][name]['density'] for c in ok if c['class']=='vector'])) if v else None,
   'density_raster':float(np.median([c['measure'][name]['density'] for c in ok if c['class']=='raster'])) if r else None,
   'edge_vector':float(np.median([c['measure'][name]['edge'] for c in ok if c['class']=='vector' and c['measure'][name]['edge'] is not None])) if any(c['class']=='vector' and c['measure'][name]['edge'] is not None for c in ok) else None,
   'edge_raster':float(np.median([c['measure'][name]['edge'] for c in ok if c['class']=='raster' and c['measure'][name]['edge'] is not None])) if any(c['class']=='raster' and c['measure'][name]['edge'] is not None for c in ok) else None,
   'roughness_vector':float(np.median([c['measure'][name]['roughness'] for c in ok if c['class']=='vector' and c['measure'][name]['roughness'] is not None])) if any(c['class']=='vector' and c['measure'][name]['roughness'] is not None for c in ok) else None,
   'roughness_raster':float(np.median([c['measure'][name]['roughness'] for c in ok if c['class']=='raster' and c['measure'][name]['roughness'] is not None])) if any(c['class']=='raster' and c['measure'][name]['roughness'] is not None for c in ok) else None}
 return out
def ssim(a,b,box):
 x0,y0,x1,y1=map(int,box); H,W=a.shape[:2]; x0=max(0,x0-2); y0=max(0,y0-2); x1=min(W,x1+2); y1=min(H,y1+2)
 if min(x1-x0,y1-y0)<7:return None
 return float(structural_similarity(lum(a[y0:y1,x0:x1]),lum(b[y0:y1,x0:x1]),data_range=255))
def pdftext(path): return subprocess.run(['pdftotext','-enc','UTF-8',str(path),'-'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE).stdout

def process(g):
 print('start',g,flush=True); paths={n:O/f'{g}-cf-{n}.pdf' for n in 'abc'}
 base=pdftext(baseline(g)); extraction={n:pdftext(path)==base for n,path in paths.items()}; print('extraction',g,extraction,flush=True)
 if not all(extraction.values()): raise ValueError(f'{g} extraction changed: {extraction}')
 cf={n:pdfium.PdfDocument(str(paths[n])) for n in 'abc'}; maps=sorted((O/'maps'/g).glob('*.json')); page_summaries=[]; all_lines=[]; adobe_cor=[]; mixedchars=[]
 for mp in maps:
  page=int(mp.stem); dat=json.loads(mp.read_text()); W,H=dat['width'],dat['height']; d=O/'renders'/g
  ims={n:np.asarray(Image.open(d/f'{page:02d}-{n}.png').convert('RGB')) for n in ('source','scanweave','adobe')}
  for n,doc in cf.items():
   ims[n]=render(doc,page-1,W,H); Image.fromarray(ims[n]).save(d/f'{page:02d}-{n}.png')
  allchars=[]; linesout=[]; ambig=0; ad_line_colors={}; ad_word_colors={}
  for obj in dat['adobe_objects']:
   if 'symbol' not in obj or not obj.get('rgba'): continue
   li,wi,ci=obj['symbol']; ad_line_colors.setdefault(li,set()).add(tuple(obj['rgba'][:3])); ad_word_colors.setdefault((li,wi),set()).add(tuple(obj['rgba'][:3])); c=dat['lines'][li]['words'][wi]['chars'][ci]
   if c.get('source_rgb') is not None: adobe_cor.append([float(lum(obj['rgba'][:3])),float(lum(c['source_rgb']))])
  for li,line in enumerate(dat['lines']):
   lc=[]; wordout=[]
   for wi,word in enumerate(line['words']):
    wc=[]
    for ci,c in enumerate(word['chars']):
     b=c['box']; ca=area(b)
     hits=[o for o in dat['scan_objects'] if inter(b,o['box'])/ca>=.12]
     if c['vector']: cls='vector'
     elif hits: ambig+=1; continue
     else: cls='raster'
     m={n:metric(im,b) for n,im in ims.items()}
     if not m['source'] or not m['scanweave']: continue
     adhit=any(inter(b,o['box'])/ca>=.12 for o in dat['adobe_objects'])
     rec={'line':line['id'],'word':word['id'],'text':c['text'],'box':b,'class':cls,'adobe_vector_overlap':adhit,'measure':m}; wc.append(rec); lc.append(rec); allchars.append(rec)
    if wc:
     wordout.append({'id':word['id'],'box':word['box'],'n_vector':sum(x['class']=='vector' for x in wc),'n_raster':sum(x['class']=='raster' for x in wc),'adobe_colors':len(ad_word_colors.get((li,wi),set())),'adobe_fill_colors':sorted(ad_word_colors.get((li,wi),set())),'metrics':summarize(wc)})
   nv=sum(x['class']=='vector' for x in lc); nr=sum(x['class']=='raster' for x in lc)
   if nv and nr:
    vals=summarize(lc)
    for n in NAMES: vals[n]['ssim']=ssim(ims['source'],ims[n],line['box'])
    record={'page':page,'id':line['id'],'box':line['box'],'n_vector':nv,'n_raster':nr,'adobe_colors':len(ad_line_colors.get(li,set())),'adobe_fill_colors':sorted(ad_line_colors.get(li,set())),'adobe_vector_overlap':sum(x['adobe_vector_overlap'] for x in lc),'metrics':vals,'words':wordout}
    linesout.append(record); all_lines.append(record); mixedchars.extend(lc)
  op=E/f'metrics-{g}-{page:02d}.json'; op.write_text(json.dumps({'page':page,'ambiguous_excluded':ambig,'lines':linesout},separators=(',',':'))+'\n')
  for part in range(0,len(allchars),500):
   (E/f'chars-{g}-{page:02d}-{part//500+1:02d}.json').write_text(json.dumps(allchars[part:part+500],separators=(',',':'))+'\n')
  page_summaries.append({'page':page,'mixed_lines':len(linesout),'ambiguous_excluded':ambig,'measured_chars_on_mixed_lines':sum(x['n_vector']+x['n_raster'] for x in linesout)})
  print(g,'page',page,'mixed',len(linesout),'ambiguous',ambig,flush=True)
   
 summaries={}
 for name in NAMES:
  summaries[name]={}
  for key in ['tone_iqr','gap','tone_error','signed_error','density_vector','density_raster','edge_vector','edge_raster','roughness_vector','roughness_raster','ssim']:
   summaries[name][key]=stats([x['metrics'][name][key] for x in all_lines])
  words=[w for line in all_lines for w in line['words'] if w['n_vector'] and w['n_raster']]
  all_words=[w for line in all_lines for w in line['words']]
  summaries[name]['word_tone_iqr']=stats([w['metrics'][name]['tone_iqr'] for w in all_words])
  summaries[name]['word_tone_error']=stats([w['metrics'][name]['tone_error'] for w in all_words])
  summaries[name]['character_abs_tone_error']=stats([abs(c['measure'][name]['tone']-c['measure']['source']['tone']) for c in mixedchars if c['measure'][name] and c['measure']['source']])
  summaries[name]['vector_signed_tone_error']=stats([c['measure'][name]['tone']-c['measure']['source']['tone'] for c in mixedchars if c['class']=='vector' and c['measure'][name] and c['measure']['source']])
  summaries[name]['mixed_word_tone_iqr']=stats([w['metrics'][name]['tone_iqr'] for w in words]); summaries[name]['mixed_word_gap']=stats([w['metrics'][name]['gap'] for w in words])
 paired={}
 for name in 'abc':
  v=[c for c in mixedchars if c['class']=='vector' and c['measure']['source'] and c['measure']['scanweave'] and c['measure'][name]]
  before=np.array([c['measure']['scanweave']['tone']-c['measure']['source']['tone'] for c in v]); after=np.array([c['measure'][name]['tone']-c['measure']['source']['tone'] for c in v])
  paired[name]={'n':len(v),'closer':int(np.sum(np.abs(after)<np.abs(before)-1e-6)),'farther':int(np.sum(np.abs(after)>np.abs(before)+1e-6)),'unchanged':int(np.sum(np.abs(np.abs(after)-np.abs(before))<=1e-6)),'dark_of_source':int(np.sum(after < -1)),'light_of_source':int(np.sum(after > 1)),'within_one':int(np.sum(np.abs(after)<=1)),'signed_change':stats((after-before).tolist())}
 a=np.asarray(adobe_cor); corr=None
 if len(a)>2 and np.std(a[:,0])>0 and np.std(a[:,1])>0:
  corr={'n':len(a),'pearson':float(np.corrcoef(a.T)[0,1]),'spearman':float(spearmanr(a[:,0],a[:,1]).statistic)}
 words=[w for line in all_lines for w in line['words']]
 summary={'document':g,'extraction_equal':extraction,'pages':page_summaries,'mixed_lines':len(all_lines),'mixed_words':sum(w['n_vector']>0 and w['n_raster']>0 for w in words),'paired_vector_errors':paired,'adobe_colors_per_mixed_line':stats([x['adobe_colors'] for x in all_lines]),'adobe_colors_per_word_on_mixed_lines':stats([w['adobe_colors'] for w in words]),'adobe_word_multicolor_count':sum(w['adobe_colors']>1 for w in words),'adobe_source_color_correlation':corr,'adobe_vector_coverage_on_measured_chars':sum(x['adobe_vector_overlap'] for x in all_lines)/sum(x['n_vector']+x['n_raster'] for x in all_lines) if all_lines else None,'scan_vector_coverage_on_measured_chars':sum(x['n_vector'] for x in all_lines)/sum(x['n_vector']+x['n_raster'] for x in all_lines) if all_lines else None,'metrics':summaries}
 (E/f'summary-{g}.json').write_text(json.dumps(summary,indent=2)+'\n'); print('done',g,flush=True)
if __name__=='__main__':
 for g in (sys.argv[1:] or G): process(g)
