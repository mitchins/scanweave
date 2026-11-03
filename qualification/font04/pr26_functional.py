"""PR #26 functional checks for the repaired q3 build (PR3) (reviewer): extraction, native search, qpdf, OTS.

Compares each retained cover-2.0-ceiling-q3 output with its default. Never converts or generates.
"""
import json
from pathlib import Path
from qualification.font04.r2a_audit import extraction, fonts, command, ROOT, sha
from qualification.font04.functional_guard import native

L = ROOT / 'qualification/font04/local'
WORK = L / 'PR3/functional'


def check(name, default, candidate, pages):
    ext = {a: extraction(p) for a, p in (('off', default), ('q3', candidate))}
    search = {a: [native(p, i)[1] for i in range(pages)] for a, p in (('off', default), ('q3', candidate))}
    d = WORK / name
    d.mkdir(parents=True, exist_ok=True)
    qpdf = command([ROOT/'tools/dist/bin/qpdf', '--check', candidate]).decode()
    ots = []
    for digest, (data, _) in fonts(candidate).items():
        f = d / (digest + '.ttf')
        f.write_bytes(data)
        ots.append(command([ROOT/'tools/src/ots-bin/ots-9.3.0-Linux/ots-sanitize', f, str(f) + '.sanitized']).decode())
    eq = {k: ext['q3'][k] == ext['off'][k] for k in ext['q3']}
    ok = all(eq.values()) and search['q3'] == search['off'] and 'No syntax or stream encoding errors' in qpdf and bool(ots)
    return dict(name=name, candidate_sha256=sha(candidate), default_sha256=sha(default), extraction_equal=eq,
                native_search_equal=search['q3'] == search['off'], qpdf_ok='No syntax or stream encoding errors' in qpdf,
                ots_fonts=len(ots), pass_=ok)


def main():
    items = [(f'p2prime-{i}', L/f'P2prime/sheet-{i}-off.pdf', L/f'PR3/runs/p2prime-{i}.pdf', 1) for i in range(9)]
    items += [(f'p2pp-{i}', L/f'P2pp/sheet-{i}-off.pdf', L/f'PR3/runs/p2pp-{i}.pdf', 1) for i in range(9)]
    items += [(f'p2-{i}', L/f'P2/sheet-{i}-off.pdf', L/f'PR3/runs/p2-{i}.pdf', 1) for i in range(9)]
    items += [('mixed', L/'R2a/baseline/mixed-off.pdf', L/'PR3/runs/mixed.pdf', 2),
              ('financial', L/'R2a/baseline/financial-off.pdf', L/'PR3/runs/financial.pdf', 13)]
    results = []
    for args in items:
        results.append(check(*args))
        print(results[-1]['name'], results[-1]['pass_'], flush=True)
    out = dict(method='R2a extraction (Poppler default/layout/raw, PDFium, MuPDF), functional_guard native PDFium search per page, qpdf --check, OTS sanitize of every embedded font',
               results=results, pass_=all(r['pass_'] for r in results))
    (ROOT/'qualification/font04/pr26-functional.json').write_text(json.dumps(out, indent=1) + '\n')
    print('ALL PASS' if out['pass_'] else 'FAILURES')


if __name__ == '__main__':
    main()
