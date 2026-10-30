"""Render PDF pages with the pinned PDFium (chromium/8100) via pypdfium2_raw bindings."""
import ctypes, sys
sys.path.insert(0, '/data/coding/scanweave/qualification/font04/local/R2a/pdfium-python')
import pypdfium2_raw as R
import numpy as np
R.FPDF_InitLibrary()

def render(path, page_index, scale):
    doc = R.FPDF_LoadDocument(path.encode(), None)
    assert doc, path
    pg = R.FPDF_LoadPage(doc, page_index)
    w, h = R.FPDF_GetPageWidthF(pg), R.FPDF_GetPageHeightF(pg)
    W, H = int(round(w * scale)), int(round(h * scale))
    bmp = R.FPDFBitmap_Create(W, H, 0)
    R.FPDFBitmap_FillRect(bmp, 0, 0, W, H, 0xFFFFFFFF)
    R.FPDF_RenderPageBitmap(bmp, pg, 0, 0, W, H, 0, R.FPDF_ANNOT | R.FPDF_LCD_TEXT * 0)
    stride = R.FPDFBitmap_GetStride(bmp)
    buf = ctypes.cast(R.FPDFBitmap_GetBuffer(bmp), ctypes.POINTER(ctypes.c_ubyte * (stride * H))).contents
    a = np.frombuffer(buf, dtype=np.uint8).reshape(H, stride)[:, :W * 4].reshape(H, W, 4)[:, :, :3][:, :, ::-1].copy()
    R.FPDFBitmap_Destroy(bmp); R.FPDF_ClosePage(pg); R.FPDF_CloseDocument(doc)
    return a, (w, h)

if __name__ == '__main__':
    from PIL import Image
    a, wh = render(sys.argv[1], int(sys.argv[2]), float(sys.argv[3]))
    Image.fromarray(a).save(sys.argv[4]); print(wh, a.shape)
