"""Exact emitted glyphs in identical default page context, one proposal per page."""
from pathlib import Path
import pikepdf
from qualification.font04.context_proposals import draw_key

def contextual_instances(base,candidate,destination,rows,selected,bindings):
    result={}
    with pikepdf.open(base) as original,pikepdf.open(candidate) as proposed:
        pdf=pikepdf.Pdf.new();fonts={}
        for i in sorted(selected):
            row=rows[i];d=bindings[i];target=draw_key(d['cid'],d['matrix']);pdf.pages.append(original.pages[row['page']]);page=pdf.pages[-1];f=proposed.pages[row['page']].Resources.Font[d['font']];key=f.objgen
            if key not in fonts:fonts[key]=pdf.copy_foreign(f)
            resources=pikepdf.Dictionary(page.Resources);fr=pikepdf.Dictionary(resources.Font);fr['/F04Review']=fonts[key];resources.Font=fr;page.Resources=resources;instructions=[];mode=0;tm=None;active=None;fill=([0],pikepdf.Operator('g'));stack=[];seen=0;target_fill=None
            for args,op in pikepdf.parse_content_stream(page):
                name=str(op)
                if name=='q':stack.append(fill)
                elif name=='Q':fill=stack.pop()
                elif name in ('g','rg','k'):fill=(list(args),op)
                if name=='Tr':mode=int(args[0])
                elif name=='Tm':tm=list(args)
                elif name=='Tf':active=str(args[0])
                if name=='Tj' and mode!=3 and active=='/F1' and tm is not None and draw_key(int.from_bytes(bytes(args[0]),'big'),tm)==target:
                    seen+=1;instructions.append(([pikepdf.Name('/F04Review'),1],pikepdf.Operator('Tf')));instructions.append((args,op));instructions.append(([pikepdf.Name('/F1'),1],pikepdf.Operator('Tf')));continue
                instructions.append((args,op))
            assert seen==1,(i,seen)
            page.Contents=pdf.make_stream(pikepdf.unparse_content_stream(instructions));result[i]=len(pdf.pages)-1
        pdf.save(destination,deterministic_id=True,object_stream_mode=pikepdf.ObjectStreamMode.generate)
    return result
