"""Standalone scientific plot from the measured B1 frontier JSON."""
from pathlib import Path
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    data=json.loads(Path('qualification/font04/reuse-fidelity-frontier.json').read_text());points=data['points'];fig,axes=plt.subplots(1,2,figsize=(11,4.5))
    baseline=json.loads(Path('qualification/font04/checkpoint-B1.json').read_text())['source_error']
    for ax,engine in zip(axes,['pdfium','poppler']):
        for method in ['star','complete','cover']:
            rows=[r for r in points if r['grouping']==method];x=[-r['program_accounting']['net']for r in rows];y=[r['native_source'][engine]['error']['mean']for r in rows];ax.plot(x,y,'.-',label=method)
            for r,xx,yy in zip(rows,x,y):ax.annotate(str(r['error_scale']),(xx,yy),xytext=(2,2),textcoords='offset points',fontsize=7)
        ax.axhline(baseline[engine]['baseline']['error']['mean'],color='black',linestyle='--',linewidth=1,label='default')
        selected=next(r for r in points if r['grouping']=='star'and r['error_scale']==1.);ax.scatter([-selected['program_accounting']['net']],[selected['native_source'][engine]['error']['mean']],marker='*',s=140,color='black',zorder=5,label='selected')
        ax.set_title(engine);ax.set_xlabel('Net programs removed (retired − added)');ax.set_ylabel('Native source coverage error');ax.grid(alpha=.2);ax.legend(fontsize=8)
    fig.suptitle('FONT-04 B1: economy / fidelity frontier (e only)');fig.text(.5,.015,'Labels = noise-floor multiplier. P3 has no pristine reference. Material-defect judgments remain sealed/pending.',ha='center',fontsize=8);fig.tight_layout(rect=(0,.04,1,.94));root=Path('qualification/font04/local/frontier');fig.savefig(root/'frontier.png',dpi=180);fig.savefig(root/'frontier.svg');plt.close(fig)

if __name__=='__main__':main()
