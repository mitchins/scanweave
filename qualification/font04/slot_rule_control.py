"""Test the literal retire>=add rule including stubs, separately from outlines."""
from pathlib import Path
import collections,copy,json,os,subprocess,sys,time
from qualification.font04.b2prime import BASE,ROOT,prepare_art
from qualification.font04.composite_transport import emit
from qualification.font04.metrics import sha

def main():
    points_path=BASE/'b2prime-points.json'
    while not points_path.exists():time.sleep(2)
    info=json.loads(points_path.read_text())
    if any(p['label']=='star-1.0-slot-net' for p in info['points']):
        print('Literal slot control already recorded; reuse immutable output');return
    path=ROOT/'financial-B2prime-star-1.0.pdf';art=Path(str(path)+'.font04');plan=json.loads((art/'plan.json').read_text());assert isinstance(plan['soft_support'],dict) and not plan['soft_support']['witness_count_gates'];rows=json.loads((art/'source.json').read_text())['rows'];account=json.loads((art/'byte-attribution.json').read_text());held=set(json.loads((BASE/'b2-frontier.json').read_text())['original_programs_held_by_invisible_or_rare_users']);users=collections.defaultdict(set)
    for i,r in enumerate(rows):
        if r['shape_key'] not in held:users[r['shape_key']].add(i)
    stubgroups=collections.defaultdict(set)
    for instance in account['instances']:stubgroups[instance['canonical']].add(instance['stub'])
    kept=plan['assignments'][:];rounds=[]
    while kept:
        allmembers={a['member'] for a in kept};membergroup={a['member']:a['canonical'] for a in kept};groups=set(membergroup.values());credits=collections.Counter()
        for key,u in users.items():
            if u<=allmembers:
                c=collections.Counter(membergroup[i] for i in u);credits[min(c,key=lambda j:(-c[j],j))]+=1
        bad={j for j in groups if credits[j]<1+len(stubgroups[j])};rounds.append(dict(groups=len(groups),rejected_groups=len(bad),cost='one new canonical plus actual unique composite stubs'))
        if not bad:break
        kept=[a for a in kept if a['canonical'] not in bad]
    label='star-1.0-slot-net';new=ROOT/f'financial-B2prime-{label}.pdf';newplan=copy.deepcopy(plan);oldmembers={a['member'] for a in kept};newplan['assignments']=kept;newplan['selected'].update(net_retirement_rule='literal_all_required_slots_including_stubs')
    for a in plan['assignments']:
        if a['member'] not in oldmembers:newplan['rejection_ledger'].append(dict(a,reasons=['literal_required_slot_net_retirement'],checks={}))
    target=prepare_art(new,newplan);newaccount=emit(new,newplan);(target/'byte-attribution.json').write_text(json.dumps(newaccount,indent=2)+'\n');(BASE/'b2prime-slot-rule.json').write_text(json.dumps(dict(rounds=rounds,substituted=len(kept),new_canonicals=newaccount['canonical_count'],new_stubs=newaccount['stub_count'],retired=len(newaccount['retired_programs']),literal_rule_pass=len(newaccount['retired_programs'])>=newaccount['canonical_count']+newaccount['stub_count'],outline_rule_control='star-1.0-net',note='Outline-level and all-slot rules are reported separately; no fresh existing-program alternative is assumed.'),indent=2)+'\n')
    env=dict(os.environ,FONT04_METRIC_WORKERS='6',FONT04_CLASS_REFERENCE='qualification/font04/local/financial-B2-P-initial.pdf')
    with (ROOT/f'B2prime-{label}-metrics.log').open('w') as log:subprocess.run([sys.executable,'-m','qualification.font04.profile_run',str(ROOT/f'B2prime-{label}-metrics-profile.json'),sys.executable,'-m','qualification.font04.class_metrics',str(new)],env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    subprocess.run([sys.executable,'-m','qualification.font04.b2prime_verify',str(new)],check=True)
    info=json.loads(points_path.read_text());info['points'].append(dict(label=label,pdf=str(new),sha256=sha(new),substituted=len(kept),net_rule='literal including stubs',ownership_control='No new substitutions if empty; otherwise same preflight as star-1.0'));points_path.write_text(json.dumps(info,indent=2)+'\n');print('Literal slot control',len(kept),newaccount['bytes'],flush=True)

if __name__=='__main__':main()
