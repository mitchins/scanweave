from pathlib import Path
import sys,subprocess,re,json
lcov=Path(sys.argv[1]);cov={};name=None
for line in lcov.read_text().splitlines():
 if line.startswith('SF:'):name=line[3:];cov.setdefault(name,{})
 elif line.startswith('DA:') and name:
  n,c,*_=line[3:].split(',');cov[name][int(n)]=int(c)
changed={};file=None;new=None
for line in subprocess.check_output(['git','diff','--no-ext-diff','--unified=0','HEAD','--','crates/scanweave-io/src/convert.rs','crates/scanweave-io/src/document.rs','crates/scanweave-io/src/page_pdf.rs','probes/m0-font-pdf/src/lib.rs'],text=True).splitlines():
 if line.startswith('+++ b/'):file=line[6:];changed.setdefault(file,set());new=None
 elif line.startswith('@@'):
  m=re.search(r'\+(\d+)(?:,(\d+))?',line);new=int(m.group(1)) if m else None
 elif new is not None and line.startswith('+') and not line.startswith('+++'):changed[file].add(new);new+=1
 elif new is not None and line.startswith(' '):new+=1
rows=[]
for file,lines in changed.items():
 matches=[v for k,v in cov.items() if k.endswith('/'+file)]; counts={n:max((m.get(n,0) for m in matches),default=0) for n in lines if any(n in m for m in matches)};r={'file':file,'executable_changed_lines':len(counts),'covered_changed_lines':sum(v>0 for v in counts.values()),'uncovered':[n for n,v in sorted(counts.items()) if not v]};rows.append(r)
total=sum(x['executable_changed_lines'] for x in rows);hit=sum(x['covered_changed_lines'] for x in rows);out={'files':rows,'covered':hit,'total':total,'percentage':100*hit/total if total else None,'note':'Local diff-line approximation, not the SonarCloud new-code metric.'};print(json.dumps(out,indent=2));Path('/data/coding/scanweave/qualification/acr06/ink37c/coverage-new.json').write_text(json.dumps(out,indent=2)+'\n')
