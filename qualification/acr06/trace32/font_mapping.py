import fitz,sys,re,json,hashlib
p=fitz.open(sys.argv[1]); seen=set(); arr=[]
def ref(s):
 m=re.search(r'(\d+)\s+0\s+R',s);return int(m.group(1)) if m else None
def stream(x,k):
 typ,val=p.xref_get_key(x,k);r=ref(val)
 return hashlib.sha256(p.xref_stream(r)).hexdigest() if typ=='xref' and r else [typ,val]
for page in p:
 for f in page.get_fonts(full=True):
  x=f[0]
  if x in seen:continue
  seen.add(x);d=ref(p.xref_get_key(x,'DescendantFonts')[1]);assert d is not None
  arr.append({'encoding':p.xref_get_key(x,'Encoding'),'unicode':stream(x,'ToUnicode'),'cidtogid':stream(d,'CIDToGIDMap'),'W':p.xref_get_key(d,'W'),'DW':p.xref_get_key(d,'DW')})
print(json.dumps(arr,sort_keys=True))
