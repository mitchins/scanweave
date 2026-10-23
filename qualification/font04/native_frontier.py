"""Native original-page fidelity for all bounded B1 grouping/error sweep points."""
from pathlib import Path
import json
import numpy as np
import pikepdf
from qualification.font04.planner import choose
from qualification.font04.geometry import register
from qualification.font04.causal import glyph_matrix
from qualification.font04.metrics import render,measure,summary,sha
from qualification.font04.pdf_helpers import font_resource


def main():
    root=Path('qualification/font04/local');artifact=root/'financial-experimental-v2.pdf.font04';directory=root/'frontier';directory.mkdir(exist_ok=True)
    snapshot=json.loads((artifact/'source.json').read_text());rows=snapshot['rows'];plan=json.loads((artifact/'plan.json').read_text());pairs=json.loads((artifact/'pair-ledger.json').read_text());meta=json.loads((artifact/'frames.json').read_text());outlines=json.loads((artifact/'outlines.json').read_text())['records'];lookup={o['key']:o for o in outlines if'gid'in o};fields=np.load(artifact/'fields.npy');geometry=json.loads((root/'financial-default.pdf.json').read_text())['pages'];bindings=json.loads((artifact/'emitted-bindings.json').read_text());n=len(rows);errors=np.full((n,n),np.inf);allowed=np.zeros((n,n),bool);params={}
    for p in pairs:
        i,j=p['member'],p['canonical'];errors[i,j]=p['error'];allowed[i,j]=not p['reasons'];params[i,j]=p['parameters']
    for c in plan['self_checks']:
        i=c['member'];errors[i,i]=c['error'];allowed[i,i]=not c['reasons'];o=lookup['font04-e-'+str(i)];x,y=meta['origins'][i];candidate=np.zeros((64,64));candidate[y:y+o['height'],x:x+o['width']]=np.array(o['coverage']).reshape(o['height'],o['width']);params[i,i]=register(fields[i],candidate)[0]
    ratios=np.full_like(errors,np.inf)
    for i,level in enumerate(plan['noise_floor']):
        if level is not None:ratios[i]=errors[i]/max(level,1e-6)
    sources={(e,pi):1-render(root/'financial-source-owned.pdf',pi,300,e).astype(float)/255 for e in ['pdfium','poppler']for pi in range(13)}
    result=[]
    for point in plan['frontier']:
        method=point['grouping'];threshold=point['error_scale'];groups=choose(allowed,ratios,threshold,method,rows);assigned={i:g['canonical']for g in groups for i in g['members']}
        with pikepdf.open(root/'financial-default.pdf')as original:
            pdf=pikepdf.Pdf.new();canonical=font_resource(pdf,artifact/'canonical.ttf',outlines);pdf.pages.append(original.pages[0]);base=pdf.pages[0].Resources.Font.F1;del pdf.pages[0]
            for pi in range(13):
                pdf.pages.append(original.pages[pi]);page=pdf.pages[-1];page.Resources=pikepdf.Dictionary(Font=pikepdf.Dictionary(B=base,C=canonical));commands=[]
                for i,row in enumerate(rows):
                    if row['page']!=pi:continue
                    if i not in assigned:draw=bindings[str(i)];m=draw['matrix'];gid=draw['cid'];font='B'
                    else:
                        j=assigned[i];o=lookup['font04-e-'+str(j)];x,y=meta['origins'][j];dx,dy,s=params[i,j];f=meta['frames'][i];left=32+s*(x-32)+dx;top=48+s*(y-48)+dy;bb=[f['cx']+(left-32)/f['scale'],f['baseline']+(top-48)/f['scale'],f['cx']+(left+s*o['width']-32)/f['scale'],f['baseline']+(top+s*o['height']-48)/f['scale']];g=geometry[pi];r=dict(row,pixel_x_pt=g['width_pt']/g['raster_width'],pixel_y_pt=g['height_pt']/g['raster_height']);matrix=glyph_matrix(r,o,bb);m=[matrix[0,0],matrix[1,0],matrix[0,1],matrix[1,1],matrix[0,2],matrix[1,2]];gid=o['gid'];font='C'
                    commands.append('BT 0 Tr 0 g /'+font+' 1 Tf '+' '.join(map(str,m))+f' Tm <{gid:04x}> Tj ET')
                page.Contents=pdf.make_stream(('\n'.join(commands)+'\n').encode())
            path=directory/f'{method}-{threshold}.pdf';pdf.save(path,deterministic_id=True)
        metrics={}
        for engine in ['pdfium','poppler']:
            values=[]
            for pi in range(13):
                actual=1-render(path,pi,300,engine).astype(float)/255;source=sources[engine,pi]
                for row in rows:
                    if row['page']!=pi or row['source']is None:continue
                    x,y,xx,yy=map(int,row['source']['bbox']);x-=4;y-=4;xx+=4;yy+=4;values.append(measure(source[y:yy,x:xx],actual[y:yy,x:xx]))
            metrics[engine]=summary(values)
        record=dict(point,native_source=metrics,program_accounting=dict(added=point['added'],retired=point['retired_visible_candidates'],net=point['net_visible_candidates'],verified_scope='All old e programs have only visible same-label users; selected point independently checked against compiled complete PDF programs.'),pristine_error=None,pristine_status='P3 has no pristine reference; P1 causal pristine metrics are reported separately.',material_defects=None,material_status='Independent blinded review pending; do not infer zero defects.',measurement_pdf=str(path),measurement_pdf_sha256=sha(path))
        result.append(record);print(method,threshold,{e:m['error']['mean']for e,m in metrics.items()},flush=True)
    Path('qualification/font04/reuse-fidelity-frontier.json').write_text(json.dumps(dict(schema='font04-native-frontier-v1',selected=plan['selected'],points=result,scope='B1 e only; measurement PDFs contain only glyph layers, not complete financial deliverables.'),indent=2))
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig,axes=plt.subplots(1,2,figsize=(10,4))
        for ax,engine in zip(axes,['pdfium','poppler']):
            for method in ['star','complete','cover']:
                values=[r for r in result if r['grouping']==method];ax.plot([r['program_accounting']['retired']-r['program_accounting']['added']for r in values],[r['native_source'][engine]['error']['mean']for r in values],'.-',label=method)
                for r in values:ax.annotate(str(r['error_scale']),(r['program_accounting']['retired']-r['program_accounting']['added'],r['native_source'][engine]['error']['mean']),fontsize=6)
            ax.set_title(engine);ax.set_xlabel('Net programs removed');ax.set_ylabel('Native source coverage error');ax.legend()
        fig.suptitle('B1 discovery frontier — material-defect review pending');fig.tight_layout();fig.savefig(directory/'frontier.png',dpi=180);fig.savefig(directory/'frontier.svg');plt.close(fig)
    except ImportError:print('matplotlib unavailable; complete numeric frontier retained',flush=True)


if __name__=='__main__':main()
