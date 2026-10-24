"""Sealed development-corpus review; never opens its separately written key."""
from collections import defaultdict
import json
import math
import os
from pathlib import Path
import random
import subprocess
import sys

import numpy as np
import pikepdf
from PIL import Image

from qualification.font04.context_instances import contextual_instances
from qualification.font04.context_proposals import draw_key
from qualification.font04.metrics import inspect, render, sha
from qualification.font04.r2a_metrics import bind, load_snapshot
from qualification.font04.r2a_package_checks import candidate_arm

ROOT = Path(__file__).resolve().parents[2]
LOCAL = ROOT/'qualification/font04/local/R2a'
GROUPS = ('forms', 'receipts', 'mixed', 'historical', 'financial')
SEED = 25102026


def stratified(populations, count, rng):
    if sum(map(len, populations.values())) <= count:
        return {g:set(rows) for g,rows in populations.items()}
    selected = {g:set() for g in populations}
    while sum(map(len,selected.values())) < count:
        for group, rows in populations.items():
            available = sorted(set(rows)-selected[group])
            if available and sum(map(len,selected.values())) < count:
                selected[group].add(rng.choice(available))
    return selected


def rejected_context(default, destination, rows, bindings, observations, pairs, selected, directory, helper):
    requests, canonicals, members = [], {}, []
    geometry = json.loads(Path(str(default)+'.json').read_text())['pages']
    by_member = {o['member']:o for o in observations}
    by_occurrence = {(r['page'],r['occurrence']):i for i,r in enumerate(rows)}
    for member in sorted(selected):
        pair = pairs[member]
        obs = by_member[member]
        i = by_occurrence[obs['page'],obs['occurrence']]
        old = bindings[i]
        canonical = by_member[pair['canonical']]['canonical']
        frame = obs['frame']
        origin = canonical['origin']
        dx, dy, scale = pair['parameters']
        left = 32+scale*(origin[0]-.5-32)+dx
        top = 48+scale*(origin[1]-.5-48)+dy
        bbox = [frame['cx']+(left-32)/frame['scale'], frame['baseline']+(top-48)/frame['scale'],
                frame['cx']+(left+scale*canonical['width']-32)/frame['scale'], frame['baseline']+(top+scale*canonical['height']-48)/frame['scale']]
        g = geometry[obs['page']]
        a,d = g['width_pt']/g['raster_width'],g['height_pt']/g['raster_height']
        sx,sy = (bbox[2]-bbox[0])/canonical['ink_span'][0],(bbox[3]-bbox[1])/canonical['ink_span'][1]
        new = [sx*2048*a,0,0,sy*2048*d,(bbox[0]-canonical['anchor'][0]*sx)*a,g['height_pt']-(bbox[3]+canonical['anchor'][1]*sy)*d]
        m = old['matrix']
        transform = [new[0]/m[0],0,0,new[3]/m[3],(new[4]-m[4])/m[0]*2048,(new[5]-m[5])/m[3]*2048]
        requests.append(dict(canonical=pair['canonical'],original_gid=old['gid'],transform=transform))
        canonicals[pair['canonical']] = dict(canonical,member=pair['canonical'])
        members.append(i)
    with pikepdf.open(default) as pdf:
        data = next(iter(pdf.pages[0].Resources.Font.values())).DescendantFonts[0].FontDescriptor.FontFile2.read_bytes()
    fontpath = directory/'default.ttf'
    fontpath.write_bytes(data)
    request = directory/'counterfactual-request.json'
    request.write_text(json.dumps(dict(default_font=str(fontpath),canonicals=list(canonicals.values()),instances=requests)))
    newfont, gids = directory/'counterfactual.ttf', directory/'counterfactual-gids.json'
    subprocess.run([helper,request,newfont,gids],check=True)
    stub_gids = json.loads(gids.read_text())
    result = {}
    with pikepdf.open(default) as original:
        pdf = pikepdf.Pdf.new()
        # copy_foreign caches imports: mutating that object also changes /F1
        # on every subsequently imported page. Clone the font dictionary before
        # installing the reduced counterfactual program and Identity GID map.
        imported = pdf.copy_foreign(original.pages[0].Resources.Font.F1)
        parent = pdf.make_indirect(pikepdf.Dictionary(imported))
        child = pikepdf.Dictionary(parent.DescendantFonts[0])
        descriptor = pikepdf.Dictionary(child.FontDescriptor)
        descriptor.FontFile2 = pdf.make_stream(newfont.read_bytes())
        child.FontDescriptor = pdf.make_indirect(descriptor)
        child.CIDToGIDMap = pikepdf.Name.Identity
        parent.DescendantFonts = pikepdf.Array([pdf.make_indirect(child)])
        for i,gid in zip(members,stub_gids):
            row,draw = rows[i],bindings[i]
            pdf.pages.append(original.pages[row['page']])
            page = pdf.pages[-1]
            resources = pikepdf.Dictionary(page.Resources)
            fonts = pikepdf.Dictionary(resources.Font)
            fonts['/R2aProbe'] = parent
            resources.Font = fonts
            page.Resources = resources
            instructions,mode,tm,active,seen = [],0,None,None,0
            for args,op in pikepdf.parse_content_stream(page):
                name = str(op)
                if name == 'Tr':mode = int(args[0])
                elif name == 'Tm':tm = list(args)
                elif name == 'Tf':active = str(args[0])
                if name == 'Tj' and mode != 3 and active == '/F1' and tm is not None and draw_key(int.from_bytes(bytes(args[0]),'big'),tm)==draw_key(draw['cid'],draw['matrix']):
                    instructions.extend([([pikepdf.Name('/R2aProbe'),1],pikepdf.Operator('Tf')),([pikepdf.String(gid.to_bytes(2,'big'))],op),([pikepdf.Name('/F1'),1],pikepdf.Operator('Tf'))])
                    seen += 1
                else:instructions.append((args,op))
            assert seen == 1,(i,seen)
            page.Contents = pdf.make_stream(pikepdf.unparse_content_stream(instructions))
            result[i] = len(pdf.pages)-1
        pdf.save(destination,deterministic_id=True)
    return result


