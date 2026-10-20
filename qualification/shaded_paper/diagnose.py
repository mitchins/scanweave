"""Fixed development page; source pixels are never changed for conversion."""
from pathlib import Path
import json,numpy as np,pikepdf
from PIL import Image,ImageDraw
B=Path(__file__).resolve().parent;R=B.parents[1]
p=pikepdf.open(R/'qualification/pdf_packaging/real/input/history-02.pdf');im=pikepdf.PdfImage(next(iter(p.pages[0].Resources.XObject.values()))).as_pil_image().convert('RGB');a=np.asarray(im);g=np.round(a@np.array([.2126,.7152,.0722])).astype(np.uint8);h,w=g.shape
patches=[a[:6,:6],a[:6,-6:],a[-6:,:6],a[-6:,-6:]];corners=np.array([np.sort(x.reshape(-1,3),axis=0)[18] for x in patches]);paper=np.sort(corners,axis=0)[2];global_fg=np.abs(a@np.array([.2126,.7152,.0722])-paper@np.array([.2126,.7152,.0722]))>60
T=128;nx=(w+T-1)//T;ny=(h+T-1)//T;grid=np.zeros((ny,nx))
for y in range(ny):
 for x in range(nx):
  v=np.sort(g[y*T:min(h,(y+1)*T),x*T:min(w,(x+1)*T)].ravel());grid[y,x]=v[(len(v)*90+99)//100-1]
gx=np.clip((np.arange(w)+.5)/T-.5,0,nx-1);gy=np.clip((np.arange(h)+.5)/T-.5,0,ny-1);xx=gx.astype(int);yy=gy.astype(int);fx=gx-xx;fy=gy-yy
field=(grid[yy[:,None],xx]*(1-fx)+grid[yy[:,None],np.minimum(xx+1,nx-1)]*fx)*(1-fy[:,None])+(grid[np.minimum(yy+1,ny-1)[:,None],xx]*(1-fx)+grid[np.minimum(yy+1,ny-1)[:,None],np.minimum(xx+1,nx-1)]*fx)*fy[:,None]
residual=field-g;fg=residual>60
# Fixed visually inspected regions, not pixel-perfect truth or held-out labels.
regions={'dark_outer_margin':[1460,300,1650,2100],'unprinted_top_paper':[300,230,1100,320],'printed_text_and_interline':[220,410,1140,1300],'showthrough_and_spots':[240,1330,1100,1510]}
measure={}
for name,(x0,y0,x1,y1) in regions.items():
 measure[name]={'bbox_px':[x0,y0,x1,y1],'global_foreground_fraction':float(global_fg[y0:y1,x0:x1].mean()),'candidate_foreground_fraction':float(fg[y0:y1,x0:x1].mean()),'median_gray':float(np.median(g[y0:y1,x0:x1]))}
out={'page_size':[w,h],'paper_corner_rgb':paper.tolist(),'page_median_gray':float(np.median(g)),'global_foreground_fraction':float(global_fg.mean()),'candidate_foreground_fraction':float(fg.mean()),'regions':measure,'note':'region fractions measure classification, not character accuracy'}
(B/'illumination.json').write_text(json.dumps(out,indent=2))
ims=[('Original',im),('Current foreground',Image.fromarray(np.uint8(global_fg)*255)),('Local paper',Image.fromarray(np.uint8(np.clip(field,0,255)))),('Ink confidence',Image.fromarray(np.uint8(np.clip(residual/120,0,1)*255))),('Candidate foreground',Image.fromarray(np.uint8(fg)*255))]
sheet=Image.new('RGB',(1600,2300),'white')
for i,(name,im) in enumerate(ims):
 im=im.convert('RGB');im.thumbnail((520,1080));x=(i%3)*530;y=(i//3)*1140;sheet.paste(im,(x,y+25));ImageDraw.Draw(sheet).text((x+5,y+5),name,fill='black')
sheet.save(B/'illumination.png')
# Reproducible background/foreground source evidence.
Image.fromarray(np.uint8(fg)*255).save(B/'candidate-mask.png');Image.fromarray(np.uint8(field)).save(B/'paper-estimate.png')
print(json.dumps(out,indent=2))
