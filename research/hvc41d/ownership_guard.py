"""Fail closed unless every patch pixel belongs to the recorded source unit."""
import numpy as np

def require_owned(patch,owner):
 patch=np.asarray(patch,dtype=bool);owner=np.asarray(owner,dtype=bool)
 if patch.shape!=owner.shape:raise ValueError('ownership dimensions differ')
 outside=int((patch&~owner).sum())
 if outside:raise ValueError(f'patch exceeds recorded ownership by {outside} pixels')
 return True
