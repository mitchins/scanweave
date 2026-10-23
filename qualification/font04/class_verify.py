"""Complete frequent-class PDF checks and non-duplicated program attribution."""
from pathlib import Path
import collections,io,json,subprocess,sys
import pikepdf
from fontTools.ttLib import TTFont
from qualification.font04.metrics import inspect,sha
from qualification.font04.b1_audit import check_pdf
from qualification.font04.class_metrics import bind
from qualification.font04.prime_verify import text,stats
ROOT=Path('qualification/font04/local')

def programs(inv):return collections.Counter(h for f in inv['fonts'].values() for h in f['hashes'][1:])
def owners(inv):
    result=collections.defaultdict(set)
    for u in inv['users']:result[u['program']].add(u['character'])
    return result

def class_stats(inv,char):
    draws=[d for d in inv['draws'] if d['character']==char];used={(d['font_hash'],d['gid']) for d in draws};required={(d['font_hash'],d['gid']) for d in inv['users'] if d['character']==char}
    return dict(draws=len(draws),visible_designs=len(used),draws_per_design=len(draws)/len(used) if used else None,required_slots=len(required))

def main(path):
    art=Path(str(path)+'.font04');snap=json.loads((art/'source.json').read_text());plan=json.loads((art/'plan.json').read_text());base=inspect(ROOT/'financial-default.pdf');inv=inspect(path);added=programs(inv)-programs(base);retired=programs(base)-programs(inv);before=owners(base);after=owners(inv);classes={}
    for char in sorted({r['character'] for r in snap['rows']}):
        aa=sum(n for h,n in added.items() if after[h]=={char});rr=sum(n for h,n in retired.items() if before[h]=={char});classes[char]=dict(default=class_stats(base,char),experimental=class_stats(inv,char),added_programs=aa,retired_programs=rr,net_retired=rr-aa,substituted=sum(a.get('character','e')==char for a in plan['assignments']))
    shared=dict(added=[dict(program=h,count=n,owners=sorted(after[h])) for h,n in added.items() if len(after[h])!=1],retired=[dict(program=h,count=n,owners=sorted(before[h])) for h,n in retired.items() if len(before[h])!=1])
    t0,s0=text(ROOT/'financial-default.pdf');t,s=text(path);pop0=subprocess.check_output(['pdftotext','-layout',str(ROOT/'financial-default.pdf'),'-']);pop=subprocess.check_output(['pdftotext','-layout',str(path),'-']);validation=check_pdf(path)
    assert t0==t and s0==s and pop0==pop
    assert all(v['returncode']==0 for v in validation.values())
    glyph277=next(r for r in snap['rows'] if r['page']==12 and r['id']=='w000133s0002' and r['character']=='e');i=glyph277['index'];a=bind(snap,base)[i];b=bind(snap,inv)[i]
    regression='not an ownership-veto arm'
    if plan.get('ownership_veto'):
        assert a['program']==b['program'] and a['matrix']==b['matrix'];regression='PASS: default owned mark program and placement retained'
    result=dict(pdf=str(path),sha256=sha(path),default=stats(base),experimental=stats(inv),added=sum(added.values()),retired=sum(retired.values()),net_retired=sum(retired.values())-sum(added.values()),classes=classes,shared_program_deltas=shared,validation=validation,text_equal=True,search_equal=True,poppler_text_equal=True,glyph_277_regression=regression,class_counts=len(classes),source_rows=len(snap['rows']),review_status='independent blinded review pending')
    (art/'class-verification.json').write_text(json.dumps(result,indent=2)+'\n');Path('qualification/font04/'+path.stem+'-verification.json').write_text(json.dumps(result,indent=2)+'\n')
    print(path.name,'net retired',result['net_retired'],'bytes',result['experimental']['bytes'])

if __name__=='__main__':main(Path(sys.argv[1]))
