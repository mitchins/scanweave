#!/usr/bin/env python3
"""Create a self-contained blinded panel. Never prints or commits its local key."""
import base64,hashlib,html,io,json,pathlib,random,secrets
from PIL import Image
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[2];Q=P/'pilot';refs=json.loads((Q/'results/phase1b/reference.json').read_text())['crops'];by={x['crop_id']:x for x in refs};cand=json.loads((B/'pilot/phase1b/triage-candidates.json').read_text());ctrl=json.loads((B/'pilot/phase1b/controls/controls.json').read_text());locks=json.loads((P/'sources.lock.json').read_text())['pages'];geo=json.loads((Q/'results/phase1b/geometry.json').read_text())['pages'];rows=['sw-E','sw-M','sw-build','ocrmypdf-E','mrc-M','adobe-E'];D=B/'pilot/human-panel';D.mkdir(parents=True,exist_ok=True);rnd=secrets.SystemRandom()
items=[];used=set();prior_boxes={(r['page'],tuple(r['bbox'])) for r in refs}
def add(page,box,kind,origin=None):
 key=(page,tuple(box))
 if key in used:return False
 used.add(key);items.append({'page':page,'bbox':list(box),'selection':kind,'private_origin':origin});return True
for cid in ['crop-0018','crop-0055','crop-0056','crop-0014','crop-0016','crop-0017','crop-0024','crop-0019','crop-0020']:
 x=by[cid];add(x['page'],x['bbox'],'provisional reference',cid)
# Pick strong new scores, distributed across detector types and pages. The row
# that produced a candidate is kept only in the local key, never in the index.
for det in ['glyph_shape','missing_ink','spurious_ink','illustration_colour','border_inversion']:
 candidates=sorted((x for x in cand if x['detector']==det and x['score'] is not None),key=lambda x:x['score'],reverse=True)
 for x in candidates:
  if len(items)>=16:break
  if (x['page'],tuple(x['bbox'])) in prior_boxes:continue
  if add(x['page'],x['bbox'],'new detector candidate',{'detector':det,'row':x['row'],'score':x['score']}):break
# Fill any remaining candidate slots from top scores, skipping repeated boxes.
for x in sorted((x for x in cand if x['score'] is not None),key=lambda x:x['score'],reverse=True):
 if len(items)>=16:break
 if (x['page'],tuple(x['bbox'])) in prior_boxes:continue
 add(x['page'],x['bbox'],'new detector candidate',{'detector':x['detector'],'row':x['row'],'score':x['score']})
# Fixed-seed stratified controls exist separately; randomize the four selected
# for the human panel without publishing the choice-to-row linkage.
for x in rnd.sample(ctrl,len(ctrl)):
 if len(items)>=20:break
 add(x['page'],x['bbox'],'fresh random control',{'row':x['row']})
assert 16<=len(items)<=20
index=[];key={};body=[]
def uri(im):
 buf=io.BytesIO();im.save(buf,format='PNG');return 'data:image/png;base64,'+base64.b64encode(buf.getvalue()).decode()
options=['wrong character shape','missing ink','spurious ink/halo','blur/texture loss','colour shift','geometry only','no defect','unclear']
for n,item in enumerate(items,1):
 cid=f'panel-{n:03d}';id=item['page'];dpi=str(int(locks[id]['resolved_dpi']));p=geo[id];src=Image.open(B/p['src']['pdfium'][dpi]['aligned_render_path']).convert('RGB'); x0,y0,x1,y1=map(int,item['bbox']);pad=4;box=(max(0,x0-pad),max(0,y0-pad),min(src.width,x1+pad),min(src.height,y1+pad));order=rows[:];rnd.shuffle(order);mapping={chr(65+i):row for i,row in enumerate(order)};key[cid]={'labels':mapping,'private_origin':item['private_origin']};index.append({'panel_id':cid,'page':id,'bbox_source_pixels':box,'selection':item['selection'],'assessment':'AI-assessed, provisional (not human-adjudicated)'});im=src.crop(box);size=(im.width*4,im.height*4);parts=[f'<figure><figcaption>Source</figcaption><img alt="source" src="{uri(im.resize(size,Image.Resampling.NEAREST))}"></figure>'];src.close()
 for label,row in mapping.items():
  g=p[row]['pdfium'][dpi];im=Image.open(B/g['aligned_render_path']).convert('RGB').crop(box).resize(size,Image.Resampling.NEAREST);choices=''.join(f'<label><input type="checkbox" name="{cid}-{label}" value="{html.escape(o)}">{html.escape(o)}</label>' for o in options);parts.append(f'<figure><figcaption>Output {label}</figcaption><img alt="output {label}" src="{uri(im)}"><div class="choices">{choices}</div></figure>')
 body.append(f'<section><h2>{cid} — {html.escape(id)}</h2><p>Source-pixel box {box}; all output labels are independently shuffled for this crop.</p><div class="strip">'+''.join(parts)+'</div></section>')
header='''<!doctype html><html lang="en"><meta charset="utf-8"><title>BOOKS-01 blinded human panel</title><style>body{font:16px system-ui;max-width:98%;margin:auto}section{border-top:1px solid #bbb;padding:1em 0}.strip{display:flex;gap:12px;overflow-x:auto;align-items:start}figure{margin:0;flex:none}img{image-rendering:pixelated;max-width:none}.choices{display:grid;gap:2px;max-width:260px}label{font-size:13px}button{position:sticky;top:0;padding:.7em;background:#174c8c;color:white;z-index:2}textarea{width:100%;height:8em}</style><h1>Blinded visual confirmation panel</h1><p>Compare each labelled output to the source. Images are aligned globally and enlarged 4× with nearest-neighbour pixels. Mark all applicable categories for each output; leave blank if not assessed. One comparator is Acrobat with its default, unmatched OCR language, no Fraktur support and page straightening, but its labels are hidden. Prior assessments are AI-assessed, provisional (not human-adjudicated).</p><button id="copy">Copy responses as JSON</button><span id="message"></span><textarea id="fallback" aria-label="Responses JSON fallback" placeholder="Responses will appear here if clipboard access is unavailable"></textarea>'''
script='''<script>document.getElementById('copy').addEventListener('click',async()=>{const groups={};document.querySelectorAll('input[type=checkbox]').forEach(x=>{if(x.checked)(groups[x.name]??=[]).push(x.value)});const value=JSON.stringify({schema:'books01-human-panel-responses/1',responses:groups},null,2);document.getElementById('fallback').value=value;try{await navigator.clipboard.writeText(value);document.getElementById('message').textContent=' Copied.'}catch(e){document.getElementById('fallback').select();document.getElementById('message').textContent=' Select and copy the JSON below.'}})</script></html>'''
page=header+''.join(body)+script;(D/'index.html').write_text(page);(D/'key.json').write_text(json.dumps(key,indent=2)+'\n');(D/'key.json').chmod(0o600);(Q/'results/phase1b/human-panel-index.json').write_text(json.dumps({'html_sha256':hashlib.sha256((D/'index.html').read_bytes()).hexdigest(),'crop_count':len(index),'crops':index,'key':'local only; not committed','assessment':'AI-assessed, provisional (not human-adjudicated)'},indent=2)+'\n');print('panel created:',len(index),'crops; mapping stays local',flush=True)
