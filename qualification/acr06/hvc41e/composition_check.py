"""Check actual completed-font composition against each reviewed individual trial."""
import pathlib,json,hashlib,collections,sys
import numpy as np,pikepdf,pypdfium2 as pdfium
from PIL import Image
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41e';L=R/'local/hvc41e/final';sys.path.insert(0,'/tmp/scanweave-hvc41/research/hvc41d');from validator import metrics
expected='391d326c7b7d7128406f9ddd4b3c26f79499394acfa2e1b976c71fa044f8b0ef';f=E/'review-decisions.json';assert hashlib.sha256(f.read_bytes()).hexdigest()==expected;allrows=json.loads(f.read_text());rows=[r for r in allrows if r['decision']=='accept'];assert len(rows)==38
candidate=L/'historical-composed.pdf';source=np.asarray(Image.open(R/'local/ink33r/renders/historical/01-source.png').convert('RGB'));h,w=source.shape[:2];wt=np.array([.2126,.7152,.0722]);lum=source.astype(float)@wt;refglobal=np.asarray(Image.open(R/'local/hvc41/masks/corpus-historical-01-reference-ink.png').convert('L'))>0
# Keep only the actual final overlay while retaining its font, glyph order and placement.
pdf=pikepdf.open(candidate);page=pdf.pages[0];page.Contents=page.Contents[-1];isolated=L/'composed-font-only.pdf';pdf.save(isolated);pdf.close();doc=pdfium.PdfDocument(str(isolated));pg=doc[0];glyphrgb=np.asarray(pg.render(scale=300/72,rev_byteorder=True,fill_color=(255,255,255,255)).to_pil().convert('RGB')).copy();pg.close();doc.close()
phase=[];allpatch=np.zeros((h,w),bool);allvector=np.zeros((h,w),bool);allowner=np.zeros((h,w),bool)
# Render one actual final-font pattern command at a time in a diagnostic copy.
# This separates neighbouring glyphs that share a measurement crop, without
# changing the completed candidate or rebuilding its font.
for ix,r in enumerate(rows):
 one=pikepdf.open(candidate);op=one.pages[0];pat=op.Resources.Pattern.Research41E;commands=pat.read_bytes().splitlines()
 if len(commands)!=len(rows):raise RuntimeError('unexpected final pattern glyph count')
 pat.write(commands[ix]);op.Contents=op.Contents[-1];onefile=L/f'.font-one-{ix:02}.pdf';one.save(onefile);one.close();d=pdfium.PdfDocument(str(onefile));page=d[0];individual=np.asarray(page.render(scale=300/72,rev_byteorder=True,fill_color=(255,255,255,255)).to_pil().convert('RGB')).copy();page.close();d.close();onefile.unlink()
 a,b,c,d=r['reference_box'];m={}
 for k in ('owner','patch','vector'):
  m[k]=np.asarray(Image.open(r['masks'][k]['path']).convert('L'))>0
 actual_luma=individual[b:d,a:c].astype(float)@wt;fill=np.array(r['fill_rgb'])@wt;v=actual_luma<(255+fill)/2
 m['actual_vector']=v;phase.append((r,m));allpatch[b:d,a:c]|=m['patch'];allowner[b:d,a:c]|=m['owner'];allvector[b:d,a:c]|=v
out=[];interactions=[]
for r,m in phase:
 a,b,c,d=r['reference_box'];p=m['patch'];v=m['actual_vector'];own=m['owner'];other_owned=np.zeros((d-b,c-a),bool);other_patch=np.zeros_like(other_owned);other_vector=np.zeros_like(other_owned)
 for s,n in phase:
  if s['proposal']==r['proposal']:continue
  x0,y0,x1,y1=s['reference_box'];u0=max(a,x0);v0=max(b,y0);u1=min(c,x1);v1=min(d,y1)
  if u1<=u0 or v1<=v0:continue
  dst=np.s_[v0-b:v1-b,u0-a:u1-a];src=np.s_[v0-y0:v1-y0,u0-x0:u1-x0];other_owned[dst]|=n['owner'][src];other_patch[dst]|=n['patch'][src];other_vector[dst]|=n['actual_vector'][src]
 other_ref=other_owned&refglobal[b:d,a:c];foreign_patch=int((p&other_ref).sum());foreign_vector=int((v&other_ref).sum());patch_overlap=int((p&other_patch).sum());vector_overlap=int((v&other_vector).sum());patch_other_vector=int((p&other_vector).sum());vector_other_patch=int((v&other_patch).sum());local_ref=lum[b:d,a:c]<(r['admission']['paper_luma']+r['source_ink_luma'])/2 if 'admission' in r else None
 # Source luminance parameters are in the frozen p1 preflight, not the review row.
 pre=json.loads((R/'hvc41d/p1-preflight-ledger.json').read_text())[r['proposal']];local_ref=lum[b:d,a:c]<(pre['admission']['paper_luma']+pre['source_ink_luma'])/2
 score=metrics(local_ref,v,pre['fill_error']);u=int((local_ref|v).sum());score['iou']=float((local_ref&v).sum()/u) if u else None;ghost=refglobal[b:d,a:c]&~allvector[b:d,a:c]&~allpatch[b:d,a:c]&nd.binary_dilation(v,structure=np.ones((3,3),bool));under=refglobal[b:d,a:c]&p&~allvector[b:d,a:c];shape_diff=int((v!=m['vector']).sum());ghost_count=int(ghost.sum());under_count=int(under.sum());interaction=bool(foreign_patch or foreign_vector or patch_overlap or vector_overlap or patch_other_vector or vector_other_patch or shape_diff or ghost_count!=r['ghost_ink_pixels'] or under_count!=r['under_replaced_ink_pixels'])
 item={'proposal':r['proposal'],'symbol':r['symbol_id'],'patch_outside_owned':int((p&~own).sum()),'patch_intersect_other_accepted_reference_ink':foreign_patch,'vector_intersect_other_accepted_reference_ink':foreign_vector,'patch_overlap_other_patch':patch_overlap,'vector_overlap_other_vector':vector_overlap,'patch_overlap_other_vector':patch_other_vector,'vector_overlap_other_patch':vector_other_patch,'composed_vs_single_glyph_vector_pixel_diff':shape_diff,'ghost_ink_pixels':ghost_count,'single_ghost_ink_pixels':r['ghost_ink_pixels'],'under_replaced_ink_pixels':under_count,'single_under_replaced_ink_pixels':r['under_replaced_ink_pixels'],'halo_mean_abs_delta_luma':r['halo_mean_abs_delta_luma'],'halo_max_abs_delta_luma':r['halo_max_abs_delta_luma'],'halo_note':'Unchanged: source ring and patch do not intersect another accepted footprint; see pairwise checks.','composed_font_validator':score,'interaction_or_metric_change':interaction}
 out.append(item)
 if interaction:interactions.append(r['proposal'])
coverage=int((refglobal&allvector).sum());data={'ledger_sha256':expected,'accepted_count':len(rows),'interactions_or_changed_metrics':interactions,'glyphs':out,'reference_ink_pixels':int(refglobal.sum()),'candidate_font_reference_overlap_pixels':coverage,'candidate_font_reference_overlap_fraction':coverage/int(refglobal.sum()),'coverage_status':'provisional until renderer and visual verification'};(E/'composition-check.json').write_text(json.dumps(data,indent=2)+'\n');print('interactions or changed metrics',interactions,'provisional reference overlap',coverage,flush=True)
