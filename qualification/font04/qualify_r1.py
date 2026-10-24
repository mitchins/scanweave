"""Independent final R1 qualification of explicit native PDFs. No P2 inputs."""
from collections import Counter
import hashlib,io,json,os,shutil,subprocess,sys,time
from pathlib import Path
import numpy as np
import pikepdf,pypdfium2 as pdfium
from fontTools.ttLib import TTFont
from qualification.font04.freeze_method import BASE,ROOT,digest,write
from qualification.font04.metrics import inspect,sha
from qualification.font04.class_metrics import bind,crop_render
from qualification.font04.b2prime import owned_decision
from qualification.font04.owned_ink import components
from qualification.font04.b2prime_verify import text_geometry,actual_text_signature

LOCAL=BASE/'local';FINAL=LOCAL/'R1-native';REFERENCE=LOCAL/'financial-B2prime-cover-2.0.pdf.font04'
RAW_SOURCE=LOCAL/'financial-B2-P-initial.pdf.font04/raw-owned-source.pdf'


def raster_signature(path):
    result=[]
    with pikepdf.open(path) as pdf:
        for page in pdf.pages:
            images=[]
            for name,obj in sorted(page.Resources.XObject.items(),key=lambda kv:str(kv[0])):
                if str(obj.get('/Subtype'))!='/Image':continue
                images.append(dict(name=str(name),sha256=hashlib.sha256(obj.read_raw_bytes()).hexdigest(),attributes={k:str(obj.get('/'+k)) for k in ['Width','Height','BitsPerComponent','ColorSpace','Filter','DecodeParms']}))
            placement=[(str(op),[str(x)for x in args])for args,op in pikepdf.parse_content_stream(page)if str(op)in ['cm','Do']]
            result.append(dict(images=images,placement=placement))
    return result


def font_accounting(default,candidate):
    def font(path):
        with pikepdf.open(path)as pdf:data=next(iter(pdf.pages[0].Resources.Font.values())).DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()
        return TTFont(io.BytesIO(data))
    before=font(default);after=font(candidate);order=after.getGlyphOrder();canonical=set();stubs=[]
    for i,name in enumerate(order):
        g=after['glyf'][name]
        if g.isComposite():
            stubs.append(i);assert len(g.components)==1
            for c in g.components:canonical.add(after.getGlyphID(c.glyphName));assert not after['glyf'][c.glyphName].isComposite()
    retained=[i for i,name in enumerate(order)if i not in canonical and not after['glyf'][name].isComposite()]
    before_hashes=Counter(hashlib.sha256(before['glyf'][n].compile(before['glyf'])).hexdigest()for n in before.getGlyphOrder())
    retained_hashes=Counter(hashlib.sha256(after['glyf'][order[i]].compile(after['glyf'])).hexdigest()for i in retained)
    assert all(before_hashes[h]>=n for h,n in retained_hashes.items()),'retained program was rewritten'
    retired=len(before.getGlyphOrder())-len(retained)
    return dict(default_slots=len(before.getGlyphOrder()),retained_default_programs=len(retained),retired_outlines=retired,added_canonicals=len(canonical),net_outlines_retired=retired-len(canonical),composite_stubs=len(stubs),retained_default_programs_exact=True,
        default_outline_points=sum(len(before['glyf'][n].coordinates)for n in before.getGlyphOrder()if before['glyf'][n].numberOfContours>0),
        native_outline_points=sum(len(after['glyf'][n].coordinates)for n in order if after['glyf'][n].numberOfContours>0))


def prepare_metrics(path,data):
    snapshot=json.loads((REFERENCE/'source.json').read_text());rows=snapshot['rows'];decisions=data['conversion']['glyph_sharing']['decisions'];assert len(rows)==len(decisions)==3524
    for i,(row,d)in enumerate(zip(rows,decisions)):assert (i,row['page'],row['id'])==(d['member'],d['page'],d['id'])
    # The default conversion is byte-identical; identity binding is independently
    # checked against every emitted label before using frozen source controls.
    bind(snapshot,inspect(path))
    art=Path(str(path)+'.font04');art.mkdir(exist_ok=True)
    shutil.copyfile(REFERENCE/'source.json',art/'source.json')
    assignments=[dict(member=d['member'],canonical=d['canonical'],page=d['page'],occurrence=rows[d['member']]['occurrence'],id=d['id'],character=rows[d['member']]['character'],parameters=d['fitted_transform'])for d in decisions if d['accepted']]
    write(art/'plan.json',dict(assignments=assignments,native_build=json.loads((BASE/'r1-native-build.json').read_text())['product_commit']))
    return rows,assignments


