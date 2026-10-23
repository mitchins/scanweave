"""Add actual encoded-outline point counts to every retired-program ledger."""
from pathlib import Path
import io,json
import pikepdf
from fontTools.ttLib import TTFont
from qualification.font04.metrics import sha
BASE=Path('qualification/font04');ROOT=BASE/'local'

def main():
    with pikepdf.open(ROOT/'financial-default.pdf') as pdf:data=pdf.pages[0].Resources.Font.F1.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()
    tt=TTFont(io.BytesIO(data));old={name:dict(points=len(tt['glyf'][name].coordinates) if tt['glyf'][name].numberOfContours>0 else 0,bytes=len(tt['glyf'][name].compile(tt['glyf']))) for name in tt.getGlyphOrder()};base_points=sum(r['points'] for r in old.values());summary=[]
    for manifest_name,byte_name in [('b2prime-points.json','b2prime-byte-attribution.json'),('b2prime-support-initial-points.json','b2prime-support-initial-byte-attribution.json')]:
        points=json.loads((BASE/manifest_name).read_text())['points'];table=json.loads((BASE/byte_name).read_text())
        for p in points:
            pdf=Path(p['pdf']);art=Path(str(pdf)+'.font04');path=art/'byte-attribution.json';a=json.loads(path.read_text());before_sha=a['sha256'];assert before_sha==sha(pdf)
            for r in a['retired_programs']:assert old[r['program']]['bytes']==r['bytes'];r['points']=old[r['program']]['points']
            retired=sum(r['points'] for r in a['retired_programs']);added=sum(r['points'] for r in a['added_programs']);v=json.loads((art/'verification.json').read_text());assert base_points-retired+added==v['experimental']['outline_points']
            a.update(retired_outline_points=retired,added_outline_points=added,per_program_byte_definition='Decoded glyf bytes before table alignment; font compression is non-additive and reported globally. Point counts are actual stored TrueType coordinates, not tracing path estimates.');path.write_text(json.dumps(a,indent=2)+'\n')
            label=p['label'].removeprefix('support-initial-');entry=table['points'][label];entry.update(retired_outline_points=retired,added_outline_points=added,per_program_ledger=str(path),per_program_ledger_sha256=sha(path));summary.append(dict(label=p['label'],retired_points=retired,added_points=added,net_points_saved=retired-added))
        (BASE/byte_name).write_text(json.dumps(table,indent=2)+'\n')
    path=ROOT/'financial-B2prime-transport.pdf.font04/byte-attribution.json';a=json.loads(path.read_text())
    for r in a['retired_programs']:assert old[r['program']]['bytes']==r['bytes'];r['points']=old[r['program']]['points']
    a.update(retired_outline_points=sum(r['points'] for r in a['retired_programs']),added_outline_points=sum(r['points'] for r in a['added_programs']));path.write_text(json.dumps(a,indent=2)+'\n')
    sidecar=ROOT/'financial-B2prime-transport.pdf.transport.json';a=json.loads(sidecar.read_text());a.update(status='Superseded dense-map diagnostic metadata',pdf=str(ROOT/'financial-B2prime-transport-dense-maps.pdf'));assert a['sha256']==sha(Path(a['pdf']));sidecar.write_text(json.dumps(a,indent=2)+'\n')
    (BASE/'b2prime-program-point-audit.json').write_text(json.dumps(dict(default_stored_points=base_points,points=summary,all_point_balances_exact=True,no_PDF_changed=True),indent=2)+'\n');print('Per-program point accounting PASS',len(summary),flush=True)

if __name__=='__main__':main()
