import json,pathlib,numpy as np
from PIL import Image
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06'); E=R/'hvc41d'; rows=json.loads((E/'calibration-exploratory.json').read_text())['rows']; out=[]
for i,r in enumerate(rows):
 a=np.asarray(Image.open(r['panel']).convert('L'))[::4,::4];cw=a.shape[1]//4;x0,y0,x1,y1=map(int,r['ocr_box']);w=x1-x0+6;h=y1-y0+6;ref=a[20:20+h,2*cw:2*cw+w]>128;font=a[20:20+h,3*cw:3*cw+w]>128
 # quantify source enclosed paper, allowing a one-pixel gap from its boundary
 holes=nd.binary_fill_holes(ref)&~ref; fh=nd.binary_fill_holes(font)&~font
 out.append({'index':i,'source_hole_pixels':int(holes.sum()),'font_hole_pixels':int(fh.sum()),'source_holes_covered_by_font':int((holes & font).sum()),'source_holes_covered_if_filled':int((holes & nd.binary_fill_holes(font)).sum()),'source_hole_regions':int(nd.label(holes)[1]),'font_hole_regions':int(nd.label(fh)[1])})
(E/'topology-diagnostic.json').write_text(json.dumps(out,indent=2)+'\n')
for i in [27,74,155,221]:print(rows[i]['control'],rows[i]['char_ocr_unverified'],out[i])
