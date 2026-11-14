#!/usr/bin/env python3
"""Report text-layer duplication and detectable reading-order issues."""
import collections,json,pathlib,re,unicodedata
import pypdfium2 as pdfium
from scipy.stats import kendalltau
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot';c=json.loads((P/'corpus.frozen.json').read_text());ids=c['pilot_6'];works={p['id']:p['work'] for p in c['pages']};runs=json.loads((Q/'results/runs.json').read_text());locks=json.loads((P/'sources.lock.json').read_text())['pages']
def norm(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',s.replace('ſ','s')).casefold()).strip()
result={}
for id in ids:
 key=id.split('/')[-1];g=json.loads((B/'gt'/works[id]/(key+'.json')).read_text());refs=[x['attributes'].get('regionRef') for x in g['reading_order'] if x['attributes'].get('regionRef')]; rank={v:i for i,v in enumerate(refs)};items=g['lines'] or [r for r in g['regions'] if r.get('text')];
 if refs:items=sorted(enumerate(items),key=lambda it:(rank.get(it[1].get('region_id',it[1].get('id')),len(rank)),it[0]));items=[x[1] for x in items]
 strings=[norm(x.get('text') or '') for x in items]; strings=[s for s in strings if len(s)>=12];reference=collections.Counter(strings);result[id]={}
 for row in ['src','sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E']:
  p=pathlib.Path(runs[id]['rows'][row].get('path',B/'pilot/runs'/key/(row+'.pdf')))
  if not p.exists():continue
  doc=pdfium.PdfDocument(str(p));text=doc[0].get_textpage().get_text_range();rawlines=[norm(s) for s in text.splitlines()];counts=collections.Counter(s for s in rawlines if len(s)>=12);duplicates=sum(max(0,n-max(1,reference.get(s,0))) for s,n in counts.items());n=norm(text);positions=[]
  for i,s in enumerate(strings):
   pos=n.find(s)
   if pos>=0:positions.append((i,pos))
  tau=float(kendalltau([x[0] for x in positions],[x[1] for x in positions]).statistic) if len(positions)>=2 else None
  result[id][row]={'duplicate_line_excess_heuristic':duplicates,'line_order_kendall_tau':tau,'matched_reference_lines_or_regions':len(positions),'reference_lines_or_regions':len(strings),'reading_order_present':g['reading_order_present'],'order_method':'exact normalized GT text matches; unmatched items excluded','dpi_confidence':locks[id]['dpi_evidence']['confidence']}
(Q/'results/extraction-diagnostics.json').write_text(json.dumps(result,indent=2,allow_nan=False)+'\n')
