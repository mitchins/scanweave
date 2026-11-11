import json,pathlib,numpy as np
from PIL import Image
from scipy import ndimage as nd
R=pathlib.Path('/data/coding/scanweave/qualification/acr06');E=R/'hvc41d';r=json.loads((E/'calibration-exploratory.json').read_text())['rows'];top=json.loads((E/'topology-calibration.json').read_text());com=json.loads((E/'component-diagnostic.json').read_text());ids=[i for i in range(143) if i not in (17,53,58,67)]+[207,208]
def masks(q):
 a=np.asarray(Image.open(q['panel']).convert('L'))[::4,::4];cw=a.shape[1]//4;x0,y0,x1,y1=map(int,q['ocr_box']);w=x1-x0+6;h=y1-y0+6;return np.pad(a[20:20+h,2*cw:2*cw+w]>128,8),np.pad(a[20:20+h,3*cw:3*cw+w]>128,8)
def m(a,b):
 st=nd.generate_binary_structure(2,1);s=min((a&nd.binary_dilation(b,structure=st)).sum()/a.sum(),(b&nd.binary_dilation(a,structure=st)).sum()/b.sum());ca=np.array(nd.center_of_mass(a));cb=np.array(nd.center_of_mass(b));return float(s),float(np.linalg.norm(ca-cb)),float(b.sum()/a.sum())
pos=[];neg=[]
for i in ids:
 a,b=masks(r[i]);s,c,q=m(a,b);pos.append((i,s,c,q,r[i]['fill_luminance_error'],top[i]['positive_guard'],com[i]['base']))
 for dy,dx in [(0,2),(0,-2),(2,0),(-2,0)]:
  bb=nd.shift(b,(dy,dx),order=0,mode='constant');s,c,q=m(a,bb);neg.append((i,s,c,q,r[i]['fill_luminance_error']))
for t in [.93,.95,.97,.98]:
 for cmax in [1.0,1.25,1.5,1.75,2.0]:
  pp=sum(s>=t and c<=cmax and .8<=q<=1.2 and f is not None and f<=15 and h and k for i,s,c,q,f,h,k in pos);nn=sum(not(s>=t and c<=cmax and .8<=q<=1.2 and f is not None and f<=15) for i,s,c,q,f in neg)
  print(t,cmax,'positive',pp,'/',len(pos),'shift_reject',nn,'/',len(neg))
(E/'centroid-diagnostic.json').write_text(json.dumps({'positive':pos,'shift':neg},indent=2,default=lambda v:v.item())+'\n')
