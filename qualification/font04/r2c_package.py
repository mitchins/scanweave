"""Build P2prime blinded package from retained sidecars and PDFs; private mappings stay sealed."""
import hashlib,json,random,math
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from qualification.font04.metrics import render,sha
from qualification.font04.s1d_eval import join,classify
from qualification.font04.r2a_package_checks import candidate_arm,check_panel
ROOT=Path(__file__).resolve().parents[2];P=ROOT/'qualification/font04/local/P2prime';S=P/'sealed'; B=P/'blind-review'
ARMS=('off','cover-2.0','cover-2.0-ceiling')
def dump(p,v): p.write_text(json.dumps(v,indent=2)+'\n')
def main():
    if S.exists() or B.exists(): raise SystemExit('Existing package: refusing to overwrite')
    S.mkdir();B.mkdir(); seed=int.from_bytes(__import__('os').urandom(16),'big'); rng=random.Random(seed)
    observations=[json.loads(x) for x in (P/'p2prime/observations.jsonl').read_text().splitlines()]; labels={x['id']:x for x in map(json.loads,(P/'p2prime/oracle/labels.jsonl').read_text().splitlines())}; pools=defaultdict(list); census={}; data={}
    for i in range(9):
        conv={a:json.loads((P/f'sheet-{i}-{a}.pdf.json').read_text())['conversion'] for a in ARMS}; rows=conv[ARMS[2]]['page_reports'][0]['reconstruction']['observations']; byid={r['symbol_id']:r for r in rows}; decisions={a:conv[a]['glyph_sharing']['decisions'] for a in ARMS[1:]}; look={a:{d['member']:d for d in ds} for a,ds in decisions.items()}; targets=[o for o in observations if o['page']==i//3 and o['sheet']==i%3]; joined=join([{'id':r['symbol_id'],'bbox':r['bbox_px'],'character':r['text_hypothesis']} for r in rows],targets)
        data[i]=(byid,look)
        for a in ARMS[1:]:
            counts=Counter(); unresolved=0
            for d in decisions[a]:
                c=look[a].get(d['canonical']); x=joined.get(d['id']);y=joined.get(c['id']) if c else None
                if not x or not y:unresolved+=1;continue
                cls=classify(labels[x],labels[y]);kind='accepted' if d['accepted'] and d['member']!=d['canonical'] else 'rejected' if not d['accepted'] else 'self';counts[cls+'|'+kind]+=1
            same_accepted=counts['same-face|accepted'];same_rejected=counts['same-face|rejected']; census[f'{i}|{a}']={'counts':dict(counts),'unresolved':unresolved,'same_face_false_rejection_rate':same_rejected/(same_accepted+same_rejected) if same_accepted+same_rejected else None,'denominator_definition':'resolved proposed non-self accepted or rejected decisions classified same-face'}
        for d in decisions[ARMS[2]]:
            if d['id'] not in byid:continue
            if d['accepted'] and d['member']!=d['canonical']:pools['admitted',i].append(d['id'])
            if not d['accepted']:pools['rejected',i].append(d['id'])
            c=look[ARMS[2]].get(d['canonical']);
            if c and d['id'].split('s')[0]!=c['id'].split('s')[0]:pools['cross_run',i].append(d['id'])
        ca={d['id'] for d in decisions[ARMS[2]] if d['accepted'] and d['member']!=d['canonical']}
        for d in decisions[ARMS[1]]:
            if d['accepted'] and d['member']!=d['canonical'] and d['id'] not in ca and d['id'] in byid:pools['controls',i].append(d['id'])
        groups=defaultdict(list)
        for r in rows:groups[r['symbol_id'].split('s')[0]].append(r)
        words=defaultdict(list)
        for group in groups.values():
            word=''.join(x['text_hypothesis'] for x in group)
            if len(word)>2:words[word].extend(group)
        for word,rs in words.items():
            if len({r['symbol_id'].split('s')[0] for r in rs})>1:
                pools['repeated',i].extend(r['symbol_id'] for r in rs)
    from qualification.font04.r2c_census import main as census_main
    census_main()
    chosen=[]; counts={}; shortages={}
    for name,minimum in [('admitted',300),('rejected',150),('controls',100),('cross_run',30),('repeated',30)]:
        available=sum(len(pools[name,i]) for i in range(9)); wanted=min(available,minimum) if name!='admitted' or available>300 else available
        counts[name]={'available':available,'selected':wanted};shortages[name]=max(0,minimum-available)
        # Round robin across nine DPI/sheet cells, shuffled inside each cell.
        buckets=[list(dict.fromkeys(pools[name,i])) for i in range(9)]
        for b in buckets:rng.shuffle(b)
        selected=[]
        while len(selected)<wanted and any(buckets):
            for i,b in enumerate(buckets):
                if b and len(selected)<wanted:selected.append((i,b.pop()))
        for i,id in selected:chosen.append({'sheet':i,'id':id,'stratum':name})
    rng.shuffle(chosen); key=[]; manifest=[]; grades=[]; failures=[]; panel_images=[]
    # Native render pages once; retain only in sealed workspace.
    for i in range(9):
        for engine in ('pdfium','poppler'):
            for a in ARMS: Image.fromarray(render(P/f'sheet-{i}-{a}.pdf',0,(200,300,600)[i//3],engine)).save(S/f'{i}-{engine}-{a}.png')
    for n,item in enumerate(chosen):
        i=item['sheet'];id=item['id'];byid,_=data[i]; target=byid[id]; word=[r for k,r in byid.items() if k.split('s')[0]==id.split('s')[0]]; dpi=(200,300,600)[i//3]; pad=max(4,round(dpi/72*3)); boxes=[r['bbox_px'] for r in word]; crop=(max(0,math.floor(min(b[0] for b in boxes))-pad),max(0,math.floor(min(b[1] for b in boxes))-pad),min(6*dpi,math.ceil(max(b[2] for b in boxes))+pad),min(9*dpi,math.ceil(max(b[3] for b in boxes))+pad)); t={'bbox':target['bbox_px']}; w=[{'bbox':r['bbox_px'],'index':r['symbol_id']} for r in word]
        src=Image.open(P/'p2prime'/f'page-{i//3}-{i%3}.png').convert('L').crop(crop)
        for engine in ('pdfium','poppler'):
            arr={a:np.asarray(Image.open(S/f'{i}-{engine}-{a}.png').crop(crop).convert('L')).copy() for a in ARMS}; arrays={'source':np.asarray(src),'current':arr['off']};
            for a in ARMS[1:]: arrays[a],_=candidate_arm(arr['off'],arr[a],crop,[t])
            for a in ARMS[1:]:
                v=check_panel({'source':arrays['source'],'current':arrays['current'],'candidate':arrays[a]},crop,[t],w)
                if max(v['black_fraction'].values())>.5 or v['outside_target_changed_pixels'] or v['missing_source_glyphs']: failures.append({'panel':n,'engine':engine,'arm':a,'check':v})
            perm=list(ARMS);rng.shuffle(perm);no=len(key)+1;key.append({'panel':no,'sheet':i,'id':id,'stratum':item['stratum'],'engine':engine,'letters':dict(zip('ABC',perm))}); grades.extend({'panel':no,'arm':letter,'distinguishable_from_source_at_100':None,'distinguishable_at_200':None,'identity_class_defect':None,'materially_worse_than_other_arms':None} for letter in 'ABC')
            imgs=[src]+[Image.fromarray(arrays['current'] if a=='off' else arrays[a]) for a in perm]; rows_img=[]
            for scale in (1,2):
                gap=12;header=22; iw,ih=src.size; canv=Image.new('RGB',((iw+gap)*4,(ih*scale)+header),'white');dr=ImageDraw.Draw(canv)
                for j,(label,im) in enumerate(zip(('SOURCE','A','B','C'),imgs)):
                    x=j*(iw*scale+gap); # canvas resized below for actual scale
                canv=Image.new('RGB',((iw*scale+gap)*4,ih*scale+header),'white');dr=ImageDraw.Draw(canv)
                for j,(label,im) in enumerate(zip(('SOURCE','A','B','C'),imgs)):
                    x=j*(iw*scale+gap);dr.text((x,2),f'{label} {scale*100}%',fill='black');canv.paste(im.resize((iw*scale,ih*scale),Image.Resampling.NEAREST).convert('RGB'),(x,header)); b=target['bbox_px'];dr.rectangle((x+(b[0]-crop[0])*scale,header+(b[1]-crop[1])*scale,x+(b[2]-crop[0])*scale,header+(b[3]-crop[1])*scale),outline='red',width=1)
                rows_img.append(canv)
            panel=Image.new('RGB',(max(x.width for x in rows_img),sum(x.height for x in rows_img)+24),'white');dr=ImageDraw.Draw(panel);dr.text((0,2),f'Panel {no}  {engine}',fill='black'); y=24
            for im in rows_img:panel.paste(im,(0,y));y+=im.height
            panel_images.append((no,panel));manifest.append({'panel':no,'renderer':engine})
    dump(S/'structural-checks.json',{'panels':len(key),'failures':failures,'pass':not failures})
    dump(S/'key.json',{'seed':seed,'sampling':counts,'shortages':shortages,'panels':key})
    dump(B/'grades-template.json',{'instructions':{'distinguishable_from_source_at_100':['yes','no'],'distinguishable_at_200':['yes','no'],'identity_class_defect':['none','wrong-character','weight','slant','stroke','counter','dot-sliver'],'materially_worse_than_other_arms':['yes','no']},'grades':grades})
    rule=json.loads((ROOT/'qualification/font04/p2prime-preregistration.json').read_text())['evaluation_rules']['identity_visibility_rule'];(B/'README.md').write_text('# P2prime blind review\n\n'+rule+'\n\nGrade every arm for each panel; save and commit grades before unsealing. Red boxes mark the target. Displays are native pixels at 100% and nearest-neighbour 200%.\n')
    for start in range(0,len(panel_images),12):
        batch=panel_images[start:start+12];width=max(p.width for _,p in batch);height=sum(p.height+12 for _,p in batch);sheet=Image.new('RGB',(width,height),'white');y=0
        for _,p in batch:sheet.paste(p,(0,y));y+=p.height+12
        sheet.save(B/f'contact-{start//12+1:03}.png',optimize=True)
    dump(B/'manifest.json',{'panels':manifest,'files':{p.name:sha(p) for p in sorted(B.iterdir()) if p.is_file() and p.name != 'manifest.json'}})
    dump(ROOT/'qualification/font04/r2c-seal.json',{'key_sha256':sha(S/'key.json'),'census_sha256':sha(S/'census.json'),'package_manifest_sha256':sha(B/'manifest.json'),'structural_checks_sha256':sha(S/'structural-checks.json'),'structural_checks_pass':not failures})
    print('package completed; structural pass:',not failures,flush=True)
if __name__=='__main__':main()
