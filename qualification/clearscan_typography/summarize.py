"""Aggregate hash-bound, same-instance evidence without averaging renderers."""
import json,re,hashlib,subprocess,gzip
from pathlib import Path
from collections import Counter,defaultdict
import numpy as np
B=Path(__file__).resolve().parent;ROOT=B.parents[1]
def load(p):return json.loads(p.read_text() if p.exists() else gzip.decompress(Path(str(p)+'.gz').read_bytes()))
def edit(a,b):
    v=list(range(len(b)+1))
    for i,x in enumerate(a,1):
        u=[i]
        for j,y in enumerate(b,1):u.append(min(u[-1]+1,v[j]+1,v[j-1]+(x!=y)))
        v=u
    return v[-1]
def timing(path):
    s=path.read_text();m=re.search(r'Elapsed .*?: ([\d:.]+)',s);v=list(map(float,m[1].split(':')));seconds=sum(x*60**i for i,x in enumerate(v[::-1]));return {'wall_seconds':seconds,'peak_rss_kb':int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',s)[1])}
summary={'starting_head':'903580f4911ce0ca15377781b70f2acedc960a99','implementation_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'documents':{},'attempts':[]}
for dpi in (300,600):
    d={};truth=''.join(r['text'] for pi in range(8) for r in load(ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/oracle/page{pi:02}.truth.json')['records']);norm=lambda s:re.sub(r'\s+','',s)
    for arm in ('previous','adobe','final'):
        m=load(B/str(dpi)/arm/'metrics.json');a=load(B/str(dpi)/arm/'audit.json');rs=[r for r in m['glyphs'] if r['geometry']=='exact' and 'source_isolated' in r];groups={}
        for severity,lo,hi in [('healthy',.95,1.001),('moderate',.8,.95),('heavy',0,.8)]:
            sub=[r for r in rs if lo<=r['source_isolated']<hi];groups[severity]={'n':len(sub)}
            for renderer in ('poppler','pdfium'):
                gains=[r[renderer+'_isolated']-r['source_isolated'] for r in sub];groups[severity][renderer]={'mean_gain':float(np.mean(gains)) if gains else None,'improved':sum(g>0 for g in gains),'regressed':sum(g<0 for g in gains)}
        x={'bytes':m['bytes'],'sha256':m['sha256'],'streams':m['streams'],'legacy_padded_iou':m['summary'],'isolated_iou':m['isolated_summary'],'image_resources':m['unique_images'],'embedded_outlines_all':m['font_outlines'],'painted_occurrences':a['painted_occurrences'],'used_font_gids':a['used_font_gids'],'distinct_painted_outline_hashes':a['distinct_painted_outline_hashes'],'severity':groups,'search':{k:v for k,v in m['search'].items() if 'matches' in k},'ocr_ground_truth_char_errors':{renderer:edit(norm(m['search'][renderer]),norm(truth)) for renderer in ('poppler','pdfium')},'ground_truth_chars':len(norm(truth)),'raster_byte_classes':a['resource_bytes_by_class']}
        if arm!='adobe':
            rp=load(B/str(dpi)/('final.json' if arm=='final' else 'previous.json'));prs=rp['page_reports'];ocs=[o for p in prs for o in p['reconstruction']['occurrences'] if o['repaired'] or o['reused']];x.update({'observations':sum(len(p['reconstruction']['observations']) for p in prs),'canonical_replacements':len(ocs),'canonical_id_count':len(set(o['prototype_id'] for o in ocs)),'repaired_occurrences':sum(o['repaired'] for o in ocs),'coverage':rp['coverage'],'suppressed_source_ink_px':sum(p.get('raster_ink_pixels_suppressed',0) for p in prs),'suppressed_fringe_px':sum(p.get('antialias_fringe_pixels_suppressed',0) for p in prs),'stage_timings':rp['stage_timings'],'qualified_searchable_raster_bytes':next(c['pdf_bytes'] for c in rp['candidates'] if c['name']=='raster_baseline'),'wrong_witness_identity':a['wrong_witness_identity'],'wrong_witness_typeface':a['wrong_witness_typeface']});x.update(timing(B/str(dpi)/('final-time.txt' if arm=='final' else 'previous-time.txt')))
        d[arm]=x
    d['source_image_only_pdf_bytes']=(ROOT/'qualification/clearscan_competitive'/str(dpi)/'source.pdf').stat().st_size;d['raw_source_isolated_iou']=d['final']['isolated_iou']['exact']['source'];d['raw_source_padded_iou']=d['final']['legacy_padded_iou']['exact']['source'];summary['documents'][str(dpi)]=d
for arm in ('smooth','subpixel','fit','fair','strong','edgefit','blur','continuous'):
    p=B/'300'/arm/'metrics.json'
    if p.exists():
        m=load(p);summary['attempts'].append({'arm':arm,'bytes':m['bytes'],'sha256':m['sha256'],'padded_iou':m['summary'],'isolated_iou':m['isolated_summary'],'streams':m['streams']})
(B/'scorecard.json').write_text(json.dumps(summary,indent=2,ensure_ascii=False)+'\n')
print(json.dumps({dpi:{arm:{k:d[arm][k] for k in ('bytes','painted_occurrences','canonical_replacements') if k in d[arm]} for arm in ('previous','adobe','final')} for dpi,d in summary['documents'].items()},indent=2))
