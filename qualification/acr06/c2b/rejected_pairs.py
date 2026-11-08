import json,re,html
from pathlib import Path
from PIL import Image,ImageDraw
from lxml import etree
r=Path('/data/coding/scanweave/qualification/acr06/local/c2b/trace'); d=json.load(open(r/'p2-6.pdf.funnel.json')); side=json.load(open(r/'p2-6.pdf.json')); root=etree.fromstring(side['pages'][0]['hocr'].encode(),etree.XMLParser(recover=True,resolve_entities=False,no_network=True)); words=root.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_word ")]'); im=Image.open('/data/coding/scanweave/qualification/font04/local/P2/p2/page-2-0.png').convert('RGB'); rows=d['rows']; selected=[]
for row in rows:
 i=row['member']; fs=[f for f in d['fits'] if f['member']==i and f['canonical']!=i and not f['reasons'] and rows[f['canonical']]['band']==row['band'] and not rows[f['canonical']]['hygiene'] and f['error']/max(row['floor'],1e-6)<=2];
 if fs:
  f=min(fs,key=lambda x:x['error'])
  if .08<f['error']<.3 and re.fullmatch(r'w\d+s\d+',row['id']) and re.fullmatch(r'w\d+s\d+',rows[f['canonical']]['id']):selected.append((f['error'],i,f['canonical']))
selected=sorted(selected,reverse=True)[:12]; canvas=Image.new('RGB',(900,100*len(selected)),'white'); draw=ImageDraw.Draw(canvas)
def crop(i):
 m=re.fullmatch(r'w(\d+)s(\d+)',rows[i]['id']);w,c=map(int,m.groups()); word=words[w]; chars=word.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," ocrx_cinfo ")]'); t=chars[c].get('title'); box=list(map(int,re.search(r'x_bboxes (\d+) (\d+) (\d+) (\d+)',t).groups())); box=[box[0]-4,box[1]-4,box[2]+4,box[3]+4];return im.crop(box)
for k,(err,i,j) in enumerate(selected):
 try:
  a,b=crop(i),crop(j); a.thumbnail((200,80));b.thumbnail((200,80));canvas.paste(a,(0,k*100));canvas.paste(b,(240,k*100));draw.text((470,k*100+5),f"{rows[i]['label']} {rows[i]['id']} vs {rows[j]['id']} err={err:.3f}",fill='black')
 except Exception as e:draw.text((470,k*100+5),str(e),fill='red')
canvas.save('/data/coding/scanweave/qualification/acr06/local/c2b/rejected-pairs.png')
