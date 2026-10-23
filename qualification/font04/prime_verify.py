"""Complete PDF accounting and functional checks for B1-prime; no global B1 writes."""
from pathlib import Path
import collections,json,re,subprocess,sys
import pypdfium2 as pdfium
from qualification.font04.metrics import inspect,sha
from qualification.font04.b1_audit import check_pdf
ROOT=Path('qualification/font04/local')

def text(path):
    doc=pdfium.PdfDocument(path);pages=[];searches=[]
    for p in doc:
        t=p.get_textpage();value=t.get_text_range();pages.append(value);found={}
        for word in sorted(set(re.findall('[A-Za-z]{3,}',value))):
            s=t.search(word);n=0
            while s.get_next() is not None:n+=1
            s.close();found[word]=n
        searches.append(found);t.close();p.close()
    doc.close()
    return pages,searches

def stats(inv):
    fid={r['font_hash'] for r in inv['users']};fonts=[f for h,f in inv['fonts'].items() if h in fid]
    draws=inv['draws'];es=[r for r in draws if r['character']=='e'];designs={(r['font_hash'],r['gid']) for r in draws};edesigns={(r['font_hash'],r['gid']) for r in es}
    return dict(bytes=inv['bytes'],sha256=inv['sha256'],draws=len(draws),designs=len(designs),e_draws=len(es),e_designs=len(edesigns),e_draws_per_design=len(es)/len(edesigns),required_slots=sum(f['slots'] for f in fonts),encoded_font_bytes=sum(f['encoded_bytes'] for f in fonts),decoded_font_bytes=sum(f['decoded_bytes'] for f in fonts),outline_points=sum(f['outline_points'] for f in fonts))

def main(paths):
    default=ROOT/'financial-default.pdf';base=inspect(default);a=collections.Counter(h for f in base['fonts'].values() for h in f['hashes'][1:]);t0,s0=text(default);p0=subprocess.check_output(['pdftotext','-layout',str(default),'-']);results={}
    for path in paths:
        inv=inspect(path);b=collections.Counter(h for f in inv['fonts'].values() for h in f['hashes'][1:]);added=b-a;retired=a-b;t,s=text(path)
        result=dict(pdf=str(path),stats=stats(inv),added=sum(added.values()),retired=sum(retired.values()),net_retired=sum(retired.values())-sum(added.values()),programs=dict(added=dict(added),retired=dict(retired)),text_equal=t==t0,search_equal=s==s0,poppler_text_equal=subprocess.check_output(['pdftotext','-layout',str(path),'-'])==p0,validation=check_pdf(path))
        assert result['text_equal'] and result['search_equal'] and result['poppler_text_equal']
        assert all(v['returncode']==0 for v in result['validation'].values())
        results[path.stem]=result;print(path.name,result['net_retired'],result['stats']['bytes'],flush=True)
    out=dict(default=stats(base),default_matches_main=sha(default)==sha(ROOT/'financial-main.pdf'),arms=results)
    Path('qualification/font04/prime-verification.json').write_text(json.dumps(out,indent=2)+'\n')

if __name__=='__main__':main([Path(p) for p in sys.argv[1:]])
