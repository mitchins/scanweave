"""Offline FONT-04 S1b veto. Run from repository root with qualification/.venv/bin/python.

Train-only per-DPI RMS pair differences are the noise scale. Oracle joins and
font rasterisation are used solely for scoring; the veto sees source masks and
OCR labels only. Missing calibration/features abstain rather than reject.
"""
import json
from collections import Counter, defaultdict
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from s1a_census import iou
from s1a_reviewer_census import shape_xor, auc
from s1b_features import features, differences, FEATURES

ROOT = Path(__file__).resolve().parents[2]
BASE = ROOT/'qualification/font04/local'
OUT = ROOT/'qualification/font04'
FONT = ROOT/'qualification/font01/local/corpus-font01-v1'

def read(p): return json.loads(p.read_text())
def lines(p): return [json.loads(s) for s in p.read_text().splitlines()]

def make_join(rows, targets):
    records, stats = {}, Counter()
    agrees, ious, margins = [], [], []
    for r in rows:
        matches = sorted(((iou(r['bbox'], o['bbox']), o) for o in targets), key=lambda x:(-x[0], x[1]['id']))
        matches = [x for x in matches if x[0] > 0]
        status = ('unmatched' if not matches else 'multi_character' if len(r['character']) != 1 else
                  'ambiguous_tie' if len(matches)>1 and abs(matches[0][0]-matches[1][0]) < 1e-12 else 'single_best')
        stats[status] += 1
        if status == 'single_best':
            v, o = matches[0]; records[r['id']] = o['id']
            agrees.append(r['character'] == o['character']); ious.append(v)
            margins.append(v-(matches[1][0] if len(matches)>1 else 0))
    return records, dict(count=len(rows), status_counts=dict(stats), single_best_rate=len(records)/len(rows) if rows else None,
                         character_agreement=float(np.mean(agrees)) if agrees else None,
                         median_iou=float(np.median(ious)) if ious else None,
                         iou_below_0_2=sum(v<.2 for v in ious), margin_below_0_05=sum(v<.05 for v in margins))

def load_dataset(name, paths, oracle_obs=None, oracle_labels=None, faces=None, p2join=None):
    allpairs, summary, stats = [], [], Counter()
    cache = {}
    for page, (src, out, obsfile, dpi) in enumerate(paths):
        rows = read(src)['rows']; obs = read(obsfile); sharing = read(out)['conversion']['glyph_sharing']
        ids = {r['id']:r for r in rows}; feat = {r['id']:features(r) for r in rows}
        if p2join is not None:
            rec = p2join['sheets'][page]['records']; join = {r['source_id']:r['candidates'][0]['id'] for r in rec if r['status']=='single_best'}
            validation = {'status_counts':dict(Counter(r['status'] for r in rec)), 'count':len(rec)}
        elif oracle_obs is not None:
            join, validation = make_join(rows, [o for o in oracle_obs if o['page']==page])
        else: join, validation = {}, None
        summary.append(dict(page=page, dpi=dpi, join=validation, original={k:sharing.get(k) for k in ('substituted','retired_outlines','added_canonicals','net_outlines_retired')}))
        for d in sharing['decisions']:
            if not d['accepted'] or d['canonical'] is None: continue
            m, c = d['member'], d['canonical']
            if m == c: stats['accepted_self'] += 1; continue
            a, b = ids[obs[m]['id']], ids[obs[c]['id']]
            delta = differences(feat[a['id']],feat[b['id']],a['character'])
            cls, sx = 'unresolved', None
            la = oracle_labels.get(join.get(a['id'])) if oracle_labels else None
            lb = oracle_labels.get(join.get(b['id'])) if oracle_labels else None
            if la and lb:
                if la['character'] != lb['character']: cls = 'different-character'
                elif la['face'] == lb['face']: cls = 'same-face'
                elif la['family'] == lb['family']: cls = 'same-family-different-style'
                else: cls = 'different-family'
                if cls in ('different-family','same-family-different-style'):
                    try: sx = shape_xor(cache, faces, la['face'], lb['face'], la['character'])
                    except (OSError, KeyError, ValueError): stats['shape_unavailable'] += 1
            allpairs.append(dict(dataset=name,page=page,dpi=dpi,member=m,canonical=c,member_id=a['id'],canonical_id=b['id'],
                                 label=a['character'],cls=cls,shape_xor=sx,delta=delta,bbox=a['bbox']))
    return allpairs, summary, dict(stats)

