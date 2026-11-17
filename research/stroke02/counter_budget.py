"""Compare actual PDF-rendered 6-counter pixels with source and local noise."""
import json,pathlib,sys
import numpy as np
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent));import crop_fit as c
B,O=c.B,c.O;key='8967062';run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());d=O/'pages-extensions'/key;res=json.loads(pathlib.Path('/tmp/scanweave-books01/qualification/books01/phase2/results.json').read_text())['pages'][run['id']]['rows'];box=(1176,758,1196,782);dpi=run['dpi'];L=np.array([.2126,.7152,.0722]);images={}
for name,path,geom in [('source',run['rows']['src']['path'],None),('baseline',run['rows']['sw-E']['path'],res['sw-E']['geometry']),('candidate',d/'candidate.pdf',res['sw-E']['geometry'])]:
 im=np.asarray(c.pdf_crop(path,key,box,dpi,2,geom).convert('RGB'));h=box[3]-box[1];w=box[2]-box[0];images[name]=c.st.linear(im[:h*2,:w*2]).reshape(h,2,w,2,3).mean((1,3))@L
source=images['source'];noise=json.loads((O/'joint-profiles.json').read_text())[key][0]['noise_linear_mad'];paper=float(np.quantile(source,.9));counter=source[773-758:776-758,1182-1176:1185-1176];near=paper-counter<=2*noise
out={'box':box,'counter_bbox':[1182,773,1185,776],'paper_luma_p90':paper,'noise_proxy_linear':noise,'counter_source_luma':counter.tolist(),'near_paper_count':int(near.sum())}
for name in ('baseline','candidate'):
 pred=images[name][773-758:776-758,1182-1176:1185-1176];delta=counter-pred;out[name]={'counter_luma':pred.tolist(),'mean_darkening':float(delta.mean()),'max_darkening':float(delta.max()),'near_paper_exceeds_two_noise':int(np.sum((delta>2*noise)&near)),'difference_from_baseline_mean':float(np.mean(np.abs(images[name]-images['baseline'])))}
(d/'counter-budget.json').write_text(json.dumps(out,indent=2));print(json.dumps(out,indent=2))
