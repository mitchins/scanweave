"""Issue the unchanged owned-ink veto directly from isolated analytic controls."""
from pathlib import Path
import json,sys
import pypdfium2 as pdfium
from qualification.font04.class_metrics import crop_render
from qualification.font04.owned_ink import components,HALO,MIN_AREA,MIN_MASS,test
from qualification.font04.metrics import sha

def main(path):
    test();art=Path(str(path)+'.font04');rows=json.loads((art/'source.json').read_text())['rows'];plan=json.loads((art/'plan.json').read_text());docs={name:pdfium.PdfDocument(art/f'class-isolated-{name}.pdf') for name in ['source','default','candidate']};ledger=[]
    for count,a in enumerate(plan['assignments']):
        i=a['member'];r=rows[i];x,y,xx,yy=map(int,r['source']['bbox']);bounds=[x-4,y-4,xx+4,yy+4];arrays={name:crop_render(art/f'class-isolated-{name}.pdf',doc,i,bounds,'analytic') for name,doc in docs.items()};cc=components(arrays['source'],arrays['default'],arrays['candidate'],i)
        for c in cc:c.update(character=r['character'],page=r['page'],id=r['id'])
        ledger.extend(cc)
        if count%100==0:print('owned analytic',count,len(plan['assignments']),flush=True)
    for doc in docs.values():doc.close()
    fired=sorted({r['member'] for r in ledger if r['fires']});mark=next(r['index'] for r in rows if r['page']==12 and r['id']=='w000133s0002' and r['character']=='e');assert mark in fired,'glyph-277 owned mark must veto substitution'
    result=dict(schema='font04-owned-components-v1',source_pdf=str(path),source_pdf_sha256=sha(path),exceptions=fired,components=ledger,policy=dict(halo_pixels=HALO,min_area=MIN_AREA,min_mass=MIN_MASS,source_threshold=.25,default_ownership_threshold=.15,candidate_footprint_threshold=.10),glyph_277_member=mark,regression_glyph_277='Owned mark veto PASS; final complete PV verification pending',reference='Same isolated 4x analytic source/default/candidate crops as class_metrics; every component logged.')
    Path('qualification/font04/b2-owned-component-ledger.json').write_text(json.dumps(result,separators=(',',':'))+'\n');print('owned veto',len(fired),'members; glyph-277 global member',mark)

if __name__=='__main__':main(Path(sys.argv[1]))
