"""Native PDF inspection and renderer-independent metric utilities."""
import hashlib
import io
import re
import subprocess
import tempfile
from pathlib import Path
import numpy as np
import pikepdf
import pypdfium2 as pdfium
from fontTools.ttLib import TTFont
from scipy import ndimage


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def matrix(values):
    a,b,c,d,e,f=map(float,values)
    return np.array([[a,c,e],[b,d,f],[0.,0.,1.]])


def operands(m):return [float(m[0,0]),float(m[1,0]),float(m[0,1]),float(m[1,1]),float(m[0,2]),float(m[1,2])]


def inspect(path):
    draws=[];programs={};fonts={};users=[];font_cache={}
    with pikepdf.open(path) as pdf:
        for pi,page in enumerate(pdf.pages):
            resources={}
            for name,font in page.Resources.Font.items():
                if str(font.Subtype)!='/Type0':continue
                desc=font.DescendantFonts[0]
                if '/FontFile2' not in desc.FontDescriptor:continue
                data=desc.FontDescriptor.FontFile2.read_bytes();identifier=hashlib.sha256(data).hexdigest()
                if identifier not in font_cache:
                    tt=TTFont(io.BytesIO(data));font_cache[identifier]=(tt,tt.getGlyphOrder(),tt['head'].unitsPerEm)
                tt,order,upem=font_cache[identifier];cmap=desc.CIDToGIDMap
                mapping=None if isinstance(cmap,pikepdf.Name) else cmap.read_bytes()
                unicode={}
                for block in re.findall(rb'beginbfchar(.*?)endbfchar',font.ToUnicode.read_bytes(),re.S):
                    for a,b in re.findall(rb'<([0-9a-fA-F]+)>\s*<([0-9a-fA-F]+)>',block):unicode[int(a,16)]=bytes.fromhex(b.decode()).decode('utf-16-be')
                hashes=[];points=0
                for gid,name_g in (enumerate(order) if identifier not in fonts else []):
                    g=tt['glyf'][name_g];blob=g.compile(tt['glyf']);h=hashlib.sha256(blob).hexdigest();hashes.append(h)
                    if g.numberOfContours>0:points+=len(g.coordinates)
                    programs[(identifier,gid)]=h
                if identifier not in fonts:fonts[identifier]=dict(slots=len(order),decoded_bytes=len(data),encoded_bytes=len(desc.FontDescriptor.FontFile2.read_raw_bytes()),outline_points=points,hashes=hashes)
                resources[str(name)]=(identifier,tt,order,upem,mapping,unicode)
            state=dict(mode=0,font=None,m=np.eye(3),size=1.);stack=[]
            for args,op in pikepdf.parse_content_stream(page):
                op=str(op)
                if op=='q':stack.append(dict(state))
                elif op=='Q':state=stack.pop()
                elif op=='Tr':state['mode']=int(args[0])
                elif op=='Tf':state['font']=str(args[0]);state['size']=float(args[1])
                elif op=='Tm':state['m']=matrix(args)
                elif op=='Tj' and state['font'] in resources:
                    fid,tt,order,upem,mapping,unicode=resources[state['font']]
                    raw=bytes(args[0])
                    for offset in range(0,len(raw),2):
                        cid=int.from_bytes(raw[offset:offset+2],'big');gid=cid if mapping is None else int.from_bytes(mapping[2*cid:2*cid+2],'big')
                        g=tt['glyf'][order[gid]];m=state['m'].copy();m[:2,:2]*=state['size']
                        row=dict(page=pi,font=state['font'],font_hash=fid,cid=cid,gid=gid,character=unicode.get(cid,''),matrix=operands(m),program=programs[(fid,gid)],invisible=state['mode']==3)
                        if g.numberOfContours:
                            center=m@np.array([(g.xMin+g.xMax)/(2*upem),(g.yMin+g.yMax)/(2*upem),1.]);row['center']=center[:2].tolist()
                        users.append(row)
                        if state['mode']!=3:draws.append(row)
    return dict(draws=draws,users=users,fonts=fonts,bytes=Path(path).stat().st_size,sha256=sha(path))


def render(path,page,dpi,engine):
    if engine=='pdfium':
        doc=pdfium.PdfDocument(path);p=doc[page];bitmap=p.render(scale=dpi/72)
        result=np.asarray(bitmap.to_pil().convert('L')).copy();bitmap.close();p.close();doc.close();return result
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(['pdftoppm','-f',str(page+1),'-l',str(page+1),'-singlefile','-r',str(dpi),'-gray','-png',str(path),d+'/page'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        from PIL import Image
        with Image.open(d+'/page.png') as image:return np.asarray(image.convert('L')).copy()


def measure(a,b):
    a=np.asarray(a,float);b=np.asarray(b,float);union=np.maximum(a,b).sum();ma=a>.5;mb=b>.5
    ea=ma^ndimage.binary_erosion(ma);eb=mb^ndimage.binary_erosion(mb)
    distance=float((ndimage.distance_transform_edt(~ea)[eb].mean()+ndimage.distance_transform_edt(~eb)[ea].mean())/2) if ea.any() and eb.any() else float(max(a.shape))
    # Translation-independent shape metric, no pristine information used by inference.
    aligned=mb
    if ma.any() and mb.any():
        delta=np.array(ndimage.center_of_mass(ma))-ndimage.center_of_mass(mb)
        aligned=ndimage.shift(mb.astype(float),delta,order=0,mode='constant')>.5
    ec=aligned^ndimage.binary_erosion(aligned)
    rigid=float((ndimage.distance_transform_edt(~ea)[ec].mean()+ndimage.distance_transform_edt(~ec)[ea].mean())/2) if ea.any() and ec.any() else float(max(a.shape))
    return dict(error=float(np.square(a-b).sum()/max(1.,union)),iou=float(np.minimum(a,b).sum()/max(1.,union)),contour_distance=distance,rigid_contour_distance=rigid,area_bias=float((b.sum()-a.sum())/max(1.,a.sum())))


def summary(rows):
    result={}
    for key in ['error','iou','contour_distance','rigid_contour_distance','area_bias']:
        values=[r[key] for r in rows]
        result[key]=dict(mean=float(np.mean(values)),p95=float(np.quantile(np.abs(values) if key=='area_bias' else values,.95))) if values else None
    return result
