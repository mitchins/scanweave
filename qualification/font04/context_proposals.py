"""Composite proposed glyphs into ordinary default page content for blind review."""
from pathlib import Path
import numpy as np
import pikepdf
from qualification.font04.causal import glyph_matrix
from qualification.font04.metrics import operands
from qualification.font04.pdf_helpers import font_resource

def draw_key(cid,m):return (int(cid),tuple(round(float(v),6) for v in m))

def contextual_pdf(base,destination,rows,proposals,bound,outlines,font_path):
    lookup={o['key']:o for o in outlines if 'gid' in o}
    targets={}
    for i in proposals:
        d=bound[str(i)] if str(i) in bound else bound[i]
        targets.setdefault(rows[i]['page'],{})[draw_key(d['cid'],d['matrix'])]=i
    seen=[]
    with pikepdf.open(base) as pdf:
        font=font_resource(pdf,font_path,outlines)
        for pi,page in enumerate(pdf.pages):
            page.Resources.Font['/FONT04Proposal']=font
            instructions=[];mode=0;tm=None;current_font=None
            for args,op in pikepdf.parse_content_stream(page):
                name=str(op)
                if name=='Tr':mode=int(args[0])
                elif name=='Tm':tm=list(args)
                elif name=='Tf':current_font=str(args[0])
                if name=='Tj' and mode!=3 and current_font=='/F1' and tm is not None:
                    raw=bytes(args[0])
                    if len(raw)==2:
                        key=draw_key(int.from_bytes(raw,'big'),tm)
                        if key in targets.get(pi,{}):seen.append(targets[pi][key]);continue
                instructions.append((args,op))
            commands=[]
            for i in sorted(targets.get(pi,{}).values()):
                proposal=proposals[i];o=lookup['font04-e-'+str(proposal['canonical'])]
                m=glyph_matrix(rows[i],o,proposal['bbox'])
                commands.append('BT 0 Tr 0 g /FONT04Proposal 1 Tf '+' '.join(map(str,operands(m)))+f" Tm <{o['gid']:04x}> Tj ET")
            original=pikepdf.unparse_content_stream(instructions)
            page.Contents=pdf.make_stream(original+b'\n'+('\n'.join(commands)+'\n').encode())
        assert sorted(seen)==sorted(proposals),('proposal replacement mismatch',sorted(set(proposals)-set(seen)))
        pdf.save(destination,deterministic_id=True)
