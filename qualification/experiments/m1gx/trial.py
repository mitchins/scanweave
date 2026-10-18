#!/usr/bin/env python3
"""Build the M1-GX 300-DPI oracle ladder from frozen M1-G data.

The converter sees only dpi300/input. Oracle outlines/placement are used only
by O1/O2 and by the independent measurement code. O4 is the frozen M1-G PDF.
"""
from __future__ import annotations
import hashlib, json, math, shutil, struct, zlib
from pathlib import Path
from io import BytesIO

import numpy as np
from PIL import Image
from skimage.measure import find_contours, approximate_polygon
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen

ROOT=Path(__file__).resolve().parents[3]
BASE=ROOT/"qualification/experiments/m1g/fixture/dpi300"
OUT=ROOT/"qualification/experiments/m1gx/300"
DPI=300
PT=72.0/DPI
KANA_FONT="/usr/share/fonts/opentype/ipafont-gothic/ipagp.ttf"

def sha(b): return hashlib.sha256(b).hexdigest()

def pdf_string(s):
    return "("+s.replace("\\","\\\\").replace("(","\\(").replace(")","\\)")+")"

def actual_text(s):
    return "<FEFF"+s.encode("utf-16-be").hex().upper()+">"

def page_truth(page):
    d=BASE/"oracle"/f"page{page:02}"
    return json.loads(Path(str(d)+".truth.json").read_text())

def unpadded_box(rec):
    # The generator records a five-pixel safety border (four for kana).
    pad=4 if ord(rec["text"][0]) > 127 else 5
    x0,y0,x1,y1=rec["bbox"]
    return [x0+pad,y0+pad,x1-pad,y1-pad]

def oracle_ink_box(oracle, rec):
    bx0,by0,bx1,by1=map(int,unpadded_box(rec))
    yy,xx=np.where(oracle[by0:by1,bx0:bx1]<170)
    if not len(xx): return [bx0,by0,bx1,by1]
    return [bx0+int(xx.min()),by0+int(yy.min()),
            bx0+int(xx.max())+1,by0+int(yy.max())+1]

def oracle_style_key(page, ch):
    if ord(ch[0])>127: return KANA_FONT
    return page_truth(page)["font"]

class PDFOutlinePen(BasePen):
    def __init__(self,glyphset, bbox, page_h):
        super().__init__(glyphset)
        self.bbox=bbox; self.page_h=page_h; self.cmd=[]; self.cur=None
        self.x0,self.y0,self.x1,self.y1=bbox
    def xy(self,p):
        x,y=p; x0,y0,x1,y1=self.bbox
        return ((x0+(x-self.gxmin)*((x1-x0)/self.gw))*PT,
                (self.page_h-(y1-(y-self.gymin)*((y1-y0)/self.gh)))*PT)
    def _moveTo(self,p):
        x,y=self.xy(p); self.cmd.append(f"{x:.4f} {y:.4f} m"); self.cur=p
    def _lineTo(self,p):
        x,y=self.xy(p); self.cmd.append(f"{x:.4f} {y:.4f} l"); self.cur=p
    def _curveToOne(self,p1,p2,p3):
        vals=[self.xy(p) for p in (p1,p2,p3)]
        self.cmd.append(" ".join(f"{v:.4f}" for p in vals for v in p)+" c"); self.cur=p3
    def _qCurveToOne(self,p1,p2):
        p0=self.cur
        c1=(p0[0]+(p1[0]-p0[0])*2/3,p0[1]+(p1[1]-p0[1])*2/3)
        c2=(p2[0]+(p1[0]-p2[0])*2/3,p2[1]+(p1[1]-p2[1])*2/3)
        self._curveToOne(c1,c2,p2)
    def _closePath(self): self.cmd.append("h")
    def _endPath(self): self.cmd.append("n")
    def _addComponent(self,glyphName,transformation):
        super()._addComponent(glyphName,transformation)
    def prepare(self,glyph):
        self.gxmin,self.gymin,self.gxmax,self.gymax=glyph.xMin,glyph.yMin,glyph.xMax,glyph.yMax
        self.gw=max(1,self.gxmax-self.gxmin); self.gh=max(1,self.gymax-self.gymin)

