"""Evaluator-only confusable identity diagnostic at known em/baseline.
Six source-font alternatives, same physical cell; translation only (+/- one
300-DPI pixel), no individual glyph bbox scaling. This is a bounded synthetic
classifier, not an exhaustive recognizer or a correctness oracle for real data.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageFont,ImageDraw
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
TEXT='e8a0g6e,a; 8e0ag6! e8a0g6e,a; 8e0ag6?'
for dpi in (300,600):
    scale=dpi//300;base=ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}';rows=[]
    for pi in range(8):
        truth=json.loads((base/'oracle'/f'page{pi:02}.truth.json').read_text());font=ImageFont.truetype(truth['font'],44*scale)
        images={'source':np.asarray(Image.open(base/'input'/f'page{pi:02}.png').convert('L'))}
        for arm in ('adobe','previous','final'):
            for geometry in ('exact','default'):
                for renderer in ('poppler','pdfium'):
                    images[f'{arm}/{geometry}/{renderer}']=np.asarray(Image.open(B/str(dpi)/arm/geometry/f'{renderer}-{pi+1}.png').convert('L'))
        for row in range(2):
            x=70*scale;y=(75+178*row)*scale
            for j,ch in enumerate(TEXT):
                advance=int(font.getlength(ch))+7*scale
                if ch in 'eag068':
                    x0=int(x)-scale;y0=int(y)+5*scale;ww=advance;hh=50*scale;templates={}
                    for alt in 'eag068':
                        im=Image.new('L',(ww,hh),255);ImageDraw.Draw(im).text((scale,-5*scale),alt,font=font,fill=15);templates[alt]=np.asarray(im)<170
                    rec={'page':pi,'id':f'p{pi:02}s{row*len(TEXT)+j:04}','true':ch,'bbox':[x0,y0,x0+ww,y0+hh],'results':{}}
                    for name,a in images.items():
                        scores={}
                        for alt,t in templates.items():
                            best=0
                            for dy in (-scale,0,scale):
                                for dx in (-scale,0,scale):
                                    z=a[y0+dy:y0+hh+dy,x0+dx:x0+ww+dx]<170
                                    best=max(best,float((z&t).sum()/max(1,(z|t).sum())))
                            scores[alt]=best
                        rank=sorted(scores,key=scores.get,reverse=True);rec['results'][name]={'selected':rank[0],'correct':rank[0]==ch,'margin':scores[rank[0]]-scores[rank[1]],'scores':scores}
                    rows.append(rec)
                x+=advance
    names=list(rows[0]['results']);summary={name:{'instances':len(rows),'incorrect':sum(not r['results'][name]['correct'] for r in rows),'ambiguous_margin_below_0_05':sum(r['results'][name]['margin']<.05 for r in rows)} for name in names}
    (B/str(dpi)/'identity.json').write_text(json.dumps({'method':__doc__,'summary':summary,'instances':rows},indent=2));print(dpi,summary,flush=True)
