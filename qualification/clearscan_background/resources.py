"""Encoded byte attribution by emitted resource; mixed resources stay mixed."""
import json,hashlib,io
from pathlib import Path
from collections import defaultdict,Counter
import pikepdf
from compare import accounting
B=Path(__file__).resolve().parent
sha=lambda a:hashlib.sha256(a).hexdigest()
def intersects(a,b):return max(a[0],b[0])<min(a[2],b[2]) and max(a[1],b[1])<min(a[3],b[3])
def font_text(pdf):
 fonts=set();ops=[]
 for page in pdf.pages:
  for f in page.Resources.Font.values():
   fd=f.get('/DescendantFonts',[f])[0].get('/FontDescriptor',{});stream=fd.get('/FontFile2')
   if stream is not None:fonts.add(sha(stream.read_bytes()))
  mode=0;row=[]
  for ins in pikepdf.parse_content_stream(page):
   op=str(ins.operator)
   if op in ['Tf','Tr','Tm','Tj','BDC','EMC']:row.append(str(ins))
  ops.append(sha('\n'.join(row).encode()))
 return {'font_program_sha256':sorted(fonts),'text_and_placement_operations_sha256':ops}
rows=[]
for dpi in [300,600]:
 identities={}
 for arm in ['previous','final','adobe']:
  path=B/str(dpi)/(arm+'.pdf');pdf=pikepdf.open(path);m=accounting(path);identities[arm]=font_text(pdf);classes=defaultdict(set);objects={};placements=[]
  report=json.loads((B/str(dpi)/(arm+'.json')).read_text()) if arm!='adobe' else None
  for pi,page in enumerate(pdf.pages):
   patches=report['page_reports'][pi]['patches'] if report else []
   regs=report['page_reports'][pi]['regions'] if report else []
   fall=[r['bbox_px'] for r in regs if isinstance(r['disposition'],dict) and 'Raster' in r['disposition']]
   vec=[r['bbox_px'] for r in regs if r['disposition']=='Vector']
   for name,x in page.Resources.get('/XObject',{}).items():
    if x.get('/Subtype')!='/Image':continue
    key=str(x.objgen);objects[key]=len(x.read_raw_bytes());im=pikepdf.PdfImage(x).as_pil_image().convert('RGB');hash=sha(im.tobytes());matches=[p for p in patches if p['w']==int(x.Width) and p['h']==int(x.Height) and p['rgb_sha256']==hash]
    if arm=='adobe':cat='adobe_raster';bb=None
    elif str(name)=='/Im0' and int(x.Width)<1800*dpi//300:cat='paper_background';bb=patches[0]['bbox_px']
    else:
     assert matches,(dpi,arm,pi,name,'native resource not matched to report')
     bb=matches[0]['bbox_px'];roles=[]
     if pi==0 and intersects(bb,[1360*dpi/300,680*dpi/300,1670*dpi/300,825*dpi/300]):roles.append('artwork')
     if any(intersects(bb,b) for b in fall):roles.append('fallback')
     if any(intersects(bb,b) for b in vec):roles.append('vector_surroundings')
     cat='native_'+'_and_'.join(roles) if roles else 'native_other_unknown'
    classes[key].add(cat);placements.append({'page':pi,'name':str(name),'object':key,'class':cat,'bbox':bb,'width':int(x.Width),'height':int(x.Height),'bytes':objects[key]})
  totals=Counter()
  for key,cats in classes.items():totals['+'.join(sorted(cats))]+=objects[key]
  assert sum(totals.values())==m['streams']['raster']
  row={'dpi':dpi,'arm':arm,'accounting':{k:v for k,v in m.items() if k!='images'},'resource_class_bytes':dict(totals),'images':placements,'font_text':identities[arm]};rows.append(row)
 for row in rows:
  if row['dpi']==dpi and row['arm']=='final':
   row['same_font_program_as_previous']=identities['final']['font_program_sha256']==identities['previous']['font_program_sha256'];row['same_text_and_placements_as_previous']=identities['final']['text_and_placement_operations_sha256']==identities['previous']['text_and_placement_operations_sha256'];assert row['same_font_program_as_previous'] and row['same_text_and_placements_as_previous']
(B/'resources.json').write_text(json.dumps({'method':__doc__,'note':'Bytes belong to serialized resources. Native mixed rectangles include paper too; no entropy bytes are invented for individual pixel meanings. vector_surroundings is geometric overlap, not proof all its pixels are obsolete.','documents':rows},indent=2));print([(r['dpi'],r['arm'],r['resource_class_bytes']) for r in rows])