class FontLocalPen(BasePen):
    """Emit one embedded TrueType glyph in local y-up font-unit coordinates."""
    def __init__(self,glyphset,glyph):
        super().__init__(glyphset); self.cmd=[]; self.cur=None
        self.xmin,self.ymin,self.xmax,self.ymax=glyph.xMin,glyph.yMin,glyph.xMax,glyph.yMax
        self.w=max(1,self.xmax-self.xmin); self.h=max(1,self.ymax-self.ymin)
    def xy(self,p): return p[0]-self.xmin,p[1]-self.ymin
    def _moveTo(self,p):
        x,y=self.xy(p); self.cmd.append(f"{x:.4f} {y:.4f} m"); self.cur=p
    def _lineTo(self,p):
        x,y=self.xy(p); self.cmd.append(f"{x:.4f} {y:.4f} l"); self.cur=p
    def _curveToOne(self,p1,p2,p3):
        vals=[self.xy(p) for p in (p1,p2,p3)]
        self.cmd.append(" ".join(f"{v:.4f}" for p in vals for v in p)+" c"); self.cur=p3
    def _qCurveToOne(self,p1,p2):
        p0=self.cur
        c1=(p0[0]+(p1[0]-p0[0])*2/3,p0[1]+(p1[1]-p0[1])*2/3)
        c2=(p2[0]+(p1[0]-p2[0])*2/3,p2[1]+(p1[1]-p2[1])*2/3)
        self._curveToOne(c1,c2,p2)
    def _closePath(self): self.cmd.append("h")
    def _endPath(self): self.cmd.append("n")
    def _addComponent(self,glyphName,transformation): super()._addComponent(glyphName,transformation)

