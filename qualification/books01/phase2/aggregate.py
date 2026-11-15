#!/usr/bin/env python3
"""Aggregate completed per-row scores and create local review examples."""
import collections,hashlib,io,json,math,pathlib,re,statistics
from PIL import Image,ImageChops,ImageDraw,ImageFilter,JpegImagePlugin
import pikepdf
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];D=B/'phase2';out=P/'phase2';pages=[x for x in json.loads((P/'corpus.frozen.json').read_text())['pages'] if x['split']=='dev'];assert len(pages)==36;locks=json.loads((P/'sources.lock.json').read_text())['pages'];rows=['src','sw-E','mrc-M','ocrmypdf-E','adobe-E'];records={};anomalies=[];scatter=[]
def med(x):
 x=[v for v in x if v is not None and math.isfinite(v)];return statistics.median(x) if x else None
def sec(path):
 try:
  t=pathlib.Path(path).read_text();cpu=[]
  for label in ['User time (seconds):','System time (seconds):']:
   m=re.search(re.escape(label)+r'\s*([\d.]+)',t);cpu.append(float(m.group(1)) if m else None)
  m=re.search(r'Maximum resident set size \(kbytes\):\s*(\d+)',t);return {'cpu_seconds':sum(cpu) if None not in cpu else None,'peak_rss_kib':int(m.group(1)) if m else None}
 except Exception:return {}
def background(path):
 try:
  with pikepdf.open(path) as pdf:
   page=pdf.pages[0];w=float(page.mediabox[2])-float(page.mediabox[0]);h=float(page.mediabox[3])-float(page.mediabox[1]);imgs=[o for o in pdf.objects if isinstance(o,pikepdf.Stream) and o.get('/Subtype')==pikepdf.Name('/Image') and not o.get('/ImageMask',False)];o=max(imgs,key=lambda x:int(x.get('/Width',0))*int(x.get('/Height',0)));iw=int(o.get('/Width',0));ih=int(o.get('/Height',0));v={'pixels':[iw,ih],'effective_dpi_assuming_page_fill':[iw*72/w,ih*72/h],'filter':str(o.get('/Filter','')),'bytes':len(o.read_raw_bytes()),'jpeg_quality':None,'jpeg_quality_note':'JPEG quantisation has no uniquely recoverable quality setting','jpeg_subsampling':None}
   if '/DCTDecode' in v['filter']:
    try:
     im=Image.open(io.BytesIO(o.read_raw_bytes()));v['jpeg_subsampling']=JpegImagePlugin.get_sampling(im);v['jpeg_quantization_table_sha256']=hashlib.sha256(json.dumps(im.quantization,sort_keys=True).encode()).hexdigest()
    except Exception as e:v['jpeg_inspection_error']=str(e)
   return v
 except Exception as e:return {'error':str(e)}
adobe_times={}
for dirname in ['adobe','adobe-p2']:
 f=B/'runs'/dirname/'timing.jsonl'
 if f.exists():
  for line in f.read_text().splitlines():
   try:
    item=json.loads(line);adobe_times[item['page']]=item
   except (ValueError,KeyError):pass
