"""Finish the bounded B2-prime experiment; stop for independent review."""
from pathlib import Path
import concurrent.futures,subprocess,sys
ROOT=Path('qualification/font04/local')

def run(module,args=(),log=None):
    with (ROOT/(log or module.rsplit('.',1)[-1]+'.log')).open('w') as stream:
        subprocess.run([sys.executable,'-m',module,*args],stdout=stream,stderr=subprocess.STDOUT,check=True)

def main():
    if '--resume' not in sys.argv:
        run('qualification.font04.profile_run',[str(ROOT/'B2prime-frontier-profile.json'),sys.executable,'-m','qualification.font04.b2prime','frontier'],'B2prime-frontier.log');print('Final no-support-gate frontier emitted',flush=True)
    run('qualification.font04.slot_rule_control',log='B2prime-slot-rule.log')
    with concurrent.futures.ThreadPoolExecutor(2) as pool:
        jobs=[pool.submit(run,'qualification.font04.score_b2prime',log='B2prime-score.log'),pool.submit(run,'qualification.font04.audit_b2prime',log='B2prime-actual-audit.log')]
        for job in jobs:job.result()
    print('All points scored, validated, deterministic and owned-ink audited',flush=True)
    run('qualification.font04.fidelity_only',log='B2prime-fidelity-only.log')
    if not Path('qualification/font04/b2prime-review-manifest.json').exists():run('qualification.font04.b2prime_review',log='B2prime-review.log')
    print('Review sealed; reviewer pending; STOP at B2-prime',flush=True)

if __name__=='__main__':main()
