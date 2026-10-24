"""Seal every final Rust-only acceptance plus the other parity divergences."""
import json,subprocess,sys,time
from pathlib import Path
from PIL import Image
from qualification.font04.freeze_method import BASE,ROOT,write,digest
from qualification.font04.metrics import inspect,render,sha
from qualification.font04.class_metrics import bind,crop_render
from qualification.font04.context_instances import contextual_instances
from qualification.font04.b2prime_review import bounds_for
import pypdfium2 as pdfium

LOCAL=BASE/'local';FINAL=LOCAL/'R1-native'


def main():
    path=BASE/'r1-parity.json';started=time.monotonic()
    while not path.exists():
        if time.monotonic()-started>14400:raise RuntimeError('Final parity report not ready')
        time.sleep(5)
    report=json.loads(path.read_text());assert report['pass_all'],'Do not seal failed parity as qualified'
    selected=set(report['rust_only_acceptances'])|{r['member']for r in report['membership_divergences']}|{r['member']for r in report['canonical_divergences']}
    if not selected:
        write(BASE/'r1-blind-review.json',dict(status='no Rust-only acceptances or parity divergences',panels=0,reviewer_pending=True));return
    snapshot=json.loads((LOCAL/'financial-B2prime-cover-2.0.pdf.font04/source.json').read_text());rows=snapshot['rows'];native=FINAL/'cover-2.0.pdf';default=FINAL/'default.pdf';bindings=bind(snapshot,inspect(native))
    staging=LOCAL/'R1-blind-private-staging';public=LOCAL/'R1-blind-review';key=LOCAL/'R1-blind-private/sealed-key.json'
    assert not staging.exists()and not public.exists()and not key.exists(),'Never overwrite a sealed package'
    staging.mkdir(mode=0o700);(staging/'assets').mkdir();context=staging/'identical-context.pdf';pages=contextual_instances(default,native,context,rows,selected,bindings);doc=pdfium.PdfDocument(context);metadata=[]
    for i,k in pages.items():
        r=rows[i];bounds=bounds_for(r);x,y,xx,yy=bounds
        for engine in ['pdfium','poppler']:
            asset=f'item{len(metadata):05d}'
            source=render(ROOT/'qualification/pdf_packaging/groups/financial-input.pdf',r['page'],300,engine)[y:yy,x:xx]
            current=render(default,r['page'],300,engine)[y:yy,x:xx]
            candidate=((1-crop_render(context,doc,k,bounds,engine))*255).round().astype('uint8')
            assert source.shape==current.shape==candidate.shape
            for label,array in [('source',source),('current',current),('candidate',candidate)]:Image.fromarray(array).save(staging/'assets'/f'{asset}-{label}.png')
            metadata.append(dict(asset=asset,member=i,page=r['page'],renderer=engine,bounds=bounds,rust_only_acceptance=i in report['rust_only_acceptances'],native_sha256=sha(native),default_sha256=sha(default),identical_default_context=True))
    doc.close();write(staging/'panels.json',metadata)
    with(FINAL/'blind-seal.log').open('w')as log:subprocess.run([sys.executable,'-m','qualification.font04.r1_seal_review',str(staging),str(public),str(key)],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,check=True)
    receipt=json.loads((public/'seal-receipt.json').read_text());result=dict(schema='font04-R1-sealed-review-v1',status='SEALED; reviewer pending; key not revealed',rust_only_acceptances=report['rust_only_acceptances'],all_rust_only_included=True,other_parity_divergences_included=True,members=len(selected),panels=receipt['panels'],review_pdf=str((public/'blinded-review.pdf').relative_to(ROOT)),review_sha256=receipt['review_sha256'],judgments=str((public/'judgments-template.json').relative_to(ROOT)),key_path=str(key.relative_to(ROOT)),key_sha256=receipt['key_sha256'],key_revealed=False,consumer_renderers=['PDFium','Poppler'],scales=['100%','400%'],source='original scanned financial input',context='Only the target draw is replaced in identical default context')
    write(BASE/'r1-blind-review.json',result);print('Sealed review ready; independent judgments pending',flush=True)


if __name__=='__main__':main()
