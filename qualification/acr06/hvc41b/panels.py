import pathlib,json,hashlib
from PIL import Image,ImageDraw,ImageFont
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41b';O=R/'local/hvc41b/panels';O.mkdir(parents=True,exist_ok=True);idx=[]
for page in (1,3,4):
 a=json.loads((E/f'admission-ledger-{page:02}.json').read_text());shape=E/f'p{page}-shape-colour.json';diag={x['symbol']:x for x in json.loads(shape.read_text())} if shape.exists() else {};src=Image.open(R/'local/ink33r/renders/historical'/f'{page:02}-source.png').convert('RGB');baseline=Image.open(R/'local/ink33r/renders/historical'/f'{page:02}-scanweave.png').convert('RGB')
 for i,x in enumerate(a):
  x0,y0,x1,y1=map(int,x['bbox']);pad=12;box=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad));parts=[]
  for im in (src,baseline,baseline):
   crop=im.crop(box);reading=crop.resize((max(1,round(crop.width*.32)),max(1,round(crop.height*.32))),Image.Resampling.LANCZOS);enlarged=reading.resize((reading.width*4,reading.height*4),Image.Resampling.NEAREST);parts.append((reading,enlarged))
  cw=max(p[1].width for p in parts)+8;rh=max(p[0].height for p in parts);eh=max(p[1].height for p in parts);sheet=Image.new('RGB',(cw*3,rh+eh+50),'white');draw=ImageDraw.Draw(sheet)
  for j,((read,big),name) in enumerate(zip(parts,('source','current #39','retained candidate'))):
   sheet.paste(read,(j*cw+4,26));sheet.paste(big,(j*cw+4,36+rh));draw.text((j*cw+4,2),name,fill='black')
  f=O/f'p{page:02}-{i+1:04}.png';sheet.save(f);h=hashlib.sha256(f.read_bytes()).hexdigest();d=diag.get(x['symbol']);x['shape_proxy_iou_pre_font']=d.get('shape_proxy_iou') if d else None;x['paint_outside_expanded_box_proxy']=d.get('painted_pixels_outside_expanded_bbox') if d else None;x['global_vs_local_luma_abs']=d.get('global_vs_local_luma_abs') if d else None;x['page_vs_local_luma_abs']=d.get('page_vs_local_luma_abs') if d else None;x['residual_check']='not applicable: original baseline retained, no vector emitted or source suppression performed';x['outcome']='rejected: frozen region admission' if not x['region_admitted'] else 'not emitted: independent glyph validation incomplete';x['panel']=str(f);x['panel_sha256']=h;idx.append({'page':page,'symbol':x['symbol'],'path':str(f),'sha256':h,'outcome':x['outcome']})
 (E/f'ledger-{page:02}.json').write_text(json.dumps(a,indent=2)+'\n')
 print('page',page,'panels',len(a),flush=True)
(E/'panel-index.json').write_text(json.dumps(idx,indent=2)+'\n')
