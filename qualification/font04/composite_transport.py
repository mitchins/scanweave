"""Opt-in complete-PDF metric-preserving composite transport; no default hook.

The default content retains CIDs, text matrices, widths and ActualText. Resource
variants resolve repeated-CID instance transforms, sharing one embedded glyf font.
"""
from pathlib import Path
import collections,copy,io,json,logging
import numpy as np
import pikepdf
from fontTools.ttLib import TTFont
from fontTools.ttLib.tables._g_l_y_f import Glyph,GlyphComponent
from fontTools.pens.ttGlyphPen import TTGlyphPen
from fontTools.pens.transformPen import TransformPen
from fontTools import subset
from qualification.font04.metrics import matrix,sha
from qualification.font04.causal import glyph_matrix
ROOT=Path('qualification/font04/local')
CONTROL=ROOT/'financial-B2-P-initial.pdf'
logging.getLogger('fontTools.ttLib.tables._h_e_a_d').setLevel(logging.ERROR)


def emit(destination,plan,control=CONTROL):
    art=Path(str(control)+'.font04');snap=json.loads((art/'source.json').read_text());rows=snap['rows'];outlines=json.loads((art/'outlines.json').read_text())['records'];lookup={int(o['key'].rsplit('-',1)[1]):o for o in outlines if 'gid'in o};geometry=json.loads((ROOT/'financial-default.pdf.json').read_text())['pages']
    bound=json.loads((art/'emitted-bindings.json').read_text());canon=TTFont(art/'canonical.ttf',recalcTimestamp=False)
    assignments={(a['page'],a['occurrence']):a for a in plan['assignments']}
    with pikepdf.open(ROOT/'financial-default.pdf') as pdf:
        parent=pdf.pages[0].Resources.Font.F1;desc=parent.DescendantFonts[0];original_data=desc.FontDescriptor.FontFile2.read_bytes();tt=TTFont(io.BytesIO(original_data),recalcTimestamp=False);order=list(tt.getGlyphOrder());glyf=tt['glyf'];metrics=tt['hmtx'].metrics
        oldmap=desc.CIDToGIDMap.read_bytes();mapping=[int.from_bytes(oldmap[i:i+2],'big') for i in range(0,len(oldmap),2)]
        instances={};transforms={};base_draws={}
        # Original bindings already verified bijective in B2; no spatial matching.
        for a in plan['assignments']:
            i=a['member'];r=dict(rows[i]);g=geometry[r['page']];r.update(pixel_x_pt=g['width_pt']/g['raster_width'],pixel_y_pt=g['height_pt']/g['raster_height']);d=bound[str(i)];base_draws[i]=d
            m=glyph_matrix(r,lookup[a['canonical']],a['bbox']);t=np.linalg.inv(matrix(d['matrix']))@m
            t[:2,2]*=tt['head'].unitsPerEm
            transforms[i]=t
        factors={j:max(1.,max(np.abs(transforms[a['member']][:2,:2]).max() for a in plan['assignments'] if a['canonical']==j)/1.5) for j in {a['canonical'] for a in plan['assignments']}}
        canonical_names={}
        for j,factor in sorted(factors.items()):
            name=f'canonical{j}';pen=TTGlyphPen(None);canon.getGlyphSet()[canon.getGlyphOrder()[lookup[j]['gid']]].draw(TransformPen(pen,(factor,0,0,factor,0,0)));glyf.glyphs[name]=pen.glyph();metrics[name]=(2048,0);canonical_names[j]=name;order.append(name)
        stub_names={};instance_ledger=[]
        for a in plan['assignments']:
            i=a['member'];j=a['canonical'];d=base_draws[i];t=transforms[i];lin=t[:2,:2]/factors[j];offset=np.rint(t[:2,2]).astype(int)
            if np.abs(lin).max()>=2 or np.abs(offset).max()>32767:raise ValueError(('composite transform range',i,t.tolist()))
            quant=np.rint(lin*16384)/16384;key=(j,tuple(quant.ravel()),tuple(offset),mapping[d['cid']])
            if key not in stub_names:
                name=f'instance{len(stub_names)}';c=GlyphComponent();c.glyphName=canonical_names[j];c.x,c.y=map(int,offset);c.transform=quant.T.tolist();c.flags=4|0x1000 # ROUND_XY_TO_GRID and UNSCALED_COMPONENT_OFFSET
                glyph=Glyph();glyph.numberOfContours=-1;glyph.components=[c];glyf.glyphs[name]=glyph;metrics[name]=metrics[tt.getGlyphOrder()[mapping[d['cid']]]];stub_names[key]=name;order.append(name)
            instances[i]=stub_names[key];instance_ledger.append(dict(member=i,canonical=j,cid=d['cid'],stub=instances[i],transform=t.tolist(),quantized_linear=quant.tolist(),offset=offset.tolist()))
        tt.setGlyphOrder(order)
        # Allocate variant maps; every unassigned occurrence uses the original map.
        variants=[];draw_variant={};needed={'.notdef'};all_draws={}
        for pi,page in enumerate(pdf.pages):
            mode=0;oi=0
            for args,op in pikepdf.parse_content_stream(page):
                if str(op)=='Tr':mode=int(args[0])
                if str(op)!='Tj':continue
                raw=bytes(args[0]);assert len(raw)==2;cid=int.from_bytes(raw,'big');a=assignments.get((pi,oi)) if mode!=3 else None
                name=instances[a['member']] if a else order[mapping[cid]];needed.add(name)
                variant=next((k for k,v in enumerate(variants) if cid not in v or v[cid]==name),None)
                if variant is None:variant=len(variants);variants.append({})
                variants[variant][cid]=name;draw_variant[pi,mode,oi,cid]=variant
                if mode!=3:oi+=1
        # Subset removes old programs only when no visible/invisible owner needs them.
        before={name:len(glyf[name].compile(glyf)) for name in order if name not in canonical_names.values() and name not in stub_names.values()}
        options=subset.Options();options.recalc_timestamp=False;options.notdef_outline=True;options.layout_features=[];options.name_IDs=['*'];sub=subset.Subsetter(options=options);sub.populate(glyphs=needed);sub.subset(tt)
        tt['head'].modified=0;tt['head'].created=0;buffer=io.BytesIO();tt.save(buffer,reorderTables=False);data=buffer.getvalue();neworder=tt.getGlyphOrder();gids={name:i for i,name in enumerate(neworder)}
        stream=pdf.make_stream(data);stream.Length1=len(data);descriptor=pikepdf.Dictionary(desc.FontDescriptor);descriptor.FontFile2=stream;descriptor=pdf.make_indirect(descriptor)
        fonts=[];widths=pdf.make_indirect(desc.W)
        for v in variants:
            child=pikepdf.Dictionary(desc);child.FontDescriptor=descriptor;child.W=widths
            mapbytes=b''.join(gids.get(v.get(cid,order[oldgid]),0).to_bytes(2,'big') for cid,oldgid in enumerate(mapping));child.CIDToGIDMap=pdf.make_stream(mapbytes)
            font=pikepdf.Dictionary(parent);font.DescendantFonts=pikepdf.Array([pdf.make_indirect(child)]);fonts.append(pdf.make_indirect(font))
        for pi,page in enumerate(pdf.pages):
            resources=pikepdf.Dictionary(page.Resources);fr=pikepdf.Dictionary(resources.Font)
            for k,f in enumerate(fonts):fr[f'/F04V{k}']=f
            resources.Font=fr;page.Resources=resources;instructions=[];mode=0;oi=0;size=1;active=None
            for args,op in pikepdf.parse_content_stream(page):
                if str(op)=='Tr':mode=int(args[0])
                if str(op)=='Tf':size=float(args[1]);active=None;continue
                if str(op)=='Tj':
                    cid=int.from_bytes(bytes(args[0]),'big');v=draw_variant[pi,mode,oi,cid]
                    if active!=v:instructions.append(([pikepdf.Name(f'/F04V{v}'),size],pikepdf.Operator('Tf')));active=v
                    if mode!=3:oi+=1
                instructions.append((args,op))
            page.Contents=pdf.make_stream(pikepdf.unparse_content_stream(instructions))
            del page.Resources.Font['/F1']
        pdf.save(destination,deterministic_id=True,compress_streams=True)
        kept=set(neworder);retired=[dict(program=name,bytes=count) for name,count in before.items() if name not in kept]
        added=[dict(program=name,kind='canonical' if name in canonical_names.values() else 'stub',bytes=len(tt['glyf'][name].compile(tt['glyf'])),points=(len(tt['glyf'][name].coordinates) if tt['glyf'][name].numberOfContours>0 else 0)) for name in neworder if name in canonical_names.values() or name in stub_names.values()]
        return dict(pdf=str(destination),sha256=sha(destination),bytes=destination.stat().st_size,decoded_font_bytes=len(data),encoded_font_bytes=None,canonical_count=len(canonical_names),stub_count=len(stub_names),font_resource_variants=len(variants),retired_programs=retired,added_programs=added,instances=instance_ledger,transport='CID/Tm/W/ActualText preserved; shared embedded TrueType composite font; metric-identical resource variants for conflicting CID transforms')

if __name__=='__main__':
    import sys
    p=Path(sys.argv[1]);plan=json.loads(Path(str(CONTROL)+'.font04/plan.json').read_text());result=emit(p,plan);Path(str(p)+'.transport.json').write_text(json.dumps(result,indent=2)+'\n');print({k:v for k,v in result.items() if k not in ('instances','added_programs','retired_programs')})
