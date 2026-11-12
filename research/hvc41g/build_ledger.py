"""Join all 38 glyph, ownership, topology and halo measurements."""
import hashlib,json,pathlib
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41g';L=R/'local/hvc41g';read=lambda name:json.loads((E/name).read_text());freeze=read('freeze.json');assert hashlib.sha256((L/'historical-frozen.pdf').read_bytes()).hexdigest()==freeze['pdf_sha256'];pre={x['proposal']:x for x in read('preflight.json')['glyphs']};actual={x['proposal']:x for x in read('qualification-glyphs.json')['glyphs']};patch={x['proposal']:x for x in read('qualification-patches.json')['glyphs']};geometry={x['proposal']:x for x in read('preflight-build.json')['glyphs']};halos=read('qualification-halo.json');render=read('qualification-render.json');out=[]
for proposal in sorted(pre):
 exception=[]
 for z in render:
  if z['page']==1 and z['comparison']=='candidate':
   for v in z['beyond_xy_delta_luma']:
    if v['nearest_glyph']==proposal:exception.append({'engine':z['engine'],'dpi':z['dpi'],**v})
 out.append({'proposal':proposal,'preflight':pre[proposal],'actual_vector_and_frozen_validator':actual[proposal],'patch':patch[proposal],'geometry':geometry[proposal],'halo':[x for x in halos if x['proposal']==proposal],'nearest_beyond_band_exceptions':exception})
assert len(out)==38 and all(not x['patch']['patch_outside_owned'] and x['actual_vector_and_frozen_validator']['validator']['pass'] for x in out)
(E/'glyph-ledger.json').write_text(json.dumps(out,indent=2)+'\n');print('glyph ledger',len(out))
