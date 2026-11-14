#!/data/coding/scanweave/qualification/.venv/bin/python -I
"""Strict frozen-OCR replacement for ScanWeave's Tesseract calls."""
import hashlib,json,os,pathlib,sys
from PIL import Image
args=sys.argv[1:]
if args==['--version']:
 os.execv('/usr/bin/tesseract',['/usr/bin/tesseract','--version'])
def fail(message):
 print('frozen OCR shim: '+message,file=sys.stderr);sys.exit(71)
try:
 record=json.loads(pathlib.Path(os.environ['BOOKS01_SHIM_RECORD']).read_text())
 if len(args)!=11:fail('unexpected argument count')
 image,prefix=args[:2]; base=['-l',record['language'],'--dpi',str(record['dpi'])]
 expected3=base+['-c','hocr_char_boxes=1','--psm','3','hocr']
 expected6=base+['--psm','6','-c','hocr_char_boxes=1','hocr']
 if args[2:]==expected3:psm='3'
 elif args[2:]==expected6:psm='6'
 else:fail('unexpected OCR argv')
 if psm not in record.get('allowed_psm',['3','6']):fail('unexpected psm')
 state=pathlib.Path(os.environ['BOOKS01_SHIM_STATE']); prior=state.read_text() if state.exists() else ''
 if (psm=='3' and prior) or (psm=='6' and prior!='3'):fail('unexpected OCR call order or duplicate')
 with Image.open(image) as im:
  if hashlib.sha256(im.convert('RGB').tobytes()).hexdigest()!=record['decoded_pixel_sha256']:fail('input decoded-pixel mismatch')
 source=pathlib.Path(record['hocr'][psm]); data=source.read_bytes()
 if hashlib.sha256(data).hexdigest()!=record['sha256'][psm]:fail('frozen hOCR hash mismatch')
 pathlib.Path(prefix+'.hocr').write_bytes(data);state.write_text(prior+psm)
except Exception as e:fail(repr(e))