for p in pages:
 id=p['id'];key=id.split('/')[-1];f=D/'runs'/key/'runs.json';run=json.loads(f.read_text()) if f.exists() else {'rows':{},'error':'run record missing'};entry={'metadata':{'tags':p.get('tags',[]),'work':p['work'],'repo':p.get('repo'),'source_type':locks[id]['source_type'],'dpi_confidence':locks[id]['dpi_evidence']['confidence']},'rows':{},'run_error':run.get('error'),'source_pdf_sha256':run.get('source_pdf_sha256'),'selected_psm':run.get('selected_psm'),'hocr_sha256':run.get('hocr_sha256'),'raster_import':run.get('raster_import')};records[id]=entry
 for row in rows:
  q=D/'metrics'/key/(row+'.json');m=json.loads(q.read_text()) if q.exists() else {'status':'missing','reason':'score not produced'};entry['rows'][row]=m
  if row in run.get('rows',{}):
   x=run['rows'][row];m['conversion']={k:x.get(k) for k in ['status','wall_seconds','reused_pilot']};m['conversion'].update(sec(x.get('time_file','')))
  if row=='adobe-E' and key in adobe_times:
   z=adobe_times[key];m['conversion']={'status':z.get('rc'),'wall_seconds':z.get('wall_s'),'timing_scope':'GUI wall time includes fixed sleeps/startup; not comparable with CLI','cpu_seconds':None,'peak_rss_kib':None}
  if m.get('status')!='ok':anomalies.append({'page':id,'row':row,'kind':'missing_or_failed','detail':m.get('error') or m.get('reason') or (('Adobe GUI return code '+str(m.get('conversion',{}).get('status'))+'; output PDF missing') if row=='adobe-E' else 'score not produced')});continue
  if row!='src' and m.get('text',{}).get('empty'):anomalies.append({'page':id,'row':row,'kind':'empty_text_layer'})
  if m.get('geometry',{}).get('status')!='accepted':anomalies.append({'page':id,'row':row,'kind':'registration_unaccepted','detail':m.get('geometry',{}).get('reason')})
  a=m.get('aligned_fidelity',{}).get('text',{}).get('ssim');rec=m.get('aligned_fidelity',{}).get('text',{}).get('ink_recall');
  if a is not None and a<.80:anomalies.append({'page':id,'row':row,'kind':'text_ssim_below_0.80','value':a})
  scatter.append({'page':id,'row':row,'bytes':m['size']['file_bytes'],'text_ssim':a,'text_ink_recall':rec})
  if row in ['sw-E','mrc-M']:
   path=pathlib.Path(run['rows'][row]['path']);m['background_detail']=background(path)
 report=(B/'pilot/runs'/key/'sw-E.pdf.json') if run.get('rows',{}).get('sw-E',{}).get('reused_pilot') else (D/'runs'/key/'sw-E.pdf.json')
 if report.exists():
  j=json.loads(report.read_text());c=j['conversion'];pr=c['page_reports'][0];owners=collections.Counter(pr.get('semantic_owner',{}).values());n=sum(owners.values());entry['opportunity']={'ocr_words':j['pages'][0]['ocr_words'],'semantic_owner_counts':dict(owners),'visible_tounicode_fraction':owners.get('visible_tounicode',0)/n if n else None,'invisible_owner_fraction':owners.get('invisible',0)/n if n else None,'ownership_caveat':'semantic-owner count is reported spans; visible_tounicode is proxy for vector words, invisible spans may retain raster ink','text_ink_coverage':pr.get('coverage'),'sw_report_font_bytes':c.get('font_bytes'),'sw_report_raster_bytes':c.get('raster_encoded_bytes'),'sw_background':entry['rows'].get('sw-E',{}).get('background_detail'),'mrc_background':entry['rows'].get('mrc-M',{}).get('background_detail')}
  def bytes_for(row,prefix):
   return sum(v for k,v in entry['rows'].get(row,{}).get('size',{}).get('stream_bytes_by_category',{}).items() if k.startswith(prefix))
  entry['opportunity'].update(sw_background_bytes=bytes_for('sw-E','background_image:'),sw_foreground_bytes=bytes_for('sw-E','foreground_image:'),sw_font_program_bytes=bytes_for('sw-E','font_program'),mrc_background_bytes=bytes_for('mrc-M','background_image:'),mrc_mask_bytes=bytes_for('mrc-M','mask:'),mrc_background_plus_mask_bytes=bytes_for('mrc-M','background_image:')+bytes_for('mrc-M','mask:'))
# Stratifications: all, work/type, tags.
def group(p):
 if p['id'].startswith('finebooks/'):return 'FineBooks '+p['work']
 tags=p.get('tags',[]);return 'Quiver '+next((x for x in ['fraktur','fontmix','antiqua'] if x in tags),'unknown')
def tag_groups(p):
 t=' '.join(p.get('tags',[]));return [name for name,match in [('illustrations',any(x in t for x in ['woodcut','illustration','ornament','music'])),('tables','table' in t),('marginalia','marginalia' in t),('dark border/book edge','dark-border' in t or 'book-edge' in t)] if match]
groups={'overall':[p['id'] for p in pages]}
for p in pages:
 groups.setdefault(group(p),[]).append(p['id'])
 for k in tag_groups(p):groups.setdefault('tag: '+k,[]).append(p['id'])
 if p['id'].startswith('finebooks/'):
  # Per-volume categories are recorded separately; FineBooks tags are not supplied.
  pass
