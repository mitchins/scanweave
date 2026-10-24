"""Summarize unmodified LLVM LCOV against added Rust source lines on main."""
import json,re,subprocess
from pathlib import Path
from qualification.font04.freeze_method import BASE,write


def main():
    root=Path('/tmp/scanweave-font04-product');records={};name=None
    for line in (BASE/'local/R1-coverage-final.lcov').read_text().splitlines():
        if line.startswith('SF:'):name=line[3:];records.setdefault(name,{})
        elif line.startswith('DA:'):
            number,hits=map(int,line[3:].split(',')[:2]);records[name][number]=max(records[name].get(number,0),hits)
    modules=[];covered=total=0
    for name,rows in records.items():
        if '/glyph_sharing/'in name or name.endswith('/src/glyph_sharing.rs'):
            h=sum(v>0 for v in rows.values());n=len(rows);modules.append(dict(file=str(Path(name).relative_to(root)),covered=h,total=n,percent=100*h/n));covered+=h;total+=n
    added={};current=None
    for line in subprocess.check_output(['git','-C',str(root),'diff','--unified=0','origin/main..HEAD','--','crates'],text=True).splitlines():
        if line.startswith('+++ b/'):current=line[6:]
        elif line.startswith('@@'):
            match=re.search(r'\+(\d+)(?:,(\d+))?',line);start=int(match[1]);count=int(match[2]or 1);added.setdefault(current,set()).update(range(start,start+count))
    files=[];hits=count=0
    for name,rows in records.items():
        try:relative=str(Path(name).relative_to(root))
        except ValueError:continue
        if '/src/'not in relative:continue
        points=added.get(relative,set())&rows.keys()
        if points:
            h=sum(rows[i]>0 for i in points);n=len(points);files.append(dict(file=relative,covered=h,total=n,percent=100*h/n,uncovered_lines=sorted(i for i in points if rows[i]==0)));hits+=h;count+=n
    result=dict(schema='font04-native-new-code-coverage-v1',product_head=subprocess.check_output(['git','-C',str(root),'rev-parse','HEAD'],text=True).strip(),runtime_build=json.loads((BASE/'r1-native-build.json').read_text())['product_commit'],tool='cargo-llvm-cov 0.9.1; rustc 1.99.0; release LLVM instrumentation',new_native_modules=dict(covered=covered,total=total,percent=100*covered/total,files=modules),all_added_rust_source_executable_lines=dict(covered=hits,total=count,percent=100*hits/count,files=files),sonar_gate=dict(name='Sonar way',new_coverage_minimum=80,meets_local_line_measurement=100*hits/count>=80,server_quality_gate='PENDING; no product PR opened; no gate or exclusion changed'),lcov='qualification/font04/local/R1-coverage-final.lcov')
    write(BASE/'r1-coverage.json',result);print('Added Rust source executable lines:',hits,count,100*hits/count);assert hits/count>=.8


if __name__=='__main__':main()
