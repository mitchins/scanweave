"""Native extraction/paint-mode accounting of frozen PDFs, without OCR reruns."""
import hashlib
import json
import subprocess
from pathlib import Path
import pypdfium2 as pdfium
import pypdfium2.raw as raw

BASE=Path(__file__).resolve().parent


def main():
    results=[]
    for record in json.loads((BASE/'object-inventory.json').read_text()):
        with pdfium.PdfDocument(record['path']) as document:
            for index,name in enumerate(record['members']):
                page=document[index];text=page.get_textpage();value=text.get_text_range()
                visible=0;invisible=0
                for i in range(text.count_chars()):
                    char=raw.FPDFText_GetUnicode(text.raw,i)
                    if not char or chr(char).isspace():
                        continue
                    obj=raw.FPDFText_GetTextObject(text.raw,i)
                    mode=raw.FPDFTextObj_GetTextRenderMode(obj) if obj else -1
                    if mode==3:
                        invisible+=1
                    elif mode in (0,1,2,4,5,6):
                        visible+=1
                poppler=subprocess.check_output(['pdftotext','-f',str(index+1),'-l',str(index+1),'-raw',record['path'],'-'],timeout=60).decode(errors='replace')
                results.append({'collection':record['collection'],'arm':record['arm'],'id':name,
                                'pdfium_nonspace_visible_mode_chars':visible,'pdfium_nonspace_invisible_mode_chars':invisible,
                                'pdfium_text_sha256':hashlib.sha256(value.encode()).hexdigest(),
                                'poppler_text_sha256':hashlib.sha256(poppler.encode()).hexdigest(),
                                'extraction_equal_without_whitespace':''.join(value.split())==''.join(poppler.split())})
    (BASE/'text-inventory.json').write_text(json.dumps(results,indent=2)+'\n')


if __name__=='__main__':
    main()
