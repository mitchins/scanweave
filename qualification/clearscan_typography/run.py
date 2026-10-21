#!/usr/bin/env python3
"""Reproduce the integrated ClearScan runs; no oracle path is passed to the converter."""
import argparse, subprocess, sys, json, hashlib, gzip, os
from pathlib import Path

FINAL_PDF = 'final.pdf'
FINAL_JSON = 'final.json'

B=Path(__file__).resolve().parent; ROOT=B.parents[1]
ap=argparse.ArgumentParser();ap.add_argument('--dpi',nargs='+',type=int,choices=(300,600),default=[300,600]);ap.add_argument('--real',action='store_true');ap.add_argument('--measure',action='store_true');a=ap.parse_args()
def call(cmd,log,env=None):
 with log.open('w') as f:subprocess.run(list(map(str,cmd)),cwd=ROOT,stdout=f,stderr=subprocess.STDOUT,env=env,check=True)
call(['cargo','build','--release','-p','scanweave-cli'],B/'reproduce-build.log')
for dpi in a.dpi:
 d=B/str(dpi);d.mkdir(exist_ok=True)
 cmd=['/usr/bin/time','-v','-o',d/'final-time.txt',ROOT/'target/release/scanweave-cli','build','--bundle',ROOT/f'qualification/experiments/m1g/fixture/dpi{dpi}/input/document.json','--profile','clearscan','--output',d/FINAL_PDF,'--report',d/FINAL_JSON]
 call(cmd,d/'final.log')
 if a.measure:
  for arm in ['adobe','previous','final']:call([sys.executable,B/'compare.py',dpi,arm,d/(arm+'.pdf')],d/(arm+'-metrics.log'))
  call([sys.executable,B/'audit.py',dpi,'final',d/FINAL_PDF,'--report',d/FINAL_JSON],d/'final-audit.log')
  call([sys.executable,B/'stages.py',dpi,'final',d/FINAL_PDF,d/FINAL_JSON],d/'final-stages.log')
  env=dict(os.environ,SCANWEAVE_TYPOGRAPHY_DPI=str(dpi),SCANWEAVE_TYPOGRAPHY_ARM='final')
  call([sys.executable,B/'geometry.py'],d/'final-geometry.log',env)
  call([sys.executable,B/'context.py',dpi,'final'],d/'final-context.log')
if a.real:
 call([sys.executable,B/'real/convert.py','final','--region-ocr'],B/'real/final.log')
 if a.measure:
  call([sys.executable,B/'real/evaluate.py','final'],B/'real/final-evaluate.log')
  call([sys.executable,B/'real/resources.py'],B/'real/resources.log')
if a.measure:
 call([sys.executable,B/'summarize.py'],B/'scorecard.log')
 call([sys.executable,B/'text_order.py'],B/'text-order.log')
print('PDFs and full reports are in',B)
