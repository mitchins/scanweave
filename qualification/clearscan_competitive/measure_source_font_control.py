#!/usr/bin/env python3
"""Render and score the original-full-font evaluator control on accepted glyphs."""
import hashlib, json, math, re, subprocess
from pathlib import Path
import numpy as np
from PIL import Image
import pypdfium2 as pdfium
ROOT=Path(__file__).resolve().parents[2]
def sha(b): return hashlib.sha256(b).hexdigest()
def iou(a,b):
    a=a<170;b=b<170
    return float((a&b).sum()/max(1,(a|b).sum()))
def render_poppler(pdf,out,dpi):
    subprocess.run(['pdftoppm','-r',str(dpi),'-png',str(pdf),str(out/'poppler')],check=True,capture_output=True)
def render_pdfium(pdf,out,dpi):
    doc=pdfium.PdfDocument(str(pdf));ims=[]
    for i,page in enumerate(doc):
        im=page.render(scale=math.nextafter(dpi/72,0.0)).to_pil().convert('L')
        p=out/f'pdfium-{i+1}.png';im.save(p);ims.append(np.asarray(im))
    return ims
def read_pngs(prefix,count):
    return [np.asarray(Image.open(f'{prefix}-{i+1}.png').convert('L')) for i in range(count)]
def family_statistics(per,stats):
    fam={}
    for ch in sorted(set(r['text'] for r in per)):
        rr=[r for r in per if r['text']==ch]
        fam[ch]={k:stats(k,rr)['mean'] for k in ('source','control_poppler','control_pdfium','final_poppler','final_pdfium')};fam[ch]['n']=len(rr)
    return fam

def main():
    dpi=300; q=ROOT/'qualification/clearscan_competitive/300/source-font-control';q.mkdir(parents=True,exist_ok=True)
    base=ROOT/'qualification/experiments/m1g/fixture/dpi300';manifest=json.loads((base/'input/document.json').read_text())
    pdf=q/'oracle-source-font.pdf';final=ROOT/'qualification/clearscan_competitive/300/clearscan.pdf'
    for arm in ('source-font-control','final'):
        p=q/arm;p.mkdir(exist_ok=True)
    render_poppler(pdf,q/'source-font-control',dpi);control_py=render_pdfium(pdf,q/'source-font-control',dpi)
    # Fresh final renderer images ensure same physical/rendering contract.
    final_dir=q/'final';final_dir.mkdir(exist_ok=True);render_poppler(final,final_dir,dpi);final_py=render_pdfium(final,final_dir,dpi)
    control_pop=read_pngs(q/'source-font-control'/'poppler',len(manifest['pages']))
    final_pop=read_pngs(final_dir/'poppler',len(manifest['pages']))
    source=[];truth=[];accepted=[]
    for pi,page in enumerate(manifest['pages']):
        source.append(np.asarray(Image.open(base/'input'/f'page{pi:02}.png').convert('L')))
        truth.append(np.asarray(Image.open(base/'oracle'/f'page{pi:02}.png').convert('L')))
        accepted.append(json.loads((q.parent/'final/stages/stage-errors.json').read_text())['occurrences'] if pi==0 else None)
    accepted={r['id'] for r in accepted[0]}
    per=[]
    for pi in range(len(manifest['pages'])):
        records=json.loads((base/'oracle'/f'page{pi:02}.truth.json').read_text())['records']
        for r in records:
            if r['id'] not in accepted or not r['text'].strip():continue
            x0,y0,x1,y1=map(int,r['bbox']);pad=5;sl=(slice(y0+pad,y1-pad),slice(x0+pad,x1-pad))
            per.append({'page':pi,'id':r['id'],'text':r['text'],
                'source':iou(source[pi][sl],truth[pi][sl]),
                'control_poppler':iou(control_pop[pi][sl],truth[pi][sl]),
                'control_pdfium':iou(control_py[pi][sl],truth[pi][sl]),
                'final_poppler':iou(final_pop[pi][sl],truth[pi][sl]),
                'final_pdfium':iou(final_py[pi][sl],truth[pi][sl])})
    def stats(key,rows=per):
        vals=[r[key] for r in rows];return {'n':len(vals),'mean':float(np.mean(vals)) if vals else None}
    fam=family_statistics(per,stats)
    input_text=''.join(s['text'] for pi in manifest['pages'] for s in json.loads((base/'input'/pi['ocr_page_path']).read_text())['spans'])
    norm=lambda x:re.sub(r'\s+','',x)
    poptext=subprocess.run(['pdftotext','-raw',str(pdf),'-'],check=True,capture_output=True,text=True).stdout
    pdfdoc=pdfium.PdfDocument(str(pdf));pdftext=''.join(p.get_textpage().get_text_range() for p in pdfdoc)
    fonts=json.loads((q/'audit.json').read_text())
    result={'dpi':dpi,'pdf':{'path':pdf.name,'bytes':pdf.stat().st_size,'sha256':sha(pdf.read_bytes())},
      'input_final_pdf':{'bytes':final.stat().st_size,'sha256':sha(final.read_bytes())},
      'tool_versions':{'poppler':subprocess.run(['pdftoppm','-v'],capture_output=True,text=True).stderr.splitlines()[0],
        'pdfium':str(pdfium.PDFIUM_INFO)},
      'render_contract':{'poppler':'pdftoppm -r 300','pdfium_scale':math.nextafter(dpi/72,0.0),'threshold':170,'crop':'truth bbox inset 5 px','population':'exact 515 emitted vector ids; whitespace excluded'},
      'population':len(per),'means':{k:stats(k) for k in ('source','control_poppler','control_pdfium','final_poppler','final_pdfium')},'by_character':fam,
      'search':{'poppler_matches_ocr_whitespace_normalized':norm(poptext)==norm(input_text),'pdfium_matches_ocr_whitespace_normalized':norm(pdftext)==norm(input_text),'poppler':poptext,'pdfium':pdftext},
      'fonts':fonts,'render_hashes':{'control_poppler':[sha((q/'source-font-control'/f'poppler-{i+1}.png').read_bytes()) for i in range(len(per) and len(manifest['pages']))],
         'control_pdfium':[sha((q/'source-font-control'/f'pdfium-{i+1}.png').read_bytes()) for i in range(len(manifest['pages']))],
         'final_poppler':[sha((final_dir/f'poppler-{i+1}.png').read_bytes()) for i in range(len(manifest['pages']))],
         'final_pdfium':[sha((final_dir/f'pdfium-{i+1}.png').read_bytes()) for i in range(len(manifest['pages']))]},'occurrences':per}
    (q/'metrics.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'means':result['means'],'search':{k:v for k,v in result['search'].items() if 'matches' in k},'bytes':pdf.stat().st_size},indent=2))
if __name__=='__main__':main()
