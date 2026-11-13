import sys,json,collections,re
import pyarrow.parquet as pq
import xml.etree.ElementTree as ET
t=pq.read_table(sys.argv[1],columns=['PageID','BarCode','xml','xml_path','text']).to_pylist()
rows=[]
for r in t:
  x=ET.fromstring(r['xml'].encode()); ns=x.tag.split('}')[0][1:]
  pg=x.find(f'{{{ns}}}Page')
  reg=collections.Counter(); ty=collections.Counter()
  for e in pg.iter():
    tag=e.tag.split('}')[1]
    if tag.endswith('Region'):
      reg[tag]+=1
      if tag=='TextRegion': ty[e.get('type','?')]+=1
  txt=r['text'] or ''
  rows.append(dict(book=r['BarCode'],page=r['PageID'],xml=r['xml_path'].rsplit('/',1)[1],w=int(pg.get('imageWidth')),h=int(pg.get('imageHeight')),chars=len(txt),fffd=txt.count('�'),regions=dict(reg),types=dict(ty)))
json.dump(rows,open(sys.argv[2],'w'))
bk=collections.defaultdict(list)
for r in rows: bk[r['book']].append(r)
for b,rs in bk.items():
  reg=collections.Counter(); ty=collections.Counter()
  for r in rs: reg.update(r['regions']); ty.update(r['types'])
  ws=sorted(r['w'] for r in rs)
  print(b,len(rs),'w',ws[0],ws[-1],'imgpages',sum(1 for r in rs if r['regions'].get('ImageRegion') or r['regions'].get('GraphicRegion')),'tablepages',sum(1 for r in rs if r['regions'].get('TableRegion')),'lowtext',sum(1 for r in rs if r['chars']<200),'fffdpages',sum(1 for r in rs if r['fffd']),dict(reg),dict(ty))
