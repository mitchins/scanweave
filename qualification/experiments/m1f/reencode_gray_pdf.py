#!/usr/bin/env python3
"""Pixel-preserving PDF-level DeviceGray control for frozen 600 DPI PDF."""
import hashlib, json, sys, zlib
from pathlib import Path
import fitz
import numpy as np

src = Path(sys.argv[1]); dst = Path(sys.argv[2])
doc = fitz.open(src)
seen = set(); converted=[]
for page in doc:
    for info in page.get_images(full=True):
        xref, width, height = info[0], info[2], info[3]
        if xref in seen: continue
        seen.add(xref)
        raw = doc.xref_stream(xref)
        colors = info[5]
        if colors not in (3, "DeviceRGB"):
            converted.append({"xref":xref,"status":"already-not-RGB","colors":colors}); continue
        pixels = np.frombuffer(raw,dtype=np.uint8)
        if pixels.size != width*height*3:
            raise ValueError(f"unexpected decoded RGB length at xref {xref}")
        rgb=pixels.reshape(height,width,3)
        if not (np.array_equal(rgb[:,:,0],rgb[:,:,1]) and np.array_equal(rgb[:,:,0],rgb[:,:,2])):
            converted.append({"xref":xref,"status":"colored-preserved","colors":colors}); continue
        gray=rgb[:,:,0].tobytes()
        doc.update_stream(xref, gray, compress=True)
        doc.xref_set_key(xref,"ColorSpace","/DeviceGray")
        converted.append({"xref":xref,"status":"converted","width":width,"height":height,
            "sample_sha256":hashlib.sha256(gray).hexdigest(),"gray_samples":len(gray),"old_rgb_samples":len(raw)})
doc.save(dst, garbage=0, deflate=False, clean=False)
doc.close()
print(json.dumps({"source":str(src),"output":str(dst),"converted_resources":sum(x['status']=='converted' for x in converted),"resources":converted},indent=2))