def extract_embedded_font(pdf_path):
    import sys,subprocess,re
    sys.path.insert(0,str(ROOT/"qualification")); from tools_env import qpdf_bin,qpdf_env
    qdf=OUT/".m1g-reconstructed.qdf.pdf"
    subprocess.run([qpdf_bin(),"--qdf","--object-streams=disable",str(pdf_path),str(qdf)],env=qpdf_env(),check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    data=qdf.read_bytes(); m=re.search(rb'/FontFile2\s+(\d+)\s+0\s+R',data)
    if not m: raise RuntimeError("frozen M1-G PDF has no embedded TrueType font")
    n=m.group(1); obj=re.search(rb'\n'+n+rb' 0 obj\s*<<(.*?)>>\s*stream\n(.*?)\nendstream',data,re.S)
    if not obj: raise RuntimeError("cannot extract M1-G FontFile2 stream")
    font=TTFont(BytesIO(obj.group(2))); qdf_data=data; qdf.unlink(); return font,qdf_data

def extracted_occurrence_mappings(qdf_data,report,obs,occs):
    import re
    fontref=re.search(rb'/CIDToGIDMap\s+(\d+)\s+0\s+R',qdf_data)
    if not fontref: raise RuntimeError("M1-G CIDToGIDMap missing")
    n=fontref.group(1); obj=re.search(rb'\n'+n+rb' 0 obj\s*<<(.*?)>>\s*stream\n(.*?)\nendstream',qdf_data,re.S)
    cmap=obj.group(2)
    def unescape_pdf_string(raw): return raw[1:-1].replace(b'\\(',b'(').replace(b'\\)',b')').replace(b'\\\\',b'\\').decode('utf-8','replace')
    matrices={}; occurrence_gids={}; proto_gids={}
    page_sections=re.findall(rb'%% Page \d+\n(.*?)endobj',qdf_data,re.S)
    if len(page_sections)!=len(report["page_reports"]): raise RuntimeError("qdf page count does not match report")
    for pi,(pr,section) in enumerate(zip(report["page_reports"],page_sections)):
        cref=re.search(rb'/Contents\s+(\d+)',section); cobj=re.search(rb'\n'+cref.group(1)+rb' 0 obj\s*<<(.*?)>>\s*stream\n(.*?)\nendstream',qdf_data,re.S)
        blocks=re.findall(rb'/Span\s*<<\s*/ActualText\s+(.*?)\s*>>\s*BDC(.*?)EMC',cobj.group(2),re.S)
        decoded=[]
        for actual,body in blocks:
            label=unescape_pdf_string(actual) if actual.startswith(b'(') else bytes.fromhex(actual[1:-1].decode()).decode('utf-16-be','replace') if actual.startswith(b'<') else ''
            tm=re.search(rb'([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+Tm',body)
            cid=re.search(rb'<([0-9A-Fa-f]{4})>\s*Tj',body)
            if tm and cid:
                matrix=[float(tm.group(i)) for i in range(1,7)]
                cv=int(cid.group(1),16); gid=struct.unpack_from('>H',cmap,cv*2)[0] if cv*2+2<=len(cmap) else 0
                decoded.append((label,matrix,cv,gid))
        used=set()
        for sid, (spi,oc) in occs.items():
            if spi!=pi or not (oc.get('repaired') or oc.get('reused')): continue
            if sid not in obs: continue
            expected_x=obs[sid][1]["bbox_px"][0]
            choices=[(abs((entry[1][4]/PT)-expected_x),j,entry) for j,entry in enumerate(decoded) if j not in used and entry[0]==oc["text"]]
            if not choices: continue
            distance,j,entry=min(choices)
            if distance>24: continue
            used.add(j); label,matrix,cid,gid=entry
            matrices[sid]=matrix
            occurrence_gids[sid]=gid
            proto_gids.setdefault(oc["prototype_id"],set()).add(gid)
    return matrices,occurrence_gids,proto_gids

def oracle_paths(page, truth, width, height):
    fonts={}
    oracle=np.asarray(Image.open(BASE/"oracle"/f"page{page:02}.png").convert("L"))
    records=[]
    for rec in truth["records"]:
        ch=rec["text"]
        if not ch or ch.isspace(): continue
        fontpath=KANA_FONT if ord(ch[0])>127 else truth["font"]
        if fontpath not in fonts:
            f=TTFont(fontpath); fonts[fontpath]=(f,f.getGlyphSet(),f.getBestCmap(),f["glyf"])
        font,gs,cmap,glyf=fonts[fontpath]
        if ord(ch[0]) not in cmap: continue
        gn=cmap[ord(ch)]; g=glyf[gn]
        if not hasattr(g,"xMin"): continue
        # The recorded box includes font side bearings. Oracle placement uses
        # the pristine source ink bounds, while the vector shape itself comes
        # from the licensed source font outline.
        bx0,by0,bx1,by1=map(int,unpadded_box(rec))
        yy,xx=np.where(oracle[by0:by1,bx0:bx1]<170)
        if not len(xx): continue
        box=[bx0+int(xx.min()),by0+int(yy.min()),bx0+int(xx.max())+1,by0+int(yy.max())+1]
        pen=PDFOutlinePen(gs,box,height); pen.prepare(g); gs[gn].draw(pen)
        records.append((rec,pen.cmd))
    for font,_,_,_ in fonts.values(): font.close()
    return records

def trace_donor(rgb, bbox, threshold):
    x0,y0,x1,y1=[int(round(x)) for x in bbox]
    crop=np.asarray(rgb)[max(0,y0):max(0,y1),max(0,x0):max(0,x1),:3]
    if crop.size==0: return []
    gray=np.mean(crop,axis=2)
    mask=gray < threshold
    contours=find_contours(np.pad(mask.astype(float),1),.5)
    paths=[]
    for contour in contours:
        q=approximate_polygon(contour, tolerance=.28)
        if len(q)<4: continue
        pts=[(x0+float(col)-1,y0+float(row)-1) for row,col in q]
        paths.append(pts)
    return paths

def fit_paths(paths, donor_box, target_box, page_h):
    dx0,dy0,dx1,dy1=donor_box; tx0,ty0,tx1,ty1=target_box
    sx=(tx1-tx0)/max(1e-6,dx1-dx0); sy=(ty1-ty0)/max(1e-6,dy1-dy0)
    out=[]
    for poly in paths:
        pts=[(tx0+(x-dx0)*sx,ty0+(y-dy0)*sy) for x,y in poly]
        if len(pts)<4: continue
        x,y=pts[0]; out.append(f"{x*PT:.4f} {(page_h-y)*PT:.4f} m")
        for x,y in pts[1:]: out.append(f"{x*PT:.4f} {(page_h-y)*PT:.4f} l")
        out.append("h")
    return out

def form_definition(glyphset,glyph_name,glyph):
    pen=FontLocalPen(glyphset,glyph); glyphset[glyph_name].draw(pen)
    return pen.w,pen.h,"\n".join(pen.cmd)+"\nf*\n"

def pdf_write(path, pages, dims, producer):
    # pages: each {rgb: HxWx3, vectors:[PDF path ops], semantic:[str]}
    objs=[];
    def add(data): objs.append(data); return len(objs)
    catalog=add(None); pagetree=add(None); helv=add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>")
    forms={}
    for item in pages:
        for key,dw,dh,ops,_matrix in item.get("forms",[]):
            if key in forms: continue
            raw=ops.encode(); comp=zlib.compress(raw,9)
            ref=add((f"<< /Type /XObject /Subtype /Form /FormType 1 /BBox [0 0 {dw:.4f} {dh:.4f}] /Resources << >> /Filter /FlateDecode /Length {len(comp)} >>\nstream\n").encode()+comp+b"\nendstream")
            forms[key]=(ref,dw,dh)
    page_ids=[]
    for item,(w,h) in zip(pages,dims):
        rgb=np.asarray(item["rgb"],dtype=np.uint8)
        gray=(not item.get("force_rgb",False)) and np.all(rgb[:,:,0]==rgb[:,:,1]) and np.all(rgb[:,:,1]==rgb[:,:,2])
        raw=(rgb[:,:,0].tobytes() if gray else rgb.tobytes()); comp=zlib.compress(raw,6)
        cs=b"/DeviceGray" if gray else b"/DeviceRGB"
        image=add(b"<< /Type /XObject /Subtype /Image /Width %d /Height %d /ColorSpace %s /BitsPerComponent 8 /Filter /FlateDecode /Length %d >>\nstream\n"%(w,h,cs,len(comp))+comp+b"\nendstream")
        content=[f"q {w*PT:.4f} 0 0 {h*PT:.4f} 0 0 cm /Im0 Do Q\n"]
        xobjects=[f"/Im0 {image} 0 R"]; xobject_names={"Im0"}
        for pathops in item.get("vectors",[]):
            if pathops: content.append("q 0 0 0 rg\n"+"\n".join(pathops)+"\nf* Q\n")
        for key,dw,dh,ops,matrix in item.get("forms",[]):
            ref,_,_=forms[key]; name="G"+hashlib.sha1(key.encode()).hexdigest()[:10]
            if name not in xobject_names:
                xobjects.append(f"/{name} {ref} 0 R"); xobject_names.add(name)
            a,d,e,f=matrix
            content.append(f"q {a:.8f} 0 0 {d:.8f} {e:.4f} {f:.4f} cm /{name} Do Q\n")
        for text,box in item.get("semantic",[]):
            # ActualText supplies Unicode while the invisible Type1 show keeps
            # ordinary text extraction behavior in both engines.
            x0,y0,x1,y1=box
            content.append(f"/Span << /ActualText {actual_text(text)} >> BDC BT /F0 8 Tf 3 Tr 1 0 0 1 {x0*PT:.4f} {(h-y1)*PT:.4f} Tm {pdf_string('?')} Tj ET EMC\n")
        cb="".join(content).encode(); cs=add(b"<< /Length %d >>\nstream\n"%len(cb)+cb+b"endstream")
        page=add(None); page_ids.append(page)
        objs[page-1]=(f"<< /Type /Page /Parent {pagetree} 0 R /MediaBox [0 0 {w*PT:.4f} {h*PT:.4f}] /Resources << /XObject << {' '.join(xobjects)} >> /Font << /F0 {helv} 0 R >> >> /Contents {cs} 0 R >>").encode()
    objs[catalog-1]=f"<< /Type /Catalog /Pages {pagetree} 0 R >>".encode()
    objs[pagetree-1]=(f"<< /Type /Pages /Count {len(page_ids)} /Kids ["+" ".join(f"{x} 0 R" for x in page_ids)+"] >>").encode()
    out=bytearray(b"%PDF-1.7\n%GX trial\n"); offsets=[0]
    for i,obj in enumerate(objs,1):
        offsets.append(len(out)); out.extend(f"{i} 0 obj\n".encode()); out.extend(obj); out.extend(b"\nendobj\n")
    xref=len(out); out.extend(f"xref\n0 {len(objs)+1}\n0000000000 65535 f \n".encode())
    for off in offsets[1:]: out.extend(f"{off:010d} 00000 n \n".encode())
    out.extend(f"trailer\n<< /Size {len(objs)+1} /Root {catalog} 0 R /Info << /Producer ({producer}) >> >>\nstartxref\n{xref}\n%%EOF\n".encode())
    path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(out)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    srcdoc=json.loads((BASE/"input/document.json").read_text())
    report=json.loads((BASE/"output/report.json").read_text())
    pages=[]; dims=[]; o1=[]; o2=[]; o3=[]; o3oi=[]; o3u=[]; o3c0=[]; o3c2=[]; o0=[]; o0rgb=[]; diagnostics={"accepted":0,"traced":0,"empty_masks":0,"inferred_removed_pixels":0,"composition_audit":[]}
    # Global lookup across page reports and observed source crops.
    obs={}; protos={}; occs={}
    for pi,pr in enumerate(report["page_reports"]):
        for ob in pr["reconstruction"]["observations"]: obs[ob["symbol_id"]]=(pi,ob)
        for proto in pr["reconstruction"]["prototypes"]: protos[proto["prototype_id"]]=proto
        for oc in pr["reconstruction"]["occurrences"]: occs[oc["symbol_id"]]=(pi,oc)
    font,qdf_data=extract_embedded_font(BASE/"output/canonical-experimental.pdf")
    glyph_order=font.getGlyphOrder(); glyphset=font.getGlyphSet(); glyf=font["glyf"]
    current_matrices,occurrence_gids,proto_gids=extracted_occurrence_mappings(qdf_data,report,obs,occs)
    proto_forms={}; gid_form={}
    for gid in sorted(set(g for gs in proto_gids.values() for g in gs)):
        name=glyph_order[gid]; g=glyf[name]
        dw,dh,ops=form_definition(glyphset,name,g)
        formkey=hashlib.sha256((f"{dw}:{dh}:"+ops).encode()).hexdigest()
        gid_form[gid]=formkey
        proto_forms.setdefault(formkey,(dw,dh,ops,gid,g.xMin,g.yMin))
    diagnostics["canonical_prototype_ids"]=len(proto_gids)
    diagnostics["actual_embedded_gids_for_prototypes"]=sum(len(gs) for gs in proto_gids.values())
    diagnostics["distinct_embedded_glyph_outlines"]=len(proto_forms)
    diagnostics["prototypes_with_multiple_embedded_gids"]={pid:sorted(gs) for pid,gs in proto_gids.items() if len(gs)>1}
    diagnostics["occurrence_matrices_mapped"]=len(current_matrices)
    # Oracle identity arm: use the pristine character and page typeface to
    # assign occurrences, then choose the most-used inferred prototype form
    # available for that true family. This does not inspect pristine outlines.
    family_counts={}
    for pi in range(len(srcdoc["pages"])):
        truth=page_truth(pi); truth_by_id={r["id"]:r for r in truth["records"]}
        for sid,(spi,oc) in occs.items():
            if spi!=pi or not (oc.get("repaired") or oc.get("reused")): continue
            rec=truth_by_id.get(sid); gid=occurrence_gids.get(sid)
            if not rec or not gid or not gid_form.get(gid): continue
            family=(oracle_style_key(pi,rec["text"]),rec["text"])
            candidate=gid_form[gid]
            family_counts.setdefault(family,{})[candidate]=family_counts.setdefault(family,{}).get(candidate,0)+1
    oracle_family_form={family:sorted(counts.items(),key=lambda kv:(-kv[1],kv[0]))[0][0]
                        for family,counts in family_counts.items() if counts}
    diagnostics["oracle_family_form_counts"]={f"{style}|{ch}":counts for (style,ch),counts in family_counts.items()}
    diagnostics["oracle_family_selected_forms"]={f"{style}|{ch}":key for (style,ch),key in oracle_family_form.items()}
    for pi,page in enumerate(srcdoc["pages"]):
        rgb=np.asarray(Image.open(BASE/"input"/f"page{pi:02}.png").convert("RGB"))
        h,w=rgb.shape[:2]; dims.append((w,h)); truth=page_truth(pi)
        original=rgb.copy(); pristine=np.asarray(Image.open(BASE/"oracle"/f"page{pi:02}.png").convert("RGB")); oracle_gray=pristine[:,:,0]
        source_vectors=[]; clean_vectors=[]; inferred_vectors=[]
        source_forms=[]; inferred_forms=[]; oracle_identity_current_forms=[]; uniform_forms=[]; c0_forms=[]; c2_forms=[]
        oracle_vecs=oracle_paths(pi,truth,w,h)
        oracle_bg=pristine.copy()
        # Oracle-clean all text interiors while preserving non-text artwork.
        for rec,_ in oracle_vecs:
            x0,y0,x1,y1=unpadded_box(rec); oracle_bg[int(y0):int(y1),int(x0):int(x1)]=255
        for rec,_ in oracle_vecs:
            clean_vectors.append(_)
        inferred_bg=original.copy(); accepted=[]
        for rec in truth["records"]:
            ent=occs.get(rec["id"])
            if not ent: continue
            _,oc=ent
            if not (oc.get("repaired") or oc.get("reused")) or not oc.get("prototype_id"): continue
            diagnostics["accepted"]+=1
            gid=occurrence_gids.get(rec["id"])
            form=proto_forms.get(gid_form.get(gid))
            if not form:
                diagnostics["empty_masks"]+=1
                continue
            dw,dh,formops,form_gid,xmin,ymin=form
            key=gid_form[gid]
            truth_box=oracle_ink_box(oracle_gray,rec)
            target=truth_box
            oracle_key=oracle_family_form.get((oracle_style_key(pi,rec["text"]),rec["text"]))
            if oracle_key:
                oracle_form=proto_forms[oracle_key]
                odw,odh,oops,ogid,oxmin,oymin=oracle_form
                x0,y0,x1,y1=target
                oracle_matrix=((x1-x0)/odw*PT,(y1-y0)/odh*PT,x0*PT,(h-y1)*PT)
                source_forms.append((oracle_key,odw,odh,oops,oracle_matrix))
            target3=oc.get("replacement_bbox_px") or obs[rec["id"]][1]["bbox_px"]
            text_matrix=current_matrices.get(rec["id"])
            if text_matrix:
                sx,_,_,sy,tx,ty=text_matrix
                current_matrix=(sx/2048.0,sy/2048.0,tx+sx*xmin/2048.0,ty+sy*ymin/2048.0)
                inferred_forms.append((key,dw,dh,formops,current_matrix))
                c0_forms.append((key,dw,dh,formops,current_matrix))
                c2_forms.append((key,dw,dh,formops,current_matrix))
                if oracle_key:
                    # Counterfactual current placement: use the same inferred
                    # replacement box and production independent-axis fit,
                    # but calculate the affine from the oracle-selected form's
                    # own dimensions. Reusing the inferred font matrix here
                    # would confound outline identity and placement.
                    candidate_current=((target3[2]-target3[0])/odw*PT,
                       (target3[3]-target3[1])/odh*PT,
                       target3[0]*PT,(h-target3[3])*PT)
                    oracle_identity_current_forms.append((oracle_key,odw,odh,oops,candidate_current))
            tw=target3[2]-target3[0]; th=target3[3]-target3[1]
            scale_px=min(tw/max(1e-6,dw),th/max(1e-6,dh))
            uniform_matrix=(scale_px*PT,scale_px*PT,
              (target3[0]+(tw-dw*scale_px)*0.5)*PT,(h-target3[3])*PT)
            uniform_forms.append((key,dw,dh,formops,uniform_matrix))
            accepted.append((rec,target))
            diagnostics["traced"]+=1
            # GX2 C2 provisional: erase only dark source samples in the exact
            # source observation box. This is a measurement arm, not a safe
            # production ownership policy.
            dx0,dy0,dx1,dy1=[int(round(v)) for v in obs[rec["id"]][1]["bbox_px"]]
            local=inferred_bg[max(0,dy0):max(0,dy1),max(0,dx0):max(0,dx1)]
            gray=local.mean(axis=2); ink=gray<145
            if local.size:
                ring=np.concatenate([local[0:2].reshape(-1,3),local[-2:].reshape(-1,3),local[:,0:2].reshape(-1,3),local[:,-2:].reshape(-1,3)],axis=0)
                paper=np.median(ring,axis=0).astype(np.uint8)
                local[ink]=paper
            diagnostics["inferred_removed_pixels"]+=int(ink.sum())
            diagnostics["composition_audit"].append({
                "occurrence_id":rec["id"],"page":pi,"unicode":rec["text"],
                "source_bbox_px":[int(dx0),int(dy0),int(dx1),int(dy1)],
                "source_dark_pixels_lt145":int(ink.sum()),"vector_gid":int(gid),
                "prototype_id":oc.get("prototype_id"),
                "reconstruction_bbox_px":[float(v) for v in target3],
                "pristine_ink_bbox_px":[float(v) for v in truth_box]})
        ocr=json.loads((BASE/"input"/page["ocr_page_path"]).read_text())
        semantics=[(s["text"],[min(p[0] for p in s["polygon"]),min(p[1] for p in s["polygon"]),max(p[0] for p in s["polygon"]),max(p[1] for p in s["polygon"])] ) for s in ocr["spans"]]
        o1.append({"rgb":oracle_bg,"vectors":[x[1] for x in oracle_vecs],"semantic":semantics})
        # O2/C1 uses the original scan with superseded source ink cleaned using
        # evaluator-only glyph regions, while retaining all non-replaced scan.
        c1=original.copy()
        for rec,_ in accepted:
            x0,y0,x1,y1=unpadded_box(rec); c1[int(y0):int(y1),int(x0):int(x1)]=oracle_bg[int(y0):int(y1),int(x0):int(x1)]
        o2.append({"rgb":c1,"vectors":source_vectors,"forms":source_forms,"semantic":semantics})
        o3.append({"rgb":c1.copy(),"vectors":inferred_vectors,"forms":inferred_forms,"semantic":semantics})
        o3oi.append({"rgb":c1.copy(),"vectors":inferred_vectors,"forms":oracle_identity_current_forms,"semantic":semantics})
        o3u.append({"rgb":c1.copy(),"vectors":inferred_vectors,"forms":uniform_forms,"semantic":semantics})
        o3c0.append({"rgb":original.copy(),"vectors":inferred_vectors,"forms":c0_forms,"semantic":semantics})
        o3c2.append({"rgb":inferred_bg,"vectors":inferred_vectors,"forms":c2_forms,"semantic":semantics})
        o0.append({"rgb":original,"vectors":[],"semantic":semantics})
        o0rgb.append({"rgb":original,"force_rgb":True,"vectors":[],"semantic":semantics})
    pdf_write(OUT/"O0-source-searchable.pdf",o0,dims,"ScanWeave GX O0 source raster")
    pdf_write(OUT/"O0-DeviceRGB-searchable.pdf",o0rgb,dims,"ScanWeave GX O0 source RGB raster control")
    pdf_write(OUT/"O1-oracle-outline-placement.pdf",o1,dims,"ScanWeave GX O1 oracle ceiling")
    pdf_write(OUT/"O2-reconstructed-oracle-placement.pdf",o2,dims,"ScanWeave GX O2 reconstructed outline oracle placement")
    pdf_write(OUT/"O3-reconstructed-current-placement.pdf",o3,dims,"ScanWeave GX O3 reconstructed outline current placement")
    pdf_write(OUT/"O3-oracle-identity-current-placement.pdf",o3oi,dims,"ScanWeave GX O3 oracle identity current placement")
    pdf_write(OUT/"O3-uniform-placement.pdf",o3u,dims,"ScanWeave GX O3 uniform-scale placement ablation")
    pdf_write(OUT/"C0-source-under-vector.pdf",o3c0,dims,"ScanWeave GX C0 source raster under vector replacement")
    pdf_write(OUT/"C2-inferred-clean-background.pdf",o3c2,dims,"ScanWeave GX C2 inferred local ink suppression")
    shutil.copyfile(BASE/"output/canonical-experimental.pdf",OUT/"O4-current-m1g.pdf")
    (OUT/"trial_diagnostics.json").write_text(json.dumps(diagnostics,indent=2)+"\n")
    (OUT/"composition_audit.json").write_text(json.dumps(diagnostics["composition_audit"],indent=2)+"\n")
    print(json.dumps({"arms":{p.name:{"bytes":p.stat().st_size,"sha256":sha(p.read_bytes())} for p in sorted(OUT.glob("*.pdf"))},"pages":len(o0),"diagnostics":diagnostics},indent=2))

if __name__=="__main__": main()
