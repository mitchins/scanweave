#!/usr/bin/env python3
"""Validate every actual final-font glyph against frozen source/ownership evidence."""
import hashlib,json,os,pathlib,sys,tempfile
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image
from scipy import ndimage as nd
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parent.parent/'hvc41d'))
from validator import metrics
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41f';L=R/'local/hvc41f/final';sha=lambda b:hashlib.sha256(b).hexdigest()
if os.getenv('SCANWEAVE_HVC41F_FINAL_GLYPHS')!='1':sys.exit('research switch required')
f=R/'hvc41e/review-decisions.json';assert sha(f.read_bytes())=='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef';rows=[r for r in json.loads(f.read_text()) if r['decision']=='accept'];candidate=L/'historical-final.pdf';ass=json.loads((E/'final-assembly.json').read_text());assert len(rows)==38 and sha(candidate.read_bytes())==ass['sha256'] and ass['rendering']=='A4';ref=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0;src=np.asarray(Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB'));lum=src@np.array([.2126,.7152,.0722]);pre=json.loads((R/'hvc41d/p1-preflight-ledger.json').read_text());previous={x['proposal']:x for x in json.loads((R/'hvc41e/composition-check.json').read_text())['glyphs']};allpatch=np.zeros(ref.shape,bool);allvector=np.zeros(ref.shape,bool);data=[]
with tempfile.TemporaryDirectory(prefix='hvc41f-glyph-noocr-') as td:
 stub=pathlib.Path(td)/'tesseract';marker=L/'ocr-invoked';stub.write_text('#!/bin/sh\ntouch '+str(marker)+'\nexit 97\n');stub.chmod(0o755);os.environ['PATH']=td+':'+os.environ['PATH'];os.environ['SCANWEAVE_HVC41C_LOCK_OCR']='1';os.environ['SCANWEAVE_HVC41C_OCR_SIDECAR']=str(R/'local/ink33r/historical.pdf.json')
 for i,r in enumerate(rows):
  pdf=pikepdf.open(candidate);p=pdf.pages[0];form=p.Resources.XObject['/ResearchPaths'];lines=form.read_bytes().splitlines();assert lines[0]==b'/Artifact BMC' and lines[-1]==b'EMC' and len(lines)==40;form.write(b'/Artifact BMC\n'+lines[i+1]+b'\nEMC');p.Contents=p.Contents[-1];temp=pathlib.Path(td)/'glyph.pdf';pdf.save(temp);pdf.close();doc=pdfium.PdfDocument(str(temp));page=doc[0];img=np.asarray(page.render(scale=300/72,rev_byteorder=True,fill_color=(255,255,255,255)).to_pil().convert('RGB'));page.close();doc.close();a,b,c,d=r['reference_box'];m={}
  for k in ('owner','patch','vector'):
   spec=r['masks'][k];path=pathlib.Path(spec['path']);assert sha(path.read_bytes())==spec['sha256'];m[k]=np.asarray(Image.open(path).convert('L'))>0
  vl=img[b:d,a:c]@np.array([.2126,.7152,.0722]);fill=np.array(r['fill_rgb'])@np.array([.2126,.7152,.0722]);m['actual']=vl<(255+fill)/2;allpatch[b:d,a:c]|=m['patch'];allvector[b:d,a:c]|=m['actual'];data.append((r,m));print('glyph',r['proposal'],flush=True)
 if marker.exists():sys.exit('OCR invoked')
out=[];bad=[]
for r,m in data:
 a,b,c,d=r['reference_box'];v=m['actual'];p=m['patch'];otherown=np.zeros(v.shape,bool);otherv=np.zeros(v.shape,bool);otherp=np.zeros(v.shape,bool)
 for s,n in data:
  if s['proposal']==r['proposal']:continue
  x0,y0,x1,y1=s['reference_box'];u0=max(a,x0);v0=max(b,y0);u1=min(c,x1);v1=min(d,y1)
  if u1<=u0 or v1<=v0:continue
  dst=np.s_[v0-b:v1-b,u0-a:u1-a];source=np.s_[v0-y0:v1-y0,u0-x0:u1-x0];otherown[dst]|=n['owner'][source];otherv[dst]|=n['actual'][source];otherp[dst]|=n['patch'][source]
 localref=lum[b:d,a:c]<(pre[r['proposal']]['admission']['paper_luma']+pre[r['proposal']]['source_ink_luma'])/2;score=metrics(localref,v,pre[r['proposal']]['fill_error']);score['iou']=float((localref&v).sum()/(localref|v).sum());ghost=ref[b:d,a:c]&~allvector[b:d,a:c]&~allpatch[b:d,a:c]&nd.binary_dilation(v,structure=np.ones((3,3),bool));under=ref[b:d,a:c]&p&~allvector[b:d,a:c];foreignp=int((p&otherown&ref[b:d,a:c]).sum());foreignv=int((v&otherown&ref[b:d,a:c]).sum());over=int((p&otherp).sum()+(v&otherv).sum()+(p&otherv).sum()+(v&otherp).sum());item={'proposal':r['proposal'],'symbol':r['symbol_id'],'identity':r['claude_identity'],'validator':score,'patch_outside_owned':int((p&~m['owner']).sum()),'patch_foreign_ink':foreignp,'vector_foreign_ink':foreignv,'inter_glyph_overlap':over,'ghost_pixels':int(ghost.sum()),'under_replaced_pixels':int(under.sum()),'vector_mask_diff_from_hvc41e':int((v!=m['vector']).sum()),'prior_hvc41e':previous[r['proposal']]};out.append(item)
 if not score['pass'] or item['patch_outside_owned'] or foreignp or foreignv or over:bad.append(r['proposal'])
result={'glyphs':out,'failing':bad,'count':len(out),'covered_reference_ink_pixels':int((ref&allvector).sum()),'reference_ink_pixels':int(ref.sum()),'ocr_stub_not_invoked':True};(E/'final-glyphs.json').write_text(json.dumps(result,indent=2)+'\n');print('failing',bad,'coverage',result['covered_reference_ink_pixels'],flush=True)
