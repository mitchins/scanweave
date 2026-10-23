"""Audit detached raw-source halo components before the fitting ownership mask."""
from pathlib import Path
import json,sys,os
import numpy as np,pikepdf,pypdfium2 as pdfium
from qualification.font04.class_metrics import crop_render
from qualification.font04.owned_ink import components

def main(path):
 art=Path(str(path)+'.font04');rows=json.loads((art/'source.json').read_text())['rows'];plan=json.loads((art/'plan.json').read_text());geometry=json.loads(Path('qualification/font04/local/financial-default.pdf.json').read_text())['pages'];pdfpath=art/'raw-owned-source.pdf'
 with pikepdf.open('qualification/font04/local/financial-default.pdf') as original:
  pdf=pikepdf.Pdf.new()
  for row in rows:
   pdf.pages.append(original.pages[row['page']]);page=pdf.pages[-1];s=row['source'];commands='';page.Resources=pikepdf.Dictionary()
   if s is not None:
    w,h=s['width'],s['height'];halo=np.array(s['halo'],float).reshape(h+4,w+4);owned=np.pad(np.array(s['mask'],bool).reshape(h,w),2);paper=float(np.quantile(halo[~owned],.8));ink=float(np.quantile(halo[owned],.15));cov=np.clip((paper-halo)/max(1,paper-ink),0,1);pixels=np.round((1-cov)*255).astype('uint8');hh,ww=pixels.shape;g=geometry[row['page']];sx=g['width_pt']/g['raster_width'];sy=g['height_pt']/g['raster_height'];x,y=s['bbox'][:2];obj=pdf.make_stream(pixels.tobytes());obj.Type=pikepdf.Name.XObject;obj.Subtype=pikepdf.Name.Image;obj.Width=ww;obj.Height=hh;obj.ColorSpace=pikepdf.Name.DeviceGray;obj.BitsPerComponent=8;page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(I=obj));commands=f'q {ww*sx:.12f} 0 0 {hh*sy:.12f} {(x-2)*sx:.12f} {g["height_pt"]-(y-2+hh)*sy:.12f} cm /I Do Q\n'
   page.Contents=pdf.make_stream(commands.encode())
  pdf.save(pdfpath,deterministic_id=True)
 reference=Path(str(os.environ.get('FONT04_RAW_DEFAULT_REFERENCE',str(path)))+'.font04')
 paths={n:(pdfpath if n=='source' else (reference if n=='default' else art)/f'class-isolated-{n}.pdf') for n in ['source','default','candidate']}
 docs={n:pdfium.PdfDocument(p) for n,p in paths.items()};ledger=[]
 for a in plan['assignments']:
  i=a['member'];r=rows[i];x,y,xx,yy=map(int,r['source']['bbox']);b=[x-4,y-4,xx+4,yy+4];v={n:crop_render(paths[n],d,i,b,'analytic') for n,d in docs.items()};cc=components(v['source'],v['default'],v['candidate'],i)
  for c in cc:c.update(character=r['character'],page=r['page'],id=r['id'])
  ledger.extend(cc)
 for d in docs.values():d.close()
 fired=sorted({c['member'] for c in ledger if c['fires']});out=dict(source=str(path),fired=fired,components=ledger,reference='Unmasked normalized source halo; current-draw coverage still establishes reproduced ownership. Diagnostic audit.')
 (art/'raw-owned-audit.json').write_text(json.dumps(out,separators=(',',':'))+'\n');print('raw halo owned fires',len(fired),fired)

if __name__=='__main__':main(Path(sys.argv[1]))
