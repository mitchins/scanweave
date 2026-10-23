"""Score every complete frontier point; no operating point is selected."""
from pathlib import Path
import concurrent.futures,json,os,subprocess,sys,time
from qualification.font04.b2prime import ROOT,BASE

def run(point):
    label=point['label'];pdf=point['pdf'];env=dict(os.environ,FONT04_METRIC_WORKERS='6',FONT04_CLASS_REFERENCE='qualification/font04/local/financial-B2-P-initial.pdf');log=ROOT/f'B2prime-{label}-metrics.log';profile=ROOT/f'B2prime-{label}-metrics-profile.json'
    with log.open('w') as stream:subprocess.run([sys.executable,'-m','qualification.font04.profile_run',str(profile),sys.executable,'-m','qualification.font04.class_metrics',pdf],env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    with (ROOT/f'B2prime-{label}-verification.log').open('w') as stream:subprocess.run([sys.executable,'-m','qualification.font04.b2prime_verify',pdf],stdout=stream,stderr=subprocess.STDOUT,check=True)
    return label

def main():
    while not (BASE/'b2prime-points.json').exists():time.sleep(2)
    points=json.loads((BASE/'b2prime-points.json').read_text())['points']
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        for label in pool.map(run,points):print('QUALIFIED',label,flush=True)

if __name__=='__main__':main()