summary={}
for name,ids in groups.items():
 summary[name]={}
 for row in rows:
  mm=[records[id]['rows'][row] for id in ids if records[id]['rows'][row].get('status')=='ok'];f=lambda x:x.get('aligned_fidelity',{}).get('text',{});scores=lambda x:x.get('text',{}).get('scores',{}).get('reading',{});summary[name][row]={'n':len(mm),'bytes_total':sum(x['size']['file_bytes'] for x in mm),'bytes_median':med([x['size']['file_bytes'] for x in mm]),'aligned_text_ssim_median':med([f(x).get('ssim') for x in mm]),'aligned_text_ink_recall_median':med([f(x).get('ink_recall') for x in mm]),'aligned_illustration_ssim_median':med([x.get('aligned_fidelity',{}).get('illustration',{}).get('ssim') for x in mm]),'aligned_paper_ssim_median':med([x.get('aligned_fidelity',{}).get('paper',{}).get('ssim') for x in mm]),'reading_cer_median':med([scores(x).get('cer') for x in mm]),'reading_wer_median':med([scores(x).get('wer') for x in mm]),'nonempty_text':sum(not x.get('text',{}).get('empty',True) for x in mm),'literal_hits':sum(x.get('search',{}).get('literal_hits',0) for x in mm),'diplomatic_hits':sum(x.get('search',{}).get('diplomatic_variant_hits',0) for x in mm),'recognized_words':sum(x.get('search',{}).get('recognized_words',0) for x in mm),'conversion_wall_median':med([x.get('conversion',{}).get('wall_seconds') for x in mm])}
# Region-stratified medians use the same metadata groups and preserve all available metrics.
for name,ids in groups.items():
 for row in rows:
  samples=[records[id]['rows'][row] for id in ids if records[id]['rows'][row].get('status')=='ok']
  summary[name][row]['aligned_region_medians']={region:{field:med([x.get('aligned_fidelity',{}).get(region,{}).get(field) for x in samples]) for field in ['ssim','ink_recall','ink_precision','deltaE2000_mean']} for region in ['text','illustration','paper']}
  summary[name][row]['reading_bag_recall_median']=med([x.get('text',{}).get('scores',{}).get('reading',{}).get('bag_character_recall') for x in samples]);summary[name][row]['diplomatic_cer_median']=med([x.get('text',{}).get('scores',{}).get('diplomatic',{}).get('cer') for x in samples]);summary[name][row]['diplomatic_wer_median']=med([x.get('text',{}).get('scores',{}).get('diplomatic',{}).get('wer') for x in samples])
comparisons=[]
for id,v in records.items():
 sw=v['rows']['sw-E'];swf=sw.get('aligned_fidelity',{}).get('text',{});ss=swf.get('ssim');sr=swf.get('ink_recall')
 for row in ['mrc-M','ocrmypdf-E','adobe-E']:
  c=v['rows'][row];f=c.get('aligned_fidelity',{}).get('text',{});cs=f.get('ssim');cr=f.get('ink_recall')
  if None in [ss,sr,cs,cr] or sw.get('status')!='ok' or c.get('status')!='ok':continue
  smaller=c['size']['file_bytes']<sw['size']['file_bytes'];comparisons.append({'page':id,'competitor':row,'sw_better_both_by_0_01':ss>cs+.01 and sr>cr+.01,'smaller_competitor_matches_both_within_0_01':smaller and cs>=ss-.01 and cr>=sr-.01,'sw_bytes':sw['size']['file_bytes'],'competitor_bytes':c['size']['file_bytes'],'sw_text_ssim':ss,'competitor_text_ssim':cs,'sw_ink_recall':sr,'competitor_ink_recall':cr})
  if smaller and sw['size']['file_bytes']>=2*c['size']['file_bytes']:anomalies.append({'page':id,'row':'sw-E','kind':'twice_competitor_size','competitor':row,'ratio':sw['size']['file_bytes']/c['size']['file_bytes']})
