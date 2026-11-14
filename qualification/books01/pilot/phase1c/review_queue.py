#!/usr/bin/env python3
"""Capped candidate queue from saved scores. No detector or converter is run."""
import collections,hashlib,json,pathlib,random
from PIL import Image,ImageOps,ImageDraw
B=pathlib.Path('/data/coding/scanweave/work/books01');Q=pathlib.Path(__file__).resolve().parents[1];ids=json.loads((Q.parent/'corpus.frozen.json').read_text())['pilot_6'];geo=json.loads((Q/'results/phase1b/geometry.json').read_text())['pages'];locks=json.loads((Q.parent/'sources.lock.json').read_text())['pages'];cands=json.loads((B/'pilot/phase1b/triage-candidates.json').read_text());controls=json.loads((B/'pilot/phase1b/controls/controls.json').read_text());refs=json.loads((Q/'results/phase1b/reference.json').read_text())['crops'];out=B/'pilot/phase1c/queue';out.mkdir(parents=True,exist_ok=True)
def iou(a,b):
 i=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]));return i/(max(1,(a[2]-a[0])*(a[3]-a[1])+(b[2]-b[0])*(b[3]-b[1])-i))
def percentile(items):
 groups=collections.defaultdict(list)
 for c in items:groups[(c['page'],c['row'],c['detector'])].append(c)
 for group in groups.values():
  vals=sorted(c['score'] for c in group)
  import bisect
  for c in group:c['rank_percentile']=bisect.bisect_right(vals,c['score'])/len(vals)
def digest(im,box):return hashlib.sha256(im.crop(tuple(box)).tobytes()).hexdigest()
percentile(cands);pages={};summary={};coverage=[]
for id in ids:
 dpi=str(int(locks[id]['resolved_dpi'])); im={r:Image.open(B/geo[id][r]['pdfium'][dpi]['aligned_render_path']).convert('RGB') for r in ['src','sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E']};ordered=sorted((c for c in cands if c['page']==id),key=lambda c:(-c['rank_percentile'],-c['score'],c['row'],c['bbox'],c['detector'])); chosen=[];per=collections.Counter();cache={}
 def equivalence(box):
  k=tuple(box)
  if k not in cache:
   hashes={r:digest(img,box) for r,img in im.items()};cache[k]=hashes
  return cache[k]
 for c in ordered:
  if len(chosen)>=10:break
  box=c['bbox'];row=c['row'];h=equivalence(box)
  # Skip source-identical output; collapse pixel-identical rows to a canonical representative.
  if h[row]==h['src']:continue
  equivalent=sorted(r for r in im if r!='src' and h[r]==h[row]);representative=next((r for r in ['sw-E','mrc-M','adobe-E','ocrmypdf-E','sw-M','sw-build'] if r in equivalent),row)
  if per[representative]>=3 or any(iou(box,x['bbox'])>=.5 for x in chosen):continue
  chosen.append({'page':id,'row':representative,'equivalent_rows':equivalent,'bbox':box,'detector':c['detector'],'raw_score':c['score'],'rank_percentile_within_page_row_detector':c['rank_percentile'],'type':'candidate'});per[representative]+=1
 # Fixed-seed random controls, excluding overlapping queue boxes; do not suppress source-identical controls.
 pool=[x for x in controls if x['page']==id];random.Random(int.from_bytes(hashlib.sha256(('books01-queue-control-v1/'+id).encode()).digest()[:8],'big')).shuffle(pool);selected=[]
 for c in pool:
  if len(selected)==2:break
  if any(iou(c['bbox'],x['bbox'])>=.5 for x in chosen+selected):continue
  h=equivalence(c['bbox']);row=c['row'];eq=sorted(r for r in im if r!='src' and h[r]==h[row]); selected.append({'page':id,'row':'src' if h[row]==h['src'] else row,'equivalent_rows':eq,'bbox':c['bbox'],'type':'random control','source_identical':h[row]==h['src']})
 queue=chosen+selected
 for j,x in enumerate(queue):
  x['queue_id']=id.split('/')[-1]+'-'+f'{j+1:02d}';box=tuple(x['bbox']);a=im['src'].crop(box);b=im[x['row']].crop(box);size=(a.width*3,a.height*3);a=a.resize(size,Image.Resampling.NEAREST);b=b.resize(size,Image.Resampling.NEAREST);sheet=Image.new('RGB',(size[0]*2+12,size[1]),'white');sheet.paste(a,(0,0));sheet.paste(b,(size[0]+12,0));sheet.save(out/(x['queue_id']+'.png'))
 # Coverage is original flagged row/detector instances whose boxes overlap a chosen
 # box and whose output pixels equal the selected representative on that chosen box.
 covered=0
 for c in ordered:
  for x in chosen:
   if iou(c['bbox'],x['bbox'])>=.5 and equivalence(x['bbox'])[c['row']]==equivalence(x['bbox'])[x['row']]:covered+=1;break
 pages[id]=queue;summary[id]={'candidate_instances':len(ordered),'candidate_instances_covered':covered,'covered_fraction':covered/len(ordered) if ordered else None,'queued_candidates':len(chosen),'random_controls':len(selected),'total_crops':len(queue),'seconds_at_20_per_crop':20*len(queue),'row_caps':dict(per)}
 for crop in refs:
  if crop['page']!=id or crop['crop_id'] not in ['crop-0018','crop-0055','crop-0056','crop-0014']:continue
  # Matching the region alone does not imply the concerned row is represented.
  concern=crop['provisional_positive_rows'];matched=[]
  for x in chosen:
   overlap=iou(crop['bbox'],x['bbox']);matching=[r for r in concern if equivalence(x['bbox'])[r]==equivalence(x['bbox'])[x['row']]]
   if overlap>=.5 and matching:matched.append({'queue_id':x['queue_id'],'iou':overlap,'rows':matching})
  coverage.append({'crop_id':crop['crop_id'],'panel':{'crop-0018':'panel-001','crop-0055':'panel-002','crop-0056':'panel-003','crop-0014':'panel-004'}[crop['crop_id']],'page':id,'concern_rows':concern,'matches':matched,'covered':bool(matched)})
 for image in im.values():image.close()
res={'definition':'At most 10 flagged crops per page, at most 3 per pixel-distinct representative row, plus 2 fixed-seed random controls. Rank by within-page, row and detector empirical raw-score percentile; ties by raw score then row, box and detector. Deduplicate boxes at IoU >= 0.5 and rows by exact decoded RGB crop bytes; omit source-identical flagged outputs. Counts use original candidate instances including duplicates.','pages':pages,'summary':summary,'concern_coverage':coverage,'projection':'36 pages = six times observed six-page workload; not a measured 36-page outcome','local_crops':'$B/pilot/phase1c/queue/'};(Q/'results/phase1c/review-queue.json').write_text(json.dumps(res,indent=2)+'\n');print('queued',sum(x['total_crops'] for x in summary.values()),'flagged',sum(x['queued_candidates'] for x in summary.values()));print('concern coverage',[(x['panel'],x['covered']) for x in coverage])
