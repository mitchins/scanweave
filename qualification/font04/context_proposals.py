"""One proposed glyph per full-context page; neighbours remain exactly default."""
from pathlib import Path
import pikepdf
from qualification.font04.causal import glyph_matrix
from qualification.font04.metrics import operands,matrix
from qualification.font04.pdf_helpers import font_resource

def draw_key(cid,m):return (int(cid),tuple(round(float(v),6) for v in m))

def contextual_pdf(base,destination,rows,proposals,bound,outlines,font_path):
    lookup={o['key']:o for o in outlines if 'gid' in o};pages={}
    with pikepdf.open(base) as original:
        pdf=pikepdf.Pdf.new();font=font_resource(pdf,font_path,outlines)
        for i,proposal in sorted(proposals.items()):
            d=bound[str(i)] if str(i) in bound else bound[i];target=draw_key(d['cid'],d['matrix']);pdf.pages.append(original.pages[rows[i]['page']]);page=pdf.pages[-1]
            resources=pikepdf.Dictionary(page.Resources);fonts=pikepdf.Dictionary(resources.Font);fonts['/FONT04Proposal']=font;resources.Font=fonts;page.Resources=resources
            instructions=[];mode=0;tm=None;current_font=None;seen=0;fill=([0],pikepdf.Operator('g'));target_fill=None;stack=[]
            for args,op in pikepdf.parse_content_stream(page):
                name=str(op)
                if name=='q':stack.append(fill)
                elif name=='Q':fill=stack.pop()
                elif name in ('g','rg','k'):fill=(list(args),op)
                if name=='Tr':mode=int(args[0])
                elif name=='Tm':tm=list(args)
                elif name=='Tf':current_font=str(args[0])
                if name=='Tj' and mode!=3 and current_font=='/F1' and tm is not None:
                    raw=bytes(args[0])
                    if len(raw)==2 and draw_key(int.from_bytes(raw,'big'),tm)==target:seen+=1;target_fill=fill;continue
                instructions.append((args,op))
            assert seen==1,('proposal replacement mismatch',i,seen)
            o=lookup['font04-e-'+str(proposal['canonical'])];m=matrix(proposal['matrix']) if 'matrix' in proposal else glyph_matrix(rows[i],o,proposal['bbox'])
            colour=' '.join(map(str,target_fill[0]))+' '+str(target_fill[1])
            command='q '+colour+' BT 0 Tr /FONT04Proposal 1 Tf '+' '.join(map(str,operands(m)))+f" Tm <{o['gid']:04x}> Tj ET Q\n"
            page.Contents=pdf.make_stream(pikepdf.unparse_content_stream(instructions)+b'\n'+command.encode());pages[i]=len(pdf.pages)-1
        pdf.save(destination,deterministic_id=True)
    return pages
