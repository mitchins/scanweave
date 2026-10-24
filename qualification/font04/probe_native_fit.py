"""Compare a native fit probe to frozen fits, without generating PDF or P2."""
import json,subprocess
from pathlib import Path
import numpy as np
from qualification.font04.freeze_method import BASE,ART,write

def prepare():
    fields=np.load(ART/'fields.npy');meta=json.loads((ART/'frames.json').read_text());out=json.loads((ART/'outlines.json').read_text())['records'];candidate=np.zeros_like(fields)
    for o in out:
        if 'gid' not in o:continue
        j=int(o['key'].rsplit('-',1)[1]);x,y=meta['origins'][j];candidate[j,y:y+o['height'],x:x+o['width']]=np.array(o['coverage']).reshape(o['height'],o['width'])
    directory=BASE/'local/native-fit';directory.mkdir(exist_ok=True)
    fields.astype('<f8').tofile(directory/'fields.bin');candidate.astype('<f8').tofile(directory/'candidates.bin')
    plan=json.loads((ART/'plan.json').read_text());pairs=json.loads((ART/'pair-ledger.json').read_text());lookup={(r['member'],r['canonical']):r for r in pairs}
    selected=[(a['member'],a['canonical']) for a in plan['assignments']]
    # Include all accepted fits and every rejected member's diagnostic attempt.
    selected+= [(r['member'],r['canonical']) for r in plan['rejection_ledger'] if 'canonical'in r]
    write(directory/'request.json',dict(fields=str((directory/'fields.bin').resolve()),candidates=str((directory/'candidates.bin').resolve()),pairs=selected))
    return directory

if __name__=='__main__':print(prepare())
