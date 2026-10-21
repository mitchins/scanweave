"""Exact unique-stream byte categories; never allocate bytes by image area."""
import collections
import csv
import json
from pathlib import Path
import pikepdf

BASE=Path(__file__).resolve().parent


def nodes(graph):
    for node in graph:
        yield node
        yield from nodes(node.get('children',[]))


def image_categories(record, pdf):
    result={}
    report=Path(record['path']+'.json')
    if record['arm']=='scanweave' and report.exists():
        conversion=json.loads(report.read_text())['conversion']
        for page,details in zip(pdf.pages,conversion['page_reports']):
            for index,patch in enumerate(details['patches']):
                image=page.Resources.XObject.get('/Im'+str(index))
                if image is None:
                    raise ValueError('Report/image name mismatch')
                role='reduced-paper' if patch['compact_background'] else 'native-whole-page' if len(details['patches'])==1 else 'native-exception'
                key=str(image.objgen)
                if key in result and result[key]!=role:
                    result[key]='shared-multiple-roles'
                else:
                    result[key]=role
    for key,image in record['images'].items():
        if image['resource_role'] in ('/SMask','/Mask') or image['ImageMask']:
            result[key]='mask-or-stencil'
        elif key not in result:
            placements=[n for p in record['pages'] for n in nodes(p['paint_graph']) if n.get('resource')==key]
            resolutions=[n['effective_dpi'] for n in placements]
            if record['arm'] in ('input','ocrmypdf1','ocrmypdf3'):
                result[key]='whole-page-mixed-content'
            elif record['arm']=='archive':
                result[key]='masked-colour-layer' if image['SMask'] else 'unmasked-colour-layer'
            elif resolutions and max(max(r)for r in resolutions)<160:
                result[key]='reduced-resolution-raster'
            else:
                result[key]='300dpi-raster-clipped' if any(record['graphics_states'][n['state_ref']]['clips']for n in placements) else '300dpi-raster'
    return result


def font_programs(font):
    """Program references from the recorded font dictionary, including direct fonts."""
    programs=set()
    descriptor=font.get('/FontDescriptor',{})
    for key in ('/FontFile','/FontFile2','/FontFile3'):
        if key in descriptor:
            programs.add(tuple(descriptor[key]['object']))
    for child in font.get('/DescendantFonts',[]):
        programs.update(font_programs(child))
    for value in font.get('/CharProcs',{}).values():
        programs.add(tuple(value['object']))
    return programs


def main():
    records=json.loads((BASE/'object-inventory.json').read_text())
    summaries=[];table=[]
    for record in records:
        with pikepdf.open(record['path']) as pdf:
            categories=image_categories(record,pdf)
            font_roles=collections.defaultdict(set)
            for key,modes in record['font_render_modes'].items():
                if key=='unknown':
                    continue
                font=record['fonts'][key]
                roles={'invisible-ocr-font' if mode==3 else 'visible-font' for mode in modes}
                for program in font_programs(font):
                    font_roles[program].update(roles)
            counts=collections.Counter();streams=[]
            page_content=set()
            for page in pdf.pages:
                contents=page.get('/Contents',[])
                page_content.update(c.objgen for c in (contents if isinstance(contents,pikepdf.Array) else [contents]))
            for obj in pdf.objects:
                if not isinstance(obj,pikepdf.Stream):
                    continue
                if obj.get('/Subtype')==pikepdf.Name.Image:
                    category=categories.get(str(obj.objgen),'unreferenced-image')
                elif obj.objgen in font_roles:
                    roles=font_roles[obj.objgen]
                    category=next(iter(roles)) if len(roles)==1 else 'shared-visible-invisible-font'
                elif obj.objgen in page_content:
                    category='page-content-stream'
                elif obj.get('/Subtype')==pikepdf.Name.Form:
                    category='form-content-stream'
                elif obj.get('/Type')==pikepdf.Name.ObjStm:
                    category='object-stream'
                elif obj.get('/Type')==pikepdf.Name.XRef:
                    category='xref-stream'
                else:
                    category='other-stream-maps-profiles-etc'
                size=len(obj.read_raw_bytes());counts[category]+=size
                streams.append({'object':list(obj.objgen),'category':category,'encoded_bytes':size})
            counts['serialized-residual']=record['pdf_bytes']-sum(counts.values())
            assert sum(counts.values())==record['pdf_bytes']
            summary={'collection':record['collection'],'arm':record['arm'],'pdf_bytes':record['pdf_bytes'],
                     'categories':dict(counts),'streams':streams,'pages':[]}
            for page,name in zip(record['pages'],record['members']):
                keys=set(n['resource']for n in nodes(page['paint_graph'])if n['kind']=='image')
                # Include dependencies even when masks are not directly placed by Do.
                pending=list(keys)
                while pending:
                    direct=pending.pop()
                    for candidate,image in record['images'].items():
                        if candidate not in keys and any(parent['image']==direct for parent in image.get('selected_parents',[])):
                            keys.add(candidate)
                            pending.append(candidate)
                summary['pages'].append({'id':name,'page':page['page'],'image_objects':sorted(keys),
                                         'referenced_image_bytes_not_additive':sum(record['images'][k]['encoded_bytes']for k in keys),
                                         'shared_objects':[k for k in keys if len(record['images'][k]['referencing_pages'])>1],
                                         'inline_stencil_count':sum(n['kind']=='inline-image'for n in nodes(page['paint_graph']))})
            summaries.append(summary)
            for category,count in counts.items():
                table.append({'collection':record['collection'],'arm':record['arm'],'scope':'unique-document-streams','page':'','member':'','category':category,'encoded_or_residual_bytes':count})
    for summary,record in zip(summaries,records):
        by_object={str(tuple(s['object'])):s['category']for s in summary['streams']}
        for page in summary['pages']:
            counts=collections.Counter()
            for key in page['image_objects']:
                counts[by_object[key]]+=record['images'][key]['encoded_bytes']
            for category,count in counts.items():
                table.append({'collection':record['collection'],'arm':record['arm'],
                              'scope':'page-referenced-images-nonadditive-if-shared','page':page['page'],
                              'member':page['id'],'category':category,'encoded_or_residual_bytes':count})
    (BASE/'byte-accounting.json').write_text(json.dumps(summaries,indent=2)+'\n')
    with (BASE/'gap-accounting.csv').open('w') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(table[0]));writer.writeheader();writer.writerows(table)
    totals={}
    for arm in dict.fromkeys(s['arm']for s in summaries):
        count=collections.Counter()
        for summary in summaries:
            if summary['arm']==arm:
                count.update(summary['categories'])
        totals[arm]=dict(count)
    print(json.dumps(totals,indent=2))


if __name__=='__main__':
    main()
