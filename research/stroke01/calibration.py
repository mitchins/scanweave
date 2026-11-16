"""Calibrate a decline gate on two fonts and test on the third font."""
import numpy as np
TRAIN={'DejaVuSerif.ttf','LiberationSerif-Regular.ttf'}
HELDOUT='LiberationSerif-Italic.ttf'

def good(row, name='local'):
    m=row['methods'][name]
    return bool(m['boundary_f1']>=.90 and m['missing_fraction']<=.20 and m['false_ink_fraction']<=.20 and m['false_joins']==0)

def calibrate(rows):
    # Empirical training precision target; ties choose higher coverage, then
    # higher precision. Fixed finite grid, no use of the held-out font's GT.
    train=[r for r in rows if r['font'] in TRAIN]
    candidates=[]
    for snr in [4,6,8,10,12,16,24,32,48,64,96]:
        for unc in [.03,.06,.1,.15,.2,.3,.5,1.]:
            chosen=[r for r in train if not r['declined'] and r['confidence']>=snr and r['uncertainty']<=unc]
            correct=sum(good(r) for r in chosen)
            if chosen and correct/len(chosen)>=.90:
                candidates.append((len(chosen),correct/len(chosen),-snr,unc))
    if not candidates:return {'snr_min':float('inf'),'uncertainty_max':0.,'training_accepted':0,'training_correct':0,'target_precision':.9}
    n,precision,neg_snr,unc=max(candidates)
    return {'snr_min':-neg_snr,'uncertainty_max':unc,'training_accepted':n,'training_correct':round(n*precision),'target_precision':.9}

def accepts(row,gate):
    return bool(not row['declined'] and row['confidence']>=gate['snr_min'] and row['uncertainty']<=gate['uncertainty_max'])
