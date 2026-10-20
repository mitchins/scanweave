"""Small grayscale image-only PDF writer for reproducible scan inputs."""
from __future__ import annotations

import hashlib
import zlib
from pathlib import Path

import numpy as np
from PIL import Image


def write_image_only_pdf(paths: list[Path], output: Path, dpi: int,
                         page_points: tuple[float, float]) -> None:
    """Write PNG grayscale pixels as FlateDecode image XObjects (no JPEG loss)."""
    if not paths:
        raise ValueError("at least one page image is required")
    wpt, hpt = page_points
    objects: list[bytes | None] = [None, None]
    page_ids: list[int] = []
    pixel_hashes: list[bytes] = []
    for image_path in paths:
        pixels = np.asarray(Image.open(image_path).convert("L"), dtype=np.uint8)
        height_px, width_px = pixels.shape
        if abs(width_px * 72 / dpi - wpt) > 0.1 or abs(height_px * 72 / dpi - hpt) > 0.1:
            raise ValueError(f"{image_path} dimensions do not match requested page size at {dpi} DPI")
        samples = pixels.tobytes()
        encoded = zlib.compress(samples, level=6)
        pixel_hashes.append(hashlib.sha256(samples).digest())
        page_id = len(objects) + 1
        image_id, content_id = page_id + 1, page_id + 2
        page_ids.append(page_id)
        page_dict = (f"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 {wpt:g} {hpt:g}] "
                     f"/Resources << /XObject << /Im0 {image_id} 0 R >> >> "
                     f"/Contents {content_id} 0 R >>").encode("ascii")
        image_dict = (f"<< /Type /XObject /Subtype /Image /Width {width_px} /Height {height_px} "
                      f"/ColorSpace /DeviceGray /BitsPerComponent 8 /Filter /FlateDecode "
                      f"/Length {len(encoded)} >>").encode("ascii")
        content = f"q\n{wpt:g} 0 0 {hpt:g} 0 0 cm\n/Im0 Do\nQ\n".encode("ascii")
        content_dict = f"<< /Length {len(content)} >>".encode("ascii")
        objects.extend((page_dict,
                        image_dict + b"\nstream\n" + encoded + b"\nendstream",
                        content_dict + b"\nstream\n" + content + b"endstream"))

    kids = " ".join(f"{page_id} 0 R" for page_id in page_ids)
    objects[0] = b"<< /Type /Catalog /Pages 2 0 R >>"
    objects[1] = f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode("ascii")
    document_id = hashlib.sha256(b"".join(pixel_hashes) + str(dpi).encode("ascii")).hexdigest()[:32].upper()
    out = bytearray(b"%PDF-1.4\n%\xe2\xe3\xcf\xd3\n")
    offsets = [0]
    for object_number, body in enumerate(objects, 1):
        assert body is not None
        offsets.append(len(out))
        out.extend(f"{object_number} 0 obj\n".encode("ascii"))
        out.extend(body)
        out.extend(b"\nendobj\n")
    xref = len(out)
    out.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    out.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        out.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    out.extend((f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R "
                f"/ID [<{document_id}><{document_id}>] >>\nstartxref\n{xref}\n%%EOF\n").encode("ascii"))
    output.write_bytes(out)
