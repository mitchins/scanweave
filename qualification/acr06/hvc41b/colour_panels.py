import json,pathlib,random,hashlib
import pypdfium2 as pdfium
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');L=R/'local/hvc41b';E=R/'hvc41b';O=L/'colour-panels';O.mkdir(parents=True,exist_ok=True);rows=json.loads((E/'p3-shape-colour.json').read_text());indices=list(range(len(rows)));worst=sorted(indices,key=lambda i:rows[i].get('global_vs_local_luma_abs',0),reverse=True)[:10];rand=indices[:];random.Random(4103).shuffle(rand);selected=worst+[i for i in rand if i not in worst][:10];docs=[pdfium.PdfDocument(str(L/f'p3-{mode}-tiles.pdf')) for mode in ('shape','global','page','local')];src=Image.open(R/'local/ink33r/renders/historical/03-source.png').convert('RGB');idx=[]
for j,i in enumerate(selected):
 r=rows[i];crops=[src.crop(tuple(r['tile_box']))]
 for d in docs:
  p=d[i];crops.append(p.render(scale=300/72,rev_byteorder=True).to_pil().convert('RGB'));p.close()
 small=[]
 for im in crops:
  x=im.resize((max(1,round(im.width*.32)),max(1,round(im.height*.32))),Image.Resampling.LANCZOS);small.append((x,x.resize((x.width*4,x.height*4),Image.Resampling.NEAREST)))
 cw=max(v[1].width for v in small)+8;rh=max(v[0].height for v in small);eh=max(v[1].height for v in small);canvas=Image.new('RGB',(cw*5,rh+eh+50),'white');draw=ImageDraw.Draw(canvas)
 for k,((a,b),name) in enumerate(zip(small,('source','shape proxy','global colour','page ink','local colour'))):draw.text((k*cw+3,2),name,fill='black');canvas.paste(a,(k*cw+3,25));canvas.paste(b,(k*cw+3,35+rh))
 f=O/f'p03-{j+1:02}.png';canvas.save(f);idx.append({'page':3,'symbol':r['symbol'],'selection':'largest_colour_difference' if i in worst else 'seeded_random','diagnostic_index':i,'file':str(f),'sha256':hashlib.sha256(f.read_bytes()).hexdigest(),'note':'Isolated pre-font paths on white; not a full candidate page.'})
for d in docs:d.close()
(E/'colour-panel-index.json').write_text(json.dumps(idx,indent=2)+'\n');print(len(idx),'colour panels')
