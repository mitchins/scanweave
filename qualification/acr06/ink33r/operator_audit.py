#!/usr/bin/env python3
"""Count show operations by effective fill color and text rendering mode.

Page content streams only; reports form XObjects to expose omissions. The audit
counts show operators, not glyphs, and does not infer a spatial text line.
"""
import collections, json, pathlib, hashlib
import pikepdf
ROOT=pathlib.Path('/data/coding/scanweave')
G=['historical','financial','mixed','receipts','forms']

def val(o):
    try: return float(o)
    except (ValueError,TypeError): return str(o)

def audit(path):
    out=[]
    with pikepdf.open(path) as pdf:
        for pg in pdf.pages:
            state={'space':'/DeviceGray','color':[0.0], 'tr':0}; stack=[]
            show=collections.Counter(); ops=collections.Counter(); colors=collections.Counter(); forms=[]; nbt=0
            for ins in pikepdf.parse_content_stream(pg):
                op=str(ins.operator); a=list(ins.operands); ops[op]+=1
                if op=='q': stack.append(dict(state))
                elif op=='Q' and stack: state=stack.pop()
                elif op=='BT': nbt+=1
                elif op=='Tr': state['tr']=int(a[0])
                elif op in ('g','rg','k'):
                    state['space']={'g':'/DeviceGray','rg':'/DeviceRGB','k':'/DeviceCMYK'}[op]; state['color']=[val(x) for x in a]
                elif op=='cs': state['space']=str(a[0]); state['color']=['unresolved']
                elif op in ('sc','scn'): state['color']=[val(x) for x in a]
                elif op in ('Tj','TJ',"'",'"'):
                    key=json.dumps([state['space'],state['color'],state['tr']],separators=(',',':'))
                    show[key]+=1
                    if state['tr'] in (0,2,4,6): colors[json.dumps([state['space'],state['color']],separators=(',',':'))]+=1
                elif op=='Do':
                    try:
                        ob=pg.Resources.XObject[a[0]]
                        if ob.get('/Subtype')==pikepdf.Name('/Form'): forms.append(str(a[0]))
                    except (KeyError,AttributeError): forms.append('unresolved:'+str(a[0]))
            out.append({'text_objects_BT':nbt,'show_by_fill_and_Tr':dict(show),'visible_fill_shows':dict(colors),'form_invocations':forms,'ops':dict(ops)})
    return {'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'pages':out}

out={}
for g in G:
    out[g]={}
    for kind,path in [('scanweave',ROOT/f'qualification/acr06/local/ink33r/{g}.pdf'),('adobe',ROOT/f'qualification/pdf_packaging/groups/{g}-adobe.pdf')]:
        out[g][kind]=audit(path)
(ROOT/'qualification/acr06/ink33r/operator-audit.json').write_text(json.dumps(out,indent=2)+'\n')