def context_crop(path, page, crop, engine):
    # Poppler region rendering changes antialias phase outside the target.
    # Render all arms as complete pages, then take the identical bitmap crop.
    x, y, xx, yy = crop
    return render(path, page, 300, engine)[y:yy, x:xx]


def bounds(row, rows):
    # Native span IDs identify the OCR word, including all its visible draws.
    word = [r for r in rows if (r['page'], r['span_id']) == (row['page'], row['span_id'])]
    x = min(r['bbox'][0] for r in word)
    y = min(r['bbox'][1] for r in word)
    xx = max(r['bbox'][2] for r in word)
    yy = max(r['bbox'][3] for r in word)
    return [max(0, int(x)-25), max(0, int(y)-16),
            min(math.ceil(row['page_width']*300/72), math.ceil(xx)+25),
            min(math.ceil(row['page_height']*300/72), math.ceil(yy)+16)]


def worse_draws(group):
    metrics = json.loads((LOCAL/f'metrics/{group}/metrics.json').read_text())
    # Same source-normalized squared ink error as the stop review table.
    # "Any isolated metric" also includes the independent direct-outline score.
    return {r['draw'] for r in metrics['records'] if r['substituted']
            and r['metric'] in ('analytic', 'direct', 'pdfium', 'poppler')
            and r['candidate']['error']-r['default']['error'] > .02}


