"""Apply a source-mask-limited white patch to the Type 3 control overlay; audit streams."""
import pathlib,pikepdf,io,json,hashlib,numpy as np
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41d';E=R/'hvc41d';origin=R/'local/hvc41b/controls/control/white/baseline.pdf';srcpdf=pikepdf.open(R/'local/ink37/controls/white.pdf');im=next(o for o in srcpdf.pages[0].Resources.XObject.values() if str(o.get('/Subtype'))=='/Image');src=np.asarray(Image.open(io.BytesIO(im.read_raw_bytes())).convert('RGB'));srcpdf.close()
a,b,c,d=718,359,746,396;lum=src[b:d,a:c].astype(float)@np.array([.2126,.7152,.0722]);mask=lum<128;pdf=pikepdf.open(L/'type3-control.pdf');pg=pdf.pages[0];pw=float(pg.MediaBox[2]);ph=float(pg.MediaBox[3]);sx=pw/src.shape[1];sy=ph/src.shape[0];ops=['q 1 1 1 rg']
for y,row in enumerate(mask):
 padded=np.pad(row.astype(np.int8),(1,1));starts=np.where(np.diff(padded)==1)[0];ends=np.where(np.diff(padded)==-1)[0]
 for x0,x1 in zip(starts,ends):ops.append(f'{(a+x0)*sx:.8f} {ph-(b+y+1)*sy:.8f} {(x1-x0)*sx:.8f} {sy:.8f} re')
ops.append('f Q');patch=pdf.make_stream(('\n'.join(ops)).encode());pg.Contents=pikepdf.Array([pg.Contents[0],patch,pg.Contents[1]]);out=L/'patch-control.pdf';pdf.save(out);pdf.close()
def streams(path):
 pdf=pikepdf.open(path);res={str(k):hashlib.sha256(v.read_raw_bytes()).hexdigest() for k,v in pdf.pages[0].Resources.XObject.items() if str(v.get('/Subtype'))=='/Image'};pdf.close();return res
j={'source_box_px':[a,b,c,d],'patched_pixel_count':int(mask.sum()),'pdf_sha256':hashlib.sha256(out.read_bytes()).hexdigest(),'baseline_image_streams_equal':streams(origin)==streams(out)};(E/'patch-control-probe.json').write_text(json.dumps(j,indent=2)+'\n');print(j)