def main():
    p2faces = {f['name']:f['path'] for f in read(OUT/'p2-preregistration-v1.1.json')['faces']}
    data, meta = {}, {}
    for split in ('train','validation','test'):
        root=FONT/split
        paths=[(BASE/f'S1/font01/{split}-{i}-cover-2.0/source.json',BASE/f'S1/font01/{split}-{i}-cover-2.0/output.pdf.json',BASE/f'S1/font01/{split}-{i}-cover-2.0/observations.json', (200,300,600)[i]) for i in range(3)]
        faces={f['name']:f['path'] for f in read(root/'manifest.json')['faces']}
        labels={x['id']:x for x in lines(root/'oracle/labels.jsonl')}
        data[split], summary, stats = load_dataset(split,paths,lines(root/'observations.jsonl'),labels,faces)
        meta[split]=dict(pages=summary,stats=stats)
    paths=[(BASE/f'S1/instrumented-{i}/source.json',BASE/f'S1/instrumented-{i}/output.pdf.json',BASE/f'S1/instrumented-{i}/observations.json',(200,300,600)[i//3]) for i in range(9)]
    labels={x['id']:x for x in lines(BASE/'P2/p2/oracle/labels.jsonl')}
    data['P2'], summary, stats = load_dataset('P2',paths,oracle_labels=labels,faces=p2faces,p2join=read(OUT/'s1a-join.json'))
    meta['P2']=dict(pages=summary,stats=stats)
    b=BASE/'R2a/export'; paths=[(b/'financial-observations/source.json',b/'financial-cover-2.0.pdf.json',b/'financial-observations/observations.json',300)]
    data['financial'], summary, stats = load_dataset('financial',paths)
    meta['financial']=dict(pages=summary,stats=stats)
    noise={}; counts={}
    for dpi in (200,300,600):
        noise[str(dpi)]={}; counts[str(dpi)]={}
        for f in FEATURES:
            x=[r['delta'][f] for r in data['train'] if r['dpi']==dpi and r['cls']=='same-face' and r['delta'] and f in r['delta']]
            counts[str(dpi)][f]=len(x)
            noise[str(dpi)][f]=float(np.sqrt(np.mean(np.square(x)))) if x else None
    (OUT/'s1b-noise.json').write_text(json.dumps(dict(method='RMS absolute same-face pair difference, FONT-01 train only, by DPI; zero scale permits only exact equality; absent scale disables feature', scales=noise, counts=counts),indent=2)+'\n')
    def veto(r,k):
        return bool(r['delta'] and any(noise[str(r['dpi'])].get(f) is not None and v > k*noise[str(r['dpi'])][f] for f,v in r['delta'].items()))
    results={}; aucs={}
    for name, rows in data.items():
        results[name]={}
        for k in (2,3,4,6):
            results[name][str(k)]={}
            for threshold in (.2,.3):
                visible=lambda r: r['cls']=='different-character' or (r['shape_xor'] is not None and r['shape_xor']>threshold)
                by=defaultdict(Counter)
                for r in rows:
                    caught=veto(r,k); cls=r['cls']
                    if visible(r): by[cls]['caught' if caught else 'remaining']+=1
                    elif cls=='same-face' and caught: by[cls]['false_veto']+=1
                    elif cls in ('different-family','same-family-different-style') and r['shape_xor'] is not None and caught: by[cls]['interchangeable_veto']+=1
                kept=sum(not veto(r,k) for r in rows)
                results[name][str(k)][str(threshold)]=dict(accepted_substitutions=len(rows),kept=kept,retained_fraction=kept/len(rows) if rows else None,by_class=dict(by),unresolved=sum(r['cls']=='unresolved' for r in rows),missing_features=sum(r['delta'] is None for r in rows))
        if name in ('P2','validation','test'):
            aucs[name]={}
            for threshold in (.2,.3):
                aucs[name][str(threshold)]={}
                for f in FEATURES:
                    pos=[r['delta'][f] for r in rows if r['delta'] and f in r['delta'] and (r['cls']=='different-character' or (r['shape_xor'] is not None and r['shape_xor']>threshold))]
                    neg=[r['delta'][f] for r in rows if r['delta'] and f in r['delta'] and r['cls']=='same-face']
                    aucs[name][str(threshold)][f]=dict(auc=auc(pos,neg) if pos and neg else None,positive=len(pos),negative=len(neg))
    # Persist row-level evidence only in local/ for reproducible review sheets.
    review_dir=BASE/'S1b'; review_dir.mkdir(parents=True, exist_ok=True)
    (review_dir/'pairs.json').write_text(json.dumps(data, separators=(',',':')))
    for name in results:
        self_count=meta[name]['stats'].get('accepted_self',0)
        for k in results[name]:
            for threshold in results[name][k]:
                r=results[name][k][threshold]
                r['accepted_members']=r['accepted_substitutions']+self_count
                r['accepted_members_kept']=r['kept']+self_count
                r['accepted_members_retained_fraction']=r['accepted_members_kept']/r['accepted_members'] if r['accepted_members'] else None
    out=dict(schema='font04-s1b-v1', description='Offline source-mask veto; retained fraction is over accepted non-self substitutions; no run-context variant implemented.',meta=meta,frontier=results,auc=aucs)
    (OUT/'s1b-frontier.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({n:{k:v['0.2'] for k,v in rs.items()} for n,rs in results.items()},indent=2))

def review_sheet(data, noise):
    """P2 k=2 review: source, frozen default, frozen cover, matched coordinates."""
    import pypdfium2 as pdfium
    from PIL import ImageFont
    import shutil
    def veto(r):
        return bool(r['delta'] and any(noise[str(r['dpi'])].get(f) is not None and v > 2*noise[str(r['dpi'])][f] for f,v in r['delta'].items()))
    def visible(r): return r['cls']=='different-character' or (r['shape_xor'] is not None and r['shape_xor']>.2)
    rows=data['P2']
    buckets={'caught':[r for r in rows if visible(r) and veto(r)],
             'missed':[r for r in rows if visible(r) and not veto(r)],
             'false-veto':[r for r in rows if not visible(r) and r['cls']!='unresolved' and veto(r)]}
    selected={k:v[:40] for k,v in buckets.items()}
    local=BASE/'S1b'; examples=OUT/'s1b-examples'; examples.mkdir(exist_ok=True)
    images={}
    for n in range(9):
        picked=[r for v in selected.values() for r in v if r['page']==n]
        if not picked: continue
        scan=Image.open(BASE/f'P2/p2/page-{n//3}-{n%3}.png').convert('RGB')
        rendered=[]
        for arm in ('off','cover-2.0'):
            doc=pdfium.PdfDocument(str(BASE/f'P2/sheet-{n}-{arm}.pdf'))
            rendered.append(doc[0].render(scale=(200,300,600)[n//3]/72).to_pil().convert('RGB'))
            doc.close()
        for r in picked:
            x0,y0,x1,y1=r['bbox']; pad=max(3,round(r['dpi']/100))
            box=(int(x0)-pad,int(y0)-pad,int(x1)+pad,int(y1)+pad)
            images[(n,r['member'])]=[im.crop(box) for im in [scan,*rendered]]
    for category, selected_rows in selected.items():
        canvas=Image.new('RGB',(720, 35+len(selected_rows)*76),'white'); draw=ImageDraw.Draw(canvas)
        draw.text((4,4),f'P2 {category}; k=2, XOR > 0.2 | scan | default | cover-2.0',fill='black')
        for i,r in enumerate(selected_rows):
            y=35+i*76
            draw.text((3,y+3),f"{i+1:02} s{r['page']} m{r['member']} <- {r['canonical']}\n{r['label']} {r['cls']}\nxor {r['shape_xor'] if r['shape_xor'] is not None else '-'}",fill='black')
            for j,im in enumerate(images[(r['page'],r['member'])]):
                im.thumbnail((160,68),Image.Resampling.NEAREST)
                canvas.paste(im,(225+j*165,y))
        canvas.save(local/f'{category}.png', optimize=True)
        if selected_rows:
            canvas.crop((0,35,720,35+76*min(3,len(selected_rows)))).save(examples/f'{category}.png',optimize=True)
    (local/'review-manifest.json').write_text(json.dumps({'rule':'P2 k=2, XOR > 0.2; first 40 in decision order','available':{k:len(v) for k,v in buckets.items()},'rows':selected},indent=2)+'\n')


if __name__=='__main__':
    main()
    review_sheet(read(BASE/'S1b/pairs.json'), read(OUT/'s1b-noise.json')['scales'])

