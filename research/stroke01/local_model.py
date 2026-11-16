"""Experimental per-component stroke-centre ink model; not production code."""
import numpy as np
from scipy import ndimage as ndi
from skimage import morphology

LUMA=np.array([.2126,.7152,.0722])

def estimate(obs, bg):
    """Return piecewise colour, alpha, components and uncertainty in linear RGB.

    A conservative noise-derived foreground proposal defines connected regions.
    Samples come from the stronger residual values on each region's skeleton;
    unlike a crop percentile, the criterion is relative to each component.
    Large components are treated as non-text, rather than used as ink samples.
    """
    h,w=obs.shape[:2]
    residual=(bg-obs)@LUMA
    centre=np.median(residual)
    noise=max(.002, float(1.4826*np.median(np.abs(residual-centre))))
    proposed=residual>max(.012,4*noise)
    labels,count=ndi.label(proposed,structure=np.ones((3,3)))
    objects=ndi.find_objects(labels)
    max_area=max(120,int(.10*h*w))
    components=[]
    eligible=np.zeros((h,w),bool)
    core=np.zeros((h,w),bool)
    for n,sl in enumerate(objects,1):
        if sl is None: continue
        region=labels[sl]==n; area=int(region.sum()); height,width=region.shape
        if area<3 or area>max_area or height>h*.72 or width>w*.72: continue
        ridge=morphology.skeletonize(region)
        rr=residual[sl][ridge]
        if len(rr)<2: continue
        strength=np.quantile(rr,.70)
        selected=ridge & (residual[sl]>=strength)
        samples=obs[sl][selected]
        if len(samples)<2: continue
        col=np.median(samples,axis=0)
        contrast=float(np.median((bg[sl][selected]-samples)@LUMA))
        scatter=float(1.4826*np.median(np.abs(((bg[sl][selected]-samples)@LUMA)-contrast)))
        comps={'label':n,'bbox':[sl[1].start,sl[0].start,sl[1].stop,sl[0].stop], 'area':area,'core_samples':len(samples),'contrast':contrast,'uncertainty':scatter/max(contrast,.005),'ink':col}
        components.append(comps); eligible[sl]|=region; core[sl]|=selected
    # A component with too few ridge samples borrows from nearby text cores,
    # not from unclassified or oversized regions; record whether it borrowed.
    for c in components:
        c['borrowed']=False
        if c['core_samples']>=4: continue
        x0,y0,x1,y1=c['bbox'];near=[]
        for other in components:
            if other is c or other['core_samples']<4:continue
            a,b,d,e=other['bbox'];dist=np.hypot((a+d-x0-x1)/2,(b+e-y0-y1)/2)
            if dist<=max(20,h*.35):near.append((dist,other))
        if near:
            near.sort(key=lambda x:x[0]); c['ink']=near[0][1]['ink'].copy();c['uncertainty']=max(c['uncertainty'],near[0][1]['uncertainty']);c['borrowed']=True
    if components:
        seed=np.zeros((h,w),np.int32)
        for i,c in enumerate(components,1):seed[labels==c['label']]=i
        _,index=ndi.distance_transform_edt(seed==0,return_indices=True)
        nearest=seed[tuple(index)]; colours=np.vstack([np.median(obs.reshape(-1,3),axis=0)]+[c['ink'] for c in components]); ink=colours[nearest]
        support=ndi.binary_dilation(eligible,iterations=2)
        contrasts=np.array([c['contrast'] for c in components]); uncertainties=np.array([c['uncertainty'] for c in components]); weights=np.array([c['core_samples'] for c in components]);
        contrast=float(np.average(contrasts,weights=weights)); uncertainty=float(np.average(uncertainties,weights=weights))
    else:
        ink=np.broadcast_to(np.median(obs.reshape(-1,3),axis=0),obs.shape).copy();support=eligible;contrast=0.;uncertainty=1.
    diff=bg-ink;alpha=np.clip(((bg-obs)*diff).sum(-1)/np.maximum((diff*diff).sum(-1),1e-8),0,1);alpha*=support
    return dict(ink=ink,alpha=alpha,core=core,support=support,components=components,noise=noise,contrast=contrast,uncertainty=uncertainty,eligible=eligible,labels=labels,proposed=proposed)