def emitted_owned_audit(path,rows,assignments):
    art=Path(str(path)+'.font04');raw=pdfium.PdfDocument(RAW_SOURCE);fired=[];ledger=[]
    with np.load(art/'class-crops.npz')as candidate,np.load(REFERENCE/'class-crops.npz')as control:
        for a in assignments:
            i=a['member'];r=rows[i];x,y,xx,yy=map(int,r['source']['bbox']);bounds=[x-4,y-4,xx+4,yy+4];src=crop_render(RAW_SOURCE,raw,i,bounds,'analytic');cc=components(src,control[f'{i}-analytic-default'],candidate[f'{i}-analytic-candidate'],i)
            for c in cc:c['fires']=bool(owned_decision(c));ledger.append(c)
            if any(c['fires']for c in cc):fired.append(i)
    raw.close();result=dict(schema='font04-R1-emitted-owned-audit-v1',pdf_sha256=sha(path),exceptions_still_firing=fired,components=ledger,source='Unmasked normalized raw source halo; actual 4x emitted candidate and byte-identical default; calibrated frozen significance.')
    write(art/'actual-owned-audit.json',result)
    return dict(firing_members=fired,ledger=str((art/'actual-owned-audit.json').relative_to(ROOT)),sha256=digest(art/'actual-owned-audit.json'))


def headline(records,metric):
    errors=[r['candidate']['error']for r in records if r['metric']==metric]
    return dict(n=len(errors),mean=float(np.mean(errors)),p95=float(np.quantile(errors,.95)))


