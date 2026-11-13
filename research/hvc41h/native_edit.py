"""Apply source-supported paper only where native cells are fully owned."""
import hashlib,json,os,pathlib,sys
import numpy as np
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41h';L=R/'local/hvc41h';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41H_PREPARE')!='1':sys.exit('research switch required')
ledger=R/'hvc41e/review-decisions.json';base=R/'local/ink33r/historical.pdf';g=R/'local/hvc41g/historical-frozen.pdf'
if sha(ledger.read_bytes())!='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef' or sha(base.read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b' or sha(g.read_bytes())!='e408daab686fd47f05451627620a79dc8770e5c299654eba4f76bb5454ef7a4b':sys.exit('frozen hashes differ')
prep=json.loads((E/'prepared.json').read_text());assert sha((R/'local/ink33r/renders/historical/01-source.png').read_bytes())==prep['source_png_sha256_before_after'];native=np.asarray(Image.open(L/'control-resized.png').convert('RGB'));edited=native.copy();masks=np.load(L/'native-masks.npz')['full'];assert native.shape==(1569,1158,3) and masks.shape==(38,1569,1158)
for i,glyph in enumerate(prep['glyphs']):edited[masks[i]]=glyph['paper_rgb']
changed=np.any(native!=edited,axis=2);allowed=masks.any(axis=0)
if (changed&~allowed).any():sys.exit('native ownership violation')
Image.fromarray(edited).save(L/'native-owned-edited.png');(E/'native-prepared.json').write_text(json.dumps({'unencoded_control_rgb_sha256':sha(native.tobytes()),'edited_rgb_sha256':sha(edited.tobytes()),'changed_native_pixels':int(changed.sum()),'allowed_native_pixels':int(allowed.sum()),'changed_outside_owned':int((changed&~allowed).sum())},indent=2)+'\n');print('native ownership pixels',int(allowed.sum()),'changed',int(changed.sum()))
