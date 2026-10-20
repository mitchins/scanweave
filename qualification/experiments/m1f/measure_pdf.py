#!/usr/bin/env python3
"""Deterministic public-PDF accounting for M1-F. Requires PyMuPDF."""
from __future__ import annotations
import hashlib
import json
import sys
from pathlib import Path
import fitz


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def inspect(path: Path) -> dict:
    raw = path.read_bytes()
    doc = fitz.open(path)
    images = {}
    page_refs = []
    contents = {}
    fonts = {}
    texts = []
    for page_no, page in enumerate(doc, 1):
        refs = []
        for entry in page.get_images(full=True):
            xref = entry[0]
            refs.append(xref)
            if xref in images:
                images[xref]["references"].append(page_no)
                continue
            info = doc.extract_image(xref)
            encoded = doc.xref_stream_raw(xref) or b""
            decoded = doc.xref_stream(xref) or b""
            color_key = doc.xref_get_key(xref, "ColorSpace")[1]
            filter_key = doc.xref_get_key(xref, "Filter")[1]
            images[xref] = {
                "xref": xref, "width": entry[2], "height": entry[3],
                "bpc": entry[4], "colors": entry[5], "colorspace": color_key,
                "filter": filter_key, "smask_xref": entry[1],
                "encoded_bytes": len(encoded), "encoded_sha256": digest(encoded),
                "decoded_bytes": len(decoded), "decoded_sha256": digest(decoded),
                "references": [page_no],
            }
        page_refs.append(refs)
        contents_xref = page.get_contents()
        for xref in contents_xref:
            contents[xref] = doc.xref_stream_raw(xref) or b""
        for f in page.get_fonts(full=True):
            fonts[f[0]] = {"xref": f[0], "extension": f[1], "type": f[2], "basefont": f[3]}
        texts.append(page.get_text())
    # Image object references and actual image streams are counted separately.
    image_bytes = sum(x["encoded_bytes"] for x in images.values())
    def resource_key(x):
        return (x["width"], x["height"], x["bpc"], x["colorspace"], x["smask_xref"], x["decoded_sha256"])
    decoded_resources = {}
    encoded_resources = {}
    for item in images.values():
        decoded_resources.setdefault(resource_key(item), item)
        encoded_key = (resource_key(item), item["encoded_sha256"], item["filter"])
        encoded_resources.setdefault(encoded_key, item)
    unique_decoded_stream_bytes = sum(x["encoded_bytes"] for x in decoded_resources.values())
    unique_encoded_stream_bytes = sum(x["encoded_bytes"] for x in encoded_resources.values())
    content_bytes = sum(map(len, contents.values()))
    font_stream_ids = set()
    for xref in range(1, doc.xref_length()):
        try:
            obj = doc.xref_object(xref, compressed=False)
            font_stream_ids.update(int(n) for n in __import__("re").findall(r"/(?:FontFile2?|FontFile3)\s+(\d+)\s+0\s+R", obj))
        except Exception:
            pass
    font_program_bytes = sum(len(doc.xref_stream_raw(fid) or b"") for fid in font_stream_ids)
    doc.close()
    return {
        "path": str(path), "sha256": digest(raw), "pdf_bytes": len(raw),
        "pages": len(page_refs), "image_uses": sum(map(len, page_refs)),
        "unique_image_objects": len(images), "images": list(images.values()),
        "unique_encoded_resource_keys": len(encoded_resources),
        "unique_decoded_sample_keys": len(decoded_resources),
        "unique_encoded_image_stream_bytes": unique_encoded_stream_bytes,
        "duplicate_encoded_image_stream_bytes": image_bytes - unique_encoded_stream_bytes,
        "fonts": list(fonts.values()), "font_references": len(fonts),
        "font_program_stream_bytes": font_program_bytes,
        "content_streams": len(contents), "content_stream_bytes": content_bytes,
        "image_stream_bytes": image_bytes,
        "remaining_overhead_bytes": len(raw) - image_bytes - content_bytes - font_program_bytes,
        "extracted_text_sha256": digest("\f".join(texts).encode()),
        "extracted_text": texts,
    }


def main(argv: list[str]) -> None:
    paths = [Path(p) for p in argv]
    print(json.dumps([inspect(p) for p in paths], indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
