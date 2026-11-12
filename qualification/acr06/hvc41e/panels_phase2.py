"""Panels from source, baseline and the one completed composed PDF."""
import pathlib,json,hashlib,textwrap
import numpy as np
from PIL import Image,ImageDraw
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41e';L=R/'local/hvc41e/final';P=L/'panels';P.mkdir(exist_ok=True);ledger=json.loads((E/'review-decisions.json').read_text());accepted=[r for r in ledger if r['decision']=='accept'];rejected=[r for r in ledger if r['decision']=='reject'];src=Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB');base=Image.open(R/'local/hvc41d/renders/pdfium-300-01-baseline.png').convert('RGB');cand=Image.open(L/'renders/pdfium-300-01-candidate.png').convert('RGB');render96=Image.open(L/'renders/pdfium-96-01-candidate.png').convert('RGB');base96=Image.open(R/'local/hvc41d/renders/pdfium-96-01-baseline.png').convert('RGB');sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest();index=[]
def save(img,name,kind,extra={}):
 f=P/name;img.save(f);index.append({'kind':kind,'path':str(f),'sha256':sha(f),**extra})
def triple(box,name,kind,scale=4,extra={}):
 imgs=[im.crop(box) for im in (src,base,cand)];cw=max(190,max(x.width for x in imgs)*scale+15);ch=max(x.height for x in imgs)*scale+30;sheet=Image.new('RGB',(cw*3,ch),'white');dr=ImageDraw.Draw(sheet)
 for i,(im,label) in enumerate(zip(imgs,['SOURCE','BASELINE #39','COMPOSED CANDIDATE'])):dr.text((cw*i+4,5),label,fill='black');sheet.paste(im.resize((im.width*scale,im.height*scale),Image.Resampling.NEAREST),(cw*i+4,25))
 save(sheet,name,kind,extra)
for r in accepted:
 a,b,c,d=map(int,r['source_box']);box=(max(0,a-6),max(0,b-6),min(src.width,c+6),min(src.height,d+6));triple(box,f"glyph-{r['proposal']:03}.png",'emitted_glyph_4x',4,{'proposal':r['proposal'],'symbol':r['symbol_id'],'claude_identity':r['claude_identity']})
# Whole page at actual 96-DPI geometry.
source96=src.resize(render96.size,Image.Resampling.LANCZOS);cw=render96.width+18;sheet=Image.new('RGB',(cw*3,render96.height+30),'white');dr=ImageDraw.Draw(sheet)
for i,(im,label) in enumerate(zip([source96,base96,render96],['SOURCE','BASELINE #39','COMPOSED CANDIDATE'])):dr.text((i*cw+4,5),label,fill='black');sheet.paste(im,(i*cw+4,25))
save(sheet,'whole-page-96.png','whole_page_reading')
for ix,ids in enumerate(([87,89,98,97,99],[110,112,114,116,120],[122,134,140,142,141],[175,187,203,201]),1):
 subset=[r for r in accepted if r['proposal'] in ids];a=max(0,int(min(x['source_box'][0] for x in subset))-90);b=max(0,int(min(x['source_box'][1] for x in subset))-20);c=min(src.width,int(max(x['source_box'][2] for x in subset))+90);d=min(src.height,int(max(x['source_box'][3] for x in subset))+20);ims=[im.crop((a,b,c,d)).resize((max(1,round((c-a)*96/300)),max(1,round((d-b)*96/300))),Image.Resampling.LANCZOS) for im in (src,base,cand)];cw=max(220,ims[0].width+12);ch=ims[0].height+28;sheet=Image.new('RGB',(cw*3,ch),'white');dr=ImageDraw.Draw(sheet)
 for i,(im,label) in enumerate(zip(ims,['SOURCE','BASELINE #39','COMPOSED CANDIDATE'])):dr.text((i*cw+4,4),label,fill='black');sheet.paste(im,(i*cw+4,23))
 save(sheet,f'line-{ix:02}-96.png','line_context_reading',{'proposals':ids,'source_box':[a,b,c,d]})
