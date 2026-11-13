#!/usr/bin/env python3
"""Record decoded dev-only JP2 evidence, including the COD wavelet transform."""
import hashlib,json,pathlib,struct,xml.etree.ElementTree as ET
from PIL import Image,features
B=pathlib.Path('/data/coding/scanweave/work/books01'); P=pathlib.Path(__file__).resolve().parents[1]; lock=json.loads((P/'sources.lock.json').read_text()); files=json.loads((B/'src/ia/dev-jp2.json').read_text())
for id,info in files.items():
 p=B/info['path']; raw=p.read_bytes(); start=raw.find(b'\xff\x4f\xff\x51'); assert start>=0; pos=raw.find(b'\xff\x52',start); assert pos>=0; length=int.from_bytes(raw[pos+2:pos+4],'big'); cod=raw[pos+4:pos+2+length]; assert len(cod)>=10; wavelet={0:'irreversible 9/7',1:'reversible 5/3'}.get(cod[9],'unknown')
 with Image.open(p) as im:
  dims=list(im.size); mode=im.mode; canonical=im.convert('L' if mode in ('1','L') else 'RGB'); pixels=hashlib.sha256(canonical.tobytes()).hexdigest(); siz=raw.find(b'\xff\x51',start); components=int.from_bytes(raw[siz+38:siz+40],'big'); bit_depths=[(raw[siz+40+3*i]&127)+1 for i in range(components)]
 work=id.split('/')[1]; node=ET.parse(B/'src/ia'/work/'scandata.xml').find(f'./pageData/page[@leafNum="{info["leaf"]}"]'); crop={e.tag:e.text for e in node.find('cropBox')}
 lock['pages'][id]['original_capture']={**info,'codestream_wavelet':wavelet,'components':components,'decoder':'Pillow '+Image.__version__+' with OpenJPEG '+str(features.version_codec('jpg_2000')),'decoded_mode':mode,'component_bit_depths':bit_depths,'decoded_pixel_sha256':pixels,'canonical_pixels':canonical.mode+'8 row-major','dimensions':dims,'scandata_crop':crop,'scandata_page_ppi':node.findtext('ppi'),'scandata_book_dpi':ET.parse(B/'src/ia'/work/'scandata.xml').findtext('./bookData/dpi'),'jp2_resolution_box': 'present, not interpreted' if b'resc' in raw[:start] or b'resd' in raw[:start] else 'absent'}
(P/'sources.lock.json').write_text(json.dumps(lock,indent=2,ensure_ascii=False)+'\n')