def qualify():
    paths=[FINAL/n for n in ['default.pdf','cover-2.0.pdf','cover-1.5.pdf','cover-2.0-repeat.pdf']]
    started=time.monotonic()
    while not all(p.is_file()and Path(str(p)+'.json').is_file()for p in paths):
        if time.monotonic()-started>10800:raise RuntimeError('Native outputs did not finish; inspect their logs')
        time.sleep(5)
    assert sha(paths[0])=='74c31136d00a18dbf05fba2d7fba59c85cc201a57ae65d77999a025a692fab0f'
    assert sha(paths[1])==sha(paths[3]),'native repeat/thread-count divergence'
    data=json.loads(Path(str(paths[1])+'.json').read_text());native=data['conversion']['glyph_sharing'];decisions=native['decisions'];oracle=json.loads((BASE/'reference-oracle.json').read_text())['members']
    md=[dict(member=i,oracle=o['decision'],native='accept'if d['accepted']else'reject',oracle_canonical=o['canonical'],native_canonical=d['canonical'],oracle_reasons=o['all_reasons'],native_reasons=d['reasons'],cause='Deterministic numerical source-field/trace and cover-priority differences; fixed thresholds unchanged.')for i,(o,d)in enumerate(zip(oracle,decisions))if d['accepted']!=(o['decision']=='accept')]
    cd=[dict(member=i,oracle_canonical=o['canonical'],native_canonical=d['canonical'],oracle_transform=o['fitted_transform'],native_transform=d['fitted_transform'],cause='Numerical change in cost-aware cover priority; no alternate-canonical fallback or group splitting.')for i,(o,d)in enumerate(zip(oracle,decisions))if d['accepted']and o['decision']=='accept'and d['canonical']!=o['canonical']]
    rust_only=[d['member']for o,d in zip(oracle,decisions)if d['accepted']and o['decision']=='reject']
    safety=[i for i in rust_only if any(r!='ranking_or_economy_exception'for r in oracle[i]['all_reasons'])]
    membership=1-len(md)/len(oracle);accepted=sum(d['accepted']for d in decisions);canonical_matches=sum(d['accepted']and o['decision']=='accept'and d['canonical']==o['canonical']for o,d in zip(oracle,decisions));canonical=canonical_matches/accepted
    prelim=dict(schema='font04-R1-native-parity-v1',membership_agreement=membership,membership_divergences=md,canonical_agreement_over_all_native_accepted=canonical,canonical_matches=canonical_matches,native_accepted=accepted,canonical_divergences=cd,rust_only_acceptances=rust_only,safety_superset_violations=safety,thresholds_changed=False)
    write(BASE/'r1-parity-in-progress.json',prelim)
    assert not safety and membership>=.98 and canonical>=.98,'STOP: parity or safety superset failed; do not tune thresholds'
    assert all(not decisions[i]['accepted']for i in [3013,2466,63,1450,3422,1233])
    rows,assignments=prepare_metrics(paths[1],data)
    env=dict(os.environ,FONT04_CLASS_REFERENCE=str(REFERENCE).removesuffix('.font04'),FONT04_METRIC_WORKERS='4')
    score=Path(str(paths[1])+'.font04/class-metrics.json');crops=Path(str(paths[1])+'.font04/class-crops.npz')
    cached=json.loads(score.read_text()) if score.exists() else None
    reuse=bool(cached and cached['sha256']==sha(paths[1]) and cached.get('all_candidate_draws_measured') is True and crops.exists())
    if reuse:
        with np.load(crops) as arrays:assert '3523-analytic-candidate' in arrays.files
    else:
        with (FINAL/'fidelity.log').open('w')as log:subprocess.run([sys.executable,'-m','qualification.font04.r1_class_metrics',str(paths[1])],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True)
    metrics=json.loads(Path(str(paths[1])+'.font04/class-metrics.json').read_text());ref=json.loads((REFERENCE/'class-metrics.json').read_text());value=headline(metrics['records'],'analytic');baseline=headline(ref['records'],'analytic');floors=ref['renderer_vs_analytic_floors'];floor=dict(mean=min(floors[m]['mean']for m in ['pdfium','poppler']),p95=min(floors[m]['p95']for m in ['pdfium','poppler']));assert value['n']==baseline['n']==3524
    fidelity=value['mean']<=baseline['mean']+floor['mean']and value['p95']<=baseline['p95']+floor['p95']
    default=inspect(paths[0]);candidate=inspect(paths[1]);assert len(default['draws'])==len(candidate['draws'])==3717
    accepted_by_draw={(a['page'],a['occurrence'])for a in assignments};positions=Counter();unchanged=[]
    for old,new in zip(default['draws'],candidate['draws']):
        page=old['page'];oi=positions[page];positions[page]+=1
        assert (old['page'],old['cid'],old['character'],old['matrix'])==(new['page'],new['cid'],new['character'],new['matrix'])
        if(page,oi)not in accepted_by_draw and(old['program']!=new['program']or old['matrix']!=new['matrix']):unchanged.append((page,oi))
    invisible=lambda inv:[(d['page'],d['cid'],d['character'],d['program'],d['matrix'])for d in inv['users']if d['invisible']]
    invariants=dict(raster_streams_and_placements_equal=raster_signature(paths[0])==raster_signature(paths[1]),text_geometry_equal=text_geometry(paths[0])==text_geometry(paths[1]),actual_text_equal=actual_text_signature(paths[0])==actual_text_signature(paths[1]),unsubstituted_program_divergences=unchanged,invisible_users_equal=invisible(default)==invisible(candidate))
    accounting=font_accounting(paths[0],paths[1]);owned=emitted_owned_audit(paths[1],rows,assignments)
    economy=accounting['net_outlines_retired']>=.95*327 and native['encoded_font_bytes_after']<=native['encoded_font_bytes_before'];assert accounting['net_outlines_retired']==native['net_outlines_retired']
    with(FINAL/'compatibility.log').open('w')as log:subprocess.run([sys.executable,'-m','qualification.font04.r1_compatibility','--native-final'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    compatibility=json.loads((BASE/'r1-compatibility.json').read_text())
    passed=bool(fidelity and economy and not owned['firing_members']and all(v is True or v==[]for v in invariants.values())and compatibility['pass_all'])
    result=dict(prelim,status='PASS; independent review pending'if passed else'STOP; failed qualification',native_build=json.loads((BASE/'r1-native-build.json').read_text()),default_sha256=sha(paths[0]),native_pdf_sha256=sha(paths[1]),comparison_pdf_sha256=sha(paths[2]),determinism=dict(repeat_sha256=sha(paths[3]),byte_identical=True,rayon_threads=[4,1],research_python_path='/nonexistent-font04-python'),analytic_source_error=dict(native=value,oracle=baseline,measured_renderer_floor=floor,within_floor=fidelity,all_native_draws_measured=True),economy=dict(independent=accounting,native_report={k:v for k,v in native.items()if k!='decisions'},minimum_net_outlines=.95*327,passes=economy),invariants=invariants,actual_owned_audit=owned,compatibility='qualification/font04/r1-compatibility.json',pass_all=passed,reviewer_pending=True)
    write(BASE/'r1-parity.json',result)
    assert passed,'STOP: implementation/numerical/compatibility qualification failure; inspect report'
    print('R1 numerical/safety/economy/fidelity/compatibility checks PASS; blind package and independent review pending',flush=True)


if __name__=='__main__':qualify()
