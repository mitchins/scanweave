#!/usr/bin/env python3
"""Independent low-resolution phase-correlation check of the reported MRC shift."""
import json,pathlib
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter
from skimage.registration import phase_cross_correlation
B=pathlib.Path('/data/coding/scanweave/work/books01');P=pathlib.Path(__file__).resolve().parents[2];p=B/'pilot/renders/8967333';a=Image.open(p/'src/pdfium-150.png').convert('L');b=Image.open(p/'mrc-M/pdfium-150.png').convert('L');w=min(a.width,b.width);h=min(a.height,b.height);a=np.asarray(a.crop((0,0,w,h)).resize((w//2,h//2),Image.Resampling.LANCZOS),dtype=float);b=np.asarray(b.crop((0,0,w,h)).resize((w//2,h//2),Image.Resampling.LANCZOS),dtype=float);a=a-gaussian_filter(a,2);b=b-gaussian_filter(b,2);out={}
for method in ['phase','unnormalized']:
 shift,error,_=phase_cross_correlation(a,b,upsample_factor=10,normalization='phase' if method=='phase' else None);out[method]={'shift_yx_75dpi_pixels':shift.tolist(),'normalized_error':float(error)}
(P/'pilot/results/phase1b/shift-check.json').write_text(json.dumps({'page':'finebooks/conchologiaiconi05reev/8967333','row':'mrc-M','source_renderer':'pdfium','method':'150-DPI renders reduced to 75 DPI; mean background removed with Gaussian sigma 2; whole-page phase correlation','results':out,'review_reference':'approximately 4 pixels at 75 DPI','limitation':'whole-page correlation can be insensitive to local or crop-specific displacement'},indent=2)+'\n')
