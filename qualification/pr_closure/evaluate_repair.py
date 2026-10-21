"""Evaluator-only pristine reference; exact physical placement, no glyph alignment."""
from pathlib import Path
import json,subprocess,math,io,sys,tempfile
import numpy as np,pypdfium2 as pdfium,pikepdf
from PIL import Image
from fontTools.ttLib import TTFont
R=Path(__file__).resolve().parents[2];B=Path(__file__).resolve().parent;D=R/'qualification/evidence/m1d_reconstruction';F=R/'qualification/fixtures/m1d_damage';sys.path.insert(0,str(R/'qualification'));from tools_env import qpdf_bin,qpdf_env,ots_bin
pos=json.loads((F/'positions.json').read_text());rec=next(x for x in pos['observations'] if x['id']=='s00');x0,y0,x1,y1=map(int,rec['bbox']);box=np.s_[y0:y1,x0:x1];source=np.asarray(Image.open(F/'source.png').convert('L'));truth=np.asarray(Image.open(R/'qualification/evaluator/m1d_damage_ground_truth.png').convert('L'))
def iou(a,b):return float((a&b).sum()/max(1,(a|b).sum()))
rows=[]
for renderer in ['poppler','pdfium']:
 row={'renderer':renderer,'source_to_pristine_iou':iou(source[box]<128,truth[box]<128)}
 for arm in ['faithful','clearscan']:
  p=D/(arm+'.pdf')
  if renderer=='poppler':
   prefix=B/(arm+'-poppler');subprocess.run(['pdftoppm','-singlefile','-r','300','-png',str(p),str(prefix)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);a=np.asarray(Image.open(str(prefix)+'.png').convert('L'))
  else:
   page=pdfium.PdfDocument(str(p))[0];pw,ph=page.get_size();scale=math.nextafter(min(300/72,source.shape[1]/pw,source.shape[0]/ph),0);row['pdfium_effective_dpi']=scale*72;a=np.asarray(page.render(scale=scale).to_pil().convert('L'))
  assert a.shape==source.shape,(renderer,a.shape,source.shape)
  row[arm+'_to_pristine_iou']=iou(a[box]<128,truth[box]<128);row[arm+'_to_source_iou']=iou(a[box]<128,source[box]<128)
 assert row['clearscan_to_pristine_iou']>row['source_to_pristine_iou'],row
 rows.append(row)
valid=[]
for arm in ['faithful','clearscan']:
 path=D/(arm+'.pdf');doc=pdfium.PdfDocument(str(path));tp=doc[0].get_textpage();txt=tp.get_text_range();assert tp.search('e').get_next() is not None
 row={'arm':arm,'native_text':txt,'poppler_text':subprocess.check_output(['pdftotext','-raw',str(path),'-']).decode(),'qpdf_status':subprocess.run([qpdf_bin(),'--check',str(path)],env=qpdf_env(),capture_output=True).returncode,'fonts':[]};q=pikepdf.open(path)
 for obj in q.objects:
  if isinstance(obj,pikepdf.Dictionary) and '/FontFile2' in obj:
   data=obj.FontFile2.read_bytes();f=TTFont(io.BytesIO(data))
   with tempfile.TemporaryDirectory(prefix='scanweave-closure-font-') as folder:
    tmp=Path(folder)/'font.ttf';tmp.write_bytes(data);row['fonts'].append({'glyphs':f['maxp'].numGlyphs,'ots_status':subprocess.run([ots_bin(),str(tmp)],capture_output=True).returncode})
 valid.append(row)
assert valid[0]['native_text']==valid[1]['native_text']
out={'comparison':rows,'validity_search':valid,'old_evaluator_failure':'faithful-to-source IoU is not necessarily larger than repaired-to-source IoU under source-patch sampling; old assertion retained and its failure logged, not weakened','note':'This evaluator reads pristine truth; the converter does not.'};(B/'repair-evaluation.json').write_text(json.dumps(out,indent=2));print(rows)
