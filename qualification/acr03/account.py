"""Bind compact ACR03 results to original artifacts, scripts and reviewed outputs."""
import hashlib
import json
import platform
import pikepdf
import subprocess
from importlib.metadata import version
from pathlib import Path

from prototype import ROOT, CASES, paths
from verify_acr03 import inspect


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    verification=json.loads((ROOT/'verification.json').read_text())
    checks=[]
    for item in verification['checks']:
        row={key:item[key] for key in ('case','path','equality')}
        if 'mode' in item:
            row['mode']=item['mode']
        detail=item['accounting']
        row['accounting']={key:detail[key] for key in ('pdf_bytes','sha256','encoded_font_program_bytes','content_stream_bytes')}
        row['accounting']['image_mask_objects']=len(detail['resources'])
        row['accounting']['encoded_raster_bytes']=sum(r['bytes'] for r in detail['resources'])
        checks.append(row)
    verification['checks']=checks
    verification['full_local_evidence_sha256']=sha(ROOT/'verification.json')
    Path('qualification/acr03/verification.json').write_text(json.dumps(verification,indent=2)+'\n')
    diagnostics=json.loads((ROOT/'diagnostics.json').read_text())
    for item in diagnostics['financial_pages']:
        item.pop('resources',None)
    Path('qualification/acr03/diagnostics.json').write_text(json.dumps(diagnostics,indent=2)+'\n')
    rows=[]
    for case,(group,index) in CASES.items():
        for method in ('crops','masked'):
            folder=ROOT/f'{case}-{method}'
            if method=='masked' and case in ('seal','shade'):
                folder=ROOT/'rejected'/folder.name
            row=json.loads((folder/'result.json').read_text())
            row['artifact_path']=str(folder/'complete.pdf')
            row['saving_percent']=100*(1-row['pdf_bytes']/row['baseline_bytes'])
            row['role_bytes']={role:sum(r['bytes'] for r in row['resources'] if r['role']==role) for role in ('paper','retained-ink','compound-object')}
            row['mask_bytes']=sum(r.get('mask_bytes',0) for r in row['resources'])
            row.pop('resources')
            rows.append(row)
    controls={}
    for group in ('controlled','financial','historical'):
        original=paths(group)[1]
        destination=ROOT/f'{group}-save-control.pdf'
        with pikepdf.open(original) as document:
            document.remove_unreferenced_resources()
            document.save(destination,deterministic_id=True,object_stream_mode=pikepdf.ObjectStreamMode.generate)
        controls[group]={'bytes':destination.stat().st_size,'sha256':sha(destination)}
    baseline=inspect(paths('financial')[1])
    candidate=inspect(ROOT/'financial-all-masked/complete.pdf')
    financial_rows=json.loads((ROOT/'financial-all-masked/results.json').read_text())
    financial={
        'save_only_control_bytes':controls['financial']['bytes'],
        'saving_against_save_only_control':controls['financial']['bytes']-candidate['pdf_bytes'],
        'baseline_image_objects':len(baseline['resources']),
        'baseline_bytes':baseline['pdf_bytes'],'candidate_bytes':candidate['pdf_bytes'],
        'saving_bytes':baseline['pdf_bytes']-candidate['pdf_bytes'],
        'saving_percent':100*(1-candidate['pdf_bytes']/baseline['pdf_bytes']),
        'candidate_sha256':candidate['sha256'],
        'role_bytes':{role:sum(r['bytes'] for p in financial_rows for r in p.get('resources',[]) if r['role']==role) for role in ('paper','retained-ink','compound-object')},
        'mask_bytes':sum(r.get('mask_bytes',0) for p in financial_rows for r in p.get('resources',[])),
        'encoded_font_program_bytes':candidate['encoded_font_program_bytes'],
        'content_stream_bytes':candidate['content_stream_bytes'],
        'image_and_mask_objects':len(candidate['resources']),
        'per_page':[{'page':r['page'],'objects':r.get('objects'),'hidden_font_shows':r.get('font_shows_transferred_to_raster'),
                     'paper_eligible':r.get('paper_eligible'),'encoded_image_bytes':sum(x['bytes'] for x in r.get('resources',[])),
                     'encoded_mask_bytes':sum(x.get('mask_bytes',0) for x in r.get('resources',[])),
                     'seconds':r.get('seconds')} for r in financial_rows],
    }
    corpus_inputs=set()
    for group,_ in CASES.values():
        corpus_inputs.update(paths(group))
    corpus_inputs.update(Path('qualification/pdf_packaging/groups')/f'{g}-{arm}.pdf' for g in ('financial','historical') for arm in ('adobe','ocrmypdf3'))
    corpus_inputs.update(Path('qualification/acr02/local')/name for name in ('prototype-adobe.pdf','prototype-controlled-indexed.pdf','history-indexed16.pdf','financial-full13-indexed16.pdf'))
    oracle_inputs=[Path('qualification/acr02/local/sources')/name for name in ('flat-logo-white.png','flat-logo-white-paper.png','statement-annotation.png','statement-white.png')]
    evidence=[]
    for folder in [ROOT/f'{case}-crops' for case in CASES]+[ROOT/f'{case}-masked' for case in CASES]+[ROOT/'rejected'/f'{case}-masked' for case in ('seal','shade')]:
        evidence.extend(p for name in ('object-mask.png','retained-ink-mask.png','paper.png') if (p:=folder/name).exists())
    scripts=sorted(Path('qualification/acr03').glob('*.py'))
    artifacts=sorted(set(ROOT.glob('*-*/complete.pdf')) | set((ROOT/'rejected').glob('*/complete.pdf')) | set(ROOT.glob('*-save-control.pdf')))
    manifest={'product_baseline':'8f14cd329493ad0cc226e480d152d7a464fb4731',
              'remote_main':'0ca94aecd74c35ea1b28bcebe7e11e863aae7f08',
              'research_reference':'38cc218f8f1e50e56679fd12d5d72c1d4a44a697',
              'inspector_reference':'ffa604ebd4ab47a6af67d2696a5c8fc15fbf3f2e',
              'python':platform.python_version(),'packages':{x:version(x) for x in ('pikepdf','numpy','scipy','Pillow','pypdfium2','fonttools')},
              'poppler':subprocess.run(['pdftoppm','-v'],capture_output=True,text=True,check=True).stderr.splitlines()[0],
              'reference_exports':json.loads((ROOT/'reference-manifest.json').read_text()),
              'evaluator_only_inputs':[{'path':str(p),'sha256':sha(p)} for p in oracle_inputs],
              'layer_evidence':[{'path':str(p),'sha256':sha(p)} for p in evidence],
              'scripts':[{'path':str(p),'sha256':sha(p)} for p in scripts],
              'inputs':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(corpus_inputs)],
              'outputs':[{'path':str(p),'bytes':p.stat().st_size,'sha256':sha(p)} for p in artifacts],
              'reviews':[{'path':str(p),'sha256':sha(p)} for p in sorted(ROOT.glob('*review.md'))],
              'production_changed':False,'holdout_opened':False}
    Path('qualification/acr03/results.json').write_text(json.dumps({'fixed_cases':rows,'financial_collection':financial,'save_only_controls':controls},indent=2)+'\n')
    Path('qualification/acr03/run-manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')


if __name__=='__main__':main()
