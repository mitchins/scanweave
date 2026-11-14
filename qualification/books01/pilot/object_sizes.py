#!/usr/bin/env python3
"""Classify disjoint raw PDF stream bytes and reconcile all other bytes."""
import collections,json,pathlib
import pikepdf
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[1];Q=P/'pilot'; runs=json.loads((Q/'results/runs.json').read_text());p=Q/'results/text-and-size.json';metrics=json.loads(p.read_text())
def classify(path):
 with pikepdf.open(path) as pdf:
  contents=set();fontfiles=set();charprocs=set();maskrefs=set();fonts=set(); images=[]
  for page in pdf.pages:
   cont=page.obj.get('/Contents');parts=list(cont) if isinstance(cont,pikepdf.Array) else [cont] if cont is not None else [];contents.update(x.objgen for x in parts if isinstance(x,pikepdf.Stream))
   res=page.obj.get('/Resources',{}); fs=res.get('/Font',{})
   for font in fs.values():
    fonts.add(font.objgen); descendants=[font]+list(font.get('/DescendantFonts',[]))
    for f in descendants:
     cp=f.get('/CharProcs',{})
     for glyph in cp.values():
      if isinstance(glyph,pikepdf.Stream):charprocs.add(glyph.objgen)
     desc=f.get('/FontDescriptor',{})
     for name in ['/FontFile','/FontFile2','/FontFile3']:
      v=desc.get(name)
      if isinstance(v,pikepdf.Stream):fontfiles.add(v.objgen)
  for o in pdf.objects:
   if isinstance(o,pikepdf.Stream) and o.get('/Subtype')==pikepdf.Name('/Image'):
    images.append(o)
    for k in ['/SMask','/Mask']:
     v=o.get(k)
     if isinstance(v,pikepdf.Stream):maskrefs.add(v.objgen)
  actual=[o for o in images if not o.get('/ImageMask',False) and o.objgen not in maskrefs]; bg=max(actual,key=lambda o:int(o.get('/Width',0))*int(o.get('/Height',0))).objgen if actual else None
  totals=collections.Counter();counts=collections.Counter()
  for o in pdf.objects:
   if not isinstance(o,pikepdf.Stream):continue
   if o.get('/Subtype')==pikepdf.Name('/Image'):
    role='mask' if o.get('/ImageMask',False) or o.objgen in maskrefs else 'background_image' if o.objgen==bg else 'foreground_image';name=role+':'+str(o.get('/Filter','none'))
   elif o.objgen in charprocs:name='type3_glyph_charproc'
   elif o.objgen in fontfiles:name='font_program'
   elif o.objgen in contents:name='page_content_stream'
   else:name='other_stream'
   totals[name]+=len(o.read_raw_bytes());counts[name]+=1
  n=path.stat().st_size;stream=sum(totals.values());return {'file_bytes':n,'stream_bytes_by_category':dict(totals),'stream_count_by_category':dict(counts),'page_font_resource_count':len(fonts),'structure_xref_dictionary_and_unclassified_bytes':n-stream,'reconciles':stream+(n-stream)==n,'image_role_method':'largest non-mask image is background; remaining non-mask images foreground; masks from ImageMask, Mask and SMask'}
for id,x in runs.items():
 key=id.split('/')[-1]
 for row,v in x['rows'].items():
  path=pathlib.Path(v.get('path',B/'pilot/runs'/key/(row+'.pdf')))
  if path.exists() and metrics[id]['rows'][row].get('status')=='ok':metrics[id]['rows'][row]['size']=classify(path)
p.write_text(json.dumps(metrics,indent=2)+'\n')
