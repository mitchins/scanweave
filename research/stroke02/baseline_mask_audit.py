"""Audit #39's recorded prototype clones against original source foreground."""
import json,pathlib
import numpy as np
from PIL import Image
B=pathlib.Path('/data/coding/scanweave/work/books01');key='12342014';run=json.loads((B/'phase2/runs'/key/'runs.json').read_text());report=json.loads(pathlib.Path(run['rows']['sw-E']['path']+'.json').read_text())['conversion']['page_reports'][0];rgb=np.asarray(Image.open(B/'stroke02/native'/f'{key}-000.png').convert('RGB'));lum=rgb@np.array([.2126,.7152,.0722]);fg=np.abs(lum-report['polarity_paper_luminance'])>60;found=[]
for entry in report['reconstruction']['canonical_geometry']:
 a,b,d,e=map(int,entry['witness_bbox_px']);mask=np.array(entry['mask'],bool).reshape(entry['height'],entry['width']);global_mask=fg[b:e,a:d]
 if global_mask.shape!=mask.shape:continue
 added=int((mask&~global_mask).sum())
 if added:found.append({'symbol_id':entry['witness_symbol_id'],'outside_global_foreground':added})
out={'page':key,'prototype_entries':len(report['reconstruction']['canonical_geometry']),'entries_with_added_pixels':len(found),'added_pixel_occurrences':sum(x['outside_global_foreground'] for x in found),'entries':found,'scope':'recorded Otsu-refined prototype clones; repeated witnesses may occur; these are not mutations of owned-unit masks'}
pathlib.Path(__file__).with_name('baseline-mask-audit.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({k:v for k,v in out.items() if k!='entries'},indent=2))
