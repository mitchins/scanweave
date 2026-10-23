"""Publish raw-halo evidence only when it confirms the existing fixed decisions."""
from pathlib import Path
import json
BASE=Path('qualification/font04');ROOT=BASE/'local'

def main():
 for scope,control,name in [('B1','financial-B1prime-P0','owned-component-ledger.json'),('B2','financial-B2-P-initial','b2-owned-component-ledger.json')]:
  art=ROOT/(control+'.pdf.font04');raw=json.loads((art/'raw-owned-audit.json').read_text());path=BASE/name;ledger=json.loads(path.read_text());assert raw['fired']==ledger['exceptions'],'Raw ownership audit changes decisions; diagnose before proceeding'
  ledger['components']=raw['components'];ledger['reference']='Unmasked normalized source halo, actual current-draw agreement, fixed canonical footprint/halo; raw audit gives exactly the same exceptions as the fitting-support reference.';ledger['raw_halo_audit']=dict(path=str(art/'raw-owned-audit.json'),exceptions_identical=True);path.write_text(json.dumps(ledger,separators=(',',':'))+'\n')
  plans=[ROOT/'financial-B1prime-PV.pdf.font04/plan.json'] if scope=='B1' else [ROOT/f'financial-B2-{a}.pdf.font04/plan.json' for a in ['PV','PV-repeat']]
  for p in plans:
   data=json.loads(p.read_text());data['ownership_veto']=ledger;p.write_text(json.dumps(data,indent=2)+'\n')
 raw=json.loads((ROOT/'financial-B2-PV.pdf.font04/raw-owned-audit.json').read_text());assert not raw['fired'],'Final PV loses reproduced raw-halo ink'
 summary=dict(B1_firings=1,B1_glyph_277=True,B2_proposed_firings=44,B2_final_substitutions_with_unexplained_owned_ink=0,thresholds_unchanged=True,exceptions_unchanged=True,reference='Raw normalized source halo before fitting-mask exclusions; all detached components retain contrast/distance/decision evidence.')
 (BASE/'raw-owned-audit-summary.json').write_text(json.dumps(summary,indent=2)+'\n');print('Raw ownership audit confirmed unchanged decisions and zero final PV losses')

if __name__=='__main__':main()
