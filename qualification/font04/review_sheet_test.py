"""Verify sheet parallelization using unrelated UI test images, no review key."""
from pathlib import Path
import json,multiprocessing,tempfile
from PIL import Image,ImageDraw
from qualification.font04.seal_b2prime_review import render_sheet

def main():
    with tempfile.TemporaryDirectory(prefix='font04-sheet-test-') as temp:
        assets=Path(temp);panels=[dict(id='test-'+str(i),renderer='test') for i in range(4)]
        for i,p in enumerate(panels):
            for label in ['source','U','V']:
                im=Image.new('L',(70+i,56),'white');ImageDraw.Draw(im).rectangle([12,8,40,40],fill=80);im.save(assets/(p['id']+'-'+label+'.png'))
        task=(assets,panels);serial=render_sheet(task)
        with multiprocessing.get_context('spawn').Pool(2) as pool:parallel=pool.map(render_sheet,[task,task])
        assert all(r==serial for r in parallel)
    Path('qualification/font04/b2prime-review-sheet-equivalence.json').write_text(json.dumps(dict(serial_parallel_stream_equal=True,sheets=2,panels_per_sheet=4,key_access=False,reference='Same ordered PIL layout and lossless compression; workers receive only public Source/U/V images.'),indent=2)+'\n');print('Sheet parallelization exact',flush=True)

if __name__=='__main__':main()
