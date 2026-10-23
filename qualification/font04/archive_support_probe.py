"""Preserve the first sweep as a fully scored diagnostic, never overwrite evidence."""
from pathlib import Path
import json,shutil,time
BASE=Path('qualification/font04');ROOT=BASE/'local'

def main():
    points=json.loads((BASE/'b2prime-points.json').read_text())['points']
    while True:
        try:
            ready=all(json.loads((BASE/(Path(p['pdf']).stem+'-verification.json')).read_text())['pass'] for p in points) and (BASE/'b2prime-actual-owned-and-determinism.json').exists()
        except (FileNotFoundError,json.JSONDecodeError):ready=False
        if ready:break
        time.sleep(2)
    receipt=[]
    def move(old,new):
        if old.exists():
            assert not new.exists(),str(new);shutil.move(old,new);receipt.append(dict(before=str(old),after=str(new)))
    archived=[]
    for point in points:
        path=Path(point['pdf']);new=ROOT/path.name.replace('financial-B2prime-','financial-B2prime-support-initial-',1)
        move(path,new);move(Path(str(path)+'.font04'),Path(str(new)+'.font04'));move(ROOT/(path.stem+'-repeat.pdf'),ROOT/(new.stem+'-repeat.pdf'))
        for suffix in ['-class-scorecard.json','-verification.json']:move(BASE/(path.stem+suffix),BASE/(new.stem+suffix))
        for suffix in ['.ttf','.ttf.sanitized']:move(Path(str(path)+suffix),Path(str(new)+suffix))
        oldtag='B2prime-'+point['label'];newtag='B2prime-support-initial-'+point['label']
        for suffix in ['-ownership-control.pdf','-owned.json','-metrics.log','-metrics-profile.json','-verification.log']:move(ROOT/(oldtag+suffix),ROOT/(newtag+suffix))
        oldprefix=str(path);newprefix=str(new)
        # Relocate only artifact metadata; measurement values are unchanged.
        for p in [Path(str(new)+'.font04')/'class-metrics.json',Path(str(new)+'.font04')/'byte-attribution.json',Path(str(new)+'.font04')/'verification.json',BASE/(new.stem+'-class-scorecard.json'),BASE/(new.stem+'-verification.json')]:
            if p.exists():
                data=json.loads(p.read_text())
                if data.get('pdf')==oldprefix:data['pdf']=newprefix
                data['relocation_note']='First sweep retained as diagnostic: missing fallback floors still indirectly gated 378 members. Original hashes/measurements unchanged.';p.write_text(json.dumps(data,indent=2)+'\n')
        archived.append(dict(point,pdf=str(new),label='support-initial-'+point['label'],ownership_control=point['ownership_control'].replace(oldtag,newtag)))
    for name in ['b2prime-points.json','b2prime-byte-attribution.json','b2prime-actual-owned-and-determinism.json']:move(BASE/name,BASE/name.replace('b2prime-','b2prime-support-initial-',1))
    (BASE/'b2prime-support-initial-points.json').write_text(json.dumps(dict(points=archived,status='diagnostic; superseded by no-support-gate sweep',initial_floor_counts=dict(individual_LOO=1705,class_weight_band_median=1441,missing=378)),indent=2)+'\n');(BASE/'b2prime-support-probe-relocations.json').write_text(json.dumps(dict(relocations=receipt,reason='Algorithm correction required by review §6.3; retain complete tested PDFs and B2-format measurements.'),indent=2)+'\n');print('Archived initial support probe',len(points),flush=True)

if __name__=='__main__':main()
