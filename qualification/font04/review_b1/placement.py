import sys, json, numpy as np, pypdfium2 as pdfium
from pathlib import Path
from scipy import ndimage
R=Path('qualification/font04/local'); art=R/'financial-experimental-v2.pdf.font04'
snap=json.loads((art/'source.json').read_text()); plan=json.loads((art/'plan.json').read_text())
acc={r['member'] for r in plan['assignments']}
K=4
def an(path,page):
    d=pdfium.PdfDocument(str(path)); b=d[page].render(scale=300*K/72,grayscale=True); a=np.asarray(b.to_pil().convert('L'),dtype=np.float32)
    h,w=a.shape; return 1-a[:h//K*K,:w//K*K].reshape(h//K,K,w//K,K).mean((1,3))/255
def err(a,b): return float(((a-b)**2).sum()/max(1.,np.maximum(a,b).sum()))
def best_shift(src,img):
    best=(err(src,img),0,0)
    for dy in np.arange(-1.5,1.51,0.25):
        for dx in np.arange(-1.5,1.51,0.25):
            s=ndimage.shift(img,(dy,dx),order=1,mode='constant'); e=err(src,s)
            if e<best[0]: best=(e,dx,dy)
    return best
out=[]
for page in range(13):
    rows=[r for r in snap['rows'] if r['page']==page and r['source'] is not None and r['index'] in acc]
    if not rows: continue
    S_=an(R/'financial-source-owned.pdf',page); A=an(R/'financial-default-isolated-e.pdf',page); B=an(R/'financial-experimental-isolated-e.pdf',page)
    for r in rows:
        x0,y0,x1,y1=map(int,r['source']['bbox']); sl=(slice(y0-4,y1+4),slice(x0-4,x1+4))
        s,a,b=S_[sl],A[sl],B[sl]
        ca=np.array(ndimage.center_of_mass(a))-ndimage.center_of_mass(s); cb=np.array(ndimage.center_of_mass(b))-ndimage.center_of_mass(s)
        ea=best_shift(s,a); eb=best_shift(s,b)
        # bbox of ink >0.5 : width/height ratios
        def wh(m):
            ys,xs=np.nonzero(m>0.5); return (xs.max()-xs.min()+1, ys.max()-ys.min()+1) if len(xs) else (0,0)
        out.append(dict(member=r['index'],page=page,err_a=err(s,a),err_b=err(s,b),shift_a=ea,shift_b=eb,cen_a=ca.tolist(),cen_b=cb.tolist(),wh_s=wh(s),wh_a=wh(a),wh_b=wh(b),mass=(float(s.sum()),float(a.sum()),float(b.sum()))))
    print(page,file=sys.stderr,flush=True)
json.dump(out,open(sys.argv[0]+".json","w"),default=float)
o=out
f=lambda k:np.array([x[k] for x in o])
print('n',len(o))
print('raw err default %.4f exp %.4f'%(f('err_a').mean(),f('err_b').mean()))
print('best-translation err default %.4f exp %.4f'%(np.mean([x['shift_a'][0] for x in o]),np.mean([x['shift_b'][0] for x in o])))
cb=np.array([x['cen_b'] for x in o]); ca=np.array([x['cen_a'] for x in o])
print('centroid offset vs source (dy,dx) default mean %s sd %s | exp mean %s sd %s'%(ca.mean(0).round(3),ca.std(0).round(3),cb.mean(0).round(3),cb.std(0).round(3)))
ws=np.array([x['wh_s'] for x in o],float); wa=np.array([x['wh_a'] for x in o],float); wb=np.array([x['wh_b'] for x in o],float)
print('ink bbox (w,h) ratio to source: default %s exp %s'%((wa/ws).mean(0).round(3),(wb/ws).mean(0).round(3)))
m=np.array([x['mass'] for x in o]); print('mass ratio default %.3f exp %.3f'%((m[:,1]/m[:,0]).mean(),(m[:,2]/m[:,0]).mean()))
