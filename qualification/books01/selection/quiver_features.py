import sys,os,re,json,collections
import xml.etree.ElementTree as ET
root=sys.argv[1]; rows=[]
for dp,_,fs in os.walk(root):
  for f in sorted(fs):
    p=os.path.join(dp,f)
    if not f.endswith('.xml'): continue
    if f=='mets.xml':
      continue
    t=ET.parse(p).getroot(); ns={'pc':t.tag.split('}')[0][1:]}
    page=t.find('pc:Page',ns)
    reg=collections.Counter(); sub=collections.Counter(); fonts=collections.Counter(); langs=collections.Counter()
    for el in page.iter():
      tag=el.tag.split('}')[1]
      if tag.endswith('Region'):
        reg[tag]+=1
        if tag=='TextRegion': sub[el.get('type','?')]+=1
        if el.get('primaryLanguage'): langs[el.get('primaryLanguage')]+=1
      if tag in('TextStyle',) and el.get('fontFamily'): fonts[el.get('fontFamily')]+=1
      if tag=='TextRegion':
        cs=el.get('custom','');
    lines=sum(1 for e in page.iter() if e.tag.endswith('}TextLine'))
    chars=0
    for e in page.iter():
      if e.tag.endswith('}TextLine'):
        u=e.find('pc:TextEquiv/pc:Unicode',ns)
        if u is not None and u.text: chars+=len(u.text)
    repo=p[len(root)+1:].split('/')[0]; work=p.split('/data/')[1].split('/')[0]
    rows.append(dict(repo=repo,work=work,page=f[:-4],w=int(page.get('imageWidth')),h=int(page.get('imageHeight')),lines=lines,chars=chars,regions=dict(reg),text_types=dict(sub),langs=dict(langs)))
json.dump(rows,open(sys.argv[2],'w'),indent=1)
for r in rows: print(r['repo'],r['page'],f"{r['w']}x{r['h']}",'L',r['lines'],'C',r['chars'],{k.replace('Region',''):v for k,v in r['regions'].items() if k!='TextRegion'},r['text_types'])
