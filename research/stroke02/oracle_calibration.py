"""Calibrate a PDF-render/reblur oracle against simulated noise and JPEG."""
import io,json,pathlib,sys
import numpy as np
from scipy import ndimage as ndi
from PIL import Image
import fitz,pypdfium2 as pdfium
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent))
import crop_fit as c
O=c.O
profiles=json.loads((O/'joint-profiles.json').read_text());rng=np.random.default_rng(341108)
# PDF contains an annular stroke and a separate bar, with known painted colors.
doc=fitz.open();page=doc.new_page(width=40,height=32);page.draw_rect(page.rect,fill=(.88,.88,.88),color=None);page.draw_oval(fitz.Rect(8,5,22,26),fill=(.28,.28,.28),color=None);page.draw_oval(fitz.Rect(12,9,18,22),fill=(.88,.88,.88),color=None);page.draw_rect(fitz.Rect(28,7,31,25),fill=(.28,.28,.28),color=None)
im=np.asarray(pdfium.PdfDocument(doc.tobytes())[0].render(scale=2).to_pil().convert('RGB'));base=c.st.linear(im).reshape(32,2,40,2,3).mean((1,3));luma=base@np.array([.2126,.7152,.0722]);out={}
for key,regions in profiles.items():
 out[key]=[]
 for region in regions:
  noise=region['noise_linear_mad'];case=[]
  for sigma in [.3,.5,.7,.93]:
   clean=ndi.gaussian_filter(luma,sigma,mode='nearest');errs=[]
   for _ in range(40):
    noisy=np.clip(clean+rng.normal(0,noise,clean.shape),0,1);srgb=c.st.srgb(np.repeat(noisy[...,None],3,axis=2));buf=io.BytesIO();Image.fromarray(srgb).save(buf,format='JPEG',quality=95,subsampling=0);buf.seek(0);observed=c.st.linear(np.asarray(Image.open(buf).convert('RGB')))@np.array([.2126,.7152,.0722]);errs.append(float(np.sqrt(np.mean((clean-observed)**2))))
   case.append({'sigma':sigma,'oracle_rmse_median':float(np.median(errs)),'oracle_rmse_p95':float(np.quantile(errs,.95))})
  out[key].append({'bbox':region['bbox'],'noise_sd_assumed':noise,'jpeg_quality':95,'simulations':40,'cases':case})
(O/'oracle-calibration.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
