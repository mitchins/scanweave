"""B2-prime bounded research driver. P2 is never an input.

Run transport + hygiene first; `frontier` refuses unverified transport evidence.
"""
from pathlib import Path
import collections,copy,io,json,os,shutil,subprocess,sys,time
import numpy as np
import pikepdf,pypdfium2 as pdfium
from qualification.font04.metrics import sha,operands,inspect
from qualification.font04.geometry import geometry
from qualification.font04.planner import choose,frame_bbox
from qualification.font04.composite_transport import emit,CONTROL,ROOT
from qualification.font04.causal import glyph_matrix
from qualification.font04.pdf_helpers import font_resource
from qualification.font04.class_metrics import crop_render
from qualification.font04.owned_ink import components
BASE=Path('qualification/font04');ART=Path(str(CONTROL)+'.font04')

def owned_decision(component):
    # Calibration separates missing detached marks from attached boundary noise.
    # No member-ID exceptions, no source dirt absent from default is promoted.
    if not component['owned_area']:return False
    if component['detached_in_ownership_halo']:
        return component['area']>=3 and component['mass']>=1.5
    return component['area']>=4 and component['mass']>=3.

def calibration():
    old=json.loads((BASE/'b2-owned-component-ledger.json').read_text());raw=json.loads((ART/'raw-owned-audit.json').read_text());fired={c['member'] for c in raw['components'] if owned_decision(c)}
    for i in [1233,3422]:assert i in fired
    rows=json.loads((ART/'source.json').read_text())['rows'];b1=json.loads((ROOT/'financial-B1prime-PV.pdf.font04/source.json').read_text())['rows'][277];mark=next(r['index'] for r in rows if (r['page'],r['id'])==(b1['page'],b1['id']));assert mark==3422
    result=dict(policy=dict(detached_min_area=3,detached_min_mass=1.5,attached_min_area=4,attached_min_mass=3.,halo=1.,source_threshold=.25,default_threshold=.15,candidate_threshold=.10),calibration_population=old['exceptions'],n=44,previously_firing=44,calibrated_firing=len(set(old['exceptions'])&fired),retained=sorted(fired),mandatory=dict(B1_glyph_277_global_member=mark,glyph_3422=3422,glyph_1233=1233),rule='Calibrated attached-boundary noise significance; detached owned components remain under a stricter threshold. Unowned scanner dirt always ignored.',review='44 reviewed B2 firings; 42 indistinguishable, two minor missing marks. Conservative threshold retains some reviewed immaterial ink.')
    (BASE/'b2prime-owned-calibration.json').write_text(json.dumps(result,indent=2)+'\n');return result

def preflight(assignments,tag,rows,lookup,frames,meta):
    destination=ROOT/f'B2prime-{tag}-ownership-control.pdf';geometry_pages=json.loads((ROOT/'financial-default.pdf.json').read_text())['pages'];bounds={}
    with pikepdf.open(ROOT/'financial-default.pdf') as original:
        pdf=pikepdf.Pdf.new();font=font_resource(pdf,ART/'canonical.ttf',list(lookup.values()))
        for a in assignments:
            i=a['member'];r=dict(rows[i]);g=geometry_pages[r['page']];r.update(pixel_x_pt=g['width_pt']/g['raster_width'],pixel_y_pt=g['height_pt']/g['raster_height']);o=lookup[a['canonical']];m=glyph_matrix(r,o,a['bbox']);pdf.pages.append(original.pages[r['page']]);page=pdf.pages[-1];page.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(F04=font));cmd='BT 0 Tr 0 g /F04 1 Tf '+' '.join(map(str,operands(m)))+f" Tm <{o['gid']:04x}> Tj ET";page.Contents=pdf.make_stream(cmd.encode());x,y,xx,yy=map(int,r['source']['bbox']);bounds[i]=[x-4,y-4,xx+4,yy+4]
        pdf.save(destination,deterministic_id=True)
    default=np.load(ART/'class-crops.npz');rawdoc=pdfium.PdfDocument(ART/'raw-owned-source.pdf');candidate=pdfium.PdfDocument(destination);ledger=[]
    for k,a in enumerate(assignments):
        i=a['member'];b=bounds[i];src=crop_render(ART/'raw-owned-source.pdf',rawdoc,i,b,'analytic');cur=default[f'{i}-analytic-default'];new=crop_render(destination,candidate,k,b,'analytic');cc=components(src,cur,new,i)
        for c in cc:c.update(character=rows[i]['character'],page=rows[i]['page'],id=rows[i]['id'],old_fires=c['fires'],fires=bool(owned_decision(c)),decision='keep_default_exception' if owned_decision(c) else 'below_calibrated_significance_or_unowned')
        ledger.extend(cc)
    candidate.close();rawdoc.close();default.close();fired=sorted({c['member'] for c in ledger if c['fires']});result=dict(exceptions=fired,components=ledger,control_pdf=str(destination),control_sha256=sha(destination),policy=calibration()['policy']);(ROOT/f'B2prime-{tag}-owned.json').write_text(json.dumps(result,separators=(',',':'))+'\n');return result

