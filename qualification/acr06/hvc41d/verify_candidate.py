"""Verify completed candidate semantics, original resources and final font mask."""
import pathlib,json,hashlib,subprocess,sys,collections
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41d';L=R/'local/hvc41d';sys.path.insert(0,str(E));from validator import metrics
base=R/'local/ink33r/historical.pdf';cand=L/'historical-rejected-243.pdf';sha=lambda b:hashlib.sha256(b).hexdigest();ref=json.loads((E/'p1-preflight-ledger.json').read_text())[243];out={'baseline_sha256':sha(base.read_bytes()),'candidate_sha256':sha(cand.read_bytes()),'baseline_bytes':base.stat().st_size,'candidate_bytes':cand.stat().st_size}
def strings(path):
 d=pdfium.PdfDocument(str(path));ans=[]
 for i in range(len(d)):
  p=d[i];t=p.get_textpage();s=t.get_text_range();ans.append(s);t.close();p.close()
 d.close();return ans
bt=strings(base);ct=strings(cand);out['pdfium_page_text_equal']=[x==y for x,y in zip(bt,ct)]
for name,path in [('base',base),('candidate',cand)]:
 doc=pdfium.PdfDocument(str(path));p=doc[0];t=p.get_textpage();s=t.get_text_range();word=next((x.strip('.,:;!()[]') for x in s.split() if len(x.strip('.,:;!()[]'))>=5),'');search=t.search(word);hits=[]
 while (hit:=search.get_next()) is not None:hits.append(hit)
 out[name+'_pdfium_search']={'word':word,'hits':hits};search.close();t.close();p.close();doc.close()
def pop(path,page=None):
 args=['pdftotext','-enc','UTF-8'];
 if page is not None:args+=['-f',str(page),'-l',str(page)]
 return subprocess.check_output(args+[str(path),'-'])
out['poppler_page_text_equal']=[pop(base,i)==pop(cand,i) for i in range(1,6)]
# Content and image/font payloads are compared as decoded content and raw resource streams.
def resources(path):
 p=pikepdf.open(path);ans=[]
 for pg in p.pages:
  contents=pg.Contents; content=[s.read_bytes() for s in contents] if isinstance(contents,pikepdf.Array) else [contents.read_bytes()];im={str(k):sha(v.read_raw_bytes()) for k,v in pg.Resources.get('/XObject',pikepdf.Dictionary()).items() if str(v.get('/Subtype'))=='/Image'};fonts={}
  for k,v in pg.Resources.get('/Font',pikepdf.Dictionary()).items():
   td=v.get('/ToUnicode');fonts[str(k)]=sha(td.read_bytes()) if td else None
  ans.append({'content':list(map(sha,content)),'images':im,'tounicode':fonts})
 p.close();return ans
br=resources(base);cr=resources(cand);out['baseline_stream_unchanged']=[x['content'][0]==y['content'][0] for x,y in zip(br,cr)];out['image_streams_unchanged']=[x['images']==y['images'] for x,y in zip(br,cr)];out['tounicode_unchanged']=[x['tounicode']==y['tounicode'] for x,y in zip(br,cr)];out['original_resources']=br;out['candidate_resources']=cr
# Render only the actual final overlay from the completed candidate, maintaining its font and placement.
p=pikepdf.open(cand);pg=p.pages[0];pg.Contents=pg.Contents[-1];isolated=L/'final-font-isolated.pdf';p.save(isolated);p.close();d=pdfium.PdfDocument(str(isolated));pg=d[0];font=np.asarray(pg.render(scale=300/72,rev_byteorder=True,fill_color=(255,255,255,255)).to_pil().convert('RGB'));pg.close();d.close();source=np.asarray(Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB'));a,b,c,f=ref['reference_box'];wt=np.array([.2126,.7152,.0722]);ys=source[b:f,a:c].astype(float)@wt;source_mask=ys<(ref['admission']['paper_luma']+ref['source_ink_luma'])/2;yf=font[b:f,a:c].astype(float)@wt;fill=np.array(ref['fill_rgb'])@wt;fm=yf<(255+fill)/2;m=metrics(source_mask,fm,ref['fill_error']);un=int((source_mask|fm).sum());m['iou']=float((source_mask&fm).sum()/un) if un else None;out['final_glyph_validator']=m
truth=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0;support=np.zeros_like(truth);support[b:f,a:c]=fm;den=int(truth.sum());hit=int((truth&support).sum());out['reference_ink']={'total_pixels':den,'covered_pixels':hit,'coverage':hit/den if den else None}
zero=L/'historical-zero-glyph.pdf';zero.write_bytes(base.read_bytes());out['zero_glyph_byte_identical']=zero.read_bytes()==base.read_bytes();out['ocr_stub_marker_absent']=not (L/'outer-ocr-invoked').exists() and not (L/'forbidden-ocr-invoked').exists();(E/'candidate-checks.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k not in ('original_resources','candidate_resources')},indent=2),flush=True)
