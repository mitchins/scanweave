"""Blinded real-document A0 versus F-self geometry review, exact native pages."""
from pathlib import Path
import json
import random
import subprocess
import sys
import numpy as np
from PIL import Image
from qualification.font04.causal import ROOT
from qualification.font04.metrics import render,sha
from qualification.font04.review_sheets import key_process


def main():
    root=ROOT/'financial';directory=Path('qualification/font04/local/review-A');directory.mkdir(exist_ok=True);assets=directory/'assets';assets.mkdir(exist_ok=True);rows=json.loads((root/'source.json').read_text())['rows'];records=json.loads((root/'evaluated.json').read_text())['records'];rng=random.Random(40412);selected=set(rng.sample(range(len(rows)),50))
    for page in range(13):
        available=[i for i,r in enumerate(rows)if r['page']==page];selected.update(rng.sample(available,min(2,len(available))))
    for engine in ['pdfium','poppler']:
        errors={r['id']:r['source']['error']for r in records if r['arm']=='F-self'and r['renderer']==engine};selected.update(sorted(range(len(rows)),key=lambda i:errors[rows[i]['id']],reverse=True)[:10])
    metadata=[]
    for engine in ['pdfium','poppler']:
        for page in range(13):
            source=render(root/'native-source.pdf',page,300,engine);baseline=render(root/'native-A0.pdf',page,300,engine);candidate=render(root/'native-F-self.pdf',page,300,engine)
            for i in sorted(selected):
                row=rows[i]
                if row['page']!=page:continue
                x,y,xx,yy=map(int,row['source']['bbox']);x-=6;y-=6;xx+=6;yy+=6;identifier=f'A-{i:03}-{engine}'
                for kind,image in [('source',source),('current',baseline),('candidate',candidate)]:Image.fromarray(image[y:yy,x:xx]).save(assets/(identifier+'-'+kind+'.png'))
                metadata.append(dict(id=identifier,type='phase-A',renderer=engine,member=i,source_id=row['id'],page=page,bounds=[x,y,xx,yy]))
    (directory/'panels.json').write_text(json.dumps(metadata,indent=2));key_process([r['id']for r in metadata],directory/'sealed-key.json');subprocess.run([sys.executable,str(Path(__file__).with_name('review_key.py')),'render',str(directory)],check=True)
    manifest=dict(status='independent judgments pending; key sealed',members=len(selected),panels=len(metadata),pdf=str(directory/'blinded-review.pdf'),sha256=sha(directory/'blinded-review.pdf'),both_renderers=True,encoding='lossless RGB Flate',scale='100% and 400% physical',comparison='A0 emitted geometry versus F-self, ownership-normalized source at exact original page transform')
    Path('qualification/font04/review-A-manifest.json').write_text(json.dumps(manifest,indent=2));print(manifest)


if __name__=='__main__':main()
