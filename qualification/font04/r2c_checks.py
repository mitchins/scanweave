"""R2c functional and economy checks on retained PDFs; never convert or generate."""
import json, re
from pathlib import Path
from qualification.font04.r2a_audit import extraction, fonts, command, ROOT, sha
from qualification.font04.functional_guard import native
from qualification.font04.s1d_eval import economy
P=ROOT/'qualification/font04/local/P2prime'
OUT=ROOT/'qualification/font04'
ARMS=('off','cover-2.0','cover-2.0-ceiling')
def main():
    checks=[]; econ=[]
    for i in range(9):
        paths={a:P/f'sheet-{i}-{a}.pdf' for a in ARMS}; ext={a:extraction(p) for a,p in paths.items()}; search={a:native(p,0)[1] for a,p in paths.items()}; entry={'sheet':i,'dpi':(200,300,600)[i//3],'arms':{}}
        ee={'sheet':i,'dpi':(200,300,600)[i//3],'arms':{}}
        for a,p in paths.items():
            d=P/'functional'/f'{i}-{a}';d.mkdir(parents=True,exist_ok=True)
            q=command([ROOT/'tools/dist/bin/qpdf','--check',p]).decode(); ots=[]
            for digest,(data,enc) in fonts(p).items():
                f=d/(digest+'.ttf');f.write_bytes(data); val=command([ROOT/'tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize',f,str(f)+'.sanitized']).decode();ots.append({'sha256':digest,'result':val})
            eq={k:ext[a][k]==ext['off'][k] for k in ext[a]}; entry['arms'][a]={'sha256':sha(p),'extraction_hashes':ext[a],'extraction_equal':eq,'native_search_equal':search[a]==search['off'],'qpdf':q,'ots':ots,'pass':all(eq.values()) and search[a]==search['off'] and bool(ots)}
            c=json.loads(Path(str(p)+'.json').read_text())['conversion']; e=economy(c) if c.get('glyph_sharing') else {};e['pdf_bytes']=p.stat().st_size;e['encoded_font_bytes_actual']=sum(x[1] for x in fonts(p).values())
            t=Path(str(p)+'.time').read_text();e['wall_time']=re.search(r'Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): (.+)',t).group(1);e['max_rss_kib']=int(re.search(r'Maximum resident set size \(kbytes\): (\d+)',t).group(1));ee['arms'][a]=e
        entry['repeat_byte_identical']=sha(paths['cover-2.0-ceiling'])==sha(P/f'sheet-{i}-cover-2.0-ceiling-repeat.pdf'); checks.append(entry);econ.append(ee);print('checked',i,flush=True)
    result={'method':'R2a extraction, functional_guard.native PDFium word search, qpdf and OTS; all retained arms','sheets':checks,'pass':all(e['repeat_byte_identical'] and all(v['pass'] for v in e['arms'].values()) for e in checks)}
    (OUT/'r2c-functional.json').write_text(json.dumps(result,indent=2)+'\n');(OUT/'r2c-economy.json').write_text(json.dumps({'method':'s1d_eval economy, actual font streams, PDF sizes and GNU time sidecars','sheets':econ},indent=2)+'\n')
if __name__=='__main__':main()
