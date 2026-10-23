"""Null replacement must preserve every page pixel, including ink/color/order."""
from pathlib import Path
import json
import numpy as np
from qualification.font04.context_instances import contextual_instances
from qualification.font04.class_metrics import bind
from qualification.font04.metrics import inspect,render,sha

def main():
    base=Path('qualification/font04');root=base/'local';pdf=root/'financial-default.pdf';snapshot=json.loads((root/'financial-B2-P-initial.pdf.font04/source.json').read_text());bound=bind(snapshot,inspect(pdf));dest=root/'B2prime-context-null-control.pdf';pages=contextual_instances(pdf,pdf,dest,snapshot['rows'],{0,3422},bound);results=[]
    for i,page in pages.items():
        for engine in ['pdfium','poppler']:
            a=render(pdf,snapshot['rows'][i]['page'],300,engine);b=render(dest,page,300,engine);changed=int(np.count_nonzero(a!=b));assert changed==0,(i,engine,changed);results.append(dict(member=i,renderer=engine,changed_pixels=changed))
    (base/'b2prime-review-context-null.json').write_text(json.dumps(dict(pdf=str(dest),sha256=sha(dest),results=results,pass_all=True,meaning='Replacing a target with the exact current program at its original content-stream position preserves the complete page, not only a crop.'),indent=2)+'\n');print('Context null PASS',len(results),flush=True)

if __name__=='__main__':main()
