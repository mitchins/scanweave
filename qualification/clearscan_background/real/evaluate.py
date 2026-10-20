"""Full-page development sample audit; no fabricated pristine-font truth."""
import json, re, subprocess, sys, hashlib, argparse
from pathlib import Path
from collections import Counter
import numpy as np
from PIL import Image, ImageDraw
import pypdfium2 as pdfium
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compare import accounting

ROOT=Path(__file__).resolve().parents[3]
B = ROOT/'qualification/clearscan_competitive/real'
ap=argparse.ArgumentParser();ap.add_argument('arm',nargs='?',default='delivered');args=ap.parse_args()
out = ROOT/'qualification/clearscan_background/real'/args.arm
rows = []
for run in json.loads((out/'runs.json').read_text()):
    name = run['name']; path = out/(name+'.pdf')
    if run['returncode'] != 0: raise RuntimeError(run)
    report = json.loads(path.with_suffix('.json').read_text())
    row = dict(run); row.update(accounting(path))
    row['observations'] = len(report['reconstruction']['observations'])
    row['vector_ink_px'] = report['coverage']['text_ink_px_vector']
    row['source_ink_suppressed_px'] = report['raster_ink_pixels_suppressed']
    row['coverage'] = report['coverage']
    row['supplied_chars'] = report['supplied_chars']
    row['source_sha256'] = hashlib.sha256((B/(name+'.png')).read_bytes()).hexdigest()
    row['rss_kb'] = int(re.search(r'Maximum resident set size \(kbytes\): (\d+)', (out/(name+'.time.txt')).read_text())[1])
    text = subprocess.check_output(['pdftotext','-raw',str(path),'-'],text=True)
    doc = pdfium.PdfDocument(str(path)); pt = doc[0].get_textpage(); pdftext = pt.get_text_range()
    row['poppler_text'] = text; row['pdfium_text'] = pdftext
    norm = lambda t: re.sub(r'\s+', '', t)
    row['renderer_text_equal'] = norm(text) == norm(pdftext)
    row['native_search'] = []
    for token in re.findall(r'[A-Za-z0-9]{4,}',pdftext)[:3]:
        search = pt.search(token); row['native_search'].append({'token':token,'found':search.get_next() is not None})
    # At 150 DPI the complete original page, not an OCR crop, is compared.
    stem = out/(name+'.poppler')
    subprocess.run(['pdftoppm','-r','150','-singlefile','-png',str(path),str(stem)],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    pop = Image.open(str(stem)+'.png').convert('RGB')
    py = doc[0].render(scale=150/72).to_pil().convert('RGB');py.save(out/(name+'.pdfium.png'))
    source = Image.open(B/(name+'.png')).convert('RGB').resize(py.size, Image.Resampling.LANCZOS)
    panels = [source,pop.resize(py.size),py]
    row['source_relative_mae_150dpi'] = {k:float(np.abs(np.asarray(img,dtype=float)-np.asarray(source,dtype=float)).mean()) for k,img in zip(['poppler','pdfium'],panels[1:])}
    row['renderer_mae_150dpi'] = float(np.abs(np.asarray(panels[1],dtype=float)-np.asarray(py,dtype=float)).mean())
    panel = Image.new('RGB',(py.width*3,py.height+24),'white')
    for i,(label,img) in enumerate(zip(['source','Poppler','PDFium'],panels)):
        panel.paste(img,(i*py.width,24));ImageDraw.Draw(panel).text((i*py.width+4,4),label,fill='black')
    panel.thumbnail((1800,1800));panel.save(out/(name+'.comparison.png'))
    rows.append(row);(out/'metrics.json').write_text(json.dumps(rows,indent=2,ensure_ascii=False)+'\n')
    print(name,row['bytes'],row['observations'],row['vector_ink_px'],flush=True)
