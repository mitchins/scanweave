#!/usr/bin/env python3
from pathlib import Path
import json,numpy as np
R=Path('/data/coding/scanweave/qualification/acr06');data=json.loads((R/'local/c2b/decomposition-records.json').read_text());out={}
metrics=['original_fit','unregistered_fit','registration_error_reduction','pristine_missing_fraction','missing_in_source_fraction','additional_mask_loss_fraction','excluded_overlap_fraction','estimated_xheight_ratio','true_point_size_ratio','repaired_fit','true_scale_fit','repaired_true_scale_fit','residual_after_joint']
for dpi in (300,600):
 a=[x for x in data if x['dpi']==dpi and x['status']=='ok' and x['same_design']];m={}
 for k in metrics:
  values=[x[k] for x in a if x.get(k) is not None];m[k]={'median':float(np.median(values)),'p90':float(np.quantile(values,.9))}
 ratio=[abs(np.log(x['estimated_xheight_ratio']/x['true_point_size_ratio'])) for x in a];translation=[(x['registration'][0]**2+x['registration'][1]**2)**.5 for x in a]
 out[str(dpi)]={'same_design_n':len(a),'metrics':m,'abs_log_scale_ratio_error':{'median':float(np.median(ratio)),'p90':float(np.quantile(ratio,.9))},'registration_translation_norm':{'median':float(np.median(translation)),'p90':float(np.quantile(translation,.9))},'passes_008':{k:sum(x[k]<=.08 for x in a) for k in ('original_fit','repaired_fit','true_scale_fit','repaired_true_scale_fit')},'max_field_reconstruction_error':max(x['reconstruction_max_abs'] for x in a),'max_fit_reconstruction_error':max(abs(x['baseline_recomputed']-x['original_fit']) for x in a)}
(R/'c2b/decomposition-aggregate.json').write_text(json.dumps(out,indent=2)+'\n')
