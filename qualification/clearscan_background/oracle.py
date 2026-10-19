"""Evaluator-only paired no-text replay; never imported by converter."""
import importlib.util,inspect,json,hashlib,io,zlib,math
from pathlib import Path
import numpy as np
from PIL import Image
import pikepdf,pypdfium2 as pdfium
B=Path(__file__).resolve().parent;R=B.parents[1]
spec=importlib.util.spec_from_file_location('fixture',R/'qualification/experiments/m1g/generate_fixture.py');g=importlib.util.module_from_spec(spec);spec.loader.exec_module(g)
src=inspect.getsource(g.make_page)
# Keep all random draws and original ink-dependent draws exactly unchanged.
src=src.replace('return rgb, oracle, records, FONT if font_path == FONT else ALT', '''art = np.asarray(pristine,dtype=np.float32).copy()
    for r in records:
        x0,y0,x1,y1=map(int,r['bbox']);art[max(y0,0):y1,max(x0,0):x1]=255
    art_ink=art<245
    bg=art+deposition+paper
    bg[dropout & art_ink]=225+paper[dropout & art_ink]
    # Recreate the already-consumed faint intensity draw with the identical RNG.
    replay=np.random.default_rng(7100+dpi*31+page)
    replay.normal(0,1,(max(2,H//90),max(2,W//90)));replay.normal(0,1.8,(H,W));replay.random((H,W));replay.random((H,W))
    intens=replay.uniform(18,65,int(faint.sum()));full=np.zeros((H,W));full[faint]=intens
    bg[faint & art_ink]=np.minimum(255,bg[faint & art_ink]+full[faint & art_ink])
    bg=Image.fromarray(np.uint8(np.clip(bg,0,255))).filter(ImageFilter.GaussianBlur(radius=.32*scale))
    return rgb, np.asarray(bg), records''')
ns=dict(g.__dict__);exec(src,ns)
def paired(dpi,page):
 scan,bg,records=ns['make_page'](dpi,page);original=np.asarray(Image.open(R/f'qualification/experiments/m1g/fixture/dpi{dpi}/input/page{page:02}.png').convert('RGB'));assert np.array_equal(scan,original),'source replay mismatch';return bg,records

def image(pdf,arr):
 im=pikepdf.Stream(pdf,zlib.compress(arr.tobytes(),6));im.Type=pikepdf.Name.XObject;im.Subtype=pikepdf.Name.Image;im.Width=arr.shape[1];im.Height=arr.shape[0];im.ColorSpace=pikepdf.Name.DeviceGray;im.BitsPerComponent=8;im.Filter=pikepdf.Name.FlateDecode;return im

def compose(source,out,bg,patches,pi=0):
 original=pikepdf.open(source);pdf=pikepdf.Pdf.new();pdf.pages.append(original.pages[pi]);page=pdf.pages[0];ops=pikepdf.unparse_content_stream([i for i in pikepdf.parse_content_stream(page) if str(i.operator)!='Do']);page.Resources.XObject=pikepdf.Dictionary();prefix=b'';w,h=map(float,[page.MediaBox[2],page.MediaBox[3]])
 for n,(arr,bb) in enumerate([(bg,[0,0,w,h])]+patches):
  name='/Bg'+str(n);page.Resources.XObject[name]=image(pdf,arr);x,y,ww,hh=bb;prefix+=f'q {ww} 0 0 {hh} {x} {y} cm {name} Do Q\n'.encode()
 at=ops.find(b'BT');assert at>=0;page.Contents=pikepdf.Stream(pdf,ops[:at]+prefix+ops[at:]);pdf.save(out)

def run():
 d=B/'stage-a';d.mkdir(exist_ok=True);dpi=300;bg,recs=paired(dpi,0);Image.fromarray(bg).save(d/'counterfactual-paper.png');base=B/'300';pdf=pikepdf.open(base/'previous.pdf');out=pikepdf.Pdf.new();out.pages.append(pdf.pages[0]);out.save(d/'A0.pdf')
 audit=json.loads((base/'previous/audit.json').read_text());vectors={r['symbol'] for r in audit['placements'] if r['page']==0};source=np.asarray(Image.open(R/'qualification/experiments/m1g/fixture/dpi300/input/page00.png').convert('L'));patches=[]
 report=json.loads((base/'previous.json').read_text())['page_reports'][0];observations={o['symbol_id']:o for o in report['reconstruction']['observations']};surface=bg.copy()
 for r in recs:
  if r['id'] in vectors or not r['text'].strip():continue
  if r['id'] in observations:
   x0,y0,x1,y1=map(int,observations[r['id']]['bbox_px']);x0=max(0,x0-2);y0=max(0,y0-2);x1=min(1800,x1+2);y1=min(900,y1+2)
  else:x0,y0,x1,y1=map(int,r['bbox'])
  surface[y0:y1,x0:x1]=source[y0:y1,x0:x1]
 # Keep the existing native-resource footprints. Only printed ink changes;
 # the true no-text replay already retains the exact degraded artwork.
 for p in report['patches'][1:]:
  x0,y0,x1,y1=map(int,p['bbox_px']);assert p['w']==x1-x0 and p['h']==y1-y0
  patches.append((surface[y0:y1,x0:x1],[x0*.24,(900-y1)*.24,(x1-x0)*.24,(y1-y0)*.24]))
 for arm,size in [('A1-native',(1800,900)),('A1',(900,450))]:compose(base/'previous.pdf',d/(arm+'.pdf'),np.asarray(Image.fromarray(bg).resize(size,Image.Resampling.LANCZOS)),patches)
 for arm in ['A0','A1-native','A1']:
  p=d/(arm+'.pdf');doc=pdfium.PdfDocument(p)
  for zoom in [1,8,16]:doc[0].render(scale=math.nextafter(zoom,0)).to_pil().save(d/f'{arm}-{zoom*100}pct.png')
 print('paired scan replay is pixel-identical; counterfactual paper saved')
if __name__=='__main__':run()
