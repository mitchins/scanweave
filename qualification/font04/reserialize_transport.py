"""Validate that serializer controls leave every painted and invisible draw exact."""
from pathlib import Path
import json,shutil
from qualification.font04.metrics import inspect,sha
ROOT=Path('qualification/font04/local')

def main():
    old=ROOT/'financial-B2prime-transport.pdf';new=ROOT/'financial-B2prime-transport-serialized.pdf';a=inspect(old);b=inspect(new)
    def signature(inv):return [{k:d[k] for k in ['page','cid','gid','font_hash','character','matrix','program','invisible']} for d in inv['users']]
    assert signature(a)==signature(b),'serialization changed a used glyph or text matrix'
    prior=ROOT/'financial-B2prime-transport-dense-maps.pdf';shutil.copyfile(old,prior);old_sha=sha(old);new_sha=sha(new);shutil.copyfile(new,old);art=Path(str(old)+'.font04')
    for p in [art/'class-metrics.json',Path('qualification/font04/financial-B2prime-transport-class-scorecard.json')]:
        m=json.loads(p.read_text());assert m['sha256']==old_sha;m.update(sha256=new_sha,bytes=old.stat().st_size,serialization_replay=dict(measured_sha256=old_sha,every_visible_and_invisible_CID_GID_program_font_and_matrix_exact=True,previous_pdf=str(prior)));p.write_text(json.dumps(m,indent=2)+'\n')
    eq=Path('qualification/font04/b2prime-measurement-equivalence.json');m=json.loads(eq.read_text());m['serialization_replay_sha256']=new_sha;eq.write_text(json.dumps(m,indent=2)+'\n')
    report=dict(before_pdf=str(prior),before_sha256=old_sha,after_pdf=str(old),after_sha256=new_sha,draw_signature_exact=True,users=len(a['users']),before_bytes=prior.stat().st_size,after_bytes=old.stat().st_size,changes='Unused CID map entries zeroed; new dictionaries and shared width array compressed in generated object streams. Actual font stream and all used mappings exact.')
    Path('qualification/font04/b2prime-serialization-equivalence.json').write_text(json.dumps(report,indent=2)+'\n');shutil.copyfile(Path(str(new)+'.transport.json'),art/'byte-attribution.json');print(report)

if __name__=='__main__':main()
