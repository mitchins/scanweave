"""Same-instance real-page measurements, no invented pristine font truth."""
import json,re,hashlib,subprocess,tempfile,sys,collections
from pathlib import Path
import pikepdf,pypdfium2 as pdfium,pypdfium2.raw as raw,numpy as np
from PIL import Image,ImageOps,ImageDraw
from lxml import etree
B=Path(__file__).resolve().parent;R=B.parents[1];D=B/'real';rows=json.loads((B/'corpus.json').read_text());M=D/'measurement';M.mkdir(exist_ok=True)
def memory(path):
 if not path.exists():return None
 m=re.search(r'Maximum resident set size \(kbytes\): (\d+)',path.read_text());return int(m.group(1)) if m else None
def resources(path):
 p=pikepdf.open(path);images=[];fonts=[];contents=[];seen=set()
 for o in p.objects:
  if not isinstance(o,pikepdf.Stream):continue
  n=len(o.read_raw_bytes())
  if o.get('/Subtype')==pikepdf.Name.Image:images.append(n)
 for pg in p.pages:
  cs=pg.Contents if isinstance(pg.Contents,pikepdf.Array) else [pg.Contents]
  for c in cs:
   if c.objgen not in seen:contents.append(len(c.read_raw_bytes()));seen.add(c.objgen)
 for o in p.objects:
  if not isinstance(o,pikepdf.Dictionary):continue
  for key in ['/FontFile','/FontFile2','/FontFile3']:
   if key in o and o[key].objgen not in seen:fonts.append(len(o[key].read_raw_bytes()));seen.add(o[key].objgen)
 return {'raster_bytes':sum(images),'image_objects':len(images),'font_bytes':sum(fonts),'content_bytes':sum(contents),'pages':len(p.pages),'pdf_bytes':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
def frame(path,idx,renderer):
 if renderer=='pdfium':
  doc=pdfium.PdfDocument(str(path));return doc[idx].render(scale=100/72).to_pil().convert('RGB')
 with tempfile.TemporaryDirectory() as t:
  root=Path(t)/'r';subprocess.run(['pdftoppm','-f',str(idx+1),'-l',str(idx+1),'-singlefile','-r','100','-png',str(path),str(root)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);return Image.open(root.with_suffix('.png')).convert('RGB').copy()
def text_stats(path,idx,queries):
 doc=pdfium.PdfDocument(str(path));tp=doc[idx].get_textpage();text=tp.get_text_range();visible=0;total=0;modes=collections.Counter()
 for i in range(tp.count_chars()):
  ch=chr(raw.FPDFText_GetUnicode(tp.raw,i));mode=raw.FPDFTextObj_GetTextRenderMode(raw.FPDFText_GetTextObject(tp.raw,i));modes[str(mode)]+=1
  if ch.strip():total+=1;visible+=mode not in [3,-1]
 return {'pdfium_text':text,'pdfium_text_sha256':hashlib.sha256(text.encode()).hexdigest(),'visible_nonspace_chars':visible,'total_nonspace_chars':total,'text_render_modes':dict(modes),'queries':[{'text':q,'found':tp.search(q).get_next() is not None} for q in queries]}
def main():
 results=[];thumbs=[]
 for idx,row in enumerate(rows):
  id=row['id'];inp=R/row['matched_input'];queries=[];hocr=D/'archive'/(id+'.hocr')
  if hocr.exists():
   root=etree.parse(str(hocr));words=[(''.join(''.join(c.itertext()) for c in e.xpath('.//*[contains(@class,"ocrx_cinfo")]')) if e.xpath('.//*[contains(@class,"ocrx_cinfo")]') else ''.join(e.itertext())).strip() for e in root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]')]
   words=[w for w in words if re.fullmatch(r'[A-Za-z0-9.,-]{3,}',w)]
   unique=list(dict.fromkeys(words));numbers=[w for w in unique if sum(c.isdigit() for c in w)>=3];queries=list(dict.fromkeys(unique[:2]+numbers[-1:]))[:3]
  if idx<30:adobe=D/'adobe-all.pdf';adobeindex=idx
  else:adobe=D/'adobe-forms.pdf';adobeindex=idx-30
  arms={'source':(inp,0),'adobe':(adobe,adobeindex)}
  for name in ['scanweave','ocrmypdf1','ocrmypdf3','archive']:
   p=D/name/(id+'.pdf')
   if p.exists():arms[name]=(p,0)
  source_frames={ren:frame(inp,0,ren) for ren in ['pdfium','poppler']};record={'id':id,'kind':row['kind'],'query_reference':'same-input independent Tesseract automatic hOCR; not ground truth','arms':{}}
  page_thumbs=[]
  for arm,(p,pi) in arms.items():
   a=text_stats(p,pi,queries);a['source_page_index']=pi
   if arm!='adobe':a.update(resources(p))
   else:
    # Actual corpus PDF bytes measured at document level, not apportioned as if
    # it were independently serialized pages with unrelated font dictionaries.
    a['shared_document_bytes']=p.stat().st_size
   ext=subprocess.check_output(['pdftotext','-f',str(pi+1),'-l',str(pi+1),'-raw',str(p),'-']).decode(errors='replace');a['poppler_text']=ext
   a['renderer_text_equal_ignoring_whitespace']=''.join(ext.split())==''.join(a['pdfium_text'].split())
   a['renderers']={}
   for ren in ['pdfium','poppler']:
    im=frame(p,pi,ren);reference=source_frames[ren];x=np.asarray(im).astype(np.int16);y=np.asarray(reference).astype(np.int16);h=min(x.shape[0],y.shape[0]);w=min(x.shape[1],y.shape[1]);diff=np.abs(x[:h,:w]-y[:h,:w]);a['renderers'][ren]={'size':list(im.size),'source_size':list(reference.size),'source_relative_mae':float(diff.mean()),'changed_fraction':float(np.any(diff!=0,axis=2).mean()),'note':'source deviation only, not a pristine-relative accuracy score'}
    if ren=='pdfium':
     thumb=ImageOps.contain(im,(175,240));canvas=Image.new('RGB',(185,265),'#ddd');canvas.paste(thumb,((185-thumb.width)//2,20));ImageDraw.Draw(canvas).text((3,3),arm,fill='black');page_thumbs.append(canvas)
   run=D/arm/(id+'.run.json')
   if run.exists():a['run']=json.loads(run.read_text());a['peak_kib']=memory(D/arm/(id+'.time.txt'))
   if arm=='scanweave':
    report=json.loads(Path(str(p)+'.json').read_text())['conversion'];pr=report['page_reports'][0];a['observations']=len(pr['reconstruction']['observations']);a['supplied_characters']=pr['supplied_chars'];a['fallback_reasons']=pr['fallback_reasons'];a['coverage']=pr['coverage'];a['selected']=report['selected'];a['reported_vectors']=sum(o.get('owner','').startswith('visible') for o in pr['occurrences']);a['semantic_spans']=pr['semantic_spans']
   record['arms'][arm]=a
  strip=Image.new('RGB',(185*6,285),'white');ImageDraw.Draw(strip).text((2,268),id+' | '+row['kind'],fill='black')
  for col,im in enumerate(page_thumbs):strip.paste(im,(col*185,0))
  thumbs.append(strip);results.append(record);(M/(id+'.json')).write_text(json.dumps(record,indent=2));print(id,flush=True)
 for start in range(0,len(thumbs),8):
  sheet=Image.new('RGB',(1110,285*len(thumbs[start:start+8])),'white')
  for j,im in enumerate(thumbs[start:start+8]):sheet.paste(im,(0,j*285))
  sheet.save(M/f'contact-{start//8+1}.png')
 (B/'real-measurements.json').write_text(json.dumps(results,indent=2))

if __name__=="__main__": main()
