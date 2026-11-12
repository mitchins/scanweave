"""Fail closed unless every patch pixel belongs to the recorded source unit."""
import numpy as np

def require_owned(patch,owner):
 patch=np.asarray(patch,dtype=bool);owner=np.asarray(owner,dtype=bool)
 if patch.shape!=owner.shape:raise ValueError('ownership dimensions differ')
 outside=int((patch&~owner).sum())
 if outside:raise ValueError(f'patch exceeds recorded ownership by {outside} pixels')
 return True

def clip_owned(proposed, owner):
 """Clip a proposed removal mask exactly to the recorded source ownership."""
 proposed=np.asarray(proposed,dtype=bool);owner=np.asarray(owner,dtype=bool)
 if proposed.shape!=owner.shape:raise ValueError('ownership dimensions differ')
 clipped=proposed & owner
 require_owned(clipped,owner)
 return clipped

def require_contained_bbox(proposal, owner):
 """Allow a traced box inside its same-symbol unit; never invent ownership."""
 if len(proposal)!=4 or len(owner)!=4 or not (owner[0]<=proposal[0] and owner[1]<=proposal[1] and owner[2]>=proposal[2] and owner[3]>=proposal[3]):
  raise ValueError('proposal box extends outside recorded unit box')
 return True
