#!/usr/bin/env python3
import hashlib,importlib.metadata as m,json,os,pathlib,platform,shutil,subprocess,sys
import fitz,pikepdf,pypdfium2,pypdfium2_raw
B=pathlib.Path('/data/coding/scanweave/work/books01'); Q=pathlib.Path(__file__).resolve().parent
def h(p):
 with open(p,'rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def version(cmd):
 try:return subprocess.run(cmd,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,timeout=20).stdout.strip()
 except Exception as e:return str(e)
models={}
for x in (B/'tessdata_best/SHA256SUMS').read_text().splitlines():
 parts=x.split(maxsplit=1)
 if len(parts)==2:models[parts[1].lstrip('*')]=parts[0]
paths=['/data/coding/scanweave/work/scanweave-ab7dfba/target/release/scanweave','/usr/bin/tesseract','/usr/bin/pdftotext','/usr/bin/pdftoppm','/data/coding/scanweave/qualification/.venv/bin/recode_pdf','/data/coding/scanweave/qualification/.venv/bin/ocrmypdf']
out={'python':sys.version,'platform':platform.platform(),'executables':{p:{'sha256':h(p)} for p in paths},'scanweave_commit':'ab7dfba','tesseract_full':version(['/usr/bin/tesseract','--version']),'tessdata_best_commit':'e12c65a915945e4c28e237a9b52bc4a8f39a0cec','traineddata_sha256':models,'hocr_config':{'origin':'/usr/share/tesseract-ocr/5/tessdata/configs/hocr','sha256':h(B/'tessdata_best/configs/hocr'),'additional_manifest':'$B/tessdata_best/SHA256SUMS.additions'},'txt_config':{'origin':'/usr/share/tesseract-ocr/5/tessdata/configs/txt','sha256':h(B/'tessdata_best/configs/txt'),'additional_manifest':'$B/tessdata_best/SHA256SUMS.additions'},'ocrmypdf':m.version('ocrmypdf'),'archive_pdf_tools':m.version('archive-pdf-tools'),'archive_shim':'LEDGER.md: getPageImageList -> get_page_images and modulo index guard','pikepdf':pikepdf.__version__,'pdfium':str(pypdfium2.PDFIUM_INFO),'mupdf':fitz.__doc__.strip(),'poppler':version(['/usr/bin/pdftoppm','-v']),'adobe':'Acrobat XI 11.0.20; existing opaque GUI output, default OCR language','optional_optimisers':{x:shutil.which(x) for x in ['pngquant','jbig2','jbig2enc']},'renderer_binaries':{'pdfium':'pypdfium2 bundled native library','mupdf':'PyMuPDF bundled library','poppler':'/usr/bin/pdftoppm'},'packages':{x:m.version(x) for x in ['numpy','scipy','pillow','scikit-image','pypdfium2','PyMuPDF']}}
native=list(pathlib.Path(fitz.__file__).parent.glob('*.so'))+list(pathlib.Path(pypdfium2_raw.__file__).parent.glob('*.so'))
out['native_renderer_libraries']={str(p):h(p) for p in native}
out['edit_distance']={'source_sha256':h(Q/'edit.c'),'library_sha256':h(B/'pilot/edit.so'),'compiler':version(['/usr/bin/cc','--version'])}
(Q/'versions.json').write_text(json.dumps(out,indent=2)+'\n')
