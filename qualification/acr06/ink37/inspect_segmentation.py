from pathlib import Path
from PIL import Image
import numpy as np, json
base=Path('/data/coding/scanweave/qualification/acr06')
rows=[]
for doc in ('historical','financial','mixed','receipts','forms'):
    for path in sorted((base/'local/ink33/renders'/doc).glob('*-source.png')):
        a=np.asarray(Image.open(path).convert('RGB'))
        h,w=a.shape[:2]
        corners=[]
        for x,y in ((0,0),(w-6,0),(0,h-6),(w-6,h-6)):
            corners.append(np.sort(a[y:y+6,x:x+6].reshape(-1,3),axis=0)[18].astype(int))
        paper=np.sort(np.array(corners),axis=0)[2]
        lum=a[:,:,0].astype(float)*.2126+a[:,:,1]*.7152+a[:,:,2]*.0722
        pl=paper@np.array([.2126,.7152,.0722])
        mask=np.abs(lum-pl)>60
        fg=a[mask]
        ink=np.partition(fg, len(fg)//2, axis=0)[len(fg)//2].astype(int) if len(fg) else paper
        interior=lum[h//10:9*h//10,w//10:9*w//10]
        hist=np.bincount(np.clip((interior/8).astype(int).ravel(),0,31),minlength=32)
        peak=int(hist.argmax())
        sample=a[h//10:9*h//10,w//10:9*w//10][(interior>=peak*8)&(interior<(peak+1)*8)]
        mode=np.median(sample,axis=0).astype(int)
        mode_lum=mode@np.array([.2126,.7152,.0722])
        alt=np.abs(lum-mode_lum)>60
        rows.append({'document':doc,'page':int(path.name[:2]),'size':[w,h], 'corner_paper':paper.tolist(),'foreground_ink':ink.tolist(),'corner_foreground_pixels':int(mask.sum()),'interior_mode_rgb':mode.tolist(),'interior_mode_luminance_bin':[peak*8,peak*8+7],'interior_mode_fraction':round(float(hist[peak]/interior.size),6),'hypothetical_mode_foreground_pixels':int(alt.sum()),'hypothetical_mask_changed_pixels':int(np.count_nonzero(mask!=alt))})
(base/'ink37/segmentation-investigation.json').write_text(json.dumps(rows,indent=2)+'\n')