def main(final):
    staging = LOCAL/'blind-private-staging-v2'
    public = LOCAL/'blind-review-v2'
    key = LOCAL/'blind-private-v2/sealed-key.json'
    assert not staging.exists() and not public.exists() and not key.exists(),'Never overwrite a sealed review'
    staging.mkdir(mode=0o700)
    (staging/'assets').mkdir()
    rng = random.Random(SEED)
    data,accepted,rejected = {},{},{}
    for group in GROUPS:
        default,candidate = final/f'{group}-off.pdf',final/f'{group}-cover-2.0.pdf'
        source = LOCAL/f'export/{group}-observations'
        rows = load_snapshot(source/'source.json')['rows']
        obs = json.loads((source/'observations.json').read_text())
        plan = json.loads((source/'plan.json').read_text())
        report = json.loads(Path(str(candidate)+'.json').read_text())['conversion']['glyph_sharing']
        choices = defaultdict(list)
        for pair in plan['fits']:
            if obs[pair['member']]['frame'] is not None and obs[pair['canonical']]['canonical'] is not None:
                choices[pair['member']].append(pair)
        proposals = {i:min(pairs,key=lambda p:(len(p['reasons']),p['error'],p['canonical'])) for i,pairs in choices.items()}
        accepted[group] = [d['member'] for d in report['decisions'] if d['accepted']]
        rejected[group] = [d['member'] for d in report['decisions'] if not d['accepted'] and d['member'] in proposals]
        geometry = json.loads(Path(str(default)+'.json').read_text())['pages']
        bindings = bind(rows,inspect(candidate),geometry)
        basebindings = bind(rows,inspect(default),geometry)
        data[group] = dict(default=default,candidate=candidate,rows=rows,observations=obs,plan=plan,report=report,proposals=proposals,bindings=bindings,basebindings=basebindings)
    aa,rr = stratified(accepted,300,rng),stratified(rejected,150,rng)
    random_rejected = {g: sorted(ids) for g,ids in rr.items()}
    assert sum(map(len,rr.values())) >= 150
    mixed_tail, financial_tail = worse_draws('mixed'), worse_draws('financial')
    assert len(financial_tail) >= len(mixed_tail), ('insufficient financial tail', len(mixed_tail), len(financial_tail))
    matched_financial = set(rng.sample(sorted(financial_tail), len(mixed_tail)))
    fixture = Path('/tmp/scanweave-font04-product/crates/scanweave-io/tests/fixtures/glyph-sharing-regressions.json')
    fixtures = json.loads(fixture.read_text())['cases']
    metadata,selection = [],{}
    for group,item in data.items():
        rows,obs = item['rows'],item['observations']
        lookup = {(r['page'],r['occurrence']):i for i,r in enumerate(rows)}
        selected = {lookup[obs[i]['page'],obs[i]['occurrence']] for i in aa[group]}
        # Diversified source impressions within actual admitted groups: review
        # these probes for visibly different weight/style, without changing bands.
        groups = defaultdict(list)
        for d in item['report']['decisions']:
            if d['accepted']:groups[d['canonical']].append(d['member'])
        diversity = sorted(groups,key=lambda j:np.ptp([sum(obs[i]['field']) for i in groups[j]]),reverse=True)[:10]
        cross = set()
        for j in diversity:
            ordered = sorted(groups[j],key=lambda i:sum(obs[i]['field']))
            cross.update([ordered[0],ordered[-1],j])
        selected.update(lookup[obs[i]['page'],obs[i]['occurrence']] for i in cross)
        tail = mixed_tail if group == 'mixed' else matched_financial if group == 'financial' else set()
        selected.update(tail)
        if group == 'mixed':
            # Exhaustive grading makes the >5% decision denominator observable.
            selected.update(lookup[obs[i]['page'],obs[i]['occurrence']] for i in accepted[group])
            selected.add(lookup[obs[518]['page'],obs[518]['occurrence']])
        fixture_members = set()
        fixture_requests = []
        if group == 'financial':
            # B1 IDs are mapped through their registered financial B2 identity.
            old_rows = json.loads((LOCAL.parent/'financial-B1prime-PV.pdf.font04/source.json').read_text())['rows']
            def native_member(case, index):
                if 'B1prime' not in case['source']:
                    return index
                old = old_rows[index]
                matches = [o['member'] for o in obs if (o['page'], o['id']) == (old['page'], old['id'])]
                assert len(matches) == 1
                return matches[0]
            for case in fixtures:
                member = native_member(case, case['member'])
                canonical = native_member(case, case['canonical'])
                fixture_members.add(member)
                fixture_requests.append((case, member, canonical))
            selected.update(lookup[obs[i]['page'],obs[i]['occurrence']] for i in fixture_members if i not in rejected[group])
            rr[group].update(i for i in fixture_members if i in rejected[group])
        directory = staging/group
        directory.mkdir()
        contexts = []
        if selected:
            path = directory/'accepted-context.pdf'
            mapping = contextual_instances(item['default'],item['candidate'],path,rows,selected,dict(enumerate(item['bindings'])))
            contexts.append(('accepted',path,mapping,None))
        if rr[group]:
            path = directory/'rejected-context.pdf'
            mapping = rejected_context(item['default'],path,rows,item['basebindings'],obs,item['proposals'],rr[group],directory,LOCAL/'export/font04_r2a_review')
            contexts.append(('rejected',path,mapping,None))
        for case_index, (case, member, canonical) in enumerate(fixture_requests):
            fixture_dir = directory/f'fixture-{case_index:02}'
            fixture_dir.mkdir()
            path = fixture_dir/'context.pdf'
            pair = dict(member=member,canonical=canonical,parameters=case['parameters'])
            mapping = rejected_context(item['default'],path,rows,item['basebindings'],obs,{member:pair},{member},fixture_dir,LOCAL/'export/font04_r2a_review')
            contexts.append(('registered-regression-fixture',path,mapping,dict(case_index=case_index,source=case['source'],member=case['member'],canonical=case['canonical'],native_member=member,native_canonical=canonical,parameters=case['parameters'])))
        cache = {}
        for engine in ('pdfium','poppler'):
            # The frozen image-only matched input is the raw scan, not the
            # compositor's isolated ownership layer or knocked-out background.
            for name,path in [('source',ROOT/f'qualification/pdf_packaging/groups/{group}-input.pdf'),('current',item['default'])]:
                for pi in range(len(json.loads(Path(str(item['default'])+'.json').read_text())['pages'])):
                    cache[engine,name,pi] = render(path,pi,300,engine)
        for kind,path,mapping,registered_case in contexts:
            for i,page in mapping.items():
                row = rows[i]
                x,y,xx,yy = crop = bounds(row, rows)
                for engine in ('pdfium','poppler'):
                    asset = f'item{len(metadata):06}'
                    arrays = {name:cache[engine,name,row['page']][y:yy,x:xx] for name in ('source','current')}
                    proposed = context_crop(path, page, crop, engine)
                    arrays['candidate'], presentation = candidate_arm(arrays['current'], proposed, crop, [row])
                    assert len({a.shape for a in arrays.values()})==1
                    for name,array in arrays.items():Image.fromarray(array).save(staging/'assets'/f'{asset}-{name}.png')
                    metadata.append(dict(asset=asset,presentation=presentation,document=group,draw=i,member=next((o['member'] for o in obs if (o['page'],o['occurrence'])==(row['page'],row['occurrence'])),None),type=kind,registered_case=registered_case,renderer=engine,page=row['page'],bounds=crop,cross_style_probe=i in {lookup[obs[k]['page'],obs[k]['occurrence']] for k in cross},identical_default_context=True,tail_stratum=i in tail,registered_member518=group=='mixed' and i==lookup[obs[518]['page'],obs[518]['occurrence']],registered_fixture=group=='financial' and any(i==lookup[obs[k]['page'],obs[k]['occurrence']] for k in fixture_members)))
        # Show complete word proposals in the same default surrounding context.
        spans = defaultdict(list)
        for i,row in enumerate(rows):spans[row['page'],row['span_id']].append(i)
        words = defaultdict(list)
        for ids in spans.values():
            word = ''.join(rows[i]['character'] for i in ids)
            if len(word)>=3:words[word].append(ids)
        repeated = [(word,instances) for word,instances in sorted(words.items()) if len(instances)>1 and any(i in selected for ids in instances for i in ids)][:10]
        for word,instances in repeated:
            for ids in instances[:2]:
                row = rows[ids[0]]
                boxes = [bounds(rows[i], rows) for i in ids]
                x,y,xx,yy = min(b[0] for b in boxes),min(b[1] for b in boxes),max(b[2] for b in boxes),max(b[3] for b in boxes)
                for engine in ('pdfium','poppler'):
                    asset = f'item{len(metadata):06}'
                    arrays = {name:cache[engine,name,row['page']][y:yy,x:xx] for name in ('source','current')}
                    proposed = render(item['candidate'],row['page'],300,engine)[y:yy,x:xx]
                    arrays['candidate'], presentation = candidate_arm(arrays['current'], proposed, [x,y,xx,yy], [rows[i] for i in ids])
                    for name,array in arrays.items():Image.fromarray(array).save(staging/'assets'/f'{asset}-{name}.png')
                    metadata.append(dict(asset=asset,presentation=presentation,document=group,type='repeated-word',word=word,draws=ids,renderer=engine,page=row['page'],bounds=[x,y,xx,yy]))
        selection[group] = dict(accepted_population=len(accepted[group]),random_accepted=sorted(aa[group]),rejected_population=len(rejected[group]),random_rejected=random_rejected[group],all_rejected=sorted(rr[group]),cross_style_members=sorted(cross),repeated_words=[word for word,_ in repeated],tail_draws=sorted(tail),fixture_members=sorted(fixture_members),all_mixed_substitutions=group=='mixed')
        print('review assets',group,len(metadata),flush=True)
    (staging/'panels.json').write_text(json.dumps(metadata,indent=2)+'\n')
    (staging/'selection.json').write_text(json.dumps(dict(seed=SEED,documents=selection),indent=2)+'\n')
    rule = (ROOT/'FONT_04_REVIEW_R2A_STOP.md').read_text().split('4. **Decision rule, fixed now, before grading.**',1)[1].rstrip()
    assert ('4. **Decision rule, fixed now, before grading.**'+rule) in (ROOT/'qualification/font04/R2A_BLIND_README.md').read_text()
    (staging/'README.md').write_text((ROOT/'qualification/font04/R2A_BLIND_README.md').read_text() + '\nReview package v2: the reference is the raw matched scan crop. Each single-member proposal is displayed in default page context, restricted to the target bounds plus 2 px. Repeated-word proposals use the union of the word members\' bounds plus 2 px, with default surrounding context. Frozen canonicals and transforms are unchanged.\n')
    subprocess.run([sys.executable,'-m','qualification.font04.r2a_seal_review',staging,public,key],check=True,env=dict(os.environ,FONT04_REVIEW_TITLE='FONT-04 R2a corpus blind review: Source / U / V'))
    receipt = json.loads((public/'seal-receipt.json').read_text())
    result = dict(schema='font04-R2a-blind-review-v2',status='SEALED; independent judgments pending',review_pdf=str(public/'blinded-review.pdf'),key_path=str(key),key_revealed=False,
                  selection=selection,random_accepted=sum(map(len,aa.values())),random_rejected_minimum=150,total_rejected=sum(map(len,rr.values())),mixed_tail=len(mixed_tail),financial_tail_population=len(financial_tail),matched_financial_tail=len(matched_financial),regression_fixtures=23,registered_fixture_members=selection['financial']['fixture_members'],receipt=receipt)
    (staging/'build-result.json').write_text(json.dumps(result,indent=2)+'\n')


if __name__=='__main__':main(Path(sys.argv[1]))
