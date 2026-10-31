"""Recompute the complete oracle census under sealed/; no public oracle labels."""
import json
from collections import Counter
from pathlib import Path
from qualification.font04.s1d_eval import join,classify,shape_xor
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'qualification/font04/local/P2prime'
def main():
    faces={x['name']:x['path'] for x in json.loads((ROOT/'qualification/font04/p2prime-preregistration.json').read_text())['faces']}; obs=[json.loads(s) for s in (P/'p2prime/observations.jsonl').read_text().splitlines()];lab={x['id']:x for x in map(json.loads,(P/'p2prime/oracle/labels.jsonl').read_text().splitlines())}; cache={};report={}
    for i in range(9):
        sheet={}; targets=[o for o in obs if o['page']==i//3 and o['sheet']==i%3]
        for arm in ('cover-2.0','cover-2.0-ceiling'):
            conv=json.loads((P/f'sheet-{i}-{arm}.pdf.json').read_text())['conversion']; rows=conv['page_reports'][0]['reconstruction']['observations'];joined=join([{'id':r['symbol_id'],'bbox':r['bbox_px'],'character':r['text_hypothesis']} for r in rows],targets); ds=conv['glyph_sharing']['decisions']; by={d['member']:d for d in ds};counts=Counter();ledger=[]
            for d in ds:
                can=by.get(d['canonical']);a=joined.get(d['id']);b=joined.get(can['id']) if can else None
                if d['member']==d['canonical']:continue
                if a is None or b is None:counts['unresolved']+=1;continue
                x,y=lab[a],lab[b];cls=classify(x,y);state='accepted' if d['accepted'] else 'rejected';counts[f'{cls}|{state}']+=1
                xor=shape_xor(cache,faces,x['face'],y['face'],x['character']) if cls in ('different-family','same-family-different-style') else None
                if state=='accepted':
                    visible=cls=='different-character' or (xor is not None and xor>.2);counts['visible']+=visible;counts['egregious']+=xor is not None and xor>=.4
                ledger.append({'member':d['member'],'canonical':d['canonical'],'member_oracle':a,'canonical_oracle':b,'class':cls,'state':state,'shape_xor':xor})
            acc=counts['same-face|accepted'];rej=counts['same-face|rejected'];sheet[arm]={'counts':dict(counts),'same_face_false_rejection_rate':rej/(acc+rej) if acc+rej else None,'same_face_denominator':acc+rej,'ledger':ledger}
        report[str(i)]=sheet
    (P/'sealed/census.json').write_text(json.dumps({'method':'s1d_eval highest IoU join, classify, and font-outline xor; false rejection is rejected / (accepted + rejected) resolved same-face non-self decisions','sheets':report},indent=2)+'\n')
if __name__=='__main__':main()
