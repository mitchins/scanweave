#!/usr/bin/env python3
"""Summarize C2 traces and sidecars. Run after run.py completes."""
import collections
import hashlib
import json
from pathlib import Path
from run import documents, OUT, INPUT

HERE = Path(__file__).resolve().parent
PR3 = INPUT / 'PR3/runs'

def read(path):
    return json.loads(Path(path).read_text())

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def paths(name):
    if name.startswith('p2pp-'):
        off = INPUT / 'P2pp' / ('sheet-' + name.split('-')[-1] + '-off.pdf')
    elif name.startswith('p2prime-'):
        off = INPUT / 'P2prime' / ('sheet-' + name.split('-')[-1] + '-off.pdf')
    elif name.startswith('p2-'):
        off = INPUT / 'P2' / ('sheet-' + name.split('-')[-1] + '-off.pdf')
    elif name.startswith('font01-'):
        _, split, i = name.split('-')
        off = INPUT / 'S1/font01' / f'{split}-{i}-off/output.pdf'
    else:
        off = INPUT / 'R2a/baseline' / f'{name}-off.pdf'
    return {'off': off, 'q3': PR3 / f'{name}.pdf', 'trace': OUT/'trace'/f'{name}.pdf', 'corrected': OUT/'corrected-only'/f'{name}.pdf'}

def conv(pdf):
    return read(str(pdf)+'.json')['conversion']

def accepted(g):
    return {d['member']: d for d in g.get('decisions', []) if d['accepted'] and d['member'] != d['canonical']}

def main():
    rows=[]; tables=collections.defaultdict(collections.Counter); members=[]; traces={}
    ledger=read(HERE/'pr26-subset-ledger-v3.json')
    prior={d['document']:d for d in ledger['documents']}
    for name, src, dpi in documents():
        pp=paths(name); q=conv(pp['q3']); c=conv(pp['corrected']); t=conv(pp['trace']); default=conv(pp['off'])
        qg=q.get('glyph_sharing') or {}; cg=c.get('glyph_sharing') or {}; tg=t.get('glyph_sharing') or {}
        qa=accepted(qg); ca=accepted(cg)
        trace_path=Path(str(pp['trace'])+'.ownership.json'); trace=read(trace_path) if trace_path.exists() else []
        traces[name]=trace
        category='financial-nonint' if name=='financial' else str(dpi)
        for v in trace:
            k=(str(v['legacy']).lower(),str(v['corrected']).lower());tables[category][k]+=1
        # Sidecar observation design keys recover the exact keys used by final_group.
        keys={(p, o['symbol_id']):o['shape_key'] for p, pr in enumerate(c['page_reports']) for o in pr['reconstruction']['observations']}
        groups=collections.defaultdict(set)
        for d in cg.get('decisions',[]):
            if d['accepted']:
                groups[d['canonical']].add(keys[(d['page'],d['id'])])
        tr={v['member']:v for v in trace}
        n=[]
        for m in sorted(set(ca)-set(qa)):
            d=ca[m]; item=dict(document=name,dpi=dpi,member=m,page=d['page'],id=d['id'],canonical=d['canonical'],fit_error=d['error'],absolute_error=d['error'],noise_floor=d['noise_floor'],relative_error=(d['error']/max(d['noise_floor'], 1e-6) if d['error'] is not None else None),witness_count=len(groups[d['canonical']]),corrected_check_margin=None,trace=tr.get(m),hard_check_reasons=d['reasons'])
            n.append(item);members.append(item)
        def econ(cv,g,p):
            return dict(pdf_bytes=p.stat().st_size,font_bytes=cv['font_bytes'],retired_outlines=g.get('retired_outlines',0),net_outlines_retired=g.get('net_outlines_retired',0),substitutions=g.get('substituted',0),sha256=sha(p))
        rows.append(dict(document=name,dpi=dpi,category=category,n=len(n),n_members=[m['member'] for m in n],q3_only_members=sorted(set(qa)-set(ca)),changed_bindings=[m for m in sorted(set(qa)&set(ca)) if any(qa[m][k]!=ca[m][k] for k in ('canonical','fitted_transform','error','id','page'))],prior_removed=prior[name]['removed_detail'],q3_vs_trace_pdf_identical=sha(pp['q3'])==sha(pp['trace']), economy={a:econ(cv,g,pp[a]) for a,cv,g in [('off',default,{}),('q3',q,qg),('corrected',c,cg)]}, trace_rows=len(trace),trace_path=str(trace_path) if trace_path.exists() else None,trace_sha256=sha(trace_path) if trace_path.exists() else None))
        print(name, len(trace), len(n), flush=True)
    data=dict(documents=rows,contingency={d:{f'{a}/{b}':v for (a,b),v in sorted(c.items())} for d,c in tables.items()},n_members=members,notes=['Outcomes are exception booleans; null means invalid. Pages and members are zero-based.', 'Fit.error is the absolute fit error; relative error is fit.error / max(noise_floor, 1e-6). The ownership preflight does not expose a continuous margin.'])
    (HERE/'measurements.json').write_text(json.dumps(data,indent=2)+'\n')
    (HERE/'ownership-traces.json').write_text(json.dumps(traces,separators=(',',':'))+'\n')
if __name__=='__main__': main()
