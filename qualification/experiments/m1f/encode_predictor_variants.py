#!/usr/bin/env python3
"""Losslessly re-encode grayscale image streams with Flate predictors 1/2/12."""
import hashlib, json, sys, zlib
from pathlib import Path
import fitz

src = Path(sys.argv[1]); outdir = Path(sys.argv[2]); outdir.mkdir(parents=True, exist_ok=True)

def filtered(samples: bytes, width: int, height: int, predictor: int) -> bytes:
    if len(samples) != width * height:
        raise ValueError("control input is not 8-bit grayscale")
    rows = [samples[y*width:(y+1)*width] for y in range(height)]
    if predictor == 1:
        return samples
    encoded = bytearray()
    previous = bytes(width)
    for row in rows:
        if predictor == 2:
            # TIFF horizontal differencing: subtract the previous sample in
            # this row (one byte per pixel for DeviceGray).
            encoded.append(row[0])
            encoded.extend((row[i] - row[i - 1]) & 255 for i in range(1, width))
        elif predictor == 12:
            # PNG Up row filter: subtract the sample in the preceding row.
            encoded.append(2)
            encoded.extend((value - previous[i]) & 255 for i, value in enumerate(row))
        else:
            raise ValueError(predictor)
        previous = row
    return bytes(encoded)

results = {}
for predictor, name in ((1, "none"), (2, "tiff"), (12, "png_up")):
    doc = fitz.open(src); seen = set(); resources = []
    for page in doc:
        for entry in page.get_images(full=True):
            xref, width, height, colors = entry[0], entry[2], entry[3], entry[5]
            if xref in seen: continue
            seen.add(xref)
            if colors not in (1, "DeviceGray"):
                raise ValueError(f"unexpected color model on image {xref}: {colors}")
            samples = doc.xref_stream(xref) or b""
            payload = zlib.compress(filtered(samples, width, height, predictor), 6)
            doc.update_stream(xref, payload, compress=False)
            doc.xref_set_key(xref, "Filter", "/FlateDecode")
            if predictor == 1:
                doc.xref_set_key(xref, "DecodeParms", "null")
            else:
                doc.xref_set_key(xref, "DecodeParms", f"<< /Predictor {predictor} /Colors 1 /BitsPerComponent 8 /Columns {width} >>")
            resources.append({"xref":xref,"width":width,"height":height,"samples":len(samples),"encoded":len(payload),"sample_sha256":hashlib.sha256(samples).hexdigest()})
    dst = outdir / f"predictor-{name}.pdf"
    doc.save(dst, garbage=0, deflate=False, clean=False); doc.close()
    results[name] = {"path":str(dst),"pdf_bytes":dst.stat().st_size,"pdf_sha256":hashlib.sha256(dst.read_bytes()).hexdigest(),"resources":resources}
(outdir / "predictor-variants.json").write_text(json.dumps({"source":str(src),"source_sha256":hashlib.sha256(src.read_bytes()).hexdigest(),"variants":results},indent=2)+"\n")
print(json.dumps({name:{"pdf_bytes":item["pdf_bytes"],"pdf_sha256":item["pdf_sha256"]} for name,item in results.items()},indent=2))
