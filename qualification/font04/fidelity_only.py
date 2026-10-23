"""Separate fidelity-only substitutions from substitutions contributing retirement."""
from pathlib import Path
import collections,json,time
from qualification.font04.b2prime import BASE,ROOT
from qualification.font04.prime_metrics import headline

def main():
    while True:
        try:points=json.loads((BASE/'b2prime-points.json').read_text())['points'];ready=len(points)==8 and all((BASE/(Path(p['pdf']).stem+'-class-scorecard.json')).exists() for p in points)
        except (FileNotFoundError,json.JSONDecodeError):ready=False
        if ready:break
        time.sleep(2)
    held=set(json.loads((BASE/'b2-frontier.json').read_text())['original_programs_held_by_invisible_or_rare_users']);result={}
    for point in points:
        art=Path(point['pdf']+'.font04');rows=json.loads((art/'source.json').read_text())['rows'];plan=json.loads((art/'plan.json').read_text());metrics=json.loads((art/'class-metrics.json').read_text());account=json.loads((art/'byte-attribution.json').read_text());users=collections.defaultdict(set);groups=collections.defaultdict(set)
        for i,r in enumerate(rows):users[r['shape_key']].add(i)
        for a in plan['assignments']:groups[a['canonical']].add(a['member'])
        allmembers={a['member'] for a in plan['assignments']};retired={key for key,u in users.items() if u<=allmembers and key not in held};fidelity=set();records=[]
        for j,members in groups.items():
            marginal=sorted(key for key in retired if users[key]&members);exclusive=sorted(key for key in retired if users[key]<=members);only=not marginal
            if only:fidelity.update(members)
            records.append(dict(canonical=j,character=rows[j]['character'],members=sorted(members),fidelity_only=only,marginal_retired_programs=marginal,exclusive_retired_programs=exclusive,added_outlines=1,unique_stubs=len({r['stub'] for r in account['instances'] if r['canonical']==j})))
        categories={}
        for name,members in [('fidelity_only',fidelity),('contributes_retirement',allmembers-fidelity)]:
            rr=[dict(r,accepted=r['member'] in members) for r in metrics['records']];categories[name]=dict(substituted=len(members),groups=sum(r['fidelity_only']==(name=='fidelity_only') for r in records),metrics={m:headline(rr,point['label'],m,'substituted') for m in ['analytic','direct','pdfium','poppler']})
        result[point['label']]=dict(categories=categories,groups=records)
    (BASE/'b2prime-fidelity-only.json').write_text(json.dumps(dict(definition='A fidelity-only group contributes no actual original-program retirement: no retired original program has a user in that group. Marginal retirement lists may overlap across groups and must never be summed; global byte attribution counts each retirement once. Stubs and fresh canonicals are counted separately.',points=result),indent=2)+'\n');print('Fidelity-only separation complete',flush=True)

if __name__=='__main__':main()
