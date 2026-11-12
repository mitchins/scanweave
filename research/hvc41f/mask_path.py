"""Trace exact unions of owned source pixels as non-rectangular contours."""
import numpy as np
def mask_polygons(mask):
 # Oriented boundary edges of the union of owned source pixels, not pixel rectangles.
 H,W=mask.shape; edges=set()
 for y,x in zip(*np.nonzero(mask)):
  if y==0 or not mask[y-1,x]:edges.add(((int(x),int(y)),(int(x+1),int(y))))
  if x==W-1 or not mask[y,x+1]:edges.add(((int(x+1),int(y)),(int(x+1),int(y+1))))
  if y==H-1 or not mask[y+1,x]:edges.add(((int(x+1),int(y+1)),(int(x),int(y+1))))
  if x==0 or not mask[y,x-1]:edges.add(((int(x),int(y+1)),(int(x),int(y))))
 original=edges.copy();loops=[];directions={(1,0):0,(0,1):1,(-1,0):2,(0,-1):3}
 while edges:
  edge=min(edges);edges.remove(edge);start,pt=edge;points=[start,pt];prev=start
  while pt!=start:
   incoming=directions[(pt[0]-prev[0],pt[1]-prev[1])];choices=[e for e in edges if e[0]==pt]
   if not choices:raise ValueError('open mask boundary')
   def priority(e):
    nxt=e[1];turn=(directions[(nxt[0]-pt[0],nxt[1]-pt[1])]-incoming)%4
    return {1:0,0:1,3:2,2:3}[turn]
   chosen=min(choices,key=priority);edges.remove(chosen);prev,pt=chosen;points.append(pt)
  loops.append(points)
 area=sum(sum(a[0]*b[1]-b[0]*a[1] for a,b in zip(loop,loop[1:]))/2 for loop in loops)
 if area!=int(mask.sum()):raise ValueError('mask boundary area mismatch')
 if sum(len(loop)-1 for loop in loops)!=len(original):raise ValueError('mask boundary changed')
 return loops
