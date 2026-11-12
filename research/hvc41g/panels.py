"""Render-indexed HVC-41G review panels; no visual disposition is made."""
import hashlib,json,pathlib
import numpy as np
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41g';L=R/'local/hvc41g';P=L/'panels';P.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();freeze=json.loads((E/'freeze.json').read_text());assert sha(L/'historical-frozen.pdf')==freeze['pdf_sha256'] and (L/'qualification.started').read_text().splitlines()==[freeze['pdf_sha256'],freeze['representation_sha256']];rows=[r for r in json.loads((R/'hvc41e/review-decisions.json').read_text()) if r['decision']=='accept'];results=json.loads((E/'qualification-render.json').read_text());halos=json.loads((E/'qualification-halo.json').read_text());src=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');w,h=src.size;idx=[]
def save(im,name,**extra):
 p=P/name;im.save(p);idx.append({'path':str(p),'sha256':sha(p),**extra})
def crop(im,box):
 a,b,c,d=box;return im.crop((round(a*im.width/w),round(b*im.height/h),round(c*im.width/w),round(d*im.height/h)))
def boxof(r,px=10,py=10):
 a,b,c,d=map(int,r['source_box']);return (max(0,a-px),max(0,b-py),min(w,c+px),min(h,d+py))
base=Image.open(L/'renders/pdfium-300-01-baseline.png').convert('RGB');cand=Image.open(L/'renders/pdfium-300-01-candidate.png').convert('RGB');base96=Image.open(L/'renders/pdfium-96-01-baseline.png').convert('RGB');cand96=Image.open(L/'renders/pdfium-96-01-candidate.png').convert('RGB');prior96=Image.open(L/'renders/pdfium-96-01-hvc41e.png').convert('RGB');sw,sh=base96.size;sheet=Image.new('RGB',(4*(sw+10),sh+36),'white');d=ImageDraw.Draw(sheet)
for j,(name,im) in enumerate([('SOURCE',src.resize((sw,sh),Image.Resampling.LANCZOS)),('#39 baseline',base96),('HVC-41E',prior96),('HVC-41G',cand96)]):d.text((j*(sw+10)+4,4),name,fill='black');sheet.paste(im,(j*(sw+10)+4,26))
save(sheet,'whole-page-96.png',kind='whole_page')
groups=[[87,89,98,97,99],[110,112,114,116,120],[122,134,140,142,141],[175,187,203,201]]
for i,ids in enumerate(groups,1):
 subset=[r for r in rows if r['proposal'] in ids];box=(max(0,int(min(r['source_box'][0] for r in subset))-90),max(0,int(min(r['source_box'][1] for r in subset))-20),min(w,int(max(r['source_box'][2] for r in subset))+90),min(h,int(max(r['source_box'][3] for r in subset))+20));ims=[crop(im,box) for im in (src,base,cand)];cw=max(i.width for i in ims)+10;ch=max(i.height for i in ims)+25;s=Image.new('RGB',(cw*3,ch),'white');dr=ImageDraw.Draw(s)
 for j,(name,im) in enumerate(zip(['source','#39','HVC-41G'],ims)):dr.text((j*cw+3,3),name,fill='black');s.paste(im,(j*cw+3,21))
 save(s,f'line-{i:02}-300.png',kind='line',proposals=ids,source_box=box)
# Nearest-neighbour enlarged crops include horizontal context on both sides.
cw,ch=690,220;sheet=Image.new('RGB',(cw*4,ch*10),'white');draw=ImageDraw.Draw(sheet)
for i,r in enumerate(rows):
 x=(i%4)*cw;y=(i//4)*ch;box=boxof(r,18,8);draw.text((x+3,y+3),f"{r['proposal']:03} | {r['symbol_id']} | {r['claude_identity'][:26]}",fill='black')
 for j,(name,im) in enumerate(zip(['source','#39','HVC-41G'],(src,base,cand))):
  draw.text((x+j*230+3,y+20),name,fill='black');tile=crop(im,box);scale=2 if tile.width*2<=225 and tile.height*2<=175 else 1;tile=tile.resize((tile.width*scale,tile.height*scale),Image.Resampling.NEAREST);sheet.paste(tile,(x+j*230+3,y+38))
save(sheet,'all-38-context.png',kind='glyph_contact_sheet',proposals=[r['proposal'] for r in rows],scale='2x nearest-neighbour unless crop exceeds cell')
# Rank by measured 300-DPI mean boundary-to-ring absolute luminance, and by beyond pixels.
halorank={r['proposal']:max((x['boundary_to_ring_mean_abs_delta_luma'] or 0) for x in halos if x['proposal']==r['proposal'] and x['dpi']==300 and x['engine'] in ('splash-aa','cairo','pdfium','mupdf')) for r in rows};beyond={r['proposal']:0 for r in rows}
for z in results:
 if z['comparison']=='candidate' and z['page']==1 and z['engine'] in ('splash-aa','cairo','pdfium','mupdf'):
  for p in z['beyond_xy_delta_luma']:
   if p['nearest_glyph'] in beyond:beyond[p['nearest_glyph']]+=1
byid={r['proposal']:r for r in rows};rankings={'halo':sorted(halorank,key=lambda i:(-halorank[i],i))[:6],'beyond':sorted(beyond,key=lambda i:(-beyond[i],-halorank[i],i))[:6]}
for kind,ids in rankings.items():
 for rank,i in enumerate(ids,1):
  box=boxof(byid[i],12,10);cw=240;ch=210;sheet=Image.new('RGB',(cw*4,ch*4),'white');dr=ImageDraw.Draw(sheet)
  for yi,dpi in enumerate((96,300)):
   for xi,eng in enumerate(('splash-aa','cairo','pdfium','mupdf')):
    im=Image.open(L/f'renders/{eng}-{dpi}-01-candidate.png').convert('RGB');mask=Image.open(L/f'renders/{eng}-{dpi}-01-candidate-boundary.png').convert('RGB');a=crop(im,box);b=crop(mask,box);scale=4 if dpi==300 else 8;a=a.resize((a.width*scale,a.height*scale),Image.Resampling.NEAREST);b=b.resize((b.width*scale,b.height*scale),Image.Resampling.NEAREST);a.thumbnail((cw-6,ch-24),Image.Resampling.NEAREST);b.thumbnail((cw-6,ch-24),Image.Resampling.NEAREST);dr.text((xi*cw+2,(yi*2)*ch+2),f'{eng} {dpi} glyph {i}',fill='black');sheet.paste(a,(xi*cw+2,(yi*2)*ch+20));dr.text((xi*cw+2,(yi*2+1)*ch+2),'yellow band / red beyond',fill='black');sheet.paste(b,(xi*cw+2,(yi*2+1)*ch+20))
  save(sheet,f'worst-{kind}-{rank:02}-{i:03}.png',kind='worst_'+kind,proposal=i,halo_mean_abs_luma=halorank[i],beyond_pixels=beyond[i])
(E/'panel-index.json').write_text(json.dumps(idx,indent=2)+'\n');print('panels',len(idx),'rankings',rankings,flush=True)
