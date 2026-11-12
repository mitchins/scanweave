"""Record frozen input, emitted geometry and identical Phase A patch bytes."""
import hashlib,json,pathlib,sys
import numpy as np,pikepdf
from PIL import Image
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f';sha=lambda b:hashlib.sha256(b).hexdigest()
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'hvc41d'))
from pdf_font import pdf_path
from ownership_guard import require_owned
ledger=R/'hvc41e/review-decisions.json';final=R/'local/hvc41e/final/historical-composed.pdf';base=R/'local/ink33r/historical.pdf';assert sha(ledger.read_bytes())=='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef';assert sha(final.read_bytes())=='9e8b3493a3256dd4cf57e3f5816abb86be367b96b5cd770942dfea8c1547a9e0';assert sha(base.read_bytes())=='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b'
rows=[r for r in json.loads(ledger.read_text()) if r['decision']=='accept'];assert len(rows)==38;outlines=json.loads((R/'local/hvc41b/interior/p000001-outlines.json').read_text())['outlines'];out=[]
with pikepdf.open(final) as p:
 pat=p.pages[0].Resources.Pattern['/Research41E'];font=pat.Resources.Font.FR;lines=pat.read_bytes().decode().splitlines();patch=p.pages[0].Contents[1].read_bytes()
 for j,r in enumerate(rows,1):
  g=outlines[r['proposal']];path=pdf_path(g['path_svg']);assert font.CharProcs[f'/g{j}'].read_bytes()==('2048 0 d0 '+path+' f').encode();rgb=' '.join(f'{x/255:.8f}' for x in r['fill_rgb']);mat=' '.join(str(x) for x in g['matrix']);assert lines[j-1]==f'BT /FR 1 Tf {rgb} rg {mat} Tm <{j:02x}> Tj ET'
  masks={}
  for k in ('owner','patch'):
   spec=r['masks'][k];blob=pathlib.Path(spec['path']).read_bytes();assert sha(blob)==spec['sha256'];masks[k]=np.asarray(Image.open(pathlib.Path(spec['path'])).convert('L'))>0
  require_owned(masks['patch'],masks['owner']);item={'proposal':r['proposal'],'frozen_outline_matrix_fill_match':True,'patch_outside_owned':int((masks['patch']&~masks['owner']).sum())}
  if r['proposal'] in (18,38,243):
   hashes={};inside=None
   for v in ('A0','A1','A2','A3'):
    with pikepdf.open(L/f'{v}-{r["proposal"]:03}.pdf') as q:
     st=q.pages[0].Contents[1];hashes[v]=sha(st.read_raw_bytes());inside=b'\n'.join(st.read_bytes().splitlines()[1:-1]) in patch
   assert len(set(hashes.values()))==1 and inside;item.update(raw_patch_sha256_by_variant=hashes,patch_operations_in_hvc41e_final=inside)
  out.append(item)
assert not (L/'ocr-invoked').exists();(E/'verified-inputs.json').write_text(json.dumps({'glyphs':out,'ocr_stub_not_invoked':True},indent=2)+'\n');print('verified',len(out),'glyphs')
