"""Bounded genuine development corpus; no synthetic oracle pages."""
import json,urllib.request,hashlib,subprocess,shutil
from pathlib import Path
import pikepdf
from PIL import Image

NATIVE_PDF_GEOMETRY = 'PDF native physical geometry'
LINN_SOURCE_PDF = 'c03-29.pdf'

B=Path(__file__).resolve().parent;R=B.parents[1];D=B/'corpus';D.mkdir(exist_ok=True);rows=[]
def fetch(url,name):
 p=D/name
 if not p.exists():p.write_bytes(urllib.request.urlopen(url,timeout=90).read())
 return p

def imagepdf(p,out,dpi=300):
 im=Image.open(p).convert('RGB'); w,h=im.size
 q=pikepdf.Pdf.new();pg=q.add_blank_page(page_size=(w*72/dpi,h*72/dpi));s=pikepdf.Stream(q,im.tobytes());s.Type=pikepdf.Name.XObject;s.Subtype=pikepdf.Name.Image;s.Width=w;s.Height=h;s.ColorSpace=pikepdf.Name.DeviceRGB;s.BitsPerComponent=8
 pg.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im=s));pg.Contents=pikepdf.Stream(q,f'q {w*72/dpi} 0 0 {h*72/dpi} 0 0 cm /Im Do Q'.encode());q.save(out)
old=R/'qualification/clearscan_competitive/real'
if not all((old/f'cord-{i:02}.png').exists() for i in range(10)) or not all((old/f'history-{i:02}.png').exists() for i in range(5)):
 from fetch_originals import fetch
 fetch();old=B/'originals'
orig=json.loads((old/'downloads.json').read_text())
for p in sorted(old.glob('*.png')):
 if '.ocr-crop' in p.name or not (p.stem.startswith('cord-') or p.stem.startswith('history-')):continue
 out=D/(p.stem+'.pdf');imagepdf(p,out)
 source=next((a for a in orig if Path(a['name']).stem==p.stem),{})
 rows.append({'id':p.stem,'kind':'receipt' if p.stem.startswith('cord') else 'historical book','source':str(p.relative_to(R)),'origin':source.get('url'),'license':'CC-BY-4.0' if p.stem.startswith('cord') else 'CC-BY-SA-4.0','dpi':'nominal 300; capture DPI unknown'})
# Public-domain 1920 town annual report: original scanned pages, financial statements and forms.
u='https://archive.org/download/annualreport1920ipsw/annualreport1920ipsw.pdf';annual=fetch(u,'annualreport1920ipsw.pdf');q=pikepdf.open(annual)
# Disjoint development pages; inspect contact sheet to classify, retain fixed indexes.
for index in [10,20,30,40,50,60,70,80,90,100,110,120,130]:
 if index>=len(q.pages):continue
 out=D/f'annual-{index+1:03}.pdf';t=pikepdf.Pdf.new();t.pages.append(q.pages[index]);t.save(out)
 rows.append({'id':out.stem,'kind':'historical annual report / financial statement','source_pdf_page':index+1,'origin':u,'license':'Public domain (1920 US government town report)','rights_reference':'https://commons.wikimedia.org/wiki/File:Annual_report_(IA_annualreport1920ipsw).pdf','dpi':NATIVE_PDF_GEOMETRY})
# Scanned pages in OCRmyPDF development resources, explicitly licensed per REUSE.
base='https://raw.githubusercontent.com/ocrmypdf/OCRmyPDF/main/'
for name in ['REUSE.toml','tests/resources/README.rst']:
 try:fetch(base+name,Path(name).name)
 except Exception as e:print(name,str(e))
for name in [LINN_SOURCE_PDF,'linn.pdf']:
 try:
  p=fetch(base+'tests/resources/'+name,'ocrmypdf-'+name);q=pikepdf.open(p);t=pikepdf.Pdf.new();t.pages.append(q.pages[0]);out=D/('scan-'+Path(name).stem+'.pdf');t.save(out)
  rows.append({'id':out.stem,'kind':'illustrated book' if name==LINN_SOURCE_PDF else 'scanned mixed-artwork product brochure','origin':base+'tests/resources/'+name,'license':'Public domain (Mark Twain source scan)' if name==LINN_SOURCE_PDF else 'CC-BY-SA-3.0; Forat Electronics (1985); see frozen REUSE.toml','dpi':NATIVE_PDF_GEOMETRY})
 except Exception as e:print(name,str(e))
# Genuine scanned federal procurement form, not a born-digital form fixture.
u='https://www.archives.gov/files/foia/pdf/1940-census.pdf'
p=fetch(u,'nara-1940-census.pdf');q=pikepdf.open(p)
for index in [0,1]:
 out=D/f'nara-form-{index+1:02}.pdf';t=pikepdf.Pdf.new();t.pages.append(q.pages[index]);t.save(out)
 rows.append({'id':out.stem,'kind':'scanned completed procurement form','source_pdf_page':index+1,'origin':u,'license':'US federal government record; public domain','dpi':NATIVE_PDF_GEOMETRY})
for row in rows:
 p=D/(row['id']+'.pdf');row.update(input_pdf=str(p.relative_to(R)),input_bytes=p.stat().st_size,sha256=hashlib.sha256(p.read_bytes()).hexdigest())
(B/'corpus.json').write_text(json.dumps(rows,indent=2));print('pages',len(rows))
