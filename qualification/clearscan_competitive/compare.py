#!/usr/bin/env python3
"""Same-instance comparison. Oracle stays exclusively in this evaluator.
Exact-size render controls exclude renderer ceil rounding (tested against source).
Default-DPI results are retained independently; no glyph is independently resized.
"""
import argparse,hashlib,json,re,subprocess,time,os,math
from pathlib import Path
from collections import defaultdict
import numpy as np
from PIL import Image,ImageDraw
import pikepdf,pypdfium2 as pdfium
ROOT=Path(__file__).resolve().parents[2]
def run(cmd): return subprocess.run(cmd,check=True,capture_output=True,text=True).stdout
def iou(a,b):
 a=a<170;b=b<170;return float((a&b).sum()/max(1,(a|b).sum()))
def accounting(path):
 p=pikepdf.open(path); seen=set();font_streams=set(); classes=defaultdict(int); images=[]; outlines=0; uses=0
 for obj in p.objects:
  if not isinstance(obj,pikepdf.Stream):continue
  raw=obj.read_raw_bytes(); kind='other_stream'
  if obj.get('/Subtype')=='/Image':
   kind='raster'; images.append({'object':list(obj.objgen),'width':int(obj.Width),'height':int(obj.Height),'colour':str(obj.get('/ColorSpace')),'filter':str(obj.get('/Filter')),'bytes':len(raw),'encoded_sha256':hashlib.sha256(raw).hexdigest(),'samples_sha256':hashlib.sha256(pikepdf.PdfImage(obj).as_pil_image().tobytes()).hexdigest()})
  classes[kind]+=len(raw)
 for page in p.pages:
  cs=page.get('/Contents'); cs=[cs] if isinstance(cs,pikepdf.Stream) else list(cs or [])
  for stream in cs:classes['content']+=len(stream.read_raw_bytes());classes['other_stream']-=len(stream.read_raw_bytes())
  for ins in pikepdf.parse_content_stream(page):
   if str(ins.operator) in ('Tj','TJ'): uses+=1
  for font in page.Resources.get('/Font',{}).values():
   descs=font.get('/DescendantFonts',[font]);
   for f in descs:
    if f.objgen in seen:continue
    seen.add(f.objgen)
    fd=f.get('/FontDescriptor',{})
    for key in ('/FontFile','/FontFile2','/FontFile3'):
     stream=fd.get(key)
     if stream is not None:
      if stream.objgen in font_streams:continue
      font_streams.add(stream.objgen)
      n=len(stream.read_raw_bytes()); classes['font']+=n;classes['other_stream']-=n
      try:
       import io
       from fontTools.ttLib import TTFont
       ft=TTFont(io.BytesIO(stream.read_bytes()));outlines+=sum(1 for name in ft.getGlyphOrder() if ft['glyf'][name].numberOfContours!=0) if 'glyf' in ft else len(ft.getGlyphOrder())
      except Exception:
       try:
        from fontTools.cffLib import CFFFontSet
        import io
        cff=CFFFontSet();cff.decompile(io.BytesIO(stream.read_bytes()),None);outlines+=len(cff[cff.fontNames[0]].CharStrings.charStrings)
       except Exception:pass
 classes['overhead']=path.stat().st_size-sum(classes.values())
 return {'bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'streams':dict(classes),'images':images,'unique_images':len(images),'text_show_operations':uses,'font_outlines':outlines or None}
def evaluate(dpi,arm,path,oracle_base=None,input_base=None):
 out=ROOT/'qualification/clearscan_competitive'/str(dpi)/arm;out.mkdir(parents=True,exist_ok=True)
 base=input_base or ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/input';oracle=oracle_base or base.parent/'oracle'
 m=json.loads((base/'document.json').read_text());sources={s['source_id']:s for s in m['sources']};doc=pdfium.PdfDocument(str(path));records=[];expected=''; ptext='';result=accounting(path)
 for kind,res in [('exact',dpi),('default',dpi)]:
  d=out/kind;d.mkdir(exist_ok=True)
  if not (os.environ.get('REUSE_RENDERS') and (d/'poppler-1.png').exists()):run(['pdftoppm','-r',str(res),'-png',str(path),str(d/'poppler')])
  for pi,p in enumerate(m['pages']):
   src=np.asarray(Image.open(base/sources[p['source_id']]['asset_path']).convert('L'));h,w=src.shape
   truth_path=oracle/f'page{pi:02}.truth.json';truth_im=oracle/f'page{pi:02}.png'
   if not truth_path.exists(): truth_path=oracle/f'page{pi+1}-truth.json';truth_im=oracle/f'page{pi+1}-pristine.png'
   td=json.loads(truth_path.read_text());truth=np.asarray(Image.open(truth_im).convert('L'))
   pop=np.asarray(Image.open(d/f'poppler-{pi+1}.png').convert('L'))[:h,:w]
   pyim=doc[pi].render(scale=math.nextafter(dpi/72,0.0) if kind=='exact' else dpi/72).to_pil().convert('L');pyim.save(d/f'pdfium-{pi+1}.png');py=np.asarray(pyim)[:h,:w]
   if kind=='exact':expected+=''.join(s['text'] for s in json.loads((base/p['ocr_page_path']).read_text())['spans']);ptext+=doc[pi].get_textpage().get_text_range()
   for g in td.get('records',td.get('glyphs',[])):
    x0,y0,x1,y1=map(int,g['bbox']);pad=4;sl=(slice(max(0,y0-pad),min(h,y1+pad)),slice(max(0,x0-pad),min(w,x1+pad)))
    rec={'page':pi,'id':g.get('id'),'text':g.get('text',g.get('char')),'geometry':kind,'bbox':g['bbox'],'source':iou(src[sl],truth[sl]),'poppler':iou(pop[sl],truth[sl]),'pdfium':iou(py[sl],truth[sl])}
    ch=rec['text'] or ''
    if ch.strip():
     isolation_pad=round((4 if ord(ch[0])>127 else 5)*dpi/300) if 'records' in td else 0
     isolated=(slice(y0+isolation_pad,y1-isolation_pad),slice(x0+isolation_pad,x1-isolation_pad))
     for name,img in [('source',src),('poppler',pop),('pdfium',py)]:rec[name+'_isolated']=iou(img[isolated],truth[isolated])
    # Translation-only diagnostic; never rescale the outline or change the primary metric.
    if kind=='exact':
     for name,img in [('poppler',pop),('pdfium',py)]:
      sy,sx=sl; best=(rec[name],0,0)
      if sy.start>=2 and sx.start>=2 and sy.stop+2<h and sx.stop+2<w:
       for dy in range(-2,3):
        for dx in range(-2,3):
         score=iou(img[sy.start+dy:sy.stop+dy,sx.start+dx:sx.stop+dx],truth[sl]);best=max(best,(score,dx,dy))
      rec[name+'_aligned']=best[0];rec[name+'_shift']=list(best[1:])
    records.append(rec)
   if kind=='exact' and pi in (0,6):
    panel=Image.new('RGB',(w*4,h+30),'white')
    for col,(label,a) in enumerate([('source',src),('pristine',truth),('poppler',pop),('pdfium',py)]):panel.paste(Image.fromarray(a).convert('RGB'),(col*w,30));ImageDraw.Draw(panel).text((col*w+5,5),label,fill='black')
    panel.save(out/f'page{pi:02}-comparison.png')
 families={}
 for ch in sorted(set(r['text'] for r in records)):
  rs=[r for r in records if r['text']==ch and r['geometry']=='exact'];families[ch]={k:float(np.mean([r[k] for r in rs])) for k in ['source','poppler','pdfium','poppler_aligned','pdfium_aligned']};families[ch]['n']=len(rs)
 summary={kind:{k:float(np.mean([r[k] for r in records if r['geometry']==kind])) for k in ['source','poppler','pdfium']} for kind in ['exact','default']}
 isolated_summary={kind:{k:float(np.mean([r[k+'_isolated'] for r in records if r['geometry']==kind and k+'_isolated' in r])) for k in ['source','poppler','pdfium']} for kind in ['exact','default']}
 norm=lambda t:re.sub(r'\s+','',t)
 text=run(['pdftotext','-raw',str(path),'-']);(out/'poppler.txt').write_text(text);(out/'pdfium.txt').write_text(ptext)
 result.update({'dpi':dpi,'arm':arm,'render_contract':{'poppler_dpi':dpi,'pdfium_exact_scale':math.nextafter(dpi/72,0.0),'default_pdfium_scale':dpi/72,'note':'Exact-size PDFium avoids floating-point ceil. Poppler uses integer physical DPI; fractional DPI shifts vector phase and is retained only as a separate diagnostic.'},'glyphs':records,'summary':summary,'families':families,'isolated_summary':isolated_summary,'best_families':sorted(families,key=lambda c:families[c]['poppler']-families[c]['source'],reverse=True)[:10],'worst_families':sorted(families,key=lambda c:families[c]['poppler']-families[c]['source'])[:10],'search':{'poppler_matches_ocr':norm(text)==norm(expected),'pdfium_matches_ocr':norm(ptext)==norm(expected),'ocr':expected,'poppler':text,'pdfium':ptext}})
 (out/'metrics.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n');print(arm,dpi,result['bytes'],summary,flush=True)
 return result
if __name__=='__main__':
 ap=argparse.ArgumentParser();ap.add_argument('dpi',type=int);ap.add_argument('arm');ap.add_argument('pdf',type=Path);ap.add_argument('--input',type=Path);ap.add_argument('--oracle',type=Path);a=ap.parse_args();evaluate(a.dpi,a.arm,a.pdf,a.oracle,a.input)