# Rank by actual outside-owner difference pixels in the local glyph neighbourhood.
eng=['pdfium','poppler','mupdf'];diffs={e:Image.open(L/f'diffs/{e}-300-outside.png').convert('RGB') for e in eng};ranks=[]
for r in accepted:
 a,b,c,d=map(int,r['source_box']);box=(max(0,a-7),max(0,b-7),min(src.width,c+7),min(src.height,d+7));counts={}
 for e in eng:
  im=diffs[e];x0=round(box[0]*im.width/src.width);x1=round(box[2]*im.width/src.width);y0=round(box[1]*im.height/src.height);y1=round(box[3]*im.height/src.height);counts[e]=int(np.any(np.asarray(im.crop((x0,y0,x1,y1)))!=0,axis=2).sum())
 ranks.append((sum(counts.values()),r,box,counts))
ranks.sort(key=lambda x:(-x[0],x[1]['proposal']))
for rank,(count,r,box,counts) in enumerate(ranks[:6],1):
 maxw=(box[2]-box[0])*4+16;maxh=(box[3]-box[1])*4+28;cw=max(180,maxw);sheet=Image.new('RGB',(cw*4,maxh*3),'white');dr=ImageDraw.Draw(sheet)
 for ri,e in enumerate(eng):
  bb=Image.open(R/f'local/hvc41d/renders/{e}-300-01-baseline.png').convert('RGB');cc=Image.open(L/f'renders/{e}-300-01-candidate.png').convert('RGB');dm=diffs[e];x0=round(box[0]*bb.width/src.width);x1=round(box[2]*bb.width/src.width);y0=round(box[1]*bb.height/src.height);y1=round(box[3]*bb.height/src.height);pan=[src.crop(box),bb.crop((x0,y0,x1,y1)),cc.crop((x0,y0,x1,y1)),dm.crop((x0,y0,x1,y1))]
  for j,(im,title) in enumerate(zip(pan,['SOURCE',f'{e} BASELINE',f'{e} CANDIDATE','OUTSIDE: EDGE YELLOW / OTHER RED'])):
   dr.text((j*cw+3,ri*maxh+4),title,fill='black');sheet.paste(im.resize((im.width*4,im.height*4),Image.Resampling.NEAREST),(j*cw+3,ri*maxh+23))
 save(sheet,f'boundary-{rank:02}-{r["proposal"]:03}.png','boundary_4x',{'proposal':r['proposal'],'local_outside_counts':counts,'rank_score':count})
# One 16-glyph rejected contact sheet; reasons are wrapped in dedicated rows.
cw=1050;rh=230;sheet=Image.new('RGB',(cw*2,rh*8),'white');dr=ImageDraw.Draw(sheet)
for j,r in enumerate(rejected):
 x=(j%2)*cw;y=(j//2)*rh;dr.text((x+5,y+4),f"REJECTED {r['proposal']} | {r['symbol_id']} | OCR {r['ocr_label']!r} | identity {r['claude_identity']!r}",fill='black');panel=Image.open(r['panel']).convert('RGB');panw=panel.width//6;a,b,c,d=map(int,r['source_box']);h=(d-b+12)*4+35;crop=panel.crop((0,0,panw*3,min(h,panel.height)));crop.thumbnail((cw-12,145),Image.Resampling.NEAREST);sheet.paste(crop,(x+5,y+23));reason=textwrap.wrap(r['reason'],width=155)
 for line,text in enumerate(reason[:4]):dr.text((x+5,y+170+line*14),text,fill='black')
save(sheet,'rejected-contact-sheet.png','rejected_contact_sheet',{'proposals':[r['proposal'] for r in rejected],'reasons':{str(r['proposal']):r['reason'] for r in rejected}})
(E/'final-panel-index.json').write_text(json.dumps(index,indent=2,ensure_ascii=False)+'\n');print('panels',len(index),'boundary ranking',[(x[1]['proposal'],x[0]) for x in ranks[:6]])
