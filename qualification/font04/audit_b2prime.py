"""Actual emitted owned-ink audits, repeat emission and complete byte partition."""
from pathlib import Path
import collections,json,os,sys,time
import numpy as np,pikepdf,pypdfium2 as pdfium
from qualification.font04.b2prime import BASE,ROOT,ART,owned_decision
from qualification.font04.composite_transport import emit
from qualification.font04.class_metrics import crop_render
from qualification.font04.owned_ink import components
from qualification.font04.metrics import sha

def partition(path):
    categories=collections.defaultdict(dict)
    with pikepdf.open(path) as pdf:
        for page in pdf.pages:
            for font in page.Resources.Font.values():
                if str(font.Subtype)!='/Type0':continue
                d=font.DescendantFonts[0]
                for key,obj in [('font',d.FontDescriptor.FontFile2),('CID_maps',d.CIDToGIDMap),('ToUnicode',font.ToUnicode)]:
                    if isinstance(obj,pikepdf.Stream):categories[key][obj.objgen]=len(obj.read_raw_bytes())
            for obj in page.Resources.XObject.values():
                if str(obj.get('/Subtype'))=='/Image':categories['raster'][obj.objgen]=len(obj.read_raw_bytes())
            for obj in ([page.Contents] if isinstance(page.Contents,pikepdf.Stream) else page.Contents):categories['content'][obj.objgen]=len(obj.read_raw_bytes())
    result={key:sum(v.values()) for key,v in categories.items()};result['dictionary_object_xref_and_other']=path.stat().st_size-sum(result.values());result['complete_pdf']=path.stat().st_size;return result

def main():
    points=json.loads((BASE/'b2prime-points.json').read_text())['points'];rows=json.loads((ART/'source.json').read_text())['rows'];source={};default={};rawpath=ART/'raw-owned-source.pdf'
    previous_path=BASE/'b2prime-actual-owned-and-determinism.json';previous=json.loads(previous_path.read_text()) if previous_path.exists() else {};bytes_path=BASE/'b2prime-byte-attribution.json';previous_bytes=json.loads(bytes_path.read_text()) if bytes_path.exists() else {};reuse={}
    for p in points:
        old=previous.get(p['label']);reuse[p['label']]=bool(old and old['repeat_sha256']==sha(Path(p['pdf'])) and Path(old['ledger']).exists() and sha(Path(old['ledger']))==old['ledger_sha256'])
    pending_assignments=any(json.loads(Path(p['pdf']+'.font04/plan.json').read_text())['assignments'] for p in points if not reuse[p['label']]);raw=pdfium.PdfDocument(rawpath) if pending_assignments else None
    with np.load(ART/'class-crops.npz') as arrays:
        for row in (rows if pending_assignments else []):
            if row['source'] is None:continue
            i=row['index'];x,y,xx,yy=map(int,row['source']['bbox']);source[i]=crop_render(rawpath,raw,i,[x-4,y-4,xx+4,yy+4],'analytic');default[i]=arrays[f'{i}-analytic-default']
    if raw is not None:raw.close()
    result={};byte_report=dict(default=partition(ROOT/'financial-default.pdf'),save_only=partition(ROOT/'financial-B2prime-save-only.pdf'),points={})
    for point in points:
        if reuse[point['label']]:
            result[point['label']]=previous[point['label']];byte_report['points'][point['label']]=previous_bytes['points'][point['label']];print(point['label'],'reuse exact PDF/owned-ledger/repeat hashes',flush=True);continue
        path=Path(point['pdf']);art=Path(str(path)+'.font04')
        while not (BASE/(path.stem+'-class-scorecard.json')).exists():time.sleep(2)
        plan=json.loads((art/'plan.json').read_text());ledger=[]
        with np.load(art/'class-crops.npz') as arrays:
            for a in plan['assignments']:
                i=a['member'];cc=components(source[i],default[i],arrays[f'{i}-analytic-candidate'],i)
                for c in cc:c.update(old_fires=c['fires'],fires=bool(owned_decision(c)))
                ledger.extend(cc)
        fired=sorted({c['member'] for c in ledger if c['fires']});assigned={a['member'] for a in plan['assignments']};mandatory=not ({1233,3422}&assigned)
        audit=dict(exceptions_still_firing=fired,mandatory_owned_ink_exceptions_retained=mandatory,components=ledger,source='Unmasked raw normalized halo, actual emitted 4x analytic candidate and default. Dirt absent from default is unowned.');(art/'actual-owned-audit.json').write_text(json.dumps(audit,separators=(',',':'))+'\n')
        repeat=ROOT/(path.stem+'-repeat.pdf');
        if not repeat.exists() or sha(path)!=sha(repeat):emit(repeat,plan)
        deterministic=sha(path)==sha(repeat)
        aa=json.loads((art/'byte-attribution.json').read_text());part=partition(path);aa.update(encoded_font_bytes=part['font'],encoded_byte_partition=part,save_only_delta_bytes=part['complete_pdf']-byte_report['save_only']['complete_pdf'],outline_program_bytes=sum(p['bytes'] for p in aa['added_programs'] if p['kind']=='canonical'),stub_program_bytes=sum(p['bytes'] for p in aa['added_programs'] if p['kind']=='stub'),retired_outline_bytes=sum(p['bytes'] for p in aa['retired_programs']),required_slot_net_change=aa['canonical_count']+aa['stub_count']-len(aa['retired_programs']));(art/'byte-attribution.json').write_text(json.dumps(aa,indent=2)+'\n');byte_report['points'][point['label']]=dict(partition=part,added_canonical_programs=aa['canonical_count'],retired_outline_programs=len(aa['retired_programs']),net_retired_outlines=len(aa['retired_programs'])-aa['canonical_count'],stub_programs=aa['stub_count'],required_slot_net_change=aa['required_slot_net_change'],added_outline_bytes=aa['outline_program_bytes'],stub_bytes=aa['stub_program_bytes'],retired_outline_bytes=aa['retired_outline_bytes'],per_program_ledger=str(art/'byte-attribution.json'),per_program_ledger_sha256=sha(art/'byte-attribution.json'))
        result[point['label']]=dict(actual_unexplained_owned_firings=fired,mandatory_owned_exceptions_retained=mandatory,deterministic=deterministic,repeat_pdf=str(repeat),repeat_sha256=sha(repeat),ledger=str(art/'actual-owned-audit.json'),ledger_sha256=sha(art/'actual-owned-audit.json'));print(point['label'],'owned fires',fired,'mandatory',mandatory,'deterministic',deterministic,flush=True)
    (BASE/'b2prime-actual-owned-and-determinism.json').write_text(json.dumps(result,indent=2)+'\n');(BASE/'b2prime-byte-attribution.json').write_text(json.dumps(byte_report,indent=2)+'\n');assert all(not r['actual_unexplained_owned_firings'] and r['mandatory_owned_exceptions_retained'] and r['deterministic'] for r in result.values())

if __name__=='__main__':main()
