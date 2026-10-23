"""Reuse frozen source/traces, change only line-frame bbox inverse, rerun A."""
from pathlib import Path
import json,os,shutil,subprocess,sys
from qualification.font04.planner import frame_bbox

BASE=Path('qualification/font04/local')

def main():
    for name in ['causal','causal-extension']:
        old=BASE/name;new=BASE/('prime-'+name)
        if new.exists():raise RuntimeError('Refuse to overwrite an existing Phase A rerun')
        shutil.copytree(old,new)
        for split in ['train','validation','test']+(['financial'] if name=='causal' else []):
            path=new/split/'source.json';data=json.loads(path.read_text())
            for r in data['rows']:
                for kind,t in r['trace'].items():
                    if not kind.startswith('line-'):continue
                    x,y=t['origin'];f=r['frame'];b=t['bbox']
                    # Width/height are physical spans and do not change.
                    w=(b[2]-b[0])*f['scale'];h=(b[3]-b[1])*f['scale']
                    t['bbox']=frame_bbox(f,(x,y),(w,h))
            path.write_text(json.dumps(data))
            env=dict(os.environ,FONT04_CAUSAL_ROOT=str(new))
            for action in ['atlas']+([] if split=='financial' else ['evaluate']):
                subprocess.run([sys.executable,'-m','qualification.font04.causal',action,split],env=env,check=True)
            if split=='financial':subprocess.run([sys.executable,'-m','qualification.font04.causal_financial_native'],env=env,check=True)
    from qualification.font04.floor_control import evaluate
    for name in ['prime-causal','prime-causal-extension']:
        for split in ['train','validation','test']+(['financial'] if name=='prime-causal' else []):evaluate(BASE/name,split)

if __name__=='__main__':main()