def prepare_art(path,plan):
    art=Path(str(path)+'.font04');art.mkdir(exist_ok=True)
    for name in ['source.json','outlines.json','frames.json','pair-ledger.json','canonical.ttf','fields.npy']:shutil.copyfile(ART/name,art/name)
    (art/'plan.json').write_text(json.dumps(plan,indent=2)+'\n');return art

def frontier():
    transport=json.loads((BASE/'b2prime-transport-verification.json').read_text());assert transport['pass'], 'transport must be qualified before soft criteria change'
    hygiene=json.loads((BASE/'b2prime-canonical-hygiene.json').read_text());assert json.loads((BASE/'b2prime-material-regressions.json').read_text())['n']==16
    calibration();rows=json.loads((ART/'source.json').read_text())['rows'];plan=json.loads((ART/'plan.json').read_text());pairs=json.loads((ART/'pair-ledger.json').read_text());fields=np.load(ART/'fields.npy');meta=json.loads((ART/'frames.json').read_text());frames=meta['frames'];out=json.loads((ART/'outlines.json').read_text())['records'];lookup={int(o['key'].rsplit('-',1)[1]):o for o in out if 'gid'in o};n=len(rows);veto=np.zeros((n,n),bool);errors=np.full((n,n),np.inf);params={};bands=[]
    for i,f in enumerate(fields):
        g=geometry(f);weight=(float(f.sum())/max(1.,float(((f>.5)^__import__('scipy').ndimage.binary_erosion(f>.5)).sum()))) if g else 0.
        bands.append(int(np.floor(np.log(max(weight,.1))/np.log(1.3))))
    support=json.loads((BASE/'b2prime-soft-support.json').read_text());assert support['no_missing_floors'] and support['source_snapshot_sha256']==sha(ART/'source.json')
    assert [r['band'] for r in support['members']]==bands
    levels={r['member']:r['floor'] for r in support['members']};assert all(v is not None and np.isfinite(v) for v in levels.values())
    excluded=set(hygiene['excluded']);pp=pairs+[dict(r,canonical=r['member'],parameters=next((a['parameters'] for a in plan['assignments'] if a['member']==r['member'] and a['canonical']==r['member']),None)) for r in plan['self_checks']]
    # Self fits are deterministic; regenerate only missing self fit parameters.
    from qualification.font04.geometry import register
    for p in pp:
        i,j=p['member'],p['canonical']
        if p['parameters'] is None:
            o=lookup[j];a=np.zeros((64,64));x,y=meta['origins'][j];a[y:y+o['height'],x:x+o['width']]=np.array(o['coverage']).reshape(o['height'],o['width']);p=dict(p,parameters=register(fields[i],a)[0].tolist())
        params[i,j]=p['parameters'];level=levels[i];errors[i,j]=p['error']/max(1e-6,level) if level is not None else np.inf;veto[i,j]=not p['reasons'] and j not in excluded and bands[i]==bands[j]
    ranked_rows=[dict(r,character=r['character']+':weight'+str(bands[i])) for i,r in enumerate(rows)]
    manifest=[]
    for method in ['star','cover']:
        for scale in [1.,1.5,2.]:
            tag=f'{method}-{scale:.1f}';groups=choose(veto,errors,scale,method,ranked_rows);assignments=[]
            for g in groups:
                j=g['canonical'];o=lookup[j]
                for i in g['members']:
                    assert rows[i]['character']==rows[j]['character'] and veto[i,j]
                    a=dict(member=i,canonical=j,character=rows[i]['character'],page=rows[i]['page'],occurrence=rows[i]['occurrence'],id=rows[i]['id'],parameters=params[i,j],bbox=frame_bbox(frames[i],meta['origins'][j],(o['width'],o['height']),params[i,j]));assignments.append(a)
            owned=preflight(assignments,tag,rows,lookup,frames,meta);exceptions=set(owned['exceptions']);survivors=[]
            for g in groups:
                aa=[a for a in assignments if a['canonical']==g['canonical'] and a['member'] not in exceptions]
                if g['canonical'] not in exceptions and len(aa)>=2:survivors.extend(aa)
            variants=[(tag,survivors,False)]
            if method=='star' and scale==1.:
                kept=survivors[:];users=collections.defaultdict(set);held=set(json.loads((BASE/'b2-frontier.json').read_text())['original_programs_held_by_invisible_or_rare_users'])
                for i,r in enumerate(rows):
                    if r['shape_key'] not in held:users[r['shape_key']].add(i)
                removed=[]
                while kept:
                    by=collections.defaultdict(list)
                    for a in kept:by[a['canonical']].append(a['member'])
                    allmembers={a['member'] for a in kept};member_group={a['member']:a['canonical'] for a in kept};credits=collections.Counter()
                    for key,u in users.items():
                        if u<=allmembers:
                            c=collections.Counter(member_group[i] for i in u);credits[min(c,key=lambda j:(-c[j],j))]+=1
                    bad={j for j in by if credits[j]<1}
                    if not bad:break
                    removed.extend(sorted(bad));kept=[a for a in kept if a['canonical'] not in bad]
                variants.append((tag+'-net',kept,True))
            for label,aa,net in variants:
                accepted={a['member'] for a in aa};rejections=[]
                for i in range(n):
                    if i in accepted:continue
                    attempt=min((p for p in pairs if p['member']==i),key=lambda p:(len(p['reasons']),p['error']),default=None)
                    if attempt is None:rejections.append(dict(member=i,reasons=['no_safe_owned_witness'],checks={}));continue
                    r=copy.deepcopy(attempt);j=r['canonical']
                    if j in excluded:r['reasons'].append('canonical_hygiene')
                    if bands[i]!=bands[j]:r['reasons'].append('stroke_weight_band')
                    if i in exceptions:r['reasons'].append('unexplained_owned_ink')
                    if not r['reasons']:r['reasons']=['ranking_or_economy_exception']
                    rejections.append(r)
                candidate_plan=dict(plan,assignments=aa,rejection_ledger=rejections,ownership_veto=dict(exceptions=sorted(exceptions-accepted),policy=owned['policy']),selected=dict(grouping=method,error_scale=scale,weight_bands=True,net_retirement_rule=net),soft_support=dict(path=str(BASE/'b2prime-soft-support.json'),sha256=sha(BASE/'b2prime-soft-support.json'),no_missing_floors=True,witness_count_gates=False),hygiene=str(BASE/'b2prime-canonical-hygiene.json'),weight_band=bands)
                path=ROOT/f'financial-B2prime-{label}.pdf';art=prepare_art(path,candidate_plan);started=time.monotonic();account=emit(path,candidate_plan);account['wall_seconds']=time.monotonic()-started;(art/'byte-attribution.json').write_text(json.dumps(account,indent=2)+'\n');manifest.append(dict(label=label,pdf=str(path),sha256=sha(path),substituted=len(aa),ownership_control=owned['control_pdf'],net_rule=net));print(label,len(aa),account['bytes'],flush=True)
    (BASE/'b2prime-points.json').write_text(json.dumps(dict(points=manifest,soft_gate_change_after_transport_sha256=sha(BASE/'b2prime-transport-verification.json'),hygiene_before_soft=True),indent=2)+'\n')

def transport():
    path=ROOT/'financial-B2prime-transport.pdf';plan=json.loads((ART/'plan.json').read_text());art=prepare_art(path,plan);account=emit(path,plan);(art/'byte-attribution.json').write_text(json.dumps(account,indent=2)+'\n')
    env=dict(os.environ,FONT04_METRIC_WORKERS='6',FONT04_CLASS_REFERENCE=str(CONTROL))
    subprocess.run([sys.executable,'-m','qualification.font04.class_metrics',str(path)],env=env,check=True)
    subprocess.run([sys.executable,'-m','qualification.font04.b2prime_verify',str(path),'--transport'],check=True)

if __name__=='__main__':
    if sys.argv[1]=='transport':transport()
    elif sys.argv[1]=='calibration':print(calibration())
    elif sys.argv[1]=='frontier':frontier()
