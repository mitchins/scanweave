"""Panels of the semantically failing trial, clearly labelled HOLD."""
import hashlib,json,pathlib,sys
import numpy as np
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f/final';P=L/'panels';P.mkdir(exist_ok=True);sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();rows=[r for r in json.loads((R/'hvc41e/review-decisions.json').read_text()) if r['decision']=='accept'];results=json.loads((E/'final-render.json').read_text());src=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');w,h=src.size;idx=[]
def save(im,name,**extra):
 p=P/name;im.save(p);idx.append({'path':str(p),'sha256':sha(p),**extra})
def crop(im,box):
 a,b,c,d=box;return im.crop((round(a*im.width/w),round(b*im.height/h),round(c*im.width/w),round(d*im.height/h)))
def boxof(r,pad=6):
 a,b,c,d=map(int,r['source_box']);return (max(0,a-pad),max(0,b-pad),min(w,c+pad),min(h,d+pad))
base=Image.open(L/'renders/pdfium-300-01-baseline.png').convert('RGB');cand=Image.open(L/'renders/pdfium-300-01-candidate.png').convert('RGB');prior=Image.open(L/'renders/pdfium-300-01-hvc41e.png').convert('RGB');base96=Image.open(L/'renders/pdfium-96-01-baseline.png').convert('RGB');cand96=Image.open(L/'renders/pdfium-96-01-candidate.png').convert('RGB');prior96=Image.open(L/'renders/pdfium-96-01-hvc41e.png').convert('RGB');sw=base96.width;sh=base96.height;sheet=Image.new('RGB',(4*(sw+10),sh+36),'white');d=ImageDraw.Draw(sheet)
for j,(name,im) in enumerate([('SOURCE',src.resize((sw,sh),Image.Resampling.LANCZOS)),('#39',base96),('HVC-41E',prior96),('HVC-41F HOLD: extraction differs',cand96)]):d.text((j*(sw+10)+4,4),name,fill='black');sheet.paste(im,(j*(sw+10)+4,26))
save(sheet,'whole-page-HOLD-96.png',kind='whole_page')
groups=[[87,89,98,97,99],[110,112,114,116,120],[122,134,140,142,141],[175,187,203,201]]
for i,ids in enumerate(groups,1):
 subset=[r for r in rows if r['proposal'] in ids];box=(max(0,int(min(r['source_box'][0] for r in subset))-90),max(0,int(min(r['source_box'][1] for r in subset))-20),min(w,int(max(r['source_box'][2] for r in subset))+90),min(h,int(max(r['source_box'][3] for r in subset))+20));ims=[crop(im,box) for im in (src,base,prior,cand)];cw=max(i.width for i in ims)+10;ch=max(i.height for i in ims)+25;s=Image.new('RGB',(cw*4,ch),'white');dr=ImageDraw.Draw(s)
 for j,(name,im) in enumerate(zip(['source','#39','HVC-41E','HVC-41F HOLD'],ims)):dr.text((j*cw+3,3),name,fill='black');s.paste(im,(j*cw+3,21))
 save(s,f'line-{i:02}-HOLD-300.png',kind='line',proposals=ids,source_box=box)
# One contact sheet of all frozen reviewed glyphs at 4x nearest-neighbour.
cw,ch=690,270;sheet=Image.new('RGB',(cw*3,ch*13),'white');draw=ImageDraw.Draw(sheet)
for i,r in enumerate(rows):
 x=(i%3)*cw;y=(i//3)*ch;box=boxof(r);draw.text((x+3,y+3),f"{r['proposal']:03} | {r['symbol_id']} | {r['claude_identity'][:35]} | HOLD",fill='black')
 for j,(name,im) in enumerate(zip(['source','#39','HVC-41F HOLD'],(src,base,cand))):
  draw.text((x+j*230+3,y+20),name,fill='black');tile=crop(im,box);tile=tile.resize((tile.width*4,tile.height*4),Image.Resampling.NEAREST);sheet.paste(tile,(x+j*230+3,y+38))
save(sheet,'all-38-HOLD-4x.png',kind='all_glyphs',proposals=[r['proposal'] for r in rows])
# Rank using beyond-band coordinates at either resolution, then strongest boundary delta locally.
rankmap={r['proposal']:[0,0.0,r] for r in rows}
for dpi in (96,300):
 for engine in ('splash-aa','cairo','pdfium','mupdf'):
  z=next(x for x in results if x['page']==1 and x['comparison']=='candidate' and x['dpi']==dpi and x['engine']==engine);im=Image.open(z['render']).convert('RGB');baseim=np.asarray(Image.open(L/f'renders/{engine}-{dpi}-01-baseline.png').convert('RGB'));new=np.asarray(im);band=np.asarray(Image.open(L/f'renders/{engine}-{dpi}-01-candidate-boundary.png').convert('RGB'));mask=(band[:,:,0]==255)&(band[:,:,1]==200)
  for r in rows:
   a,b,c,d=boxof(r,9);bounds=(round(a*im.width/w),round(b*im.height/h),round(c*im.width/w),round(d*im.height/h));x0,y0,x1,y1=bounds;entry=rankmap[r['proposal']];entry[0]+=sum(x0<=p[0]<x1 and y0<=p[1]<y1 for p in z['beyond_xy_delta_luma']);m=mask[y0:y1,x0:x1]
   if m.any():
    delta=(new[y0:y1,x0:x1].astype(float)-baseim[y0:y1,x0:x1].astype(float))@np.array([.2126,.7152,.0722]);entry[1]=max(entry[1],float(np.abs(delta[m]).max()))
ranks=list(rankmap.values())
for rank,(count,maximum,r) in enumerate(sorted(ranks,key=lambda z:(-z[0],-z[1]))[:6],1):
 box=boxof(r,9);cw=240;ch=210;sheet=Image.new('RGB',(cw*4,ch*4),'white');dr=ImageDraw.Draw(sheet)
 for yi,dpi in enumerate((96,300)):
  for xi,eng in enumerate(('splash-aa','cairo','pdfium','mupdf')):
   im=Image.open(L/f'renders/{eng}-{dpi}-01-candidate.png').convert('RGB');mask=Image.open(L/f'renders/{eng}-{dpi}-01-candidate-boundary.png').convert('RGB');a=crop(im,box);b=crop(mask,box);scale=4 if dpi==300 else 8;a=a.resize((a.width*scale,a.height*scale),Image.Resampling.NEAREST);b=b.resize((b.width*scale,b.height*scale),Image.Resampling.NEAREST);a.thumbnail((cw-6,ch-24),Image.Resampling.NEAREST);b.thumbnail((cw-6,ch-24),Image.Resampling.NEAREST);dr.text((xi*cw+2,(yi*2)*ch+2),f'{eng} {dpi} candidate',fill='black');sheet.paste(a,(xi*cw+2,(yi*2)*ch+20));dr.text((xi*cw+2,(yi*2+1)*ch+2),'yellow band / red beyond',fill='black');sheet.paste(b,(xi*cw+2,(yi*2+1)*ch+20))
 save(sheet,f'worst-{rank:02}-{r["proposal"]:03}-HOLD.png',kind='worst_boundary',proposal=r['proposal'],beyond_local_count=count,max_boundary_delta_luma=maximum)
(E/'final-panel-index.json').write_text(json.dumps(idx,indent=2)+'\n');print('HOLD panels',len(idx),'worst',[(x[2]['proposal'],x[0]) for x in sorted(ranks,key=lambda z:(-z[0],-z[1]))[:6]])
