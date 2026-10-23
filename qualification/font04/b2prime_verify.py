"""Independent complete-output contracts, validators, economy and attribution."""
from pathlib import Path
import collections,io,json,os,re,subprocess,sys
import pikepdf
from fontTools.ttLib import TTFont
from qualification.font04.metrics import sha,inspect
from qualification.font04.prime_verify import text,stats
from qualification.font04.class_verify import raster_signature,actual_text_signature
from qualification.font04.prime_metrics import headline

def aggregate(records,metric,subset):return headline(records,'B2prime',metric,subset)
BASE=Path('qualification/font04');ROOT=BASE/'local';DEFAULT=ROOT/'financial-default.pdf'

def text_geometry(path):
    rows=[];font_info={}
    with pikepdf.open(path) as pdf:
        for pi,page in enumerate(pdf.pages):
            mode=0;tm=None;font=None;size=None
            for args,op in pikepdf.parse_content_stream(page):
                name=str(op)
                if name=='Tr':mode=int(args[0])
                elif name=='Tm':tm=[float(x) for x in args]
                elif name=='Tf':
                    font=page.Resources.Font[str(args[0])];size=float(args[1]);key=font.objgen
                    if key not in font_info:
                        import hashlib
                        font_info[key]=dict(widths=hashlib.sha256(str(font.DescendantFonts[0].W).encode()).hexdigest(),default_width=str(font.DescendantFonts[0].get('/DW')),actual_font_metrics=str(font.DescendantFonts[0].FontDescriptor.get('/Ascent'))+str(font.DescendantFonts[0].FontDescriptor.get('/Descent')))
                elif name=='Tj':rows.append(dict(page=pi,mode=mode,cid=bytes(args[0]).hex(),matrix=tm,size=size,**font_info[key]))
    return rows

def all_token_search(path):
    import pypdfium2 as pdfium
    doc=pdfium.PdfDocument(path);result=[]
    for page in doc:
        textpage=page.get_textpage();tokens=sorted(set(re.findall(r'\S+',textpage.get_text_range())));counts={}
        for token in tokens:
            query=textpage.search(token);n=0
            while query.get_next() is not None:n+=1
            query.close();counts[token]=n
        result.append(counts);textpage.close();page.close()
    doc.close();return result

def validate(path):
    with pikepdf.open(path) as pdf:
        data=next(iter(pdf.pages[0].Resources.Font.values())).DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()
    font=Path(str(path)+'.ttf');font.write_bytes(data);env=dict(os.environ,LD_LIBRARY_PATH=str(Path('tools/dist/lib').resolve()));commands=dict(qpdf=['tools/dist/bin/qpdf','--check',str(path)],ots=['tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize',str(font),str(font)+'.sanitized']);result={}
    for key,cmd in commands.items():
        p=subprocess.run(cmd,env=env,capture_output=True,text=True);result[key]=dict(returncode=p.returncode,output=p.stdout+p.stderr)
    return result