# Flag unusually slow conversions and extraction deviations for inspection.
for id,v in records.items():
 for row in ['sw-E','mrc-M','ocrmypdf-E']:
  m=v['rows'][row];wall=m.get('conversion',{}).get('wall_seconds');median=summary['overall'][row]['conversion_wall_median']
  if wall is not None and median and wall>2*median:anomalies.append({'page':id,'row':row,'kind':'conversion_time_over_2x_median','wall_seconds':wall,'median_seconds':median})
 sw=v['rows']['sw-E'];frozen=sw.get('frozen_hocr_scores',{}).get('reading',{}).get('cer');extracted=sw.get('text',{}).get('scores',{}).get('reading',{}).get('cer')
 if frozen is not None and extracted is not None and extracted>frozen+.05:anomalies.append({'page':id,'row':'sw-E','kind':'document_cer_above_hocr_by_0.05','frozen_cer':frozen,'pdf_cer':extracted,'caveat':'text extraction or reading order requires inspection'})
# Representative and anomaly contact crops: aligned source-frame region, same crop in all rows.
exampledir=D/'examples';exampledir.mkdir(parents=True,exist_ok=True);representatives={}
for p in pages:representatives.setdefault(group(p),p['id'])
examplepages=set(representatives.values())|{x['page'] for x in anomalies};examplepaths={};exampleboxes={}
for id in sorted(examplepages):
 key=id.split('/')[-1];srcp=D/'renders'/key/'src'/'pdfium-native.png'
 if not srcp.exists():continue
 im=Image.open(srcp).convert('RGB');w,h=im.size;cx,cy=w//2,h//2
 # For visible fidelity anomalies, select the area with the largest low-resolution
 # aligned difference; time/size anomalies and representatives use the centre.
 visual=next((z for z in anomalies if z['page']==id and z['kind']=='text_ssim_below_0.80'),None)
 if visual:
  candidate=D/'renders'/key/visual['row']/'pdfium-aligned.png'
  if candidate.exists():
   thumb=im.convert('L').resize((96,96),Image.Resampling.BOX);other=Image.open(candidate).convert('L').resize((96,96),Image.Resampling.BOX);diff=ImageChops.difference(thumb,other).filter(ImageFilter.BoxBlur(2));maximum=max(diff.getdata());index=list(diff.getdata()).index(maximum);cx=round((index%96+.5)*w/96);cy=round((index//96+.5)*h/96)
 x0=max(0,min(w-1,cx-180));y0=max(0,min(h-1,cy-120));box=(x0,y0,min(w,x0+360),min(h,y0+240));exampleboxes[id]=list(box);cw=(box[2]-box[0])*2;ch=(box[3]-box[1])*2;sheet=Image.new('RGB',(cw*5,ch+25),'white');draw=ImageDraw.Draw(sheet)
 for n,row in enumerate(['src','sw-E','mrc-M','adobe-E','ocrmypdf-E']):
  draw.text((n*cw+4,4),row,fill='black');f=D/'renders'/key/row/('pdfium-native.png' if row=='src' else 'pdfium-aligned.png')
  if f.exists():sheet.paste(Image.open(f).convert('RGB').crop(box).resize((cw,ch),Image.Resampling.NEAREST),(n*cw,25))
  else:draw.text((n*cw+4,28),'missing or unregistered',fill='black')
 path=exampledir/(key+'.png');sheet.save(path);examplepaths[id]=str(path)
for x in anomalies:x['example']=examplepaths.get(x['page']);x['example_bbox_source_pixels']=exampleboxes.get(x['page'])
res={'pages':records,'groups':summary,'comparisons':comparisons,'scatter':scatter,'anomalies':anomalies,'representative_examples':{k:{'page':v,'path':examplepaths.get(v)} for k,v in representatives.items()},'notes':['Adobe default OCR language (not matched); no Fraktur support; page straightened (deskew).','FineBooks sources are lossy-origin processed derivatives.','Line matching inherits hOCR boxes for matched tracks and does not independently assess line order.','Image attribution uses largest non-mask image as background; effective DPI assumes page fill.','Automated detector suspicions are unreviewed.','Example crops use the same source-pixel region for all rows; low-text-SSIM examples target a low-resolution aligned difference, while other examples use the page centre. A crop may not establish the cause of an anomaly.']};(out/'results.json').write_text(json.dumps(res,indent=2,allow_nan=False)+'\n');print('aggregated',len(records),'pages',len(anomalies),'anomalies')
