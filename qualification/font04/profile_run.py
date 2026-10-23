"""Sample Linux process-tree RSS/PSS alongside GNU-time-compatible run logs."""
from pathlib import Path
import datetime,json,os,resource,subprocess,sys,time

def tree(pid):
    seen=set();todo=[pid]
    while todo:
        p=todo.pop()
        if p in seen:continue
        seen.add(p)
        try:
            for task in Path(f'/proc/{p}/task').iterdir():
                try:todo.extend(map(int,(task/'children').read_text().split()))
                except (FileNotFoundError,ProcessLookupError):pass
        except (FileNotFoundError,ProcessLookupError):pass
    return seen

def memory(pid):
    try:
        fields={line.split(':',1)[0]:int(line.split()[1]) for line in Path(f'/proc/{pid}/smaps_rollup').read_text().splitlines()[1:] if ':' in line}
        return fields.get('Rss',0),fields.get('Pss',0)
    except (FileNotFoundError,ProcessLookupError,PermissionError):return 0,0

def main():
    output=Path(sys.argv[1]);command=sys.argv[2:];start=time.monotonic();utc=datetime.datetime.now(datetime.timezone.utc).isoformat();p=subprocess.Popen(command);rss=pss=processes=0;samples=0
    while p.poll() is None:
        children=tree(p.pid);values=[memory(pid) for pid in children];rss=max(rss,sum(v[0] for v in values));pss=max(pss,sum(v[1] for v in values));processes=max(processes,len(children));samples+=1;time.sleep(.5)
    code=p.wait();usage=resource.getrusage(resource.RUSAGE_CHILDREN)
    result=dict(command=command,returncode=code,utc_start=utc,wall_seconds=time.monotonic()-start,user_seconds=usage.ru_utime,system_seconds=usage.ru_stime,max_single_process_rss_kib=usage.ru_maxrss,sampled_peak_tree_rss_kib=rss,sampled_peak_tree_pss_kib=pss,sampling_interval_seconds=.5,samples=samples,max_processes=processes,cpu_affinity_count=len(os.sched_getaffinity(0)),measurement='RSS sums include shared pages repeatedly; summed PSS apportions shared pages. Sampled peaks have 0.5s temporal resolution. Runs share a machine with other discovery work; no isolated performance claim.')
    output.write_text(json.dumps(result,indent=2)+'\n');sys.exit(code)

if __name__=='__main__':main()
