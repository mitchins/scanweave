"""Conservative group veto for the existing exact text/search contract.

Canonical normalization can change extractor font-size/layout heuristics without
changing Unicode or ink identity. Test existing star groups in deterministic order;
any group which changes either native extraction/search stays on its old outlines.
No glyph acceptance veto, error criterion, OCR text, raster or compositor is relaxed.
Counterfactual PDFs are diagnostics; final output is rebuilt by the normal CLI.
"""
from pathlib import Path
from decimal import Decimal
import json,re,subprocess,sys,tempfile
import pikepdf
import pypdfium2 as pdfium
from qualification.font04.metrics import inspect,sha
BASE=Path('qualification/font04/local/financial-default.pdf')

def native(path,page):
    doc=pdfium.PdfDocument(path);p=doc[page];t=p.get_textpage();value=t.get_text_range();counts={}
    for word in sorted(set(re.findall('[A-Za-z]{3,}',value))):
        search=t.search(word);n=0
        while search.get_next() is not None:n+=1
        search.close();counts[word]=n
    t.close();p.close();doc.close()
    pop=subprocess.check_output(['pdftotext','-f',str(page+1),'-l',str(page+1),'-layout',str(path),'-'])
    return value,counts,pop

class Probe:
    def __init__(self,path,rows,assignments):
        self.path=path;self.rows=rows;self.assigned={a['member']:a for a in assignments};self.pdf=pikepdf.open(path);self.base=pikepdf.open(BASE);inv=inspect(BASE);self.old={pi:[d for d in inv['draws'] if d['page']==pi] for pi in range(13)};self.by_occ={pi:{r['occurrence']:r['index'] for r in rows if r['page']==pi and r['index'] in self.assigned} for pi in range(13)};self.reference={pi:native(BASE,pi) for pi in range(13)};self.instructions={pi:list(pikepdf.parse_content_stream(self.pdf.pages[pi])) for pi in range(13)}
    def check(self,accepted,pages):
        failed=[]
        for pi in sorted(pages):
            pdf=pikepdf.Pdf.new();pdf.pages.append(self.pdf.pages[pi]);page=pdf.pages[-1];pdf.pages.append(self.base.pages[pi]);font=pdf.pages[-1].Resources.Font.F1;del pdf.pages[-1];resources=pikepdf.Dictionary(page.Resources);fonts=pikepdf.Dictionary(resources.Font);fonts['/FONT04Default']=font;resources.Font=fonts;page.Resources=resources;instructions=[];mode=0;occ=0
            for args,op in self.instructions[pi]:
                name=str(op)
                if name=='Tr':mode=int(args[0])
                if name=='Tj' and mode!=3:
                    member=self.by_occ[pi].get(occ);old=self.old[pi][occ];occ+=1
                    if member is not None and member not in accepted:
                        instructions.extend([([pikepdf.Name('/FONT04Default'),1],pikepdf.Operator('Tf')),([Decimal(str(x)) for x in old['matrix']],pikepdf.Operator('Tm')),([pikepdf.String(old['cid'].to_bytes(2,'big'))],pikepdf.Operator('Tj')),([pikepdf.Name('/F1'),1],pikepdf.Operator('Tf'))]);continue
                instructions.append((args,op))
            assert occ==len(self.old[pi])
            page.Contents=pdf.make_stream(pikepdf.unparse_content_stream(instructions))
            with tempfile.TemporaryDirectory() as tmp:
                output=Path(tmp)/'probe.pdf';pdf.save(output,deterministic_id=True);current=native(output,0)
            equal=[current[i]==self.reference[pi][i] for i in range(3)]
            if not all(equal):failed.append(dict(page=pi,pdfium_text=equal[0],pdfium_search=equal[1],poppler_layout=equal[2]))
        return failed

def main(path,ownership=None):
    art=Path(str(path)+'.font04');rows=json.loads((art/'source.json').read_text())['rows'];plan=json.loads((art/'plan.json').read_text());groups={}
    for a in plan['assignments']:groups.setdefault(a['canonical'],[]).append(a)
    owner=json.loads(Path(ownership).read_text()) if ownership else None;owned=set(owner['exceptions']) if owner else set();eligible={}
    for j,items in groups.items():
        survivors=[a for a in items if a['member'] not in owned] if j not in owned else []
        if len(survivors)>=2:eligible[j]=survivors
    probe=Probe(path,rows,plan['assignments']);assert not probe.check(set(),range(13)), 'default counterfactual is not identical'
    kept=set();accepted_groups=[];rejected=[]
    # e is the independently passed B1 control. Other groups are checked against
    # this fixed safe seed; the order is precommitted label/canonical order.
    seed={j:items for j,items in eligible.items() if rows[j]['character']=='e'}
    seed_members={a['member'] for items in seed.values() for a in items}
    if not probe.check(seed_members,range(13)):kept|=seed_members;accepted_groups.extend(sorted(seed))
    else:seed={}
    order=sorted((j for j in eligible if j not in seed),key=lambda j:(rows[j]['character'],j))
    for count,j in enumerate(order):
        items=eligible[j];proposed=kept|{a['member'] for a in items};pages={a['page'] for a in items};failed=probe.check(proposed,pages)
        if failed:rejected.append(dict(canonical=j,character=rows[j]['character'],members=[a['member'] for a in items],reason='functional_text_identity',value=failed,limit=dict(pdfium_text=True,pdfium_search=True,poppler_layout=True)))
        else:kept=proposed;accepted_groups.append(j)
        if count%10==0:print('functional groups',count,len(order),'kept draws',len(kept),flush=True)
    assert not probe.check(kept,range(13))
    result=dict(schema='font04-functional-veto-v1',control_pdf=str(path),control_sha256=sha(path),ownership_ledger=ownership,accepted_members=sorted(kept),accepted_groups=accepted_groups,rejected_groups=rejected,method='Deterministic group-wise exact native text/search veto; e seed then label/canonical order. Original star groups and every glyph veto unchanged.',final_counterfactual_text_search_equal=True)
    dest=Path('qualification/font04/'+('b2-PV-functional-ledger.json' if ownership else 'b2-P-functional-ledger.json'));dest.write_text(json.dumps(result,indent=2)+'\n');print('functional result',len(kept),'draws',len(accepted_groups),'groups;',len(rejected),'group exceptions')

if __name__=='__main__':main(Path(sys.argv[1]),sys.argv[2] if len(sys.argv)>2 else None)
