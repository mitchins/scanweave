"""Record the failed final PDF extraction difference without writing text into the PDF."""
import difflib,hashlib,json,os,pathlib,subprocess,sys,tempfile
import pypdfium2 as pdfium
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f/final';base=R/'local/ink33r/historical.pdf';candidate=L/'historical-final.pdf';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_SEMANTIC_DIFF')!='1':sys.exit('research switch required')
if sha(base.read_bytes())!='68c874e44bd0bf8d48ffed413d674c6c307c6d3d4742e008ca12b2b6ab4a713b' or sha(candidate.read_bytes())!=json.loads((E/'final-assembly.json').read_text())['sha256']:sys.exit('input mismatch')
def pdftext(path):
 d=pdfium.PdfDocument(str(path));out=[]
 for p in d:
  t=p.get_textpage();out.append(t.get_text_range());t.close();p.close()
 d.close();return out
def pop(path,i):return subprocess.check_output(['pdftotext','-f',str(i),'-l',str(i),'-enc','UTF-8',str(path),'-']).decode('utf8')
def diff(a,b):return [{'operation':tag,'baseline_offset':[i,j],'candidate_offset':[k,l],'baseline_codepoints':[f'U+{ord(c):04X}' for c in a[i:j]],'candidate_codepoints':[f'U+{ord(c):04X}' for c in b[k:l]]} for tag,i,j,k,l in difflib.SequenceMatcher(a=a,b=b,autojunk=False).get_opcodes() if tag!='equal']
with tempfile.TemporaryDirectory(prefix='hvc41f-diff-noocr-') as td:
 marker=L/'ocr-invoked';stub=pathlib.Path(td)/'tesseract';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(R/'local/ink33r/historical.pdf.json');a=pdftext(base);b=pdftext(candidate);out=[]
 for i in range(5):
  p=pop(base,i+1);q=pop(candidate,i+1);out.append({'page':i+1,'pdfium_baseline_length':len(a[i]),'pdfium_candidate_length':len(b[i]),'pdfium_differences':diff(a[i],b[i]),'poppler_baseline_length':len(p),'poppler_candidate_length':len(q),'poppler_differences':diff(p,q)})
 if marker.exists():sys.exit('OCR invoked')
(E/'final-semantic-differences.json').write_text(json.dumps(out,indent=2)+'\n');print('differences',[(z['page'],len(z['pdfium_differences']),len(z['poppler_differences'])) for z in out])
