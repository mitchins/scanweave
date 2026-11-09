from pathlib import Path
import io,json,pikepdf,hashlib
base=Path('/data/coding/scanweave/qualification/acr06/local/ink37');rows=[]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def page_sizes(p):
 x=0
 for o in p.Resources.get('/XObject',{}).values():
  if str(o.get('/Subtype'))=='/Image':x+=len(o.read_raw_bytes())
 dest=pikepdf.Pdf.new();dest.pages.append(p); buf=io.BytesIO();dest.save(buf); dest.close();return x,len(buf.getvalue())
for d in ('historical','financial','mixed','receipts','forms'):
 a=base/'polarity37'/f'{d}-main.pdf';b=base/'owner37'/f'{d}.pdf'
 if not b.exists():continue
 z=json.loads(Path(str(b)+'.json').read_text());pdfs=[pikepdf.open(a),pikepdf.open(b)]
 for i,(x,y) in enumerate(zip(pdfs[0].pages,pdfs[1].pages)):
  r=z['conversion']['page_reports'][i]; mainimg,mainsize=page_sizes(x); candimg,candsize=page_sizes(y); count=r['polarity_visible_occurrences'];gate=r['polarity_raster_baseline']
  rows.append({'document':d,'page':i+1,'paper':r['polarity_paper_luminance'],'ink':r['polarity_ink_luminance'],'inverted':r['polarity_inverted'],'visible_main':count,'visible_candidate':0 if gate else count,'fallback':gate,'main_image_bytes':mainimg,'candidate_image_bytes':candimg,'main_isolated_page_bytes':mainsize,'candidate_isolated_page_bytes':candsize,'main_document_sha256':sha(a),'candidate_document_sha256':sha(b),'main_document_bytes':a.stat().st_size,'candidate_document_bytes':b.stat().st_size})
 for p in pdfs:p.close()
Path('/data/coding/scanweave/qualification/acr06/ink37/polarity37/owner-census.json').write_text(json.dumps(rows,indent=2)+'\n')
for r in rows:print(r['document'],r['page'],r['inverted'],r['visible_main'],r['fallback'],r['main_image_bytes'],r['candidate_image_bytes'],r['main_isolated_page_bytes'],r['candidate_isolated_page_bytes'])
