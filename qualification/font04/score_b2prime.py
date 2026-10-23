"""Score every complete frontier point; no operating point is selected."""
from pathlib import Path
import concurrent.futures,json,os,subprocess,sys,time
from qualification.font04.b2prime import ROOT,BASE

def run(point):
    label=point['label'];pdf=point['pdf'];env=dict(os.environ,FONT04_METRIC_WORKERS='6',FONT04_CLASS_REFERENCE='qualification/font04/local/financial-B2-P-initial.pdf');log=ROOT/f'B2prime-{label}-metrics.log';profile=ROOT/f'B2prime-{label}-metrics-profile.json'
    from qualification.font04.metrics import sha
    art=Path(pdf+'.font04');card=BASE/(Path(pdf).stem+'-class-scorecard.json');measured=False
    if card.exists() and profile.exists():
        measured=json.loads(card.read_text())['sha256']==sha(Path(pdf)) and (art/'class-crops.npz').exists()
    if not measured:
        with log.open('w') as stream:subprocess.run([sys.executable,'-m','qualification.font04.profile_run',str(profile),sys.executable,'-m','qualification.font04.class_metrics',pdf],env=env,stdout=stream,stderr=subprocess.STDOUT,check=True)
    existing=art/'verification.json';verified=False
    if existing.exists():
        prior=json.loads(existing.read_text());verified=prior['pass'] and prior['sha256']==sha(Path(pdf)) and 'pdfium_all_token_queries' in prior
    if not verified:
        with (ROOT/f'B2prime-{label}-verification.log').open('w') as stream:subprocess.run([sys.executable,'-m','qualification.font04.b2prime_verify',pdf],stdout=stream,stderr=subprocess.STDOUT,check=True)
    return label

def main():
    while not (BASE/'b2prime-points.json').exists():time.sleep(2)
    points=json.loads((BASE/'b2prime-points.json').read_text())['points']
    errors=[]
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
        jobs={pool.submit(run,point):point['label'] for point in points}
        for future in concurrent.futures.as_completed(jobs):
            try:print('QUALIFIED',future.result(),flush=True)
            except Exception as error:errors.append(dict(label=jobs[future],error=str(error)));print('FAILED',jobs[future],str(error),flush=True)
    if errors:raise RuntimeError(errors)

if __name__=='__main__':main()
