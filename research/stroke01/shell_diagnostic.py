"""Reference colour on the 613 illustration; not part of the text model."""
import json, pathlib
import numpy as np
from PIL import Image
B=pathlib.Path('/data/coding/scanweave/work/books01/stroke01')
source=np.asarray(Image.open(B/'native/8967062-000.png').convert('RGB').crop((1080,370,1300,730)))
luminance=source @ np.array([.2126,.7152,.0722]);cut=float(np.percentile(luminance,10));selected=source[luminance<=cut]
result={'bbox_source':[1080,370,1300,730],'description':'median RGB of darkest 10% observed shell ROI; illustration is multicoloured and this is not a fitted physical ink colour','median_rgb':np.median(selected,axis=0).tolist(),'luma_cut':cut,'samples':int(len(selected))}
(B/'corrected/shell-reference.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