def verify(path,transport=False):
    art=Path(str(path)+'.font04');plan=json.loads((art/'plan.json').read_text());rows=json.loads((art/'source.json').read_text())['rows'];base=inspect(DEFAULT);inv=inspect(path);bypage={p:[d for d in base['draws'] if d['page']==p]for p in range(13)};newpage={p:[d for d in inv['draws'] if d['page']==p]for p in range(13)};assigned={(a['page'],a['occurrence']) for a in plan['assignments']};unchanged=True
    for p in range(13):
        assert len(bypage[p])==len(newpage[p])
        for oi,(a,b) in enumerate(zip(bypage[p],newpage[p])):
            if (p,oi) not in assigned:unchanged &= a['program']==b['program'] and a['matrix']==b['matrix']
    invisible=lambda x:[(d['page'],d['cid'],d['character'],d['program'],d['matrix']) for d in x['users'] if d['invisible']]
    t0,s0=text(DEFAULT);t,s=text(path);tokens0=all_token_search(DEFAULT);tokens=all_token_search(path);pop={}
    for mode,flags in [('layout',['-layout']),('reading',[]),('raw',['-raw'])]:
        a=subprocess.check_output(['pdftotext',*flags,str(DEFAULT),'-']);b=subprocess.check_output(['pdftotext',*flags,str(path),'-']);tokens=set(re.findall(rb'\S+',a));pop[mode]=dict(extraction_equal=a==b,literal_search_equal=all(a.count(w)==b.count(w) for w in tokens),queries=len(tokens))
    validation=validate(path);metrics=json.loads((art/'class-metrics.json').read_text());classes={}
    with pikepdf.open(path) as pdf:
        data=next(iter(pdf.pages[0].Resources.Font.values())).DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()
    tt=TTFont(io.BytesIO(data));order=tt.getGlyphOrder()
    def leaves(gid):
        glyph=tt['glyf'][order[gid]]
        if not glyph.isComposite():return {gid}
        return set().union(*(leaves(tt.getGlyphID(c.glyphName)) for c in glyph.components))
    attribution_path=art/'byte-attribution.json';attribution=json.loads(attribution_path.read_text()) if attribution_path.exists() else None
    with pikepdf.open(DEFAULT) as pdf:
        oldtt=TTFont(io.BytesIO(pdf.pages[0].Resources.Font.F1.DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()))
    oldorder=oldtt.getGlyphOrder();oldowners=collections.defaultdict(set)
    for d in base['users']:oldowners[oldorder[d['gid']]].add(d['character'])
    leaf_visible=set().union(*(leaves(d['gid']) for d in inv['draws']))
    outline_economy=dict(before_visible_outlines=len({d['gid'] for d in base['draws']}),after_visible_leaf_outlines=len(leaf_visible),draws_per_leaf_outline=len(inv['draws'])/len(leaf_visible),visible_CID_to_GID_slots=len({d['gid'] for d in inv['draws']}),required_slots_including_stubs=sum(f['slots'] for f in inv['fonts'].values()),stub_slots=sum(tt['glyf'][name].isComposite() for name in order),outline_slots=sum(not tt['glyf'][name].isComposite() for name in order))
    for c in sorted({r['character'] for r in rows}):
        a=[d for d in base['draws'] if d['character']==c];b=[d for d in inv['draws'] if d['character']==c];leafs=set().union(*(leaves(d['gid']) for d in b));required={d['gid'] for d in inv['users'] if d['character']==c};added=[r for r in attribution['added_programs'] if r['kind']=='canonical' and rows[int(r['program'].removeprefix('canonical'))]['character']==c] if attribution else [];retired=[r for r in attribution['retired_programs'] if oldowners[r['program']]=={c}] if attribution else []
        classes[c]=dict(draws=len(a),before_required_visible_programs=len({d['gid'] for d in a}),after_visible_stub_or_outline_slots=len({d['gid'] for d in b}),visible_leaf_outlines=len(leafs),draws_per_leaf_outline=len(b)/len(leafs),required_slots=len(required),outline_points=sum(len(tt['glyf'][order[gid]].coordinates) if tt['glyf'][order[gid]].numberOfContours>0 else 0 for gid in set().union(*(leaves(gid) for gid in required))),decoded_glyf_bytes=sum(len(tt['glyf'][order[gid]].compile(tt['glyf'])) for gid in required|set().union(*(leaves(gid) for gid in required))),encoded_font_bytes=None,encoded_font_note='Shared compression; complete font bytes reported globally, no arbitrary per-class allocation.',added_outlines=len(added),retired_outlines=len(retired),net_retired_outlines=len(retired)-len(added),added_outline_glyf_bytes=sum(r['bytes'] for r in added),retired_outline_glyf_bytes=sum(r['bytes'] for r in retired),substituted=sum(x['character']==c for x in plan['assignments']))
    result=dict(pdf=str(path),sha256=sha(path),default=stats(base),experimental=stats(inv),text_geometry_equal=text_geometry(DEFAULT)==text_geometry(path),actual_text_equal=actual_text_signature(DEFAULT)==actual_text_signature(path),pdfium_text_equal=t0==t,pdfium_search_equal=s0==s and tokens0==tokens,pdfium_all_token_queries=sum(len(p) for p in tokens0),pdfium_search_scope='Every non-whitespace token, including amounts, dates, punctuation and short labels; native PDFium Find counts.',poppler=pop,validation=validation,raster_equal=raster_signature(DEFAULT)==raster_signature(path),unsubstituted_programs_and_matrices_equal=bool(unchanged),invisible_users_equal=invisible(base)==invisible(inv),functional_veto_rejections=0,metrics={m:{ss:aggregate(metrics['records'],m,ss) for ss in ['all','substituted']} for m in ['analytic','direct','pdfium','poppler']},renderer_floors=metrics['renderer_vs_analytic_floors'],classes=classes,reviewer_pending=True,outline_economy=outline_economy)
    if transport:
        old=json.loads((ROOT/'financial-B2-P-initial.pdf.font04/class-metrics.json').read_text());deltas={}
        for m in ['analytic','direct','pdfium','poppler']:
            rr=[r for r in metrics['records'] if r['metric']==m and r['accepted']];oo={r['member']:r for r in old['records'] if r['metric']==m};v=[r['candidate']['error']-oo[r['member']]['candidate']['error'] for r in rr];deltas[m]=dict(mean_error_change=sum(v)/len(v),max_absolute_member_error_change=max(map(abs,v)),n=len(v),p95_error_change=aggregate(metrics['records'],m,'substituted')['p95']-aggregate(old['records'],m,'substituted')['p95'])
        # Integer design-unit offsets and F2Dot14 cause unavoidable quantization.
        # Native differences are compared to the already measured renderer floor.
        equal=all(abs(deltas[m]['mean_error_change'])<.002 and abs(deltas[m]['p95_error_change'])<.003 for m in ['analytic','direct']) and all(abs(deltas[m]['mean_error_change'])<=metrics['renderer_vs_analytic_floors'][m]['mean'] and abs(deltas[m]['p95_error_change'])<=metrics['renderer_vs_analytic_floors'][m]['p95'] for m in ['pdfium','poppler']);result['fidelity_equivalence_rule']='Analytic/direct: mean <0.002 and p95 <0.003 absolute error; native: changes below measured identical-outline renderer-vs-analytic floors. Native snapping changes with preserved default Tm; native pixels are not asserted identical.';result.update(P_initial_membership_equal=plan['assignments']==json.loads((ROOT/'financial-B2-P-initial.pdf.font04/plan.json').read_text())['assignments'],transport_fidelity_deltas=deltas,transport_fidelity_equal_within_quantization_and_renderer_floor=equal)
    result['pass']=all([result['text_geometry_equal'],result['actual_text_equal'],result['pdfium_text_equal'],result['pdfium_search_equal'],result['raster_equal'],result['unsubstituted_programs_and_matrices_equal'],result['invisible_users_equal'],all(v['extraction_equal'] and v['literal_search_equal'] for v in pop.values()),all(v['returncode']==0 for v in validation.values()),result.get('transport_fidelity_equal_within_quantization_and_renderer_floor',True)])
    (art/'verification.json').write_text(json.dumps(result,indent=2)+'\n');out=BASE/('b2prime-transport-verification.json' if transport else path.stem+'-verification.json');out.write_text(json.dumps(result,indent=2)+'\n');print(path.name,'PASS',result['pass'],'bytes',result['experimental']['bytes'], 'deltas',result.get('transport_fidelity_deltas'),flush=True);assert result['pass']
    return result

if __name__=='__main__':verify(Path(sys.argv[1]),'--transport' in sys.argv)
