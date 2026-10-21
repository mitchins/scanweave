"""Small generated PDFs test forensic mechanics, not real-document preservation.

Actual corpus measurements/visual review are recorded separately. No historical
PDF is required or modified by these CI controls.
"""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

import numpy as np
import pikepdf
from PIL import Image

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE/'raster_competitors'))
import account
import components
import experiments
import inspect_pdf
import layers
import render_compare
import run_inventory
import text_inventory
import verify_current
from test_inspector import InspectorTests


def fixture(path, indexed=False, mask=False, jpeg=False, inline=False):
    pdf=pikepdf.Pdf.new()
    samples=np.full((96,64,3),245,dtype=np.uint8)
    samples[20:65:3,10:53]=[50,60,70]
    samples[70:72,4:58]=[110,100,90]
    for _ in range(3):
        page=pdf.add_blank_page(page_size=(64*72/300,96*72/300))
        im=Image.fromarray(samples)
        stream=experiments.rgb_stream(pdf,im,jpeg=jpeg)
        if indexed:
            values=np.zeros((96,64),dtype=np.uint8)
            values[20:65:3,10:53]=1;values[70:72,4:58]=2
            stream=pikepdf.Stream(pdf,zlib.compress(values.tobytes()))
            stream.update({'/Type':pikepdf.Name.XObject,'/Subtype':pikepdf.Name.Image,
                           '/Width':64,'/Height':96,'/BitsPerComponent':8,
                           '/ColorSpace':pikepdf.Array([pikepdf.Name.Indexed,pikepdf.Name.DeviceRGB,2,pikepdf.String(bytes([245,245,245,50,60,70,110,100,90]))]),
                           '/Filter':pikepdf.Name.FlateDecode})
        if mask:
            alpha=pikepdf.Stream(pdf,zlib.compress(bytes([255])*(64*96)))
            alpha.update({'/Type':pikepdf.Name.XObject,'/Subtype':pikepdf.Name.Image,
                          '/Width':64,'/Height':96,'/BitsPerComponent':8,
                          '/ColorSpace':pikepdf.Name.DeviceGray,'/Filter':pikepdf.Name.FlateDecode})
            stream.SMask=alpha
        font=pikepdf.Dictionary(Type=pikepdf.Name.Font,Subtype=pikepdf.Name.Type1,BaseFont=pikepdf.Name.Helvetica)
        page.Resources=pikepdf.Dictionary(XObject=pikepdf.Dictionary(Im0=stream),Font=pikepdf.Dictionary(F1=font))
        ops=b'q 15.36 0 0 23.04 0 0 cm /Im0 Do Q 0 g 0.1 w 1 1 m 14 1 l S BT /F1 2 Tf 3 Tr 1 3 Td (test) Tj 0 Tr ET'
        if inline:
            ops+=b' q 1 0 0 1 1 1 cm BI /W 1 /H 1 /BPC 1 /IM true ID \x80 EI Q'
        page.Contents=pikepdf.Stream(pdf,ops)
    path.parent.mkdir(parents=True,exist_ok=True)
    pdf.save(path,deterministic_id=True)


class RasterPipelineTests(unittest.TestCase):
    def test_generated_pdf_pipeline(self):
        with tempfile.TemporaryDirectory() as directory, contextlib.ExitStack() as stack:
            root=Path(directory);base=root/'qualification/raster_competitors';base.mkdir(parents=True)
            pack=root/'qualification/pdf_packaging';tonal=root/'qualification/tonal_raster'
            group={'historical':{'members':['history-00','history-01','history-02'], 'input':'qualification/pdf_packaging/groups/historical-input.pdf'}}
            records=[]
            for arm in render_compare.ARMS:
                path=tonal/'collections/historical.pdf' if arm=='scanweave' else pack/'groups'/f'historical-{arm}.pdf'
                fixture(path,indexed=arm=='ocrmypdf3',mask=arm=='archive',inline=arm=='adobe')
                records.append({'path':str(path.relative_to(root)),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
                if arm=='scanweave':
                    report={'conversion':{'page_reports':[{'patches':[{'compact_background':False}]}for _ in range(3)]}}
                    Path(str(path)+'.json').write_text(json.dumps(report))
            (pack/'groups.json').write_text(json.dumps(group))
            (pack/'run-manifest.json').write_text(json.dumps({'artifacts':records}))
            (tonal/'run-manifest.json').write_text(json.dumps({'files':[]}))
            (base/'regions.json').write_text(json.dumps({'history-02':[{'class':'thin-marks','label':'line and text','box':[.1,.1,.9,.9]}]}))
            for module in (run_inventory,experiments,verify_current):
                stack.enter_context(patch.object(module,'ROOT',root))
            for module in (run_inventory,account,layers,components,experiments,render_compare,text_inventory,verify_current):
                stack.enter_context(patch.object(module,'BASE',base))
            stack.enter_context(patch.object(run_inventory,'PACK',pack))
            stack.enter_context(patch.object(run_inventory,'TONAL',tonal))
            stack.enter_context(patch.object(render_compare,'LOCAL',base/'local'))
            stack.enter_context(patch.object(layers,'LOCAL',base/'local'))
            stack.enter_context(patch.object(components,'LOCAL',base/'local'))
            stack.enter_context(patch.object(experiments,'OUT',base/'local/experiments'))
            stack.enter_context(patch.object(layers,'SELECTED',('history-02',)))
            stack.enter_context(patch.object(components,'SELECTED',((2,'history-02'),)))
            with contextlib.redirect_stdout(io.StringIO()):
                run_inventory.main();account.main();text_inventory.main()
                render_compare.main();render_compare.main()  # Exercise verified cache path.
                layers.main();components.main();experiments.main()
            inventory=json.loads((base/'object-inventory.json').read_text())
            self.assertEqual(len(inventory),6)
            self.assertEqual(sum(len(d['pages'])for d in inventory),18)
            self.assertTrue(all(d['encoded_stream_bytes']['image']>0 for d in inventory))
            self.assertEqual(len(json.loads((base/'region-results.json').read_text())['pages']),36)
            self.assertTrue(all(v['ordered_replay_pixel_identical']for r in json.loads((base/'layer-results.json').read_text())for v in r['renderers'].values()))
            # Current-command orchestration control: fake process only copies the
            # test input. It is not conversion/quality evidence.
            class Completed:
                returncode=0
            def copy_command(command,**kwargs):
                destination=Path(command[-1]);destination.write_bytes((tonal/'collections/historical.pdf').read_bytes())
                self.assertEqual(kwargs['timeout'],1800)
                return Completed()
            with patch.object(verify_current.subprocess,'run',side_effect=copy_command), contextlib.redirect_stdout(io.StringIO()):
                verify_current.main()
            self.assertTrue(json.loads((base/'current-verification.json').read_text())[0]['byte_identical'])

    def test_grayscale_jpeg_metadata_and_geometry_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'jpeg.pdf';fixture(path,jpeg=True)
            report=inspect_pdf.inspect(path)
            self.assertTrue(all('jpeg'in image for image in report['images'].values()))
        source=Image.new('RGB',(12,10),'white');candidate=Image.new('RGB',(13,10),'white')
        metrics=render_compare.features(source,candidate)
        self.assertEqual(metrics['mae'],0)
        self.assertEqual(metrics['geometry']['uncompared_output_pixels'],10)
        self.assertFalse(metrics['geometry']['equal_canvas'])


if __name__=='__main__':
    unittest.main()
